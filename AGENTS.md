# AGENTS.md — instructions for coding agents

This file is for any automated coding agent working on **mini-hr**, especially
small/cheap models. Read it before editing. If you are unsure, stop and report
what you found instead of guessing.

## 1. What this project is

`mini-hr` is a FastAPI + Celery RAG service. It:

1. Accepts PDF/TXT uploads (`routes/data.py`).
2. Extracts text with PyMuPDF and splits it into overlapping chunks
   (`controllers/ProcessController.py`).
3. Stores projects/assets/chunks in PostgreSQL (`models/`, SQLAlchemy async).
4. Embeds chunks with OpenAI or Cohere and stores vectors in pgvector or Qdrant
   (`stores/`).
5. Answers questions from retrieved chunks (`controllers/NLPController.py`).

The `hr` and `screening` route modules are not implemented yet. `main.py`
imports them optionally and prints a warning when they are missing.

## 2. Non-negotiable dependency rules

`src/requirements.txt` is a **single** file that must install on **Python
3.10 through 3.14**.

- Keep every version pinned with `==`.
- Before adding or changing a dependency, verify that a wheel exists for both
  Python 3.10 and 3.14. Use:

  ```bash
  pip install --dry-run --only-binary=:all: -r src/requirements.txt
  ```

  A source build that fails on Python 3.14 means the version is not acceptable.
- Do **not** reintroduce these removed packages:
  - `langchain` (pins `numpy<2`; breaks Python 3.14)
  - `motor`, `pydantic-mongo`
  - `pgvector` (the Python package is not used; pgvector is only a PostgreSQL
    extension)
  - `nltk`
  - `starlette-exporter`, `fastapi-health`
- Use `psycopg2-binary`, never `psycopg2`. The Docker image has no `libpq-dev`.
- Known-good pins that must not be casually downgraded:
  - `PyMuPDF==1.27.2`
  - `cohere==7.3.1`
  - `asyncpg==0.32.0`
  - `psycopg2-binary==2.9.13`
  - `SQLAlchemy==2.0.44`
  - `greenlet==3.3.0`
- The Docker image intentionally uses Python 3.10. Do not change the base image
  to 3.14 to "fix" a dependency. Fix the dependency instead.

If a dependency cannot satisfy these rules, **do not invent a workaround**.
Report the exact failing command and error.

## 3. Do not re-add LangChain

Document loading and splitting are intentionally implemented directly:

- `ProcessController.get_file_content()` reads TXT with the standard library and
  PDFs with `pymupdf`.
- `ProcessController.process_simpler_splitter()` does overlap-aware splitting.

Keep `Document(page_content=..., metadata=...)` as the internal shape. Preserve
`source` and `page` metadata when editing chunking code.

## 4. File map

| Path | Responsibility |
| --- | --- |
| `src/main.py` | FastAPI startup/shutdown, DB engine, provider wiring |
| `src/celery_app.py` | Celery instance, queues, routes, beat schedule |
| `src/helpers/config.py` | Pydantic settings; all env vars live here |
| `src/routes/` | HTTP endpoints |
| `src/controllers/` | Upload, chunking, RAG orchestration |
| `src/models/db_schemes/` | SQLAlchemy tables |
| `src/models/*Model.py` | Async DB access helpers |
| `src/stores/llm/` | OpenAI/Cohere providers |
| `src/stores/vectordb/` | Qdrant/pgvector providers |
| `src/tasks/` | Celery tasks |
| `src/utils/idempotency_manager.py` | Task deduplication records |
| `docker/` | Dockerfile, Compose stack, env examples |
| `docs/void-linux.md` | Native Void Linux setup |

## 5. Environment and configuration rules

- Add a setting to **all three** places when it is user-facing:
  1. `src/helpers/config.py`
  2. `src/.env.example`
  3. `docker/env/.env.example.app`
- Keep the local and Docker examples consistent. Docker uses service names
  (`pgvector`, `redis`, `rabbitmq`) as hosts; local development uses
  `localhost`.
- Never commit real API keys. Use placeholders such as `sk-your-openai-key`.
- `Settings` loads `.env` from the current working directory. Commands that
  import the app must run from `src/` or export the variables.
- Do not make required settings optional just to silence an error. Fix the
  example/env instead, unless the setting is genuinely optional.

## 6. Database rules

- The schema is defined by SQLAlchemy models in
  `src/models/db_schemes/mini_hr/schemes/`.
- Migrations live in
  `src/models/db_schemes/mini_hr/alembic/versions/`.
- If you change a model, add a migration. Do not rely on
  `create_all()`.
