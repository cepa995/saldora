"""Saldora invoice reports router — five analytical report templates."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.line_item import InvoiceLineItem
from app.models.user import User
from app.schemas.report import (
    ExpenseSummaryBucket,
    ExpenseSummaryResponse,
    MonthlyBreakdownItem,
    MonthlyBreakdownResponse,
    PriceComparisonItem,
    PriceComparisonResponse,
    ReceivedGoodsItem,
    ReceivedGoodsResponse,
    SpendingBySupplierItem,
    SpendingBySupplierResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Shared filter helper
# ---------------------------------------------------------------------------


def _build_conditions(
    org_id,
    date_from: date | None,
    date_to: date | None,
    seller_pib: str | None,
    search: str | None,
) -> list:
    """Build a list of SQLAlchemy WHERE conditions for line item queries.

    Args:
        org_id: Organization UUID to scope results.
        date_from: Inclusive lower bound for invoice_date.
        date_to: Inclusive upper bound for invoice_date.
        seller_pib: Exact PIB filter; skipped when None.
        search: Case-insensitive substring filter on description; skipped when None.

    Returns:
        List of SQLAlchemy column expressions suitable for .where(*conditions).
    """
    conditions = [InvoiceLineItem.organization_id == org_id]
    if date_from:
        conditions.append(InvoiceLineItem.invoice_date >= date_from)
    if date_to:
        conditions.append(InvoiceLineItem.invoice_date <= date_to)
    if seller_pib:
        conditions.append(InvoiceLineItem.seller_pib == seller_pib)
    if search:
        conditions.append(InvoiceLineItem.description.ilike(f"%{search}%"))
    return conditions


# ---------------------------------------------------------------------------
# 1. Received Goods
# ---------------------------------------------------------------------------


@router.get("/received-goods", response_model=ReceivedGoodsResponse)
async def get_received_goods(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    seller_pib: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> ReceivedGoodsResponse:
    """Return received goods aggregated by line item description.

    Groups all matching line items by description and aggregates quantity,
    amount, average unit price, and distinct supplier information.
    Results are ordered by total_amount descending.

    Args:
        db: Database session.
        user: Authenticated user.
        date_from: Inclusive start date filter on invoice_date.
        date_to: Inclusive end date filter on invoice_date.
        seller_pib: Filter to a specific supplier by PIB.
        search: Case-insensitive substring filter on description.

    Returns:
        Aggregated received-goods rows with grand total and item count.
    """
    conditions = _build_conditions(user.organization_id, date_from, date_to, seller_pib, search)

    query = (
        select(
            InvoiceLineItem.description,
            func.sum(InvoiceLineItem.quantity).label("total_quantity"),
            func.sum(InvoiceLineItem.total).label("total_amount"),
            func.avg(InvoiceLineItem.unit_price).label("avg_unit_price"),
            func.count(func.distinct(InvoiceLineItem.seller_pib)).label("supplier_count"),
            func.array_agg(func.distinct(InvoiceLineItem.seller_name)).label("suppliers"),
        )
        .where(*conditions)
        .group_by(InvoiceLineItem.description)
        .order_by(func.sum(InvoiceLineItem.total).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    items = [
        ReceivedGoodsItem(
            description=row.description,
            total_quantity=float(row.total_quantity) if row.total_quantity is not None else None,
            total_amount=float(row.total_amount),
            avg_unit_price=float(row.avg_unit_price) if row.avg_unit_price is not None else None,
            supplier_count=row.supplier_count,
            suppliers=[s for s in (row.suppliers or []) if s is not None],
        )
        for row in rows
    ]

    grand_total = sum(item.total_amount for item in items)
    return ReceivedGoodsResponse(items=items, grand_total=grand_total, item_count=len(items))


# ---------------------------------------------------------------------------
# 2. Spending by Supplier
# ---------------------------------------------------------------------------


@router.get("/spending-by-supplier", response_model=SpendingBySupplierResponse)
async def get_spending_by_supplier(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    seller_pib: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> SpendingBySupplierResponse:
    """Return total spending grouped by supplier.

    Aggregates line item totals and distinct invoice counts per supplier,
    ordered by total_amount descending.

    Args:
        db: Database session.
        user: Authenticated user.
        date_from: Inclusive start date filter on invoice_date.
        date_to: Inclusive end date filter on invoice_date.
        seller_pib: Filter to a specific supplier by PIB.
        search: Case-insensitive substring filter on description.

    Returns:
        Per-supplier spending rows with grand total.
    """
    conditions = _build_conditions(user.organization_id, date_from, date_to, seller_pib, search)

    query = (
        select(
            InvoiceLineItem.seller_pib,
            InvoiceLineItem.seller_name,
            func.sum(InvoiceLineItem.total).label("total_amount"),
            func.count(func.distinct(InvoiceLineItem.invoice_id)).label("invoice_count"),
        )
        .where(*conditions)
        .group_by(InvoiceLineItem.seller_pib, InvoiceLineItem.seller_name)
        .order_by(func.sum(InvoiceLineItem.total).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    items = [
        SpendingBySupplierItem(
            seller_name=row.seller_name,
            seller_pib=row.seller_pib,
            total_amount=float(row.total_amount),
            invoice_count=row.invoice_count,
        )
        for row in rows
    ]

    grand_total = sum(item.total_amount for item in items)
    return SpendingBySupplierResponse(items=items, grand_total=grand_total)


# ---------------------------------------------------------------------------
# 3. Monthly Breakdown
# ---------------------------------------------------------------------------


@router.get("/monthly-breakdown", response_model=MonthlyBreakdownResponse)
async def get_monthly_breakdown(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    seller_pib: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=500),
) -> MonthlyBreakdownResponse:
    """Return a paginated list of individual line items ordered by date.

    Fetches all matching line items with full detail for granular monthly
    analysis. Results are ordered by invoice_date desc then created_at desc.

    Args:
        db: Database session.
        user: Authenticated user.
        date_from: Inclusive start date filter on invoice_date.
        date_to: Inclusive end date filter on invoice_date.
        seller_pib: Filter to a specific supplier by PIB.
        search: Case-insensitive substring filter on description.
        page: Page number (1-based).
        per_page: Number of items per page (max 500).

    Returns:
        Paginated line items with aggregate total amount and total row count.
    """
    conditions = _build_conditions(user.organization_id, date_from, date_to, seller_pib, search)

    # Aggregate totals across the full result set
    agg_query = select(
        func.sum(InvoiceLineItem.total).label("total_amount"),
        func.count().label("item_count"),
    ).where(*conditions)
    agg_result = await db.execute(agg_query)
    agg_row = agg_result.one()
    total_amount = float(agg_row.total_amount or 0)
    item_count = agg_row.item_count or 0

    # Paginated rows
    offset = (page - 1) * per_page
    rows_query = (
        select(InvoiceLineItem)
        .where(*conditions)
        .order_by(
            InvoiceLineItem.invoice_date.desc().nullslast(),
            InvoiceLineItem.created_at.desc(),
        )
        .offset(offset)
        .limit(per_page)
    )
    rows_result = await db.execute(rows_query)
    rows = rows_result.scalars().all()

    items = [
        MonthlyBreakdownItem(
            id=str(row.id),
            invoice_id=str(row.invoice_id),
            description=row.description,
            quantity=float(row.quantity) if row.quantity is not None else None,
            unit_price=float(row.unit_price) if row.unit_price is not None else None,
            total=float(row.total),
            tax_rate=float(row.tax_rate) if row.tax_rate is not None else None,
            seller_name=row.seller_name,
            invoice_date=row.invoice_date.isoformat() if row.invoice_date is not None else None,
        )
        for row in rows
    ]

    return MonthlyBreakdownResponse(
        items=items,
        total_amount=total_amount,
        item_count=item_count,
    )


# ---------------------------------------------------------------------------
# 4. Price Comparison
# ---------------------------------------------------------------------------


@router.get("/price-comparison", response_model=PriceComparisonResponse)
async def get_price_comparison(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    seller_pib: str | None = Query(default=None),
    search: str = Query(...),
) -> PriceComparisonResponse:
    """Return price statistics grouped by description and supplier.

    Requires a search term to narrow the comparison to relevant items.
    Returns min, max, and average unit prices per (description, supplier)
    combination, useful for identifying pricing discrepancies.

    Args:
        db: Database session.
        user: Authenticated user.
        date_from: Inclusive start date filter on invoice_date.
        date_to: Inclusive end date filter on invoice_date.
        seller_pib: Filter to a specific supplier by PIB.
        search: Required description substring filter (case-insensitive).

    Returns:
        Aggregated price comparison rows ordered by description then avg_unit_price.

    Raises:
        HTTPException: 422 if search parameter is missing (enforced by FastAPI).
    """
    conditions = _build_conditions(user.organization_id, date_from, date_to, seller_pib, search)

    query = (
        select(
            InvoiceLineItem.description,
            InvoiceLineItem.seller_name,
            InvoiceLineItem.seller_pib,
            func.avg(InvoiceLineItem.unit_price).label("avg_unit_price"),
            func.min(InvoiceLineItem.unit_price).label("min_unit_price"),
            func.max(InvoiceLineItem.unit_price).label("max_unit_price"),
            func.sum(InvoiceLineItem.quantity).label("total_quantity"),
            func.count(func.distinct(InvoiceLineItem.invoice_id)).label("invoice_count"),
        )
        .where(*conditions)
        .group_by(
            InvoiceLineItem.description,
            InvoiceLineItem.seller_pib,
            InvoiceLineItem.seller_name,
        )
        .order_by(
            InvoiceLineItem.description,
            func.avg(InvoiceLineItem.unit_price),
        )
    )

    result = await db.execute(query)
    rows = result.all()

    items = [
        PriceComparisonItem(
            description=row.description,
            seller_name=row.seller_name,
            seller_pib=row.seller_pib,
            avg_unit_price=float(row.avg_unit_price) if row.avg_unit_price is not None else None,
            min_unit_price=float(row.min_unit_price) if row.min_unit_price is not None else None,
            max_unit_price=float(row.max_unit_price) if row.max_unit_price is not None else None,
            total_quantity=float(row.total_quantity) if row.total_quantity is not None else None,
            invoice_count=row.invoice_count,
        )
        for row in rows
    ]

    return PriceComparisonResponse(items=items)


# ---------------------------------------------------------------------------
# 5. Expense Summary
# ---------------------------------------------------------------------------


@router.get("/expense-summary", response_model=ExpenseSummaryResponse)
async def get_expense_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    seller_pib: str | None = Query(default=None),
    search: str | None = Query(default=None),
    group_by: str = Query(default="month"),
) -> ExpenseSummaryResponse:
    """Return total expenses bucketed by time period.

    Uses date_trunc to group line items into monthly or weekly buckets,
    providing a time-series view of spending. Results are ordered
    chronologically by period.

    Args:
        db: Database session.
        user: Authenticated user.
        date_from: Inclusive start date filter on invoice_date.
        date_to: Inclusive end date filter on invoice_date.
        seller_pib: Filter to a specific supplier by PIB.
        search: Case-insensitive substring filter on description.
        group_by: Time bucket granularity — "month" (default) or "week".

    Returns:
        Time-bucketed expense totals with grand total.

    Raises:
        HTTPException: 400 if group_by is not "month" or "week".
    """
    if group_by not in ("month", "week"):
        raise HTTPException(
            status_code=400,
            detail="group_by must be 'month' or 'week'",
        )

    conditions = _build_conditions(user.organization_id, date_from, date_to, seller_pib, search)

    period_trunc = func.date_trunc(group_by, InvoiceLineItem.invoice_date)

    query = (
        select(
            period_trunc.label("period"),
            func.sum(InvoiceLineItem.total).label("total_amount"),
            func.count().label("item_count"),
        )
        .where(*conditions)
        .group_by(period_trunc)
        .order_by(period_trunc)
    )

    result = await db.execute(query)
    rows = result.all()

    buckets = [
        ExpenseSummaryBucket(
            period=row.period.strftime("%Y-%m") if row.period is not None else "",
            total_amount=float(row.total_amount),
            item_count=row.item_count,
        )
        for row in rows
        if row.period is not None
    ]

    grand_total = sum(b.total_amount for b in buckets)
    return ExpenseSummaryResponse(buckets=buckets, grand_total=grand_total)
