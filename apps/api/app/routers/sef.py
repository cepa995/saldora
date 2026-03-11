"""SEF (eFaktura) inbox router.

Provides endpoints for listing, viewing, processing, rejecting, and
archiving SEF invoices, as well as triggering and checking sync status.
All endpoints match the frontend contract in apps/web/src/lib/api/sef.ts.
"""

import logging
import math
from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_feature, require_role
from app.models.sef_invoice import SefInvoice
from app.models.user import User
from app.plans import Feature
from app.schemas.sef import (
    SefInvoiceResponse,
    SefListResponse,
    SefPaginationInfo,
    SefSyncStatusResponse,
)
from app.services.sef.process import process_sef_invoice
from app.services.sef.sync import get_sync_status, sync_sef_invoices

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_feature(Feature.SEF_INTEGRATION))])


def _serialize_sef_invoice(inv: SefInvoice) -> SefInvoiceResponse:
    """Convert a SefInvoice model to the response schema.

    Args:
        inv: SefInvoice database model instance.

    Returns:
        SefInvoiceResponse matching frontend SefInvoice interface.
    """
    return SefInvoiceResponse(
        id=inv.id,
        sef_id=inv.sef_id,
        status=inv.status,
        invoice_number=inv.invoice_number,
        supplier_name=inv.supplier_name,
        supplier_pib=inv.supplier_pib,
        amount=str(inv.amount) if inv.amount is not None else None,
        currency=inv.currency,
        invoice_date=inv.invoice_date.isoformat() if inv.invoice_date else None,
        received_at=inv.received_at.isoformat(),
        processed_invoice_id=str(inv.invoice_id) if inv.invoice_id else None,
        created_at=inv.created_at.isoformat(),
        updated_at=inv.updated_at.isoformat(),
    )


# Allowed sort columns (whitelist to prevent SQL injection)
_SORT_COLUMNS = {
    "received_at": SefInvoice.received_at,
    "amount": SefInvoice.amount,
    "status": SefInvoice.status,
    "invoice_date": SefInvoice.invoice_date,
}


@router.get("/inbox", response_model=SefListResponse)
async def list_sef_invoices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None),
    sort: Literal["received_at", "amount", "status", "invoice_date"] = Query(default="received_at"),
    order: Literal["asc", "desc"] = Query(default="desc"),
) -> SefListResponse:
    """List SEF inbox invoices with filtering, sorting, and pagination.

    Args:
        db: Database session.
        user: Authenticated user.
        page: Page number (1-indexed).
        per_page: Items per page (max 100).
        status_filter: Filter by internal status.
        date_from: Filter invoices received on or after this date.
        date_to: Filter invoices received on or before this date.
        search: Search in invoice_number, supplier_name, supplier_pib.
        sort: Column to sort by.
        order: Sort direction.

    Returns:
        Paginated list of SEF invoices.
    """
    org_id = user.organization_id

    # Base query
    query = select(SefInvoice).where(
        SefInvoice.organization_id == org_id,
        SefInvoice.direction == "INBOUND",
    )
    count_query = (
        select(func.count())
        .select_from(SefInvoice)
        .where(
            SefInvoice.organization_id == org_id,
            SefInvoice.direction == "INBOUND",
        )
    )

    # Apply filters
    if status_filter:
        query = query.where(SefInvoice.status == status_filter)
        count_query = count_query.where(SefInvoice.status == status_filter)

    if date_from:
        query = query.where(func.date(SefInvoice.received_at) >= date_from)
        count_query = count_query.where(func.date(SefInvoice.received_at) >= date_from)

    if date_to:
        query = query.where(func.date(SefInvoice.received_at) <= date_to)
        count_query = count_query.where(func.date(SefInvoice.received_at) <= date_to)

    if search:
        search_term = f"%{search}%"
        search_filter = or_(
            SefInvoice.invoice_number.ilike(search_term),
            SefInvoice.supplier_name.ilike(search_term),
            SefInvoice.supplier_pib.ilike(search_term),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = max(1, math.ceil(total / per_page))

    # Apply sorting
    sort_column = _SORT_COLUMNS.get(sort, SefInvoice.received_at)
    order_func = desc if order == "desc" else asc
    query = query.order_by(order_func(sort_column))

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    # Execute
    result = await db.execute(query)
    invoices = result.scalars().all()

    return SefListResponse(
        data=[_serialize_sef_invoice(inv) for inv in invoices],
        pagination=SefPaginationInfo(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        ),
    )


@router.get("/inbox/{invoice_id}", response_model=SefInvoiceResponse)
async def get_sef_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SefInvoiceResponse:
    """Get a single SEF invoice by ID.

    Args:
        invoice_id: UUID of the SEF invoice.
        db: Database session.
        user: Authenticated user.

    Returns:
        Full SEF invoice response.

    Raises:
        HTTPException: 404 if not found.
    """
    result = await db.execute(
        select(SefInvoice).where(
            SefInvoice.id == invoice_id,
            SefInvoice.organization_id == user.organization_id,
        )
    )
    inv = result.scalar_one_or_none()

    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SEF invoice not found",
        )

    return _serialize_sef_invoice(inv)


