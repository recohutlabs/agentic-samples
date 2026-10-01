"""PDF-to-contract orchestration: classify, extract, then verify before returning JSON."""
from pathlib import Path
from progress import step, log
from pydantic import BaseModel
from agents.classifier import classify
from agents.extractor import extract_candidate
from agents.verifier import verify_contract
from config import load_openai_config
from registry import CONTRACT_TYPES
from tools.pdf_reader import read_contract_text

def extract(pdf: Path, observer=None) -> BaseModel:
    """Read once and return the verified schema; any stage failure stops output."""
    emit = observer or (lambda stage, message: None)
    emit('reading', 'Reading all PDF pages within bounded text limits.')
    with step('Reading PDF', 'read_contract_text'):
        text = read_contract_text(pdf)
    log(f'PDF loaded — {len(text):,} text characters')
    log('Function: load_openai_config()', debug=True)
    key, model = load_openai_config()
    emit('classification', 'Model classification started.')
    with step('Classification', 'classify'):
        kind = classify(text, key, model, CONTRACT_TYPES)
    if kind not in CONTRACT_TYPES:
        raise ValueError(f'Contract type is {kind}; supported types are {", ".join(CONTRACT_TYPES)}.')
    log(f'Contract type — {kind}')
    definition = CONTRACT_TYPES[kind]
    emit('extraction', 'Model structured extraction started.')
    with step('Extraction', 'extract_candidate'):
        candidate = extract_candidate(text, kind, definition, key, model)
    emit('verification', 'Model source verification started.')
    with step('Verification', 'verify_contract'):
        verified = verify_contract(text, candidate, kind, definition, key, model)
    return verified
