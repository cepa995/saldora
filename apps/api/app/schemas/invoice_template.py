"""Pydantic schemas for invoice template CRUD."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TemplateFieldMapping(BaseModel):
    """Extraction rule for a single invoice field.

    Attributes:
        field_name: Name of the field (e.g. invoice_number, total_amount).
        label_text: Nearby label text used to locate the field.
        bbox: Bounding box region [x1, y1, x2, y2] in relative coordinates.
        regex_pattern: Regex pattern to validate/parse the extracted value.
        value_format: Expected format (e.g. 'date_dmy', 'decimal_comma', 'string').
        confidence: Confidence weight for this mapping (0.0-1.0).
    """

    field_name: str
    label_text: str | None = None
    bbox: list[float] | None = None
    regex_pattern: str | None = None
    value_format: str | None = None
    confidence: float = 1.0


class InvoiceTemplateCreate(BaseModel):
    """Schema for manually creating a template (admin use).

    Attributes:
        seller_pib: Seller tax ID.
        seller_name: Seller company name.
        layout_fingerprint: SHA-256 hash of layout structure.
        field_mappings: Per-field extraction rules.
        line_item_mappings: Line item extraction rules.
        sample_invoice_id: Invoice this template was derived from.
    """

    seller_pib: str = Field(..., max_length=20)
    seller_name: str | None = Field(None, max_length=255)
    layout_fingerprint: str = Field(..., max_length=64)
    field_mappings: dict = Field(default_factory=dict)
    line_item_mappings: dict | None = None
    sample_invoice_id: UUID | None = None


class InvoiceTemplateUpdate(BaseModel):
    """Schema for updating a template.

    Attributes:
        seller_name: Updated seller name.
        field_mappings: Updated extraction rules.
        line_item_mappings: Updated line item rules.
        is_active: Enable or disable the template.
    """

    seller_name: str | None = None
    field_mappings: dict | None = None
    line_item_mappings: dict | None = None
    is_active: bool | None = None


class InvoiceTemplateResponse(BaseModel):
    """Full template response.

    Attributes:
        id: Template UUID.
        organization_id: Owning organization.
        seller_pib: Seller tax ID.
        seller_name: Seller company name.
        layout_fingerprint: Layout hash.
        field_mappings: Per-field extraction rules.
        line_item_mappings: Line item extraction rules.
        sample_invoice_id: Source invoice UUID.
        usage_count: Times used.
        success_count: Successful extractions without LLM.
        success_rate: Success percentage.
        is_active: Whether template is active.
        last_used_at: Last usage timestamp.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: UUID
    organization_id: UUID
    seller_pib: str
    seller_name: str | None
    layout_fingerprint: str
    field_mappings: dict
    line_item_mappings: dict | None
    sample_invoice_id: UUID | None
    usage_count: int
    success_count: int
    success_rate: float
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceTemplateListResponse(BaseModel):
    """Paginated list of templates.

    Attributes:
        data: List of templates.
        pagination: Pagination metadata.
    """

    data: list[InvoiceTemplateResponse]
    pagination: dict


class TemplateStatsResponse(BaseModel):
    """Aggregated template statistics for the dashboard.

    Attributes:
        total_templates: Number of active templates.
        total_processed: Invoices processed this month.
        template_hits: Invoices processed via template (no LLM).
        llm_calls: Invoices that required LLM.
        hit_rate: Percentage of template hits.
        estimated_savings: Estimated LLM cost saved (USD).
    """

    total_templates: int
    total_processed: int
    template_hits: int
    llm_calls: int
    hit_rate: float
    estimated_savings: float