@router.post("/inbox/{invoice_id}/process", response_model=SefInvoiceResponse)
async def process_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> SefInvoiceResponse:
    """Process a SEF invoice — creates a FakturaAI invoice from it.

    Args:
        invoice_id: UUID of the SEF invoice to process.
        db: Database session.
        user: Authenticated user.

    Returns:
        Updated SEF invoice with status 'processed'.

    Raises:
        HTTPException: 404 if not found, 409 if already processed.
    """
    try:
        sef_inv = await process_sef_invoice(db, invoice_id, user.organization_id)
        return _serialize_sef_invoice(sef_inv)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post("/inbox/{invoice_id}/reject", response_model=SefInvoiceResponse)
async def reject_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> SefInvoiceResponse:
    """Reject a SEF invoice.

    Args:
        invoice_id: UUID of the SEF invoice to reject.
        db: Database session.
        user: Authenticated user.

    Returns:
        Updated SEF invoice with status 'rejected'.

    Raises:
        HTTPException: 404 if not found, 409 if not in valid state.
    """
    result = await db.execute(
        select(SefInvoice).where(
            SefInvoice.id == invoice_id,
            SefInvoice.organization_id == user.organization_id,
        )
    )
    inv = result.scalar_one_or_none()

    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SEF invoice not found",
        )

    if inv.status in ("processed", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reject invoice with status '{inv.status}'",
        )

    inv.status = "rejected"
    await db.commit()
    await db.refresh(inv)

    return _serialize_sef_invoice(inv)


@router.post("/inbox/{invoice_id}/archive", response_model=SefInvoiceResponse)
async def archive_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> SefInvoiceResponse:
    """Archive a SEF invoice without processing.

    Args:
        invoice_id: UUID of the SEF invoice to archive.
        db: Database session.
        user: Authenticated user.

    Returns:
        Updated SEF invoice with status 'archived'.

    Raises:
        HTTPException: 404 if not found.
    """
    result = await db.execute(
        select(SefInvoice).where(
            SefInvoice.id == invoice_id,
            SefInvoice.organization_id == user.organization_id,
        )
    )
    inv = result.scalar_one_or_none()

    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SEF invoice not found",
        )

    inv.status = "archived"
    await db.commit()
    await db.refresh(inv)

    return _serialize_sef_invoice(inv)


@router.post("/sync", response_model=SefSyncStatusResponse)
async def trigger_sync(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> SefSyncStatusResponse:
    """Trigger a manual sync with the SEF system.

    Acquires a Redis lock to prevent concurrent syncs.

    Args:
        request: FastAPI request (for Redis access).
        db: Database session.
        user: Authenticated user.

    Returns:
        Updated sync status after sync completes.

    Raises:
        HTTPException: 409 if sync already in progress.
    """
    redis = request.app.state.redis

    try:
        await sync_sef_invoices(db, user.organization_id, redis)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    status_data = await get_sync_status(db, user.organization_id, redis)
    return SefSyncStatusResponse(**status_data)


@router.get("/sync/status", response_model=SefSyncStatusResponse)
async def sync_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SefSyncStatusResponse:
    """Get current SEF sync status.

    Args:
        request: FastAPI request (for Redis access).
        db: Database session.
        user: Authenticated user.

    Returns:
        Sync status including last sync time and pending count.
    """
    redis = request.app.state.redis
    status_data = await get_sync_status(db, user.organization_id, redis)
    return SefSyncStatusResponse(**status_data)
