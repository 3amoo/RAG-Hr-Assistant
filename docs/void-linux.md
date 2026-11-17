# Running RAG-Hr-Assistant natively on Void Linux

This guide targets Void Linux with the distribution Python 3.14 and a native
(runit-managed) PostgreSQL + Redis setup. Docker is still the easiest way to run
the full stack; use this guide when you want to run the API and Celery directly
on the host.

## What works natively

| Component | Native Void package | Notes |
| --- | --- | --- |
| Python | `python3` (3.14) | All dependencies have cp314 wheels |
| PostgreSQL | `postgresql18` / `postgresql18-client` | Used for projects, assets, chunks, task records |
| Redis | `redis` | Used as Celery result backend, and can also be the broker |
| Qdrant | Python package `qdrant-client` | Embedded/local mode; no server needed |
| RabbitMQ | not packaged | Use Redis as the Celery broker, or run RabbitMQ in Docker |
| pgvector | not packaged | Use the Qdrant backend, or run PostgreSQL in Docker |

The project supports `VECTOR_DB_BACKEND="QDRANT"` without any pgvector
extension. That is the recommended native setup.

## 1. Install system packages

```bash
sudo xbps-install -S \
  python3 python3-pip python3-devel \
  base-devel git curl \
  postgresql18 postgresql18-client \
  redis
```

`python3-devel` and `base-devel` are only needed if a package falls back to a
source build. The commands below install binary wheels only, so they normally
are not used.

## 2. Start PostgreSQL

Enable the runit service (the service name matches the installed package):

```bash
sudo ln -s /etc/sv/postgresql18 /var/service/
sudo sv up postgresql18
sudo sv status postgresql18
```

The package initializes the data directory on first start. If your installation
does not, initialize it manually:

```bash
sudo install -d -o postgres -g postgres /var/lib/postgresql
sudo -u postgres initdb -D /var/lib/postgresql -E UTF8
sudo sv restart postgresql18
```

Create the database and set a password for the application user:

```bash
sudo -u postgres psql <<'SQL'
ALTER USER postgres WITH PASSWORD 'CHANGE_ME';
CREATE DATABASE minihr OWNER postgres;
SQL
```

If you prefer a dedicated user:

```bash
sudo -u postgres psql <<'SQL'
CREATE USER minihr WITH PASSWORD 'CHANGE_ME';
CREATE DATABASE minihr OWNER minihr;
SQL
```

Then set `POSTGRES_USERNAME` and `POSTGRES_PASSWORD` in `src/.env` to match.

> **pgvector:** if you want `VECTOR_DB_BACKEND="PGVECTOR"` natively, you must
> build the extension from <https://github.com/pgvector/pgvector> against the
> PostgreSQL server headers. Void does not ship a `pgvector` package. Building
> it is outside the scope of this guide; use Qdrant or the Docker stack
> instead.

## 3. Start Redis

```bash
sudo ln -s /etc/sv/redis /var/service/
sudo sv up redis
sudo sv status redis
```

Protect Redis with a password. Edit `/etc/redis/redis.conf`:

```conf
requirepass CHANGE_ME
```

Then restart it:

```bash
sudo sv restart redis
```

## 4. Create the Python environment

From the repository root:

```bash
cd src
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install --only-binary=:all: -r requirements.txt
pip check
```

`--only-binary=:all:` is important: it makes pip fail fast instead of trying to
compile a package that has no Python 3.14 wheel. All pinned dependencies in
`requirements.txt` are expected to install this way.

## 5. Configure the application

```bash
cp .env.example .env
```

Edit `src/.env`. For a native Void setup, the important values are:

