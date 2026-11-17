# RAG-Hr-Assistant

A small HR assistant built on Retrieval-Augmented Generation (RAG). It ingests
company documents (PDF/TXT), splits them into overlapping chunks, stores them in
PostgreSQL, embeds them with an LLM provider, and answers questions from the
indexed content.

The project follows the same layout and conventions as the `mini-rag` series:
FastAPI, SQLAlchemy, Alembic, Celery, Redis, RabbitMQ, Qdrant/pgvector, and
Prometheus/Grafana.

> **Status:** the document ingestion, indexing, search, and RAG endpoints are
> implemented. The `hr` and `screening` route modules are placeholders and are
> skipped at startup when they are absent.

## Features

- Upload PDF/TXT files per project.
- Split documents into overlapping chunks while preserving source and page
  metadata.
- Store chunks in PostgreSQL and embeddings in Qdrant or pgvector.
- Semantic search and RAG answers through OpenAI or Cohere.
- Background processing with Celery (file processing, indexing, maintenance).
- Idempotent task execution records in PostgreSQL.
- Prometheus metrics and an optional Flower dashboard.

## API overview

All routes are under `/api/v1`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | App name and version |
| `POST` | `/data/upload/{project_id}` | Upload a document |
| `POST` | `/data/process/{project_id}` | Chunk uploaded documents (Celery task) |
| `POST` | `/data/process-and-push/{project_id}` | Chunk and index in one workflow |
| `POST` | `/nlp/index/push/{project_id}` | Index existing chunks |
| `GET` | `/nlp/index/info/{project_id}` | Vector collection info |
| `POST` | `/nlp/index/search/{project_id}` | Semantic search |
| `POST` | `/nlp/index/answer/{project_id}` | RAG answer |

Interactive docs: <http://localhost:8000/docs>.

## Quick start with Docker

The Compose stack runs FastAPI, Celery worker/beat, Flower, PostgreSQL with
pgvector, Qdrant, RabbitMQ, Redis, Nginx, Prometheus, and Grafana.

```bash
cd docker

cp env/.env.example.app env/.env.app
cp env/.env.example.postgres env/.env.postgres
cp env/.env.example.rabbitmq env/.env.rabbitmq
cp env/.env.example.redis env/.env.redis
cp env/.env.example.grafana env/.env.grafana
cp env/.env.example.postgres-exporter env/.env.postgres-exporter

# Edit env/.env.app and add your OpenAI/Cohere API keys.
docker compose up --build
```

Useful URLs:

| Service | URL |
| --- | --- |
| API docs | <http://localhost:8000/docs> |
| Nginx | <http://localhost> |
| Flower | <http://localhost:5555> |
| RabbitMQ management | <http://localhost:15672> |
| Grafana | <http://localhost:3000> |
| Prometheus | <http://localhost:9090> |
| Qdrant | <http://localhost:6333/dashboard> |

Migrations run automatically from `docker/minihr/entrypoint.sh` before the API
starts.

## Local development on Void Linux

The dependencies are pinned to versions that provide wheels for Python
3.10–3.14. On Void Linux with Python 3.14, install them with binary wheels only:

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
# edit .env, especially the API keys and database settings

# From the repository root:
alembic -c src/models/db_schemes/mini_hr/alembic.ini upgrade head

cd src
uvicorn main:app --reload
```

See [docs/void-linux.md](docs/void-linux.md) for the full native setup,
including PostgreSQL, Redis, migrations, Celery, and the Qdrant alternative to
pgvector.

## Configuration

Configuration is read from environment variables and/or a `.env` file. Start
from `src/.env.example` for local development and
`docker/env/.env.example.app` for Compose. The two examples are intentionally
kept in sync.

Key settings:

- `GENERATION_BACKEND` / `EMBEDDING_BACKEND`: `OPENAI` or `COHERE`.
- `VECTOR_DB_BACKEND`: `PGVECTOR` or `QDRANT`.
- `POSTGRES_*`: relational database connection.
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`: task queue endpoints.
- `PRIMARY_LANG` / `DEFAULT_LANG`: prompt language (`en` or `ar`).

## Project layout

```text
src/
  main.py                 FastAPI app and startup wiring
  celery_app.py           Celery app, queues, routes, beat schedule
  routes/                 HTTP endpoints
  controllers/            Upload, chunking, RAG orchestration
  models/                 SQLAlchemy models and DB access objects
  stores/llm/             OpenAI/Cohere providers and prompt templates
  stores/vectordb/        Qdrant and pgvector providers
  tasks/                  Celery tasks
  utils/                  Metrics and idempotency helpers
docker/                   Dockerfile, Compose stack, service env examples
docs/void-linux.md        Native Void Linux setup
```

## Development checks

```bash
cd src
python -m compileall -q .
python -c "import main, celery_app"
pip check
```

The import check needs a valid `.env` (or the equivalent environment
variables), because settings are loaded at import time.

## Dependency notes

- Python 3.10–3.14 are supported by a single `src/requirements.txt`.
- LangChain was removed; PDF/TXT parsing uses PyMuPDF and the standard library.
- `psycopg2-binary` is used because the Docker image does not install
  `libpq-dev`.
- `PyMuPDF==1.27.2` and `cohere==7.3.1` are the first versions that work on
  Python 3.14 in this project.
- Do not add packages without checking that a wheel exists for Python 3.10 and
  3.14.

## The course

This is an educational project. The original code was explained step by step in
an Arabic video series (list coming soon).

---

Part of the mini-* series: **mini-rag** (document Q&A) · **RAG-Hr-Assistant** (HR
assistant).
