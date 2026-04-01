"""Scheduled export log model — tracks automated archive deliveries."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class ScheduledExportLog(Base, UUIDMixin):
    """Tracks each automated archive export delivery.

    One row per organization per monthly export attempt.
    Provides audit trail of what was sent, when, and to whom.
    """

    __tablename__ = "scheduled_export_logs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    delivery_method: Mapped[str] = mapped_column(String(20), nullable=False, server_default="email")
    delivered_to: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    invoice_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_sel_org_id", "organization_id"),
        Index("ix_sel_period", "period"),
    )