```dotenv
POSTGRES_USERNAME="postgres"
POSTGRES_PASSWORD="CHANGE_ME"
POSTGRES_HOST="localhost"
POSTGRES_PORT=5432
POSTGRES_MAIN_DATABASE="minihr"

# No pgvector extension is required with Qdrant.
VECTOR_DB_BACKEND="QDRANT"
VECTOR_DB_PATH="qdrant_db"

# Recommended: run Qdrant as a server (for example in Docker) so the API and
# Celery workers can share it. Leave QDRANT_URL empty only for single-process
# local mode.
QDRANT_URL="http://localhost:6333"
QDRANT_API_KEY=""

# RabbitMQ is not packaged on Void; use Redis for both broker and results.
CELERY_BROKER_URL="redis://:CHANGE_ME@localhost:6379/0"
CELERY_RESULT_BACKEND="redis://:CHANGE_ME@localhost:6379/0"
```

Add your `OPENAI_API_KEY` and/or `COHERE_API_KEY` as needed.

### Qdrant: server vs local mode

`QDRANT_URL` selects the mode:

- **Server mode** (`QDRANT_URL="http://localhost:6333"`): the API and all Celery
  workers can share one Qdrant instance. This is the recommended native setup.
  Qdrant is not packaged on Void; the simplest option is Docker:

  ```bash
  docker run -d --name qdrant \
    -p 6333:6333 \
    -v qdrant_storage:/qdrant/storage \
    qdrant/qdrant:v1.13.6
  ```

- **Local mode** (`QDRANT_URL=""`): `qdrant-client` opens the on-disk database
  at `VECTOR_DB_PATH`. Only one process can hold that database open at a time,
  so local mode is suitable for a single API process, not for an API plus
  Celery workers.

When running from `src/`, a relative `VECTOR_DB_PATH` becomes
`src/qdrant_db/`.

## 6. Run migrations

From the repository root:

```bash
alembic -c src/models/db_schemes/mini_hr/alembic.ini upgrade head
```

Or from `src/`:

```bash
alembic -c models/db_schemes/mini_hr/alembic.ini upgrade head
```

The Alembic environment builds the database URL from the same `POSTGRES_*`
settings as the application, so there is only one place to configure it.

## 7. Start the API and workers

Terminal 1 — API:

```bash
cd src
. .venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — Celery worker:

```bash
cd src
. .venv/bin/activate
celery -A celery_app worker \
  --loglevel=info \
  --queues=default,file_processing,data_indexing
```

Terminal 3 — Celery beat (optional, runs maintenance cleanup):

```bash
cd src
. .venv/bin/activate
celery -A celery_app beat --loglevel=info
```

Open <http://127.0.0.1:8000/docs>.

## 8. Verify the installation

```bash
cd src
. .venv/bin/activate

python -m compileall -q .
python -c "import main, celery_app"
pip check
```

If the import check fails with missing settings, make sure you are running from
`src/` (where `.env` lives) or export the variables in your shell.

## Troubleshooting

### `No matching distribution found` or a source build starts

Some older pins have no cp314 wheel. Keep the versions in `requirements.txt`
and install with `--only-binary=:all:`. Do not "fix" this by downgrading Python
or by adding LangChain.

Known-good pins on Python 3.14:

- `PyMuPDF==1.27.2`
- `cohere==7.3.1`
- `asyncpg==0.32.0`
- `psycopg2-binary==2.9.13`
- `SQLAlchemy==2.0.44`
- `greenlet==3.3.0`

### `pydantic.v1.errors.ConfigError` from Cohere

You are on an old Cohere release. Use `cohere==7.3.1` (or newer) as pinned in
`requirements.txt`.

### `psycopg2` build error

Use `psycopg2-binary`, not `psycopg2`. The Docker image does not install
`libpq-dev`.

### Alembic cannot connect

Check `src/.env` (`POSTGRES_*`) and make sure PostgreSQL is running:

```bash
pg_isready -h localhost -p 5432
```

### Celery cannot connect to RabbitMQ

RabbitMQ is not packaged on Void. Use Redis as the broker:

```dotenv
CELERY_BROKER_URL="redis://:CHANGE_ME@localhost:6379/0"
```

### Qdrant local storage errors

Only one process can open a local Qdrant path at a time. If you see a lock
error, either run a single API process or switch to server mode by setting
`QDRANT_URL` (see above). The Docker stack uses pgvector by default, so it does
not have this limitation.
