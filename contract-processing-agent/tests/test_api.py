"""Focused API contracts; injected extractors verify host behavior without invented model proof."""
import time
from fastapi.testclient import TestClient
from pydantic import BaseModel
from api import create_app

class Contract(BaseModel):
    contract_id:str='TEST-001'
    contract_type:str='service_agreement'
    customer:str='Customer'
    vendor:str='Vendor'
    start_date:str='2026-01-01'
    end_date:str='2026-12-31'

def client(path,processor=lambda _:Contract(),token='secret'):
    return TestClient(create_app(db_path=path,token=token,processor=processor,chatter=lambda *args:{'answer':'Customer contract TEST-001.','contract_ids':[args[1][0]['id']],'model':'test-double'}))
HEADERS={'Authorization':'Bearer secret'}
FIXTURE='PRO-003-peoplespring-store-staffing-services-master-agreement.pdf'
def wait(c,id):
    for _ in range(100):
        row=c.get('/v1/jobs/'+id,headers=HEADERS).json()
        if row['status'] in ('completed','failed'):return row
        time.sleep(.01)
    raise AssertionError('Job did not terminate')

def test_shared_sessions_idempotency_and_chat(tmp_path):
    path=tmp_path/'product.db'
    with client(path) as a,client(path) as b:
        assert a.get('/v1/fixtures').status_code==401
        body={'fixture':FIXTURE,'operation_id':'one'}
        row=a.post('/v1/process',json=body,headers=HEADERS).json();done=wait(a,row['id'])
        assert done['status']=='completed'
        assert b.get('/v1/contracts/'+done['contract_id'],headers=HEADERS).json()['parsed']['contract_id']=='TEST-001'
        assert b.post('/v1/process',json=body,headers=HEADERS).json()['id']==row['id']
        assert len(b.get('/v1/contracts',headers=HEADERS).json()['contracts'])==1
        assert b.post('/v1/process',json={**body,'fixture':'FAC-001-cleaning.pdf'},headers=HEADERS).status_code==409
        answer=b.post('/v1/chat',json={'message':'Who is the customer?','contract_id':row['id']},headers=HEADERS).json()
        assert len(a.get('/v1/conversations/'+answer['conversation_id'],headers=HEADERS).json()['messages'])==2
        assert a.get('/v1/jobs/'+row['id']+'/events',headers=HEADERS).json()['events'][-1]['stage']=='completed'

def test_sanitized_failure_and_unsupported_upload(tmp_path):
    def failed(_):raise RuntimeError('SECRET_PROVIDER_RESPONSE')
    with client(tmp_path/'product.db',failed) as c:
        assert c.post('/v1/upload',files={'file':('secret.pdf',b'%PDF invalid','application/pdf')},data={'operation_id':'invalid'},headers=HEADERS).status_code==415
        row=c.post('/v1/process',json={'fixture':FIXTURE,'operation_id':'fail'},headers=HEADERS).json()
        result=wait(c,row['id'])
        assert result['status']=='failed' and 'SECRET' not in str(result)
        assert c.get('/v1/contracts',headers=HEADERS).json()['contracts']==[]
        assert c.post('/v1/process',json={'fixture':'../../.env','operation_id':'bad'},headers=HEADERS).status_code==404

def test_missing_token_fails_closed(tmp_path):
    with client(tmp_path/'product.db',token='') as c:
        assert c.get('/health').status_code==200
        assert c.get('/contracts').status_code==503

def test_interrupted_job_is_terminal_when_owner_died(tmp_path):
    from store import Store,now
    path=tmp_path/'product.db';store=Store(path)
    with store.connect() as db:
        db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?)',('orphan','orphan-operation','sha','processing','input.pdf',None,None,now(),now(),2147483647))
    recovered=Store(path).job('orphan')
    assert recovered['status']=='failed'
    assert recovered['error']['code']=='runtime_interrupted'

def test_function_progress_is_durable_without_document_payload(tmp_path):
    from progress import step,log
    def instrumented(_):
        with step('Classification','classify'):
            log('Contract type — service_agreement')
        with step('Extraction','extract_candidate'):pass
        with step('Verification','verify_contract'):pass
        return Contract()
    with client(tmp_path/'product.db',instrumented) as c:
        row=c.post('/process',json={'fixture':FIXTURE,'operation_id':'progress'},headers=HEADERS).json()
        assert wait(c,row['id'])['status']=='completed'
        messages=[e['message'] for e in c.get('/jobs/'+row['id']+'/events',headers=HEADERS).json()['events']]
        for stage in ('Classification','Extraction','Verification'):
            assert stage+' started' in messages
            assert any(m.startswith(stage+' completed') for m in messages)
        assert 'Function: classify()' in messages
