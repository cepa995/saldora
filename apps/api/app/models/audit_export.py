"""
AuditExport model.

Tracks audit export requests for tax inspections (Poreska Uprava).
Each record represents a generated ZIP archive containing invoice
registers, VAT summaries, audit trails, and original documents.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class AuditExport(Base, UUIDMixin, TimestampMixin):
    """Record of an audit export generated for tax inspection.

    Stores metadata about the export request, the generated file,
    and its lifecycle (processing → ready → expired).

    Attributes:
        organization_id: Organization that requested the export.
        requested_by: User who initiated the export (must be admin).
        date_from: Start of the export date range.
        date_to: End of the export date range.
        reason: Optional reason/reference for the export.
        status: Lifecycle status (processing, ready, expired).
        file_path: S3 key where the ZIP is stored.
        file_size_bytes: Size of the generated ZIP in bytes.
        invoice_count: Number of invoices included in the export.
        download_url: Presigned S3 URL for downloading.
        expires_at: When the presigned URL expires.
        include_documents: Whether original PDFs were included.
        include_audit_trail: Whether the audit trail CSV was included.
        include_vat_summary: Whether the VAT summary XLSX was included.
    """

    __tablename__ = "audit_exports"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )

    # Export parameters
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lifecycle
    status: Mapped[str] = mapped_column(String(20), default="processing", nullable=False)

    # Generated file metadata
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    invoice_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Content flags
    include_documents: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    include_audit_trail: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    include_vat_summary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    organization: Mapped[Organization] = relationship()
    requester: Mapped[User] = relationship(foreign_keys=[requested_by])

    __table_args__ = (
        Index("ix_audit_exports_org_id", "organization_id"),
        Index("ix_audit_exports_created_at", "created_at"),
    )
