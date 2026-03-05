"""Export schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ExportOptions(BaseModel):
    """Options for export generation."""

    include_line_items: bool = True
    nested_json: bool = False
    date_format: str = "DD.MM.YYYY"
    decimal_separator: str = ","
    delimiter: str = Field(
        default="semicolon",
        description="CSV delimiter: 'semicolon', 'comma', or 'tab'",
    )
    encoding: str = "utf-8"


class ExportRequest(BaseModel):
    """Request to export invoices.

    Attributes:
        format: Target export format.
        invoice_ids: List of invoice UUIDs to export.
        template_id: Export template to use ('default' for system default).
        options: Format-specific export options.
        skip_validation: When True, bypass blocking rules (except MiniMax
            XML verification requirement). Allows exporting invoices with
            missing fields or low confidence.
    """

    format: Literal["xlsx", "csv", "json", "minimax_xml"] = "xlsx"
    invoice_ids: list[UUID] = Field(min_length=1)
    template_id: str = "default"
    options: ExportOptions = Field(default_factory=ExportOptions)
    skip_validation: bool = False


class ExportBlockedResponse(BaseModel):
    """Response when invoices are blocked from export."""

    blocked_invoices: list[dict]
    message: str


class AuditExportRequest(BaseModel):
    """Request for audit/tax inspection export."""

    date_from: str = Field(description="Start date (YYYY-MM-DD)")
    date_to: str = Field(description="End date (YYYY-MM-DD)")
    include_documents: bool = True
    include_audit_trail: bool = True
    include_vat_summary: bool = True
    reason: str | None = Field(
        default=None,
        description="Reason for export (e.g., 'Poreska kontrola br. 123/2025')",
    )


# --- Export Template Schemas ---


class TemplateField(BaseModel):
    """A single field in an export template.

    Attributes:
        key: Field key matching INVOICE_HEADERS_SR keys.
        label: Custom display label for the column header.
        order: Display order (1-based, lower numbers appear first).
    """

    key: str = Field(description="Field key, e.g. 'invoice_number'")
    label: str = Field(max_length=100, description="Custom display label")
    order: int = Field(ge=1, description="Display order (1-based)")


class ExportTemplateCreate(BaseModel):
    """Schema for creating a custom export template.

    Attributes:
        name: Template display name.
        description: Optional longer description.
        fields: Ordered list of field definitions.
        date_format: Optional date format override.
        decimal_separator: Optional decimal separator override.
        supported_formats: Which export formats this template supports.
    """

    name: str = Field(max_length=255)
    description: str | None = None
    fields: list[TemplateField] = Field(min_length=1)
    date_format: str | None = Field(default=None, pattern=r"^(DD\.MM\.YYYY|YYYY-MM-DD)$")
    decimal_separator: str | None = Field(default=None, pattern=r"^[,.]$")
    supported_formats: list[str] | None = None


class ExportTemplateUpdate(BaseModel):
    """Schema for partially updating a custom export template.

    Attributes:
        name: New template name.
        description: New description.
        fields: New field definitions.
        date_format: New date format override.
        decimal_separator: New decimal separator override.
        supported_formats: New supported formats list.
    """

    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    fields: list[TemplateField] | None = None
    date_format: str | None = Field(default=None, pattern=r"^(DD\.MM\.YYYY|YYYY-MM-DD)$")
    decimal_separator: str | None = Field(default=None, pattern=r"^[,.]$")
    supported_formats: list[str] | None = None


class ExportTemplateResponse(BaseModel):
    """Full export template response.

    Attributes:
        id: Template UUID.
        organization_id: Owning organization (NULL for system defaults).
        name: Template display name.
        description: Optional description.
        is_default: Whether this is a system-provided template.
        fields: Ordered list of field definitions.
        date_format: Date format override, if set.
        decimal_separator: Decimal separator override, if set.
        supported_formats: Supported export formats.
        created_by: User who created the template.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: UUID
    organization_id: UUID | None
    name: str
    description: str | None
    is_default: bool
    fields: list[dict]
    date_format: str | None
    decimal_separator: str | None
    supported_formats: list[str] | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Audit Export Schemas ---


class AuditExportResponse(BaseModel):
    """Response for a completed audit export.

    Attributes:
        id: Export record UUID.
        download_url: Presigned S3 URL for downloading the ZIP.
        file_size: Size of the ZIP file in bytes.
        invoice_count: Number of invoices included.
        period: Date range of the export.
        status: Current status (processing, ready, expired).
        reason: Optional reason for the export.
        expires_at: When the download URL expires.
        created_at: When the export was requested.
    """

    id: UUID
    download_url: str | None
    file_size: int | None
    invoice_count: int | None
    period: dict
    status: str
    reason: str | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
