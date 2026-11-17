import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.db_schemes.mini_hr.schemes.celery_task_execution import CeleryTaskExecution


class IdempotencyManager:

    def __init__(self, db_client, db_engine):
        self.db_client = db_client
        self.db_engine = db_engine

    def create_args_hash(self, task_name: str, task_args: dict):
        combined_data = {
            **task_args,
            "task_name": task_name,
        }
        json_string = json.dumps(combined_data, sort_keys=True, default=str)
        return hashlib.sha256(json_string.encode()).hexdigest()

    @staticmethod
    def _retry_condition(existing, now, task_time_limit):
        """Build a guarded WHERE clause for taking over an existing task.

        The guard always includes the row's current status (and its old
        ``started_at`` for stale running tasks), so only one worker can claim a
        retry. Return ``None`` when the task must not be retried.
        """
        if existing.status == "SUCCESS":
            return None

        if existing.status in ("PENDING", "STARTED", "RETRY"):
            started_at = existing.started_at or existing.created_at
            if started_at is None:
                return None
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            stale_before = now - timedelta(seconds=task_time_limit + 60)
            if started_at > stale_before:
                return None
            return and_(
                CeleryTaskExecution.status == existing.status,
                func.coalesce(
                    CeleryTaskExecution.started_at, CeleryTaskExecution.created_at
                ) <= stale_before,
            )

        # FAILURE or any other terminal state can be retried safely.
        return CeleryTaskExecution.status == existing.status

    async def claim_task(self, task_name: str, task_args: dict,
                         celery_task_id: str = None,
                         task_time_limit: int = 600):
        """Atomically claim one execution for ``(task_name, task_args)``.

        Returns ``(record, claimed)``. Exactly one concurrent worker receives
        ``claimed=True``; every other worker gets the winning row back and
        should skip execution. This replaces the old check-then-insert flow,
        which raced when the queue held the same task more than once.
        """
        args_hash = self.create_args_hash(task_name, task_args)
        now = datetime.now(timezone.utc)

        async with self.db_client() as session:
            insert_stmt = (
                pg_insert(CeleryTaskExecution)
                .values(
                    task_name=task_name,
                    task_args_hash=args_hash,
                    task_args=task_args,
                    celery_task_id=celery_task_id,
                    status="PENDING",
                    started_at=now,
                )
                .on_conflict_do_nothing(
                    index_elements=["task_name", "task_args_hash"]
                )
                .returning(CeleryTaskExecution)
            )
            record = (await session.execute(insert_stmt)).scalar_one_or_none()
            if record is not None:
                await session.commit()
                return record, True

            # Another worker recorded this task first. Take over only a failed
            # or stale attempt, using a guarded UPDATE so two workers cannot
            # both claim the same retry.
            existing = (
                await session.execute(
                    select(CeleryTaskExecution).where(
                        CeleryTaskExecution.task_name == task_name,
                        CeleryTaskExecution.task_args_hash == args_hash,
                    )
                )
            ).scalar_one_or_none()

            if existing is None:
                return None, False

            # Do not call rollback() here: it expires ``existing`` and the
            # caller needs its loaded attributes after the session closes.
            condition = self._retry_condition(existing, now, task_time_limit)
            if condition is None:
                return existing, False

            update_stmt = (
                update(CeleryTaskExecution)
                .where(CeleryTaskExecution.execution_id == existing.execution_id)
                .where(condition)
                .values(
                    status="PENDING",
                    celery_task_id=celery_task_id,
                    started_at=now,
                    completed_at=None,
                    result=None,
                )
                .returning(CeleryTaskExecution)
            )
            claimed = (await session.execute(update_stmt)).scalar_one_or_none()
            await session.commit()
            if claimed is None:
                return existing, False
            return claimed, True

    async def update_task_status(self, execution_id: int, status: str,
                                 result: dict = None, celery_task_id: str = None):
        """Update a task status and, optionally, its Celery task id."""
        async with self.db_client() as session:
            task_record = await session.get(CeleryTaskExecution, execution_id)
            if task_record:
                task_record.status = status
                if result is not None:
                    task_record.result = result
                if celery_task_id is not None:
                    task_record.celery_task_id = celery_task_id
                if status in ("SUCCESS", "FAILURE"):
                    task_record.completed_at = datetime.now(timezone.utc)
                await session.commit()

    async def cleanup_old_tasks(self, time_retention: int = 86400) -> int:
        """Delete task records older than ``time_retention`` seconds."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=time_retention)

        async with self.db_client() as session:
            stmt = delete(CeleryTaskExecution).where(
                CeleryTaskExecution.created_at < cutoff_time
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount
