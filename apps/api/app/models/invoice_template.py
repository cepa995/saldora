"""Invoice template model for layout-based extraction without LLM."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class InvoiceTemplate(Base, UUIDMixin, TimestampMixin):
    """Learned invoice layout template for a specific seller.

    Stores the structural fingerprint and field extraction rules derived
    from a successful LLM extraction. When a new invoice matches the
    fingerprint, fields are extracted using coordinates and regex patterns
    instead of calling the LLM — reducing cost to zero for recurring
    supplier layouts.

    Attributes:
        organization_id: Owning organization (multi-tenant scoping).
        seller_pib: Seller tax ID this template applies to.
        seller_name: Seller company name (for display).
        layout_fingerprint: SHA-256 hash of structural layout elements.
        field_mappings: Per-field extraction rules (bounding boxes,
            labels, regex patterns, value formats).
        line_item_mappings: Extraction rules for repeating line item
            regions (header row, data rows, column positions).
        sample_invoice_id: Invoice this template was learned from.
        usage_count: Number of times this template was used.
        success_count: Number of successful extractions (no LLM fallback).
        success_rate: Percentage of extractions that succeeded without LLM.
        is_active: Whether this template is available for matching.
        last_used_at: When this template was last used for extraction.
    """

    __tablename__ = "invoice_templates"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    seller_pib: Mapped[str] = mapped_column(String(20), nullable=False)
    seller_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    layout_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)

    field_mappings: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    line_item_mappings: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    sample_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
    )

    usage_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    success_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    success_rate: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0.0", nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
