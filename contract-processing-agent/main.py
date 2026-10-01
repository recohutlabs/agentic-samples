# /// script
# requires-python = ">=3.11"
# dependencies = ["strands-agents[openai]==1.57.1", "pydantic==2.13.5", "pypdf==6.19.0", "python-dotenv==1.2.2"]
# ///
"""Run: uv run main.py contract.pdf; configure OPENAI_API_KEY/OPENAI_MODEL in .env."""
import argparse
import sys
from pathlib import Path
from pydantic import ValidationError
from workflow import extract
from progress import progress_session

def main() -> int:
    """Output the fixed contract JSON; failures exit nonzero without logging provider payloads."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--debug', action='store_true', help='Show function, model stream and structured-output events on stderr.')
    args = parser.parse_args()
    try:
        with progress_session(debug=args.debug) as progress:
            result = extract(args.pdf)
            progress.log('Processing completed')
        print(result.model_dump_json(indent=2))
        return 0
    except Exception as error:
        # Validation details can echo contract text or model output.
        print(f'Extraction failed ({type(error).__name__}).', file=sys.stderr)
        if isinstance(error, (FileNotFoundError, ValueError)) and not isinstance(error, ValidationError):
            print(str(error), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
