"""Read-only SQLite capability over a host-scoped view of the product contracts table.

The model controls SELECT expressions, never data scope, credentials, writes or limits.
Oversized results fail without rows; no partial page can masquerade as a complete sum.
"""
import hashlib
import json
import re
import sqlite3
from threading import Lock
from contextlib import closing
from decimal import Decimal, localcontext, InvalidOperation
from time import monotonic
from pathlib import Path

MAX_ROWS=100
MAX_BYTES=60_000
MAX_SQL_CHARS=6_000
MAX_SECONDS=2.0
MAX_QUERIES=8
FUNCTIONS={'count','min','max','coalesce','ifnull','nullif','lower','upper','length','trim','substr','replace','instr','abs','round','date','datetime','strftime','julianday','json_extract','json_type','json_array_length','json_valid','decimal_sum','decimal_avg'}

class QueryRejected(ValueError):
    """Typed host rejection; SQL and database payloads never enter provider error text."""
    def __init__(self,code):self.code=code;super().__init__(code)

class DecimalSum:
    """Exact decimal accumulation; floats/non-finite values fail instead of rounding money."""
    def __init__(self):self.value=Decimal(0);self.count=0
    def step(self,value):
        if value is None:return
        if isinstance(value,float):raise ValueError('Use source decimal text, not SQLite float casts.')
        text=str(value)
        if len(text)>128:raise ValueError('Decimal length limit.')
        number=Decimal(text)
        if not number.is_finite() or abs(number.as_tuple().exponent)>64 or abs(number.adjusted())>64:raise ValueError('Decimal precision limit.')
        with localcontext() as context:
            context.prec=max(60,max(self.value.adjusted(),number.adjusted())-min(self.value.as_tuple().exponent,number.as_tuple().exponent)+3);self.value+=number
        self.count+=1
    def finalize(self):return format(self.value,'f') if self.count else None

class DecimalAverage(DecimalSum):
    def finalize(self):
        if not self.count:return None
        with localcontext() as context:
            context.prec=60
            return format(self.value/Decimal(self.count),'f')

