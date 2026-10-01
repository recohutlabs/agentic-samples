"""Validate structured model results; never substitute a result after failure."""
from typing import TypeVar
from pydantic import BaseModel
from strands import Agent
from progress import log
Schema = TypeVar("Schema", bound=BaseModel)

def require_model(agent: Agent, prompt: str, schema: type[Schema], limits: dict, missing: str) -> Schema:
    """Run one structured call and reject a missing result before validation."""
    log('Function: require_model() — submitting structured model request', debug=True)
    result = agent(prompt, structured_output_model=schema, limits=limits)
    metrics = getattr(result, 'metrics', None)
    usage = getattr(metrics, 'accumulated_usage', {}) or {}
    counts = {key: value for key, value in usage.items()
              if key in ('inputTokens', 'outputTokens', 'totalTokens')
              and isinstance(value, (int, float))}
    if counts:
        log('Token usage: ' + ', '.join(f'{key}={value}' for key, value in counts.items()), debug=True)
    if result.structured_output is None:
        raise ValueError(missing)
    log('Function: model_validate() — validating structured result', debug=True)
    return schema.model_validate(result.structured_output)
