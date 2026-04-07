"""Saldora invoice reports router — analytical report templates.

Includes 5 general reports plus restaurant-specific reports
(kalkulacija, RUC, spending by category).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.line_item import InvoiceLineItem
from app.models.product_catalog import ProductCatalog
from app.models.user import User
from app.models.invoice import Invoice
from app.schemas.report import (
    AgingBucket,
    AgingResponse,
    CategorySpendingItem,
    CategorySpendingResponse,
    ExpenseSummaryBucket,
    ExpenseSummaryResponse,
    KalkulacijaItem,
    KalkulacijaResponse,
    MonthlyBreakdownItem,
    MonthlyBreakdownResponse,
    OpenItemsResponse,
    OpenItemsRow,
    PriceComparisonItem,
    PriceComparisonResponse,
    ReceivedGoodsItem,
    ReceivedGoodsResponse,
    RucItem,
    RucResponse,
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
    client_id: str | None = None,
) -> list:
    """Build a list of SQLAlchemy WHERE conditions for line item queries.

    Args:
        org_id: Organization UUID to scope results.
        date_from: Inclusive lower bound for invoice_date.
        date_to: Inclusive upper bound for invoice_date.
        seller_pib: Exact PIB filter; skipped when None.
        search: Case-insensitive substring filter on description; skipped when None.
        client_id: Filter to a specific agency client; skipped when None.

    Returns:
        List of SQLAlchemy column expressions suitable for .where(*conditions).
    """
    conditions = [
        InvoiceLineItem.organization_id == org_id,
        InvoiceLineItem.invoice_id.in_(
            select(Invoice.id).where(Invoice.status.in_(["verified", "exported"]))
        ),
    ]
    if date_from:
        conditions.append(InvoiceLineItem.invoice_date >= date_from)
    if date_to:
        conditions.append(InvoiceLineItem.invoice_date <= date_to)
    if seller_pib:
        conditions.append(InvoiceLineItem.seller_pib == seller_pib)
    if search:
        conditions.append(InvoiceLineItem.description.ilike(f"%{search}%"))
    if client_id:
        conditions.append(InvoiceLineItem.client_id == client_id)
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
    client_id: str | None = Query(default=None),
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
    conditions = _build_conditions(
        user.organization_id, date_from, date_to, seller_pib, search, client_id
    )

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
    client_id: str | None = Query(default=None),
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
    conditions = _build_conditions(
        user.organization_id, date_from, date_to, seller_pib, search, client_id
    )

    # Subquery: remaining amount per invoice (total - paid)
    remaining_expr = Invoice.total_amount - func.coalesce(Invoice.paid_amount, 0)

    gross = InvoiceLineItem.total + func.coalesce(InvoiceLineItem.tax_amount, 0)

    # Per line item, its share of the invoice remaining amount:
    # line_remaining = line_gross / invoice_total * invoice_remaining
    # This correctly handles partial payments proportionally.
    line_remaining = case(
        (
            Invoice.total_amount > 0,
            gross / Invoice.total_amount * remaining_expr,
        ),
        else_=gross,
    )

    query = (
        select(
            InvoiceLineItem.seller_pib,
            InvoiceLineItem.seller_name,
            func.sum(gross).label("total_amount"),
            func.count(func.distinct(InvoiceLineItem.invoice_id)).label("invoice_count"),
            func.coalesce(func.sum(line_remaining), 0).label("unpaid_amount"),
        )
        .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
        .where(*conditions)
        .group_by(InvoiceLineItem.seller_pib, InvoiceLineItem.seller_name)
        .order_by(func.sum(gross).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    items = [
        SpendingBySupplierItem(
            seller_name=row.seller_name,
            seller_pib=row.seller_pib,
            total_amount=float(row.total_amount),
            invoice_count=row.invoice_count,
            unpaid_amount=float(row.unpaid_amount),
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
    client_id: str | None = Query(default=None),
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
    conditions = _build_conditions(
        user.organization_id, date_from, date_to, seller_pib, search, client_id
    )

    # Aggregate totals across the full result set
    agg_query = select(
        func.sum(InvoiceLineItem.total).label("total_amount"),
        func.count().label("item_count"),
    ).where(*conditions)
    agg_result = await db.execute(agg_query)
    agg_row = agg_result.one()
    total_amount = float(agg_row.total_amount or 0)
    item_count = agg_row.item_count or 0

    # Paginated rows with payment status from parent invoice
    offset = (page - 1) * per_page
    rows_query = (
        select(InvoiceLineItem, Invoice.payment_status)
        .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
        .where(*conditions)
        .order_by(
            InvoiceLineItem.invoice_date.desc().nullslast(),
            InvoiceLineItem.created_at.desc(),
        )
        .offset(offset)
        .limit(per_page)
    )
    rows_result = await db.execute(rows_query)
    rows = rows_result.all()

    items = [
        MonthlyBreakdownItem(
            id=str(row.InvoiceLineItem.id),
            invoice_id=str(row.InvoiceLineItem.invoice_id),
            description=row.InvoiceLineItem.description,
            quantity=float(row.InvoiceLineItem.quantity) if row.InvoiceLineItem.quantity is not None else None,
            unit_price=float(row.InvoiceLineItem.unit_price) if row.InvoiceLineItem.unit_price is not None else None,
            total=float(row.InvoiceLineItem.total),
            tax_rate=float(row.InvoiceLineItem.tax_rate) if row.InvoiceLineItem.tax_rate is not None else None,
            tax_amount=float(row.InvoiceLineItem.tax_amount) if row.InvoiceLineItem.tax_amount is not None else None,
            seller_name=row.InvoiceLineItem.seller_name,
            invoice_date=row.InvoiceLineItem.invoice_date.isoformat() if row.InvoiceLineItem.invoice_date is not None else None,
            payment_status=row.payment_status or "unpaid",
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
    search: str | None = Query(default=None),
    client_id: str | None = Query(default=None),
) -> PriceComparisonResponse:
    """Return price statistics grouped by description and supplier.

    Returns items that appear from 2+ different suppliers.
    Optional search term narrows to specific items.
    Shows min, max, and average unit prices per (description, supplier)
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
    conditions = _build_conditions(
        user.organization_id, date_from, date_to, seller_pib, search, client_id
    )

    # Use canonical product name if linked, otherwise raw description
    item_name = func.coalesce(ProductCatalog.canonical_name, InvoiceLineItem.description)

    query = (
        select(
            item_name.label("description"),
            InvoiceLineItem.seller_name,
            InvoiceLineItem.seller_pib,
            func.avg(InvoiceLineItem.unit_price).label("avg_unit_price"),
            func.min(InvoiceLineItem.unit_price).label("min_unit_price"),
            func.max(InvoiceLineItem.unit_price).label("max_unit_price"),
            func.sum(InvoiceLineItem.quantity).label("total_quantity"),
            func.count(func.distinct(InvoiceLineItem.invoice_id)).label("invoice_count"),
        )
        .outerjoin(ProductCatalog, InvoiceLineItem.product_id == ProductCatalog.id)
        .where(*conditions)
        .group_by(
            item_name,
            InvoiceLineItem.seller_pib,
            InvoiceLineItem.seller_name,
        )
        .order_by(item_name, func.avg(InvoiceLineItem.unit_price))
    )

    result = await db.execute(query)
    rows = result.all()

    # Filter: only items that appear from 2+ suppliers
    from collections import defaultdict

    by_desc: dict[str, list] = defaultdict(list)
    for row in rows:
        by_desc[row.description].append(row)

    items = []
    for desc, desc_rows in by_desc.items():
        unique_pibs = {r.seller_pib for r in desc_rows if r.seller_pib}
        if len(unique_pibs) < 2:
            continue
        for row in desc_rows:
            items.append(
                PriceComparisonItem(
                    description=row.description,
                    seller_name=row.seller_name,
                    seller_pib=row.seller_pib,
                    avg_unit_price=(
                        float(row.avg_unit_price) if row.avg_unit_price is not None else None
                    ),
                    min_unit_price=(
                        float(row.min_unit_price) if row.min_unit_price is not None else None
                    ),
                    max_unit_price=(
                        float(row.max_unit_price) if row.max_unit_price is not None else None
                    ),
                    total_quantity=(
                        float(row.total_quantity) if row.total_quantity is not None else None
                    ),
                    invoice_count=row.invoice_count,
                )
            )

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
    client_id: str | None = Query(default=None),
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

    conditions = _build_conditions(
        user.organization_id, date_from, date_to, seller_pib, search, client_id
    )

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


