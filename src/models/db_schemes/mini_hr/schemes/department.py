# ======================================================
# Import Libs
# ======================================================

import uuid

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID

from .mini_hr_base import SQLAlchemyBase


# ======================================================
# Func.
# ======================================================
# - Department — SQLAlchemy model for departments
# ======================================================

class Department(SQLAlchemyBase):

    __tablename__ = "departments"

    department_id = Column(Integer, primary_key=True, autoincrement=True)
    department_uuid = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    name = Column(String(length=255), unique=True, nullable=False)
    description = Column(String(length=1000), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
