"""Model classification constrained to registered types and explicit failure categories."""
from typing import Literal
from pydantic import ConfigDict, create_model
from agents.factory import make_agent
from agents.runner import require_model
from prompts.classification import classification_instructions

def classification_schema(definitions):
    """Generate the allowed labels from the registry, including unsupported/unclear."""
    labels = tuple(definitions) + ('unsupported', 'unclear')
    return create_model('ContractType', __config__=ConfigDict(extra='forbid'),
                        contract_type=(Literal[labels], ...))

def classify(text: str, key: str, model: str, definitions) -> str:
    """Classify complete PDF text; reject missing results without extraction fallback."""
    return require_model(
        make_agent(key, model, classification_instructions(definitions), 1000),
        f'Classify this document:\n\n{text}', classification_schema(definitions),
        {'turns': 3, 'output_tokens': 3000, 'total_tokens': 60000},
        'Model returned no contract type; extraction was not attempted.',
    ).contract_type
