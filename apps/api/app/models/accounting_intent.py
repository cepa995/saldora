"""
AccountingIntent model.

Bridges extracted invoice data and accounting semantics (SRS Section 4.10).
Stores document classification, VAT treatment, suggested konta, and review
flags produced by the 5-step accounting pipeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.invoice import Invoice


class AccountingIntent(Base, UUIDMixin, TimestampMixin):
    """
    Accounting classification and VAT treatment for an invoice.

    Generated automatically when an invoice is verified. Contains the
    5-step pipeline output: document type, transaction type, VAT treatment,
    suggested konta, and review flags.
    """

    __tablename__ = "accounting_intents"

    # Context
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
    )

    # Step 1: Document classification
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # INPUT_INVOICE, OUTPUT_INVOICE, CREDIT_NOTE_IN, CREDIT_NOTE_OUT,
    # DEBIT_NOTE_IN, DEBIT_NOTE_OUT, ADVANCE_INVOICE, FINAL_INVOICE, PROFORMA

    # Step 2: Transaction type
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # DOMESTIC, FOREIGN_EU, FOREIGN_NON_EU, REVERSE_CHARGE, EXEMPT, INTERNAL

    # Step 3: VAT treatment
    vat_treatment: Mapped[str] = mapped_column(String(30), nullable=False)
    # DEDUCTIBLE_FULL, DEDUCTIBLE_PARTIAL, NON_DEDUCTIBLE,
    # OUTPUT_STANDARD, OUTPUT_REDUCED, OUTPUT_EXEMPT,
    # REVERSE_CHARGE_IN, REVERSE_CHARGE_OUT
    is_deductible: Mapped[bool] = mapped_column(Boolean, default=True)

    # Step 4: VAT breakdown and konta
    vat_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    suggested_konta: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Future: Issue #35 (PDV book mapping) and Issue #36 (rules engine)
    pdv_book_entries: Mapped[dict] = mapped_column(JSONB, default=dict)
    applied_rules: Mapped[list] = mapped_column(JSONB, default=list)

    # Confidence
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    # Review
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False)
    review_reasons: Mapped[list] = mapped_column(JSONB, default=list)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    invoice: Mapped[Invoice] = relationship(back_populates="accounting_intent")

    __table_args__ = (
        Index("ix_accounting_intents_invoice_id", "invoice_id"),
        Index("ix_accounting_intents_organization_id", "organization_id"),
        Index(
            "ix_accounting_intents_requires_review",
            "requires_review",
            postgresql_where="requires_review = true",
        ),
        Index(
            "ix_accounting_intents_doc_txn_type",
            "document_type",
            "transaction_type",
        ),
    )
