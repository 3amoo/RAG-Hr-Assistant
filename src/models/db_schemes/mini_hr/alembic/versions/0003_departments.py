"""add departments

Revision ID: 0003_departments
Revises: 0002_celery_task_executions
Create Date: 2026-11-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_departments"
down_revision: Union[str, None] = "0002_celery_task_executions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("department_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("department_uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("department_id"),
    )
    op.create_index(
        "ix_departments_department_uuid",
        "departments",
        ["department_uuid"],
        unique=True,
    )
    op.create_index("ix_departments_name", "departments", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_departments_name", table_name="departments")
    op.drop_index("ix_departments_department_uuid", table_name="departments")
    op.drop_table("departments")
