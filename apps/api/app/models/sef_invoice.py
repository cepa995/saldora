"""SEF invoice model."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class SefInvoice(Base, UUIDMixin, TimestampMixin):
    """An invoice received from or sent to the SEF system.

    Tracks both an internal status for UI display and the raw SEF status
    for system fidelity. Linked to a Saldora Invoice after processing.
    """

    __tablename__ = "sef_invoices"
    __table_args__ = (
        UniqueConstraint("organization_id", "sef_id", name="uq_sef_invoices_org_sef_id"),
        Index("ix_sef_invoices_org_id", "organization_id"),
        Index("ix_sef_invoices_status", "status"),
        Index("ix_sef_invoices_sef_status", "sef_status"),
        Index("ix_sef_invoices_invoice_id", "invoice_id"),
        Index("ix_sef_invoices_received_at", "received_at"),
    )

    # Ownership
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Link to Saldora invoice (set after processing)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
    )

    # SEF identifiers
    sef_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sef_internal_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cir_invoice_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Internal status for UI: new, pending, processed, rejected, archived
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)

    # Raw SEF status: DELIVERED, SEEN, APPROVED, REJECTED, CANCELLED, PAID, STORNO, ERROR
    sef_status: Mapped[str] = mapped_column(String(30), nullable=False)
    sef_status_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Direction
    direction: Mapped[str] = mapped_column(String(10), default="INBOUND", nullable=False)

    # Invoice summary fields (denormalized for list display)
    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_pib: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="RSD")
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # When the invoice was received from SEF
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Raw SEF data
    ubl_xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    sef_response_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Processing metadata
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization = relationship("Organization", backref="sef_invoices")
    invoice = relationship("Invoice", backref="sef_invoice")
