"""Authenticated asynchronous PDF processing API over one product-owned database."""
import asyncio
import hashlib
import hmac
import json
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from store import Store, ROOT, DEFAULT_DB, now
from workflow import extract
from chat import answer_contracts
from contract_query import ContractQuery
from progress import progress_session
from config import load_openai_config
from tools.pdf_reader import read_contract_text, MAX_PDF_BYTES

class Process(BaseModel):
    model_config=ConfigDict(extra='forbid')
    fixture:str=Field(min_length=1,max_length=160)
    operation_id:str=Field(min_length=1,max_length=128)
class Chat(BaseModel):
    model_config=ConfigDict(extra='forbid')
    message:str=Field(min_length=1,max_length=4000)
    contract_id:str|None=None
    conversation_id:str|None=Field(default=None,max_length=128)

def create_app(*, db_path=None, token=None, session_id=None, processor=None, chatter=None):
    """Dependency injection is for focused tests; live defaults always use real model calls."""
    store=Store(db_path or os.getenv('CONTRACT_DB_PATH') or DEFAULT_DB)
    secret=token if token is not None else os.getenv('CONTRACT_SESSION_TOKEN','')
    process_contract=processor or extract;chat_contracts=chatter or answer_contracts
    pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='contract-processing')
    @asynccontextmanager
    async def lifespan(app):
        yield
        pool.shutdown(wait=False,cancel_futures=True)
    app=FastAPI(title='Contract Processing Agent',lifespan=lifespan)
    app.state.store=store
    app.add_middleware(CORSMiddleware,allow_origin_regex=r'https?://(?:localhost|127\.0\.0\.1)(?::\d+)?',allow_methods=['GET','POST','OPTIONS'],allow_headers=['Authorization','Content-Type','X-Demo-Token'])
    @app.middleware('http')
    async def auth(request:Request,call_next):
        if request.url.path not in ('/health','/v1/health','/v1/capabilities','/capabilities') and request.method!='OPTIONS':
            from fastapi.responses import JSONResponse
            supplied=request.headers.get('authorization','').removeprefix('Bearer ') or request.headers.get('x-demo-token','')
            if not secret:return JSONResponse(status_code=503,content={'detail':'Runtime access token is not configured.'})
            if not hmac.compare_digest(secret,supplied):return JSONResponse(status_code=401,content={'detail':'Authentication required.'})
        return await call_next(request)
    @app.get('/health')
    def health():return {'status':'ok','runtime':'local','session_id':session_id or os.getenv('CONTRACT_SESSION_ID'),'runtime_generation':os.getenv('CONTRACT_RUNTIME_GENERATION')}
    @app.get('/capabilities')
    def capabilities():return {**health(),'capabilities':['pdf-processing','shared-contracts','model-chat'],'api_prefix':'/v1','authentication':'bearer'}
    @app.get('/readiness')
    def readiness():
        try:key,model=load_openai_config()
        except ValueError:raise HTTPException(503,'Model credentials are not configured.')
        return {'status':'ready','model':model,'database':'shared-product','authentication':True}
    @app.get('/fixtures')
    def fixtures():return {'fixtures':[{'id':p.name,'name':p.name,'size_bytes':p.stat().st_size} for p in sorted((ROOT/'data').glob('*.pdf'))]}
    def run_job(id,pdf,name,sha,temporary):
        try:
            store.update(id,'processing');store.event(id,'processing','Classification, extraction and verification started.')
            with progress_session(debug=True,observer=lambda message:store.event(id,'activity',message)):
                result=process_contract(pdf)
            data=result.model_dump(mode='json')
            store.save_contract(id,data,name,sha);store.update(id,'completed',id);store.event(id,'completed','Verified contract persisted.')
        except Exception:
            store.update(id,'failed',error={'code':'processing_failed','message':'Contract processing failed. Check model availability or PDF support, then use a new operation ID to retry.'})
            store.event(id,'failed','Processing failed; no contract was stored.')
        finally:
            if temporary:pdf.unlink(missing_ok=True)
    def submit(pdf,name,operation,temporary=False):
        sha=hashlib.sha256(pdf.read_bytes()).hexdigest();fingerprint=hashlib.sha256((name+sha).encode()).hexdigest()
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT id,fingerprint FROM jobs WHERE operation_id=?',(operation,)).fetchone()
            if old:
                if temporary:pdf.unlink(missing_ok=True)
                if old['fingerprint']!=fingerprint:raise HTTPException(409,'Operation ID already refers to different input.')
                return store.job(old['id'])
            active=db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','processing')").fetchone()[0]
            if active>=4:
                if temporary:pdf.unlink(missing_ok=True)
                raise HTTPException(429,'Processing capacity reached; retry after current jobs finish.')
            id=str(uuid.uuid4());stamp=now()
            db.execute('INSERT INTO jobs(id,operation_id,fingerprint,status,source_name,contract_id,error,created_at,updated_at,owner_pid) VALUES(?,?,?,?,?,?,?,?,?,?)',(id,operation,fingerprint,'queued',name,None,None,stamp,stamp,os.getpid()))
        store.event(id,'queued','PDF accepted for processing.')
        pool.submit(run_job,id,pdf,name,sha,temporary)
        return store.job(id)
    @app.post('/process',status_code=202)
    def process(body:Process):
        pdf=ROOT/'data'/body.fixture
        if Path(body.fixture).name!=body.fixture or not pdf.is_file() or pdf.suffix!='.pdf':raise HTTPException(404,'Fixture not found.')
        return submit(pdf,pdf.name,body.operation_id)
    @app.post('/upload',status_code=202)
    async def upload(file:UploadFile=File(...),operation_id:str=Form(...,min_length=1,max_length=128)):
        name=Path(file.filename or '').name
        if not name.lower().endswith('.pdf'):raise HTTPException(415,'Upload a text-based PDF.')
        with tempfile.NamedTemporaryFile(suffix='.pdf',delete=False) as out:
            path=Path(out.name);size=0
            try:
                while chunk:=await file.read(65536):
                    size+=len(chunk)
                    if size>MAX_PDF_BYTES:raise HTTPException(413,'PDF exceeds 20 MB.')
                    out.write(chunk)
            except BaseException:path.unlink(missing_ok=True);raise
        try:
            await asyncio.to_thread(read_contract_text,path)
        except Exception:
            path.unlink(missing_ok=True);raise HTTPException(415,'Unsupported PDF; supply a complete text-based, unencrypted PDF within limits.')
        return submit(path,name,operation_id,True)
    @app.get('/jobs')
    def jobs(limit:int=Query(50,ge=1,le=100)):
        return {'jobs':[store.job(row['id']) for row in store.rows('SELECT id FROM jobs ORDER BY created_at DESC LIMIT ?',(limit,))]}
    @app.get('/jobs/{id}')
    def job(id:str):
        result=store.job(id)
        if not result:raise HTTPException(404,'Job not found.')
        return result
    @app.get('/jobs/{id}/events')
    def events(id:str):
        job(id)
        return {'events':store.rows('SELECT sequence,stage,message,created_at FROM events WHERE job_id=? ORDER BY sequence',(id,))}
    @app.get('/contracts')
    def contracts(limit:int=Query(50,ge=1,le=100)):
        return {'contracts':store.rows('SELECT id,contract_id,contract_type,customer,vendor,start_date,end_date,source_name,created_at FROM contracts ORDER BY created_at DESC LIMIT ?',(limit,))}
    @app.get('/contracts/{id}')
    def contract(id:str):
        rows=store.rows('SELECT * FROM contracts WHERE id=?',(id,))
        if not rows:raise HTTPException(404,'Contract not found.')
        return rows[0]
    @app.get('/conversations/{id}')
    def conversation(id:str):return {'conversation_id':id,'messages':store.rows('SELECT role,content,contract_id,created_at,metadata FROM messages WHERE conversation_id=? ORDER BY sequence',(id,))}
    @app.get('/conversations')
    def conversations():return {'conversations':store.rows('SELECT conversation_id,MAX(created_at) updated_at FROM messages GROUP BY conversation_id ORDER BY updated_at DESC LIMIT 50')}
    @app.post('/chat')
    async def chat(body:Chat):
        records=[contract(body.contract_id)] if body.contract_id else store.rows('SELECT * FROM contracts ORDER BY created_at DESC LIMIT 101' if chatter else 'SELECT id FROM contracts LIMIT 1')
        if not records:raise HTTPException(422,'Process a contract before asking questions.')
        conversation_id=body.conversation_id or str(uuid.uuid4())
        history=store.rows('SELECT role,content FROM messages WHERE conversation_id=? ORDER BY sequence DESC LIMIT 6',(conversation_id,))[::-1]
        try:answer=await asyncio.to_thread(chat_contracts,body.message,records if chatter else ContractQuery(store.path,body.contract_id),history)
        except ValueError:raise HTTPException(422,'Contract evidence exceeds limits or the answer failed validation. Select a contract and retry.')
        except Exception:raise HTTPException(503,'Model chat is unavailable; no answer was generated.')
        store.message(conversation_id,'user',body.message,body.contract_id)
        store.message(conversation_id,'assistant',answer['answer'],body.contract_id,{key:answer[key] for key in ('model','query_count','query_evidence') if key in answer})
        return {**answer,'conversation_id':conversation_id}
    for route in list(app.routes):
        if hasattr(route,'methods') and route.path not in ('/openapi.json','/docs','/docs/oauth2-redirect','/redoc'):
            app.add_api_route('/v1'+route.path,route.endpoint,methods=list(route.methods),status_code=route.status_code)
    return app

def app():
    """Uvicorn/demo-manager factory; secrets and ports remain runtime-owned."""
    return create_app()
