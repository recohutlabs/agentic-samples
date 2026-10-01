"""Product-owned SQLite state shared by all runtime sessions; no session-scoped data."""
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / 'data' / 'contracts.db'

def now():
    return datetime.now(timezone.utc).isoformat()

class Store:
    """Short atomic connections own jobs, events, extracted contracts and chat history."""
    def __init__(self, path=DEFAULT_DB):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, operation_id TEXT UNIQUE, fingerprint TEXT NOT NULL, status TEXT NOT NULL, source_name TEXT, contract_id TEXT, error TEXT, created_at TEXT, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS contracts(id TEXT PRIMARY KEY, contract_id TEXT, contract_type TEXT, customer TEXT, vendor TEXT, start_date TEXT, end_date TEXT, source_name TEXT, source_sha256 TEXT, parsed TEXT NOT NULL, created_at TEXT);
            CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, stage TEXT, message TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS messages(sequence INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL, role TEXT, content TEXT, contract_id TEXT, created_at TEXT);
            ''')
            message_columns={row[1] for row in db.execute('PRAGMA table_info(messages)')}
            if 'metadata' not in message_columns:db.execute('ALTER TABLE messages ADD COLUMN metadata TEXT')
            columns={row[1] for row in db.execute('PRAGMA table_info(jobs)')}
            if 'owner_pid' not in columns:db.execute('ALTER TABLE jobs ADD COLUMN owner_pid INTEGER')
            for row in db.execute("SELECT id,owner_pid FROM jobs WHERE status IN ('queued','processing')").fetchall():
                if row['owner_pid'] is None:continue
                try:os.kill(row['owner_pid'],0)
                except ProcessLookupError:
                    db.execute("UPDATE jobs SET status='failed',error=?,updated_at=? WHERE id=?",(json.dumps({'code':'runtime_interrupted','message':'Processing runtime stopped before completion. Retry with a new operation ID.'}),now(),row['id']))
                except PermissionError:pass
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15); db.row_factory=sqlite3.Row
        return db
    def rows(self, sql, args=()):
        with self.connect() as db:
            rows=[dict(row) for row in db.execute(sql,args)]
        for row in rows:
            for field in ('parsed','error','metadata'):
                if field in row and row[field] is not None: row[field]=json.loads(row[field])
        return rows
    def job(self, id):
        rows=self.rows('SELECT * FROM jobs WHERE id=?',(id,))
        if not rows:return None
        row=rows[0];row.pop('fingerprint');row.pop('owner_pid',None);return row
    def event(self, id, stage, message):
        with self.connect() as db:db.execute('INSERT INTO events(job_id,stage,message,created_at) VALUES(?,?,?,?)',(id,stage,message,now()))
    def update(self,id,status,contract_id=None,error=None):
        with self.connect() as db:db.execute('UPDATE jobs SET status=?,contract_id=?,error=?,updated_at=? WHERE id=?',(status,contract_id,json.dumps(error) if error else None,now(),id))
    def save_contract(self,id,data,name,sha):
        with self.connect() as db:
            db.execute('INSERT INTO contracts VALUES(?,?,?,?,?,?,?,?,?,?,?)',(id,data.get('contract_id'),data.get('contract_type'),data.get('customer') or data.get('employer'),data.get('vendor') or data.get('employee'),data.get('start_date'),data.get('end_date'),name,sha,json.dumps(data),now()))
    def message(self,conversation,role,content,contract,metadata=None):
        with self.connect() as db:db.execute('INSERT INTO messages(conversation_id,role,content,contract_id,created_at,metadata) VALUES(?,?,?,?,?,?)',(conversation,role,content,contract,now(),json.dumps(metadata) if metadata else None))
