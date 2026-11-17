"""add celery task executions

Revision ID: 0002_celery_task_executions
Revises: 0001_initial
Create Date: 2026-11-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_celery_task_executions"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "celery_task_executions",
        sa.Column("execution_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("task_args_hash", sa.String(length=64), nullable=False),
        sa.Column("celery_task_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("task_args", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("execution_id"),
    )
    op.create_index(
        "ixz_task_name_args_hash",
        "celery_task_executions",
        ["task_name", "task_args_hash"],
        unique=True,
    )
    op.create_index(
        "ixz_task_execution_status",
        "celery_task_executions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ixz_task_execution_created_at",
        "celery_task_executions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ixz_celery_task_id",
        "celery_task_executions",
        ["celery_task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ixz_celery_task_id", table_name="celery_task_executions")
    op.drop_index("ixz_task_execution_created_at", table_name="celery_task_executions")
    op.drop_index("ixz_task_execution_status", table_name="celery_task_executions")
    op.drop_index("ixz_task_name_args_hash", table_name="celery_task_executions")
    op.drop_table("celery_task_executions")
