"""Invoice model."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization


class Invoice(Base, UUIDMixin, TimestampMixin):
    """
    An invoice processed through OCR pipeline

    Lifecycle: processing -> review -> verified -> exported
    -> error (at any point)
    """

    __tablename__ = "invoices"

    # Ownership
    organization_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="processing", index=True
    )  # processing, review, verified, exported, error

    # Core fields (populated by OCR)
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    invoice_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)

    # Parties (stored as JSON for schema flexibility)
    seller: Mapped[dict | None] = mapped_column(JSON)
    buyer: Mapped[dict | None] = mapped_column(JSON)

    # Amounts (Numeric for exact decimal math - NEVER use Float for money)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(String(3), default="RSD")

    # Line items
    line_items: Mapped[list | None] = mapped_column(JSON)

    # Document reference
    document_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    document_path: Mapped[str | None] = mapped_column(String(500))
    document_content_type: Mapped[str | None] = mapped_column(String(100))

    # OCR Metadata
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    field_confidence: Mapped[dict | None] = mapped_column(JSON)
    warnings: Mapped[list | None] = mapped_column(JSON)
    ocr_engine: Mapped[str | None] = mapped_column(String(50))
    processing_time_ms: Mapped[int | None] = mapped_column()
    raw_ocr_text: Mapped[str | None] = mapped_column(Text)

    # Relationships
    organization: Mapped[Organization] = relationship(back_populates="invoices")
