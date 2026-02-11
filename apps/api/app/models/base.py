"""
SQLAlchemy base model and mixins.

Every table needs id, created_at, updated_at. Writing them once and
mixing them in keeps models focused on their own fields. For example:

class Invoice(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invoices"
    # Only invoice-specific fields go here
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class UUIDMixin:
    """Adds a UUID primary key."""

    id: Mapped[uuid4] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)


class TimestampMixin:
    """Adds created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
