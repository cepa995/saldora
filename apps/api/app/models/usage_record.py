"""Usage record model — tracks monthly resource usage per organization."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization


class UsageRecord(Base, UUIDMixin, TimestampMixin):
    """Monthly usage snapshot for an organization.

    One record per organization per billing period (calendar month).
    Updated incrementally as invoices are created and storage is consumed.
    """

    __tablename__ = "usage_records"
    __table_args__ = (
        Index(
            "uq_usage_org_period",
            "organization_id",
            "period_start",
            unique=True,
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    invoices_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    api_calls_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    storage_bytes: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")

    # Relationship
    organization: Mapped[Organization] = relationship()
