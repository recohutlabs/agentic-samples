"""Security/scope/precision tests for the real SQLite query capability."""
import pytest
from store import Store
from contract_query import ContractQuery,QueryRejected

@pytest.fixture
def product(tmp_path):
    store=Store(tmp_path/'product.db')
    for id,total,currency in [('first','0.10','INR'),('second','0.20','INR'),('third','10.00','USD')]:
        store.save_contract(id,{'contract_id':id.upper(),'contract_type':'service_agreement','customer':'Example','vendor':'Supplier','end_date':'2027-03-31','fees_and_pricing':{'currency':currency,'stated_total':total,'fees':[{'amount':total,'frequency':'annual'}]}},id+'.pdf','sha')
    return store

def test_complete_decimal_aggregation_and_json1(product):
    q=ContractQuery(product.path)
    rows=q.query("SELECT json_extract(parsed,'$.fees_and_pricing.currency') currency, decimal_sum(json_extract(parsed,'$.fees_and_pricing.stated_total')) total, COUNT(*) contracts FROM contracts GROUP BY currency")
    assert rows['complete'] and rows['scope_count']==3
    assert rows['rows']==[{'currency':'INR','total':'0.30','contracts':2},{'currency':'USD','total':'10.00','contracts':1}]
    assert q.query("SELECT c.id,json_extract(j.value,'$.frequency') frequency FROM contracts c,json_each(json_extract(c.parsed,'$.fees_and_pricing.fees')) j")['row_count']==3

def test_selected_scope_cannot_escape(product):
    q=ContractQuery(product.path,'first')
    assert q.query('SELECT id FROM contracts WHERE id != \'first\'')['rows']==[]
    assert q.query('SELECT id FROM contracts UNION SELECT id FROM contracts')['rows']==[{'id':'first'}]
    assert q.query('SELECT COUNT(*) count FROM contracts')['rows']==[{'count':1}]
    with pytest.raises(QueryRejected):q.query('SELECT id FROM main.contracts')

@pytest.mark.parametrize('sql',[
 'DELETE FROM contracts','UPDATE contracts SET customer=\'evil\'','INSERT INTO contracts(id) VALUES(\'evil\')',
 'DROP TABLE contracts','ATTACH DATABASE \':memory:\' AS other','PRAGMA table_info(contracts)',
 'SELECT * FROM jobs','SELECT * FROM sqlite_master','SELECT * FROM main.contracts',
 'SELECT load_extension(\'evil\') FROM contracts',"SELECT SUM(CAST(json_extract(parsed,'$.fees_and_pricing.stated_total') AS REAL)) FROM contracts",
 'WITH contracts AS (SELECT * FROM main.contracts) SELECT * FROM contracts',
 'EXPLAIN SELECT * FROM contracts',
 "SELECT decimal_sum('1e100000000') FROM contracts",
 'SELECT id FROM contracts LIMIT 1','SELECT 1','SELECT id FROM contracts; DELETE FROM contracts',
])
def test_forbidden_operations(sql,product):
    with pytest.raises(QueryRejected):ContractQuery(product.path).query(sql)
    assert product.rows('SELECT COUNT(*) n FROM contracts')[0]['n']==3

def test_oversized_result_returns_no_subset(product,monkeypatch):
    import contract_query
    monkeypatch.setattr(contract_query,'MAX_ROWS',1)
    q=ContractQuery(product.path)
    with pytest.raises(QueryRejected,match='result_row_limit'):q.query('SELECT id FROM contracts')
    assert q.evidence[-1]['complete'] is False
    assert q.evidence[-1]['row_count']==0

def test_vm_budget_and_byte_limit(product,monkeypatch):
    import contract_query
    monkeypatch.setattr(contract_query,'MAX_BYTES',10)
    with pytest.raises(QueryRejected,match='result_byte_limit'):ContractQuery(product.path).query('SELECT parsed FROM contracts')
    monkeypatch.setattr(contract_query,'MAX_BYTES',60000)
    array='['+','.join('1' for _ in range(500))+']'
    with pytest.raises(QueryRejected):ContractQuery(product.path).query("SELECT COUNT(*) FROM contracts,json_each('"+array+"') a,json_each('"+array+"') b")

def test_query_call_budget(product,monkeypatch):
    import contract_query
    monkeypatch.setattr(contract_query,'MAX_QUERIES',1)
    q=ContractQuery(product.path);q.query('SELECT COUNT(*) FROM contracts')
    with pytest.raises(QueryRejected,match='query_budget_exhausted'):q.query('SELECT COUNT(*) FROM contracts')
