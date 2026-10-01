"""Shared contract ingestion tolerates additive columns owned by other writers."""
from store import Store


def test_save_contract_preserves_additive_ingestion_metadata(tmp_path):
    path = tmp_path / 'product.db'
    first = Store(path)
    first.save_contract('prior', {'contract_id': 'PRIOR'}, 'prior.pdf', 'prior-hash')
    with first.connect() as db:
        db.execute('ALTER TABLE contracts ADD COLUMN ingestion_metadata TEXT')
        db.execute('UPDATE contracts SET ingestion_metadata=? WHERE id=?',
                   ('{"owner":"external-ingestion"}', 'prior'))
    # Reopening must preserve the external schema and its existing records.
    second = Store(path)
    data = {'contract_id': 'NEW', 'contract_type': 'employment_contract',
            'employer': 'Example employer', 'employee': 'Example employee'}
    second.save_contract('new', data, 'new.pdf', 'new-hash')
    rows = {row['id']: row for row in first.rows('SELECT * FROM contracts')}
    assert rows['prior']['ingestion_metadata'] == '{"owner":"external-ingestion"}'
    assert rows['prior']['parsed'] == {'contract_id': 'PRIOR'}
    assert rows['new']['ingestion_metadata'] is None
    assert rows['new']['parsed'] == data
    assert rows['new']['customer'] == 'Example employer'
    assert rows['new']['vendor'] == 'Example employee'
