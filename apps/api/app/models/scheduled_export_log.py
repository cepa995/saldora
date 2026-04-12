"""Export log model — tracks all archive export deliveries.

Unified table for both automated monthly exports and manual
on-demand exports (previously split between scheduled_export_logs
and audit_exports).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class ScheduledExportLog(Base, UUIDMixin):
    """Tracks each archive export delivery (automated or manual).

    Provides audit trail of what was generated, when, to whom,
    and a download link for re-downloading within the expiry window.
    """

    __tablename__ = "scheduled_export_logs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False, server_default="")
    delivery_method: Mapped[str] = mapped_column(String(20), nullable=False, server_default="email")
    delivered_to: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    invoice_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Discriminator: 'scheduled' (monthly auto) or 'manual' (on-demand)
    export_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="scheduled")

    # Manual export fields
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Generated file
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Content toggles
    include_documents: Mapped[bool] = mapped_column(Boolean, server_default="true", default=True)
    include_audit_trail: Mapped[bool] = mapped_column(Boolean, server_default="true", default=True)
    include_vat_summary: Mapped[bool] = mapped_column(Boolean, server_default="true", default=True)

    __table_args__ = (
        Index("ix_sel_org_id", "organization_id"),
        Index("ix_sel_period", "period"),
        Index("ix_sel_export_type", "export_type"),
        Index("ix_sel_requested_by", "requested_by"),
    )
