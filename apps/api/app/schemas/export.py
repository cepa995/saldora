"""Export schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ExportOptions(BaseModel):
    """Options for export generation."""

    include_line_items: bool = True
    date_format: str = "DD.MM.YYYY"
    decimal_separator: str = ","
    encoding: str = "utf-8"


class ExportRequest(BaseModel):
    """Request to export invoices."""

    format: Literal["xlsx", "csv", "json"] = "xlsx"
    invoice_ids: list[UUID] = Field(min_length=1)
    template_id: str = "default"
    options: ExportOptions = Field(default_factory=ExportOptions)


class ExportResponse(BaseModel):
    """Export generation response."""

    id: UUID
    download_url: str
    expires_at: datetime
    file_size: int = Field(description="File size in bytes")
    invoice_count: int
    format: str


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