# ===========================================================================
# Restaurant-specific reports
# ===========================================================================


@router.get("/kalkulacija", response_model=KalkulacijaResponse)
async def kalkulacija_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    seller_pib: str | None = Query(None),
    search: str | None = Query(None),
    client_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KalkulacijaResponse:
    """Price calculation (kalkulacija) report.

    Shows each line item with purchase price, configured margin, and
    calculated selling price. Uses margin from product_catalog if
    available, otherwise uses a default 40%.

    Args:
        date_from: Start of reporting period.
        date_to: End of reporting period.
        seller_pib: Optional supplier filter.
        search: Optional item description filter.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        Kalkulacija report with per-item price calculations.
    """
    org_id = current_user.organization_id
    conditions = _build_conditions(org_id, date_from, date_to, seller_pib, search, client_id)

    # Join with product_catalog to get margin/selling_price
    query = (
        select(
            InvoiceLineItem.description,
            InvoiceLineItem.quantity,
            InvoiceLineItem.unit_price,
            InvoiceLineItem.total,
            InvoiceLineItem.tax_rate,
            InvoiceLineItem.tax_amount,
            InvoiceLineItem.seller_name,
            InvoiceLineItem.invoice_date,
            ProductCatalog.selling_price.label("catalog_selling_price"),
            ProductCatalog.default_margin_pct.label("catalog_margin"),
            ProductCatalog.unit_of_measure.label("catalog_uom"),
        )
        .outerjoin(ProductCatalog, InvoiceLineItem.product_id == ProductCatalog.id)
        .where(*conditions)
        .order_by(InvoiceLineItem.invoice_date.desc(), InvoiceLineItem.description)
    )

    result = await db.execute(query)
    rows = result.all()

    default_margin = 40.0
    items = []
    total_purchase = 0.0
    total_selling = 0.0

    for row in rows:
        qty = float(row.quantity) if row.quantity else 1.0
        price = float(row.unit_price) if row.unit_price else 0.0
        purchase_value = round(qty * price, 2)
        margin_pct = float(row.catalog_margin) if row.catalog_margin else default_margin
        margin_amount = round(purchase_value * margin_pct / 100, 2)
        tax_rate = float(row.tax_rate) if row.tax_rate else 20.0
        tax_on_margin = round((purchase_value + margin_amount) * tax_rate / 100, 2)
        selling_value = round(purchase_value + margin_amount + tax_on_margin, 2)
        selling_price = round(selling_value / qty, 2) if qty else 0.0

        items.append(
            KalkulacijaItem(
                description=row.description or "",
                unit_of_measure=row.catalog_uom,
                quantity=float(row.quantity) if row.quantity else None,
                purchase_price=price if price else None,
                purchase_value=purchase_value,
                margin_pct=margin_pct,
                margin_amount=margin_amount,
                tax_rate=tax_rate,
                tax_amount=tax_on_margin,
                selling_price=selling_price,
                selling_value=selling_value,
                supplier_name=row.seller_name,
                invoice_date=row.invoice_date,
            )
        )
        total_purchase += purchase_value
        total_selling += selling_value

    return KalkulacijaResponse(
        items=items,
        total_purchase_value=round(total_purchase, 2),
        total_selling_value=round(total_selling, 2),
        total_margin=round(total_selling - total_purchase, 2),
        item_count=len(items),
    )


