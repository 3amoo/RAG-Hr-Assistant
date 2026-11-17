from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str
    APP_VERSION: str

    # Single shared key for the local API. Empty disables auth for local dev.
    API_KEY: str = ""
    METRICS_PATH: str = "/metrics"

    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int

    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_MAIN_DATABASE: str

    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str

    OPENAI_API_KEY: str = ""
    OPENAI_API_URL: str = ""
    COHERE_API_KEY: str = ""

    GENERATION_MODEL_ID_LITERAL: List[str] = []
    GENERATION_MODEL_ID: str = ""
    EMBEDDING_MODEL_ID: str = ""
    EMBEDDING_MODEL_SIZE: int = 1024
    INPUT_DAFAULT_MAX_CHARACTERS: int = 1024
    GENERATION_DAFAULT_MAX_TOKENS: int = 200
    GENERATION_DAFAULT_TEMPERATURE: float = 0.1

    VECTOR_DB_BACKEND_LITERAL: List[str] = []
    VECTOR_DB_BACKEND: str
    VECTOR_DB_PATH: str
    VECTOR_DB_DISTANCE_METHOD: str = "cosine"
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int = 100
    # Optional Qdrant server connection. When QDRANT_URL is empty the provider
    # uses the local on-disk database at VECTOR_DB_PATH.
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""

    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"

    # Retrievals scoring below this are treated as low-confidence and refused.
    MIN_RETRIEVAL_SCORE: float = 0.25

    # Celery configuration
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_TASK_TIME_LIMIT: int = 600
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_WORKER_CONCURRENCY: int = 2
    CELERY_FLOWER_PASSWORD: str = ""
    FLOWER_AUTH_USER: str = "admin"


@lru_cache
def get_settings():
    return Settings()
