# RAG-Hr-Assistant

Retrieval-Augmented Generation (RAG) service for HR policy documents. Upload
PDF or TXT policies, index them into PostgreSQL (pgvector) or Qdrant, and ask
questions that are answered from the indexed content using OpenAI or Cohere.

> **Status:** the v1 policy copilot is implemented: ingestion, chunking,
> indexing, semantic search, cited answers with low-confidence refusal, API-key
> auth, a local UI, offline tests, and a golden evaluation suite. There is no
> hosted demo. All values in example env files are placeholders, not secrets.

## Features

- Per-project document upload (PDF/TXT) with type and size validation.
- Overlap-aware chunking that preserves `source` and `page` metadata.
- Embeddings through OpenAI or Cohere, selected by a provider factory.
- Vector storage in PostgreSQL + pgvector (default) or Qdrant. Collections are
  named `vectors_<embedding_size>_<project_id>` for both backends.
- Semantic search and RAG answers with English and Arabic prompt templates.
- **Cited answers:** every grounded answer returns citations with chunk ID,
  document, page, section, score and a quoted snippet.
- **Refusal:** retrievals below `MIN_RETRIEVAL_SCORE` are refused instead of
  producing a possibly wrong answer.
- Shared API-key authentication on the data and NLP endpoints.
- A plain HTML/JS local UI for asking questions and inspecting citations.
- Background processing with Celery (file processing, indexing, maintenance,
  workflow) over Redis or RabbitMQ, with idempotent task records.
- Prometheus metrics and an optional Flower dashboard.
- 15 offline golden questions with hit@5, citation-validity and refusal-accuracy
  metrics; no LLM judge, latency or cost gate.

## API overview

All functional routes are under `/api/v1`. `GET /` redirects to the local UI.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/` | App name and version (unauthenticated health check) |
| `POST` | `/api/v1/data/upload/{project_id}` | Upload a document |
| `POST` | `/api/v1/data/process/{project_id}` | Chunk uploaded documents (Celery task) |
| `POST` | `/api/v1/data/process-and-push/{project_id}` | Chunk and index in one workflow |
| `POST` | `/api/v1/nlp/index/push/{project_id}` | Index existing chunks |
| `GET` | `/api/v1/nlp/index/info/{project_id}` | Vector collection info |
| `POST` | `/api/v1/nlp/index/search/{project_id}` | Semantic search |
| `POST` | `/api/v1/nlp/index/answer/{project_id}` | Cited RAG answer |

Except for the health check, endpoints require the `X-API-Key` header when
`API_KEY` is configured. Interactive docs: <http://localhost:8000/docs>.

The answer endpoint returns:

```json
{
  "signal": "rag_answer_success",
  "answer": "Employees are entitled to 25 days of paid annual leave.",
  "citations": [
    {
      "chunk_id": 7,
      "asset_name": "leave_policy.txt",
      "doc_type": "POLICY",
      "page": 2,
      "section": null,
      "score": 0.81,
      "quote": "Full-time employees are entitled to 25 days of paid annual leave..."
    }
  ],
  "low_confidence": false
}
```

A refused question returns `signal: "rag_answer_refused"`, a short refusal
answer, `citations: []` and `low_confidence: true`. There is no hosted demo and
no public demo endpoint.

## Quick start with Docker

The Compose stack runs FastAPI, Celery worker/beat, Flower, PostgreSQL with
pgvector, Qdrant, RabbitMQ, Redis, Nginx, Prometheus and Grafana.

```bash
cd docker

cp env/.env.example.app env/.env.app
cp env/.env.example.postgres env/.env.postgres
cp env/.env.example.rabbitmq env/.env.rabbitmq
cp env/.env.example.redis env/.env.redis
cp env/.env.example.grafana env/.env.grafana
cp env/.env.example.postgres-exporter env/.env.postgres-exporter

# Edit env/.env.app: replace every CHANGE_ME and add your OpenAI/Cohere keys.
docker compose up --build
```

Useful URLs:

| Service | URL |
| --- | --- |
| Local UI | <http://localhost:8000/ui/> |
| API docs | <http://localhost:8000/docs> |
| Nginx | <http://localhost> |
| Flower | <http://localhost:5555> |
| RabbitMQ management | <http://localhost:15672> |
| Grafana | <http://localhost:3000> |
| Prometheus | <http://localhost:9090> |
| Qdrant | <http://localhost:6333/dashboard> |

Migrations run automatically from `docker/minihr/entrypoint.sh` before the API
starts.

## Local development

Dependencies are pinned to versions that provide wheels for Python 3.10–3.14.
On Void Linux with Python 3.14, install them with binary wheels only (the system
Python is externally managed, so a venv is required):

```bash
cd src
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install --only-binary=:all: -r requirements.txt
```

Then:

```bash
cp .env.example .env
# edit .env: replace CHANGE_ME values, set API_KEY and add provider keys

