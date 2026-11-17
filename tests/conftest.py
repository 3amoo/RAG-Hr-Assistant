import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(TESTS))

# Tests never rely on a developer's real .env. These are set before any
# application module imports the cached settings object.
os.environ.update(
    {
        "APP_NAME": "RAG-Hr-Assistant",
        "APP_VERSION": "test",
        "FILE_ALLOWED_TYPES": '["text/plain", "application/pdf"]',
        "FILE_MAX_SIZE": "10",
        "FILE_DEFAULT_CHUNK_SIZE": "1000",
        "POSTGRES_USERNAME": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_MAIN_DATABASE": "test",
        "GENERATION_BACKEND": "OPENAI",
        "EMBEDDING_BACKEND": "COHERE",
        "VECTOR_DB_BACKEND": "PGVECTOR",
        "VECTOR_DB_PATH": "qdrant_db",
        "PRIMARY_LANG": "en",
        "DEFAULT_LANG": "en",
        "MIN_RETRIEVAL_SCORE": "0.25",
        "API_KEY": "",
        "METRICS_PATH": "/metrics",
    }
)

from helpers.config import get_settings  # noqa: E402

get_settings.cache_clear()