@router.get("/ruc", response_model=RucResponse)
async def ruc_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    seller_pib: str | None = Query(None),
    search: str | None = Query(None),
    client_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RucResponse:
    """RUC (Razlika u Ceni) report — markup analysis per product.

    Groups items by canonical product name (or raw description),
    calculates average purchase price, and compares with configured
    selling price from the product catalog.

    Args:
        date_from: Start of reporting period.
        date_to: End of reporting period.
        seller_pib: Optional supplier filter.
        search: Optional item description filter.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        RUC report with per-product margin analysis.
    """
    org_id = current_user.organization_id
    conditions = _build_conditions(org_id, date_from, date_to, seller_pib, search, client_id)

    # Group by product (canonical name or raw description)
    canonical = func.coalesce(ProductCatalog.canonical_name, InvoiceLineItem.description)

    query = (
        select(
            canonical.label("product_name"),
            ProductCatalog.category,
            func.avg(InvoiceLineItem.unit_price).label("avg_price"),
            ProductCatalog.selling_price,
            func.sum(InvoiceLineItem.quantity).label("total_qty"),
            func.sum(InvoiceLineItem.total).label("total_value"),
            func.array_agg(func.distinct(InvoiceLineItem.seller_name)).label("suppliers"),
        )
        .outerjoin(ProductCatalog, InvoiceLineItem.product_id == ProductCatalog.id)
        .where(*conditions)
        .group_by(canonical, ProductCatalog.category, ProductCatalog.selling_price)
        .order_by(canonical)
    )

    result = await db.execute(query)
    rows = result.all()

    items = []
    total_purchase = 0.0
    margin_sum = 0.0
    margin_count = 0

    for row in rows:
        avg_price = float(row.avg_price) if row.avg_price else 0.0
        sell_price = float(row.selling_price) if row.selling_price else None
        total_val = float(row.total_value) if row.total_value else 0.0

        ruc_amount = None
        ruc_pct = None
        if sell_price and avg_price > 0:
            ruc_amount = round(sell_price - avg_price, 2)
            ruc_pct = round((ruc_amount / avg_price) * 100, 2)
            margin_sum += ruc_pct
            margin_count += 1

        suppliers = [s for s in (row.suppliers or []) if s]

        items.append(
            RucItem(
                description=row.product_name or "",
                category=row.category,
                avg_purchase_price=round(avg_price, 2) if avg_price else None,
                selling_price=sell_price,
                ruc_amount=ruc_amount,
                ruc_pct=ruc_pct,
                total_purchased_qty=(float(row.total_qty) if row.total_qty else None),
                total_purchased_value=round(total_val, 2),
                suppliers=suppliers,
            )
        )
        total_purchase += total_val

    avg_margin = round(margin_sum / margin_count, 2) if margin_count else 0.0

    return RucResponse(
        items=items,
        avg_margin_pct=avg_margin,
        total_purchase_value=round(total_purchase, 2),
        item_count=len(items),
    )


