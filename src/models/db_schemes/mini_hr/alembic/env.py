"""Alembic environment for the mini-HR database.

The database URL is built from the application settings (which read the
environment and/or a local .env file), so migrations use exactly the same
credentials as the API and the Celery workers.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import URL

# ---------------------------------------------------------------------------
# Make the application importable regardless of the current directory.
# Local repo: <repo>/src/models/db_schemes/mini_hr/alembic/env.py
# Docker:     /app/models/db_schemes/mini_hr/alembic/env.py
# ---------------------------------------------------------------------------
ALEMBIC_DIR = Path(__file__).resolve().parent
APP_DIR = ALEMBIC_DIR.parents[3]

for path in (str(APP_DIR), str(ALEMBIC_DIR.parent)):
    if path not in sys.path:
        sys.path.insert(0, path)

# Load src/.env even when alembic is invoked from the repository root.
# Existing environment variables keep precedence (override=False).
load_dotenv(APP_DIR / ".env")

from helpers.config import get_settings  # noqa: E402
from models.db_schemes.mini_hr.schemes import SQLAlchemyBase  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLAlchemyBase.metadata


def _database_url() -> str:
    settings = get_settings()
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=settings.POSTGRES_USERNAME,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_MAIN_DATABASE,
    )
    return url.render_as_string(hide_password=False)


config.set_main_option("sqlalchemy.url", _database_url())


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