# From the repository root:
alembic -c src/models/db_schemes/mini_hr/alembic.ini upgrade head

# Generate synthetic policies for trying the pipeline locally:
python scripts/generate_sample_data.py

cd src
uvicorn main:app --reload
```

Open <http://localhost:8000/ui/>, enter the `API_KEY` from your `.env` and a
project ID, and ask a question about an uploaded document. Generated policy
files live in `assets/sample-data/` and are ignored by git; pass `--force` to
the generator to overwrite them.

See [docs/void-linux.md](docs/void-linux.md) for the full native setup,
including PostgreSQL, Redis, migrations, Celery, and the Qdrant alternative to
pgvector.

## Configuration

Configuration is read from environment variables and/or a `.env` file. Start
from `src/.env.example` for local development and
`docker/env/.env.example.app` for Compose. The two examples are kept in sync.

Key settings:

- `APP_NAME` / `APP_VERSION`: application identity.
- `API_KEY`: shared key required on data/NLP routes. Empty disables auth for
  trusted local development only.
- `METRICS_PATH`: Prometheus endpoint path (default `/metrics`).
- `GENERATION_BACKEND` / `EMBEDDING_BACKEND`: `OPENAI` or `COHERE`.
- `VECTOR_DB_BACKEND`: `PGVECTOR` or `QDRANT`.
- `POSTGRES_*`: relational database connection.
- `MIN_RETRIEVAL_SCORE`: lowest accepted cosine similarity (default `0.25`).
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`: task queue endpoints.
- `FLOWER_AUTH_USER` / `CELERY_FLOWER_PASSWORD`: Flower dashboard credentials.
- `PRIMARY_LANG` / `DEFAULT_LANG`: prompt language (`en` or `ar`).

## Project layout

```text
src/
  main.py                 FastAPI app, UI mount and startup wiring
  celery_app.py           Celery app, queues, routes, beat schedule
  routes/                 HTTP endpoints
  routes/schemes/         Request schemas
  controllers/            Upload, chunking, RAG orchestration
  models/                 SQLAlchemy models, DAOs, answer/citation models
  stores/llm/             OpenAI/Cohere providers and prompt templates
  stores/vectordb/        Qdrant and pgvector providers
  tasks/                  Celery tasks
  utils/                  Metrics and idempotency helpers
  ui/                     Plain HTML/CSS/JS local UI
docker/                   Dockerfile, Compose stack, service env examples
docs/void-linux.md        Native Void Linux setup
scripts/                  Synthetic sample-data generator
evals/                    Golden questions and offline evaluation runner
tests/                    Offline pytest suite
.github/workflows/ci.yml  Compile + test workflow
```

## Development checks

From the repository root, with the venv activated:

```bash
python -m compileall -q src
python -m pytest -q
python evals/run_eval.py
```

The test and evaluation suites are fully offline: they use fake LLM and
embedding clients and need no database or API keys. CI runs the same compile
and test steps on Python 3.14.

## Dependencies

- Python 3.10–3.14 are supported by a single `src/requirements.txt`.
- Every version is pinned. Wheel availability is verified with
  `pip install --dry-run --only-binary=:all: -r src/requirements.txt`.
- Document loading and splitting are implemented directly with PyMuPDF and the
  standard library; LangChain is not used.
- `psycopg2-binary` is used because the Docker image does not install
  `libpq-dev`.
- Test tooling (`pytest`, `pytest-asyncio`, `httpx`) is pinned in the same file.

## Roadmap

- Metadata filters (document type, department, language, effective date).
- Role-based access control, audit logging and PII redaction.
- Recruiting and onboarding products (out of v1 scope).
- Structured logging, request IDs and further API hardening.
- No hosted demo or public demo endpoint is planned.

## Security

- Never commit `.env` files, API keys, uploaded documents or database dumps.
- All committed values are placeholders; replace every `CHANGE_ME` before any
  deployment and set a non-empty `API_KEY`.
- If a real key or password was ever committed, rotate it and purge the git
  history; a force-push alone does not guarantee removal from GitHub.
- Keep the API behind Nginx and do not expose it publicly without authentication.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