@router.get("/dpu")
async def dpu_report(
    date: date = Query(...),
    client_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """DPU (Dnevni Promet Ugostitelja) report for a specific date.

    Groups all line items received on the given date by product name,
    sums quantities as "purchased". Opening stock and closing stock
    are placeholders (0) until inventory tracking is implemented.

    Args:
        date: The date to report on.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        DPU report data with items, totals and date.
    """
    org_id = current_user.organization_id

    query = (
        select(
            func.coalesce(ProductCatalog.canonical_name, InvoiceLineItem.description).label(
                "description"
            ),
            ProductCatalog.unit_of_measure,
            func.sum(InvoiceLineItem.quantity).label("purchased"),
            ProductCatalog.selling_price,
        )
        .outerjoin(ProductCatalog, InvoiceLineItem.product_id == ProductCatalog.id)
        .where(
            InvoiceLineItem.organization_id == org_id,
            InvoiceLineItem.invoice_date == date,
            *([InvoiceLineItem.client_id == client_id] if client_id else []),
        )
        .group_by(
            func.coalesce(ProductCatalog.canonical_name, InvoiceLineItem.description),
            ProductCatalog.unit_of_measure,
            ProductCatalog.selling_price,
        )
        .order_by(func.coalesce(ProductCatalog.canonical_name, InvoiceLineItem.description))
    )

    result = await db.execute(query)
    rows = result.all()

    items = []
    total_purchased = 0.0
    for row in rows:
        purchased = float(row.purchased) if row.purchased else 0.0
        sell_price = float(row.selling_price) if row.selling_price else None
        total_purchased += purchased * (float(row.selling_price) if row.selling_price else 0)

        items.append(
            {
                "description": row.description or "",
                "unit_of_measure": row.unit_of_measure,
                "opening_stock": 0,
                "purchased": purchased,
                "closing_stock": None,
                "consumed": None,
                "selling_price": sell_price,
                "revenue": None,
            }
        )

    return {
        "date": date.isoformat(),
        "items": items,
        "total_purchased_value": round(total_purchased, 2),
        "total_revenue": None,
    }


@router.get("/spending-by-category", response_model=CategorySpendingResponse)
async def spending_by_category(
    date_from: date = Query(...),
    date_to: date = Query(...),
    client_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategorySpendingResponse:
    """Spending grouped by product category.

    Uses categories from the product_catalog. Items without a catalog
    entry are grouped as 'Nekategorisano'.

    Args:
        date_from: Start of reporting period.
        date_to: End of reporting period.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        Spending totals per category.
    """
    org_id = current_user.organization_id
    conditions = _build_conditions(org_id, date_from, date_to, None, None, client_id)

    cat_label = func.coalesce(ProductCatalog.category, "Nekategorisano")

    query = (
        select(
            cat_label.label("category"),
            func.sum(InvoiceLineItem.total).label("total_amount"),
            func.count(func.distinct(InvoiceLineItem.description)).label("item_count"),
            func.count(func.distinct(InvoiceLineItem.invoice_id)).label("invoice_count"),
        )
        .outerjoin(ProductCatalog, InvoiceLineItem.product_id == ProductCatalog.id)
        .where(*conditions)
        .group_by(cat_label)
        .order_by(func.sum(InvoiceLineItem.total).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    items = [
        CategorySpendingItem(
            category=row.category,
            total_amount=float(row.total_amount) if row.total_amount else 0.0,
            item_count=row.item_count,
            invoice_count=row.invoice_count,
        )
        for row in rows
    ]

    grand_total = sum(i.total_amount for i in items)
    return CategorySpendingResponse(items=items, grand_total=grand_total)


# ---------------------------------------------------------------------------
# Open Items (Otvorene stavke)
# ---------------------------------------------------------------------------


@router.get("/open-items", response_model=OpenItemsResponse)
async def open_items_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    seller_pib: str | None = Query(default=None),
    client_id: str | None = Query(default=None),
    payment_status: str | None = Query(
        default=None, description="Filter: 'unpaid' or 'partially_paid'"
    ),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OpenItemsResponse:
    """List unpaid and partially paid invoices with days overdue.

    Shows all invoices that haven't been fully paid, ordered by
    due date. Calculates days overdue from due_date.

    Args:
        date_from: Filter invoices on or after this date.
        date_to: Filter invoices on or before this date.
        seller_pib: Filter to a specific supplier.
        client_id: Filter by client (Agency feature).
        payment_status: Filter by 'unpaid' or 'partially_paid'.
        db: Database session.
        user: Authenticated user.

    Returns:
        Open items with totals.
    """
    from uuid import UUID as PyUUID

    conditions = [
        Invoice.organization_id == user.organization_id,
        Invoice.payment_status.in_(["unpaid", "partially_paid"]),
        Invoice.status.in_(["verified", "exported"]),
    ]

    if payment_status and payment_status in ("unpaid", "partially_paid"):
        conditions.append(Invoice.payment_status == payment_status)

    if date_from:
        conditions.append(Invoice.invoice_date >= date_from)
    if date_to:
        conditions.append(Invoice.invoice_date <= date_to)
    if seller_pib:
        conditions.append(Invoice.seller["pib"].as_string() == seller_pib)
    if client_id:
        conditions.append(Invoice.client_id == PyUUID(client_id))

    result = await db.execute(
        select(Invoice)
        .where(*conditions)
        .order_by(Invoice.due_date.asc().nullslast(), Invoice.invoice_date.asc())
    )
    invoices = result.scalars().all()

    today = date.today()
    items: list[OpenItemsRow] = []
    total_open = 0.0
    total_overdue = 0.0

    for inv in invoices:
        total = float(inv.total_amount) if inv.total_amount else 0.0
        paid = float(inv.paid_amount) if inv.paid_amount else 0.0
        remaining = total - paid

        days_overdue = 0
        if inv.due_date and inv.due_date < today:
            days_overdue = (today - inv.due_date).days

        seller_name = None
        s_pib = None
        if inv.seller and isinstance(inv.seller, dict):
            seller_name = inv.seller.get("name")
            s_pib = inv.seller.get("pib")

        items.append(
            OpenItemsRow(
                invoice_id=str(inv.id),
                invoice_number=inv.invoice_number,
                invoice_date=inv.invoice_date,
                due_date=inv.due_date,
                seller_name=seller_name,
                seller_pib=s_pib,
                total_amount=total,
                paid_amount=paid,
                remaining_amount=remaining,
                payment_status=inv.payment_status or "unpaid",
                days_overdue=days_overdue,
                currency=inv.currency or "RSD",
            )
        )
        total_open += remaining
        if days_overdue > 0:
            total_overdue += remaining

    return OpenItemsResponse(
        items=items,
        total_open_amount=round(total_open, 2),
        total_overdue_amount=round(total_overdue, 2),
        count=len(items),
    )


# ---------------------------------------------------------------------------
# Aging Analysis (Analiza dospeća)
# ---------------------------------------------------------------------------


@router.get("/aging", response_model=AgingResponse)
async def aging_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    seller_pib: str | None = Query(default=None),
    client_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgingResponse:
    """Aging analysis of unpaid invoices grouped by overdue buckets.

    Groups outstanding invoices into 0-30, 31-60, 61-90, and 90+ day
    buckets based on how many days past due_date.

    Args:
        date_from: Filter invoices on or after this date.
        date_to: Filter invoices on or before this date.
        seller_pib: Filter to a specific supplier.
        client_id: Filter by client (Agency feature).
        db: Database session.
        user: Authenticated user.

    Returns:
        Aging buckets with totals.
    """
    from uuid import UUID as PyUUID

    conditions = [
        Invoice.organization_id == user.organization_id,
        Invoice.payment_status.in_(["unpaid", "partially_paid"]),
        Invoice.status.in_(["verified", "exported"]),
    ]

    if date_from:
        conditions.append(Invoice.invoice_date >= date_from)
    if date_to:
        conditions.append(Invoice.invoice_date <= date_to)
    if seller_pib:
        conditions.append(Invoice.seller["pib"].as_string() == seller_pib)
    if client_id:
        conditions.append(Invoice.client_id == PyUUID(client_id))

    result = await db.execute(
        select(Invoice).where(*conditions)
    )
    invoices = result.scalars().all()

    today = date.today()
    buckets_data: dict[str, dict] = {
        "0-30": {"count": 0, "total": 0.0},
        "31-60": {"count": 0, "total": 0.0},
        "61-90": {"count": 0, "total": 0.0},
        "90+": {"count": 0, "total": 0.0},
    }

    for inv in invoices:
        total = float(inv.total_amount) if inv.total_amount else 0.0
        paid = float(inv.paid_amount) if inv.paid_amount else 0.0
        remaining = total - paid

        days_overdue = 0
        if inv.due_date and inv.due_date < today:
            days_overdue = (today - inv.due_date).days

        if days_overdue <= 30:
            bucket_key = "0-30"
        elif days_overdue <= 60:
            bucket_key = "31-60"
        elif days_overdue <= 90:
            bucket_key = "61-90"
        else:
            bucket_key = "90+"

        buckets_data[bucket_key]["count"] += 1
        buckets_data[bucket_key]["total"] += remaining

    buckets = [
        AgingBucket(
            bucket=key,
            count=data["count"],
            total_amount=round(data["total"], 2),
        )
        for key, data in buckets_data.items()
    ]

    grand_total = sum(b.total_amount for b in buckets)
    # Overdue = everything past 30 days
    overdue_total = sum(b.total_amount for b in buckets if b.bucket != "0-30")

    return AgingResponse(
        buckets=buckets,
        grand_total=round(grand_total, 2),
        overdue_total=round(overdue_total, 2),
    )
