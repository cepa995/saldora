"""
Denormalized invoice line item model.

Read-optimized copy of line items from the invoices.line_items
JSON column. Populated at OCR completion and on user edits.
The JSON column remains the source of truth.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class InvoiceLineItem(Base, UUIDMixin):
    """Denormalized invoice line item for reporting queries."""

    __tablename__ = "invoice_line_items"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_catalog.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    quantity: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    discount: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    tax_base: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    total: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    tax_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    tax_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    seller_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seller_pib: Mapped[str | None] = mapped_column(String(20), nullable=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RSD")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_ili_invoice_id", "invoice_id"),
        Index("ix_ili_org_id", "organization_id"),
        Index("ix_ili_description", "description"),
        Index("ix_ili_seller_pib", "seller_pib"),
        Index("ix_ili_invoice_date", "invoice_date"),
        Index("ix_ili_org_date", "organization_id", "invoice_date"),
    )
