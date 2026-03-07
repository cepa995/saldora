"""SEF (eFaktura) schemas.

Response schemas match the frontend TypeScript types defined in
apps/web/src/lib/types/sef.ts exactly.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class SefInvoiceResponse(BaseModel):
    """Single SEF invoice — matches frontend SefInvoice interface."""

    id: UUID
    sef_id: str
    status: Literal["new", "pending", "processed", "rejected", "archived"]
    invoice_number: str | None = None
    supplier_name: str | None = None
    supplier_pib: str | None = None
    amount: str | None = None
    currency: str = "RSD"
    invoice_date: str | None = None
    received_at: str
    processed_invoice_id: str | None = None
    created_at: str
    updated_at: str


class SefPaginationInfo(BaseModel):
    """Pagination metadata — matches frontend SefPaginationInfo."""

    page: int
    per_page: int
    total: int
    total_pages: int


class SefListResponse(BaseModel):
    """Paginated list of SEF invoices — matches frontend SefListResponse."""

    data: list[SefInvoiceResponse]
    pagination: SefPaginationInfo


class SefSyncStatusResponse(BaseModel):
    """Sync status — matches frontend SefSyncStatus."""

    last_sync_at: str | None = None
    pending_count: int = 0
    is_syncing: bool = False
