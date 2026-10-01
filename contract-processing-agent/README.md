# Contract Processing Agent

Python reference implementation for fictional service and employment contracts. Read a text PDF, classify its contracting relationship, extract type-specific structured data, verify it against the source, then optionally save/query results through an authenticated API.

This is a development sample, not legal advice, signature authentication or a production contract system. A second model pass does not guarantee accuracy.

## Setup and CLI

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). From this sample directory:

```bash
uv sync
```

Create `.env` locally (never commit credentials):

```dotenv
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=your-supported-model-id
```

The model must support the structured outputs used by the sample. Model calls incur provider usage.

```bash
uv run main.py data/FAC-001-cleaning.pdf
uv run main.py data/FAC-001-cleaning.pdf --debug > contract.json 2> run.log
```

CLI output JSON goes to stdout; progress and durations go to stderr. Debug mode reports available function/model event metadata without raw PDF text, prompts, model reasoning or credentials. The CLI returns structured JSON; API processing also persists records.

## Authenticated API

Use a private runtime token generated into an environment variable, without printing its value:

```bash
export CONTRACT_SESSION_TOKEN="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export CONTRACT_DB_PATH="$PWD/data/contracts.db"
uv run uvicorn api:app --factory --host 127.0.0.1 --port 8765
```

In another shell, set the same token securely before sending requests. Keep that token out of screenshots, logs and source control. Every data route requires `Authorization: Bearer <token>`; `/health` is public. Routes also have `/v1` aliases.

```bash
curl -fsS http://127.0.0.1:8765/fixtures \
  -H "Authorization: Bearer $CONTRACT_SESSION_TOKEN"

curl -fsS http://127.0.0.1:8765/process \
  -H "Authorization: Bearer $CONTRACT_SESSION_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"fixture":"FAC-001-cleaning.pdf","operation_id":"example-cleaning-001"}'
```

Processing returns a job with an ID and authoritative status. Read `/jobs/{id}` until `completed` or `failed`; `/jobs/{id}/events` records actual processing stages. A completed job's `contract_id` is the stored record ID, distinct from the agreement reference inside its parsed JSON. Reusing an operation ID with the same input reconciles the existing job; use a new ID for a deliberate retry after failure.

Upload a text PDF using multipart form fields `file` and `operation_id` at `/upload`. Read history at `/contracts` and complete structured data at `/contracts/{id}`. `/chat` accepts `message`, optional stored `contract_id`, and optional `conversation_id`. Its returned conversation ID can be reused and read through `/conversations/{id}`. Chat reads saved JSON and cannot modify contracts or execute business actions.

The default database is `data/contracts.db`. Runtime sessions for the same product must share one database path; tokens and session IDs do not partition records. Treat access tokens as access to that shared portfolio. The sample is not a multi-tenant authorization system. Keep the database and uploaded/private artifacts out of a public repository.

## Schemas and limits

`registry.py` joins family descriptions, Pydantic schemas and extraction instructions. Service agreements retain fees, renewal, termination, liability and scope. Employment contracts retain employer/employee, compensation, probation and employment terms. Unknown facts remain null. Unsupported or ambiguous contract families stop before extraction; stage failures prevent successful final output.

PDFs must be unencrypted and text-based: at most 20 MB, 200 pages and 120,000 extracted text characters. Pages without extractable text are rejected. Scanned PDFs/OCR are unsupported.

Chat uses a model-selected `query_contracts(sql)` tool over the physical shared SQLite database in read-only mode. A host-owned view restricts selected-contract scope; portfolio SQL may scan all persisted contracts. JSON1 reads nested terms, and `decimal_sum` / `decimal_avg` aggregate source money strings with decimal arithmetic. Ordinary SQLite SUM/AVG/TOTAL are forbidden. Group currencies and compatible fee units; stated totals are not actual payments.

Each chat permits eight queries. Each query is bounded to 6,000 SQL characters, two seconds and 250,000 SQLite VM operations; outputs are limited to 100 rows / 60,000 bytes. Excess output is rejected with no partial rows. These are output limits, not a 100-contract portfolio cutoff. Writes, other tables, ATTACH, PRAGMA, CTEs and LIMIT/pagination are denied. Responses expose `query_count` and `query_evidence` (hash, status, row count, completeness). Chat uses six recent conversation messages and checks supporting record IDs against host scope. These controls do not guarantee sentence-level accuracy. Contract terms describe promises, not observed payments, renewal, performance or signature authentication.

## Checks and evaluation

Focused offline checks do not call a model:

```bash
uv run --frozen python -m pytest tests/test_api.py tests/test_contract_query.py tests/test_progress.py tests/test_routing.py tests/test_verification.py tests/test_employment_fixes.py -q
```

The model evaluation is separate and incurs provider usage:

```bash
uv run python evaluation/run.py
```

See [evaluation/README.md](evaluation/README.md) for frozen source interpretations and grading. The original five-fictional-document trial classified 5/5 correctly and passed 117/118 selected checks at extraction and verification, with no scored verifier improvement/regression. Scores cover selected fields, not complete clauses, legal validity, repeated stability or the entire portfolio. The subsequent full frozen five-case trial summarized in [evaluation/final-summary.json](evaluation/final-summary.json) passed 118/118 at both stages, 5/5 classifications and zero errors. It recorded no verifier correction or regression. This is one focused live trial; it does not prove broader accuracy or verifier improvement.

## Add a contract family

Add a schema in `models/`, source-only instructions in `prompts/`, then register both and the contracting-relationship description in `registry.py`. Keep a literal matching `contract_type`, forbid extra fields, and distinguish unknown from explicit zero/false. Add representative classification and extraction checks. The workflow obtains allowed families from the registry.
