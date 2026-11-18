# ======================================================
# Import Libs
# ======================================================

import asyncio
import logging

from celery_app import celery_app, get_setup_utils
from utils.idempotency_manager import IdempotencyManager


# ======================================================
# Func.
# ======================================================
# - clean_celery_executions_table — Celery beat task to prune old claims
# - _clean_celery_executions_table — claim and run claim cleanup idempotently
# ======================================================

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.maintenance.clean_celery_executions_table",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def clean_celery_executions_table(self):
    return asyncio.run(_clean_celery_executions_table(self))


async def _clean_celery_executions_table(task_instance):
    db_engine, vectordb_client = None, None

    try:
        (
            db_engine,
            db_client,
            _llm_provider_factory,
            _vectordb_provider_factory,
            _generation_client,
            _embedding_client,
            vectordb_client,
            _template_parser,
        ) = await get_setup_utils()

        idempotency_manager = IdempotencyManager(db_client, db_engine)
        deleted = await idempotency_manager.cleanup_old_tasks(time_retention=86400)
        logger.info("Deleted %s old task records", deleted)

        return {"deleted": deleted}

    except Exception as e:
        logger.error("Task failed: %s", str(e))
        raise
    finally:
        try:
            if db_engine:
                await db_engine.dispose()
            if vectordb_client:
                await vectordb_client.disconnect()
        except Exception as e:
            logger.error("Task failed while cleaning: %s", str(e))