class ContractQuery:
    """One request's bounded SQL budget and evidence, scoped independently of model SQL."""
    def __init__(self,path,contract_id=None):
        self.path=Path(path).resolve();self.contract_id=contract_id;self.evidence=[];self.lock=Lock()
        with closing(self.connection()) as db:
            self.scope_count=db.execute('SELECT COUNT(*) FROM contracts').fetchone()[0]
        if contract_id and self.scope_count!=1:raise QueryRejected('contract_not_found')
    def connection(self):
        db=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True,timeout=2)
        db.row_factory=sqlite3.Row
        # TEMP view shadows the physical table. Authorizer allows underlying reads
        # only when SQLite identifies this exact host-owned view as their source.
        where=' WHERE id IS NOT NULL' if self.contract_id is None else " WHERE id='"+self.contract_id.replace("'","''")+"'"
        db.execute('CREATE TEMP VIEW contracts AS SELECT * FROM main.contracts'+where)
        # Initialize JSON1 table function before authorization denies schema writes.
        db.execute("SELECT value FROM json_each('[]')").fetchall()
        db.create_aggregate('decimal_sum',1,DecimalSum)
        db.create_aggregate('decimal_avg',1,DecimalAverage)
        return db
    def query(self,sql):
        """Serialize request-budget admission even if the model issues parallel tools."""
        with self.lock:return self._query(sql)
    def _query(self,sql):
        """Return complete bounded SELECT results or a typed rejection with zero rows."""
        if len(self.evidence)>=MAX_QUERIES:raise QueryRejected('query_budget_exhausted')
        record={'query_sha256':hashlib.sha256(str(sql).encode()).hexdigest(),'status':'rejected','row_count':0,'complete':False}
        self.evidence.append(record)
        if not isinstance(sql,str) or not 1<=len(sql)<=MAX_SQL_CHARS:
            record['error_code']='sql_length_limit';raise QueryRejected('sql_length_limit')
        # Reject explicit pagination/sampling and CTE name shadowing of the scoped view.
        lexical=re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|--[^\n]*|/\*.*?\*/",' ',sql,flags=re.S)
        if not re.match(r'^\s*SELECT\b',lexical,re.I):
            record['error_code']='select_required';raise QueryRejected('select_required')
        if re.search(r'\bLIMIT\b',lexical,re.I):
            record['error_code']='partial_query_forbidden';raise QueryRejected('partial_query_forbidden')
        if re.search(r'\bWITH\b',lexical,re.I):
            record['error_code']='cte_forbidden';raise QueryRejected('cte_forbidden')
        db=self.connection()
        db.execute('BEGIN')
        scope_count=db.execute('SELECT COUNT(*) FROM contracts').fetchone()[0]
        read_source=False;started=monotonic();ticks=0
        def authorize(action,a,b,database,source):
            nonlocal read_source
            if action==sqlite3.SQLITE_SELECT:return sqlite3.SQLITE_OK
            if action==sqlite3.SQLITE_READ:
                if a=='contracts' and ((database=='main' and source=='contracts') or database=='temp'):
                    read_source=True;return sqlite3.SQLITE_OK
                if a=='json_each' and database=='main':return sqlite3.SQLITE_OK
            if action==sqlite3.SQLITE_FUNCTION and (b or a or '').lower() in FUNCTIONS:return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        def budget():
            nonlocal ticks
            ticks+=1
            return int(monotonic()-started>MAX_SECONDS or ticks>250)
        db.set_authorizer(authorize);db.set_progress_handler(budget,1000)
        try:
            cursor=db.execute(sql)
            rows=[dict(row) for row in cursor.fetchmany(MAX_ROWS+1)]
            if not read_source:raise QueryRejected('source_read_required')
            if len(rows)>MAX_ROWS:raise QueryRejected('result_row_limit')
            data=json.dumps(rows,ensure_ascii=False)
            if len(data.encode())>MAX_BYTES:raise QueryRejected('result_byte_limit')
            record.update(status='completed',row_count=len(rows),complete=True,scope_count=scope_count,result_sha256=hashlib.sha256(data.encode()).hexdigest(),seconds=round(monotonic()-started,4))
            return {'rows':rows,'row_count':len(rows),'complete':True,'scope_count':scope_count,'scope':'selected_contract' if self.contract_id else 'all_persisted_contracts','query_sha256':record['query_sha256']}
        except QueryRejected as error:
            record['error_code']=error.code;raise
        except sqlite3.Error:
            record['error_code']='query_rejected';raise QueryRejected('query_rejected') from None
        finally:db.close()

SCHEMA_DESCRIPTION='''Table contracts (host-scoped, read-only):
id TEXT primary key (stored record UUID, use for citations); contract_id TEXT (source reference, may be null); contract_type TEXT (service_agreement or employment_contract); customer TEXT/vendor TEXT (service customer/vendor, or employment employer/employee projected for listing only); start_date/end_date TEXT ISO date or null (contract commencement/controlling expiry, not actual renewal/termination events); source_name TEXT; source_sha256 TEXT; created_at TEXT UTC persistence timestamp; parsed TEXT complete JSON conforming to the supplied family schemas. Use JSON1 json_extract(parsed,'$.path') and json_each(json_extract(parsed,'$.list')). JSON null or absent is unknown, not zero. Query nested employment employer/employee fields for employment semantics. Money is decimal TEXT; decimal_sum/decimal_avg perform decimal aggregation, SUM/AVG/TOTAL are forbidden. Aggregate stated_total only when the question asks for stated contract totals, group by currency, expose unknown totals separately. Fee line amounts are rates/optional/fixed commitments: group by currency, frequency, kind, basis and period and do not treat their sum as whole-contract spending or actual payments. Fees may already incorporate amendments. No actual payments, deliveries, renewals, execution authentication or performance events exist. Counts use COUNT(*) over full scoped table. No WITH/CTEs or LIMIT/pagination: narrow filters or aggregate; >100 output rows or >60k bytes returns no partial rows. Each query has 2 sec/250k VM instruction budget; at most 8 calls per chat request. SQL reads may reference only contracts view and JSON1 json_each.''' 
