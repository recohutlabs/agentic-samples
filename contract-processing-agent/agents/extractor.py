"""Extract a candidate using the selected registered family schema."""
from pydantic import BaseModel
from registry import ContractDefinition
from agents.factory import make_agent
from agents.runner import require_model

def extract_candidate(text: str, kind: str, definition: ContractDefinition, key: str, model: str) -> BaseModel:
    """Read all supplied text and return a validated candidate; missing output fails."""
    return require_model(
        make_agent(key, model, definition.instructions, 14000),
        f'Extract this {kind} from the PDF:\n\n{text}', definition.schema,
        {'turns': 3, 'output_tokens': 42000, 'total_tokens': 120000},
        'Extraction returned no structured result.',
    )