- Use timezone-aware datetimes (`datetime.now(timezone.utc)`).
- `CeleryTaskExecution.celery_task_id` is a **string** (Celery ids are UUID
  strings). Do not change it to `UUID`.
- The unique index `ixz_task_name_args_hash` is intentional: tasks are
  deduplicated by task name + arguments hash.
- Alembic builds the database URL from `POSTGRES_*` settings in
  `alembic/env.py`. Do not hardcode credentials in `alembic.ini`.

Useful commands:

```bash
# Render SQL without a database
alembic -c src/models/db_schemes/mini_hr/alembic.ini upgrade head --sql

# Apply migrations
alembic -c src/models/db_schemes/mini_hr/alembic.ini upgrade head
```

## 7. Docker rules

- `docker/minihr/entrypoint.sh` **must** end with `exec "$@"`. Without it the
  container runs migrations and exits instead of starting the API.
- `docker/minihr/alembic.ini` is the in-container config. Keep
  `script_location = %(here)s/alembic`.
- The Dockerfile copies `src/` into `/app`, so the Alembic directory is
  `/app/models/db_schemes/mini_hr/alembic`.
- Keep `docker/env/.env.example.*` in sync with the Compose service names.
- Do not add a second copy of the Dockerfile under `docker/minirag/`.

## 8. Async and Celery rules

- Celery tasks are synchronous functions that call `asyncio.run(...)` around an
  async implementation. Keep that pattern.
- Always dispose the async engine and disconnect the vector DB client in a
  `finally` block.
- SQLAlchemy sessions are created with
  `sessionmaker(..., class_=AsyncSession, expire_on_commit=False)`.
- Use `await session.execute(...)`, `await session.commit()`,
  `await session.refresh(...)`. A missing `await` is the most common bug in
  this codebase.
- Provider methods that perform I/O are async in the vector DB layer. Do not
  call them without `await`.
- `PGVectorProvider.is_collection_existed()` returns a row or `None`; use it in
  a boolean context.
- Qdrant collections are named `collection_<embedding_size>_<project_id>`.
  The pgvector table prefix is `collection_`, matching that naming.

## 9. Verification checklist

Run these before claiming a change is complete:

```bash
cd src

# 1. Syntax
python -m compileall -q .

# 2. Imports (needs a valid .env or exported settings)
python -c "import main, celery_app"

# 3. Dependency consistency
pip check
```

For dependency changes:

```bash
pip install --dry-run --only-binary=:all: -r src/requirements.txt
```

For migration changes:

```bash
alembic -c src/models/db_schemes/mini_hr/alembic.ini upgrade head --sql
```

If a check cannot run because a service is missing (PostgreSQL, Redis, etc.),
say so explicitly. Do not report "verified" when you only read the code.

## 10. Editing discipline for small models

- Read the whole file before editing it. Do not rewrite a file from a partial
  view.
- Prefer the smallest possible edit. Do not reformat unrelated code.
- Match the existing style: plain imports, no type-annotation overhaul, no
  async framework migration.
- Do not delete files or features unless the task explicitly asks for it.
- Do not add new abstractions, factories, or configuration layers for a
  one-line change.
- Do not claim a command passed unless you ran it and saw the exit status.
- When two files must stay in sync (env examples, model + migration, config +
  docs), update both in the same change.
- If you are about to do something that is not covered here, ask for
  clarification rather than guessing.

## 11. Known pitfalls

| Symptom | Likely cause |
| --- | --- |
| Container exits after migrations | `entrypoint.sh` missing `exec "$@"` |
| `No module named 'schemes'` in Alembic | `env.py` did not add the app dir to `sys.path` |
| `sqlalchemy.exc.MissingGreenlet` | missing `await` on an async SQLAlchemy call |
| `pydantic.v1.errors.ConfigError` | old `cohere`; use `7.3.1` |
| `No matching distribution found` | no cp314 wheel; keep the pinned version and use `--only-binary=:all:` |
| Cohere `embed` response has no `.embeddings.float_` | Cohere 7.x returns a different shape; see `CoHereProvider.embed_text()` |
| `psycopg2` build error | use `psycopg2-binary` |
| Qdrant lock error | local mode opened by more than one process; set `QDRANT_URL` |
| Alembic connects to the wrong DB | check `POSTGRES_*` in the environment used by `alembic` |

## 12. Documentation rules

- Update `README.md` when user-facing commands or endpoints change.
- Update `docs/void-linux.md` when native dependencies, services, or
  environment variables change.
- Keep instructions copy-pasteable and test commands before documenting them.
- Do not document features that are only placeholders (`hr`, `screening`).
