"""Invoice schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CompanyInfo(BaseModel):
    """Company information extracted from invoice."""

    pib: str | None = Field(default=None, description="Tax ID (PIB) - 9 digits")
    mb: str | None = Field(default=None, description="Registration number (MB) - 8 digits")
    name: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    verified: bool = Field(default=False, description="APR verification status")
    apr_status: str | None = Field(default=None, description="APR company status")


class LineItem(BaseModel):
    """Invoice line item."""

    description: str
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    total: Decimal | None = None
    tax_rate: Decimal | None = None
    tax_amount: Decimal | None = None


class TaxGroup(BaseModel):
    """A single tax rate group from invoice breakdown."""

    rate: Decimal
    base_amount: Decimal
    tax_amount: Decimal


class FieldConfidence(BaseModel):
    """Confidence score for an extracted field."""

    field_name: str
    value: str
    confidence: float = Field(ge=0, le=100)
    needs_review: bool = Field(default=False)


class InvoiceCreate(BaseModel):
    """Schema for manual invoice creation."""

    invoice_number: str
    invoice_date: date
    due_date: date | None = None
    seller_pib: str
    seller_name: str
    buyer_pib: str | None = None
    buyer_name: str | None = None
    subtotal: Decimal
    tax_rate: Decimal = Field(default=Decimal("20.00"))
    tax_amount: Decimal
    total_amount: Decimal
    currency: str = Field(default="RSD")
    line_items: list[LineItem] = Field(default_factory=list)


class InvoiceUpdate(BaseModel):
    """Schema for invoice update (partial)."""

    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    seller_pib: str | None = None
    seller_mb: str | None = None
    seller_name: str | None = None
    seller_address: str | None = None
    seller_city: str | None = None
    seller_postal_code: str | None = None
    buyer_pib: str | None = None
    buyer_mb: str | None = None
    buyer_name: str | None = None
    buyer_address: str | None = None
    buyer_city: str | None = None
    buyer_postal_code: str | None = None
    subtotal: Decimal | None = None
    tax_rate: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None
    currency: str | None = None
    line_items: list[LineItem] | None = None
    tax_groups: list[TaxGroup] | None = None


class InvoiceResponse(BaseModel):
    """Full invoice response."""

    id: UUID
    status: Literal["processing", "review", "verified", "exported", "error"]
    confidence_score: float | None = Field(ge=0, le=100)

    # Core fields
    invoice_number: str | None
    invoice_date: date | None
    due_date: date | None

    # Parties
    seller: CompanyInfo | None
    buyer: CompanyInfo | None

    # Amounts
    subtotal: Decimal | None
    tax_rate: Decimal | None
    tax_amount: Decimal | None
    total_amount: Decimal | None
    currency: str = "RSD"

    # Line items
    line_items: list[LineItem] = Field(default_factory=list)

    # Tax breakdown by rate
    tax_groups: list[TaxGroup] = Field(default_factory=list)

    # Confidence details
    field_confidences: list[FieldConfidence] = Field(default_factory=list)

    # Warnings and flags
    warnings: list[str] = Field(default_factory=list)
    blocked: bool = Field(default=False, description="Export blocked due to errors")
    field_warnings: dict[str, str] = Field(
        default_factory=dict,
        description="field_name → severity ('error'|'warning')",
    )

    # Document
    document_url: str | None = None

    # OCR debug data
    raw_ocr_text: str | None = Field(default=None, description="Raw OCR output text")
    raw_llm_output: str | None = Field(default=None, description="Raw LLM extraction JSON")

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    """Paginated list of invoices."""

    data: list[InvoiceResponse]
    pagination: dict = Field(
        default_factory=lambda: {
            "page": 1,
            "per_page": 20,
            "total": 0,
            "total_pages": 0,
        }
    )


class ProcessingStatus(BaseModel):
    """Invoice processing status."""

    id: UUID
    status: Literal["uploaded", "queued", "processing", "completed", "failed"]
    progress: int = Field(ge=0, le=100, default=0)
    stage: str | None = Field(
        default=None,
        description="Current processing sub-stage",
    )
    estimated_time: int | None = Field(
        default=None, description="Estimated remaining time in seconds"
    )
    error_message: str | None = None
    document_id: UUID | None = None
    created_at: datetime
