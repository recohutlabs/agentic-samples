"""Construct consistently configured Strands agents for each bounded model step."""
from progress import callback_handler, log
from strands import Agent
from strands.models.openai_responses import OpenAIResponsesModel

def make_agent(key: str, model: str, instructions: str, output_tokens: int, tools=None) -> Agent:
    """One Strands agent configured for classification or type-specific extraction."""
    log('Function: make_agent() — creating Strands agent', debug=True)
    return Agent(
        model=OpenAIResponsesModel(
            model_id=model,
            client_args={'api_key': key, 'timeout': 120.0, 'max_retries': 1},
            params={'max_output_tokens': output_tokens, 'store': False},
        ),
        system_prompt=instructions,
        tools=tools or [],
        callback_handler=callback_handler(),
        load_tools_from_directory=False,
    )
