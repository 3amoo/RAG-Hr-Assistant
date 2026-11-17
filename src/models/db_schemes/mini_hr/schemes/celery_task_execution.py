from sqlalchemy import Column, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB

from .mini_hr_base import SQLAlchemyBase


class CeleryTaskExecution(SQLAlchemyBase):

    __tablename__ = "celery_task_executions"

    execution_id = Column(Integer, primary_key=True, autoincrement=True)

    task_name = Column(String(255), nullable=False)
    task_args_hash = Column(String(64), nullable=False)
    # Celery task ids are UUID strings. Keep this as a string so a task id can
    # be stored directly without converting it to uuid.UUID first.
    celery_task_id = Column(String(36), nullable=True)

    status = Column(String(20), nullable=False, default="PENDING")

    task_args = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("ixz_task_name_args_hash", task_name, task_args_hash, unique=True),
        Index("ixz_task_execution_status", status),
        Index("ixz_task_execution_created_at", created_at),
        Index("ixz_celery_task_id", celery_task_id),
    )
