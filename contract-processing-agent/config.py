"""Load the model and credentials without logging secrets."""
import os
from pathlib import Path
from dotenv import dotenv_values
DEFAULT_MODEL = "gpt-6-luna"

def load_openai_config() -> tuple[str, str]:
    """API key and model id from the sample .env, then the process environment."""
    env = dotenv_values(Path(__file__).resolve().with_name('.env'))
    key = (env.get('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY') or '').strip()
    model = (env.get('OPENAI_MODEL') or os.getenv('OPENAI_MODEL') or DEFAULT_MODEL).strip().removeprefix('openai:')
    if not key or not model:
        raise ValueError('Set OPENAI_API_KEY in .env or the process environment; OPENAI_MODEL is optional.')
    return key, model
