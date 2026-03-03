"""AccountingIntent schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class KontoEntry(BaseModel):
    """A single konto entry in the debit/credit arrays."""

    konto: str
    name: str
    amount: str


class SuggestedKonta(BaseModel):
    """Suggested debit and credit konta."""

    debit: list[KontoEntry] = Field(default_factory=list)
    credit: list[KontoEntry] = Field(default_factory=list)


class AccountingIntentReviewRequest(BaseModel):
    """Request body for marking an accounting intent as reviewed."""

    notes: str | None = None


class AccountingIntentResponse(BaseModel):
    """Full accounting intent response."""

    id: UUID
    invoice_id: UUID
    organization_id: UUID

    # Classification
    document_type: str
    transaction_type: str
    vat_treatment: str
    is_deductible: bool

    # Financial data
    vat_breakdown: dict = Field(default_factory=dict)
    suggested_konta: dict = Field(default_factory=dict)

    # Future fields
    pdv_book_entries: dict = Field(default_factory=dict)
    applied_rules: list = Field(default_factory=list)

    # Confidence
    confidence: Decimal

    # Review
    requires_review: bool
    review_reasons: list[str] = Field(default_factory=list)
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None

    # Notes
    notes: str | None = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
