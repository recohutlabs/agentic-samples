"""Re-read the source and correct a candidate without expanding the public JSON schema."""
import json
from pydantic import BaseModel
from registry import ContractDefinition
from prompts.verification import VERIFICATION_INSTRUCTIONS
from agents.factory import make_agent
from agents.runner import require_model

def verify_contract(text: str, candidate: BaseModel, kind: str, definition: ContractDefinition, key: str, model: str) -> BaseModel:
    """Return source-supported corrections; provider/validation failure stops the workflow."""
    payload = json.dumps({'contract_type': kind, 'pdf_text': text,
                          'candidate': candidate.model_dump(mode='json')}, ensure_ascii=False)
    verified = require_model(
        make_agent(key, model, VERIFICATION_INSTRUCTIONS + definition.instructions, 14000),
        'Verify and correct the candidate using this source payload:\n' + payload,
        definition.schema,
        {'turns': 3, 'output_tokens': 42000, 'total_tokens': 120000},
        'Verification returned no structured result; no final contract was produced.',
    )
    if getattr(verified, 'contract_type', None) != kind:
        raise ValueError('Verification changed the selected contract type.')
    return verified
