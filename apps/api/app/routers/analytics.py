"""Analytics router — dashboard stats and correction quality metrics."""

from datetime import UTC, datetime
from uuid import UUID

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.correction_log import CorrectionLog
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.correction import (
    CorrectionAnalyticsResponse,
    FieldErrorRate,
    HighConfidenceError,
    RepeatPattern,
)
from app.schemas.dashboard import (
    DashboardStatsResponse,
    MonthlyTotal,
    MonthlyVolume,
    StatusCount,
)

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    client_id: UUID | None = Query(default=None),
) -> DashboardStatsResponse:
    """Return aggregated dashboard statistics for charts.

    Returns monthly invoice volume, status distribution, and monthly
    totals for the last 12 months. Scoped to the user's organization.

    Args:
        db: Database session.
        user: Authenticated user.
        client_id: Optional client filter for agency users.

    Returns:
        Dashboard chart data with monthly_volume, status_distribution,
        and monthly_totals.
    """
    org_id = user.organization_id
    now = datetime.now(UTC)
    twelve_months_ago = now - relativedelta(months=11)
    month_start = twelve_months_ago.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Base conditions
    conditions = [Invoice.organization_id == org_id]
    if client_id is not None:
        conditions.append(Invoice.client_id == client_id)

    # 1. Monthly volume (last 12 months)
    month_trunc = func.date_trunc("month", Invoice.created_at)
    volume_query = (
        select(
            month_trunc.label("month"),
            func.count().label("count"),
        )
        .where(*conditions, Invoice.created_at >= month_start)
        .group_by(month_trunc)
        .order_by(month_trunc)
    )
    volume_result = await db.execute(volume_query)
    volume_map = {row.month.strftime("%Y-%m"): row.count for row in volume_result}

    # 2. Status distribution (all invoices)
    status_query = (
        select(
            Invoice.status,
            func.count().label("count"),
        )
        .where(*conditions)
        .group_by(Invoice.status)
    )
    status_result = await db.execute(status_query)
    status_distribution = [StatusCount(status=row.status, count=row.count) for row in status_result]

    # 3. Monthly totals (last 12 months, sum total_amount)
    totals_query = (
        select(
            month_trunc.label("month"),
            func.coalesce(func.sum(Invoice.total_amount), 0).label("total"),
        )
        .where(*conditions, Invoice.created_at >= month_start)
        .group_by(month_trunc)
        .order_by(month_trunc)
    )
    totals_result = await db.execute(totals_query)
    totals_map = {row.month.strftime("%Y-%m"): float(row.total) for row in totals_result}

    # Fill missing months with zeros for continuous chart data
    monthly_volume: list[MonthlyVolume] = []
    monthly_totals: list[MonthlyTotal] = []
    for i in range(12):
        m = month_start + relativedelta(months=i)
        key = m.strftime("%Y-%m")
        monthly_volume.append(MonthlyVolume(month=key, count=volume_map.get(key, 0)))
        monthly_totals.append(MonthlyTotal(month=key, total_rsd=totals_map.get(key, 0.0)))

    return DashboardStatsResponse(
        monthly_volume=monthly_volume,
        status_distribution=status_distribution,
        monthly_totals=monthly_totals,
    )


@router.get("/corrections", response_model=CorrectionAnalyticsResponse)
async def get_correction_analytics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
) -> CorrectionAnalyticsResponse:
    """Return aggregated correction metrics for quality monitoring.

    Admin-only endpoint scoped to the current organization.
    Provides field error rates, high-confidence errors, and repeat
    patterns to help identify systemic extraction issues.

    Args:
        db: Database session.
        user: Authenticated user (must be admin).
        date_from: Filter corrections on or after this datetime.
        date_to: Filter corrections on or before this datetime.

    Returns:
        Aggregated correction analytics.
    """
    org_id = user.organization_id

    # Base conditions for all queries
    conditions = [CorrectionLog.organization_id == org_id]
    if date_from:
        conditions.append(CorrectionLog.created_at >= date_from)
    if date_to:
        conditions.append(CorrectionLog.created_at <= date_to)

    # Total invoices in org (denominator for error rate)
    invoice_count_result = await db.execute(
        select(func.count()).select_from(
            select(Invoice.id).where(Invoice.organization_id == org_id).subquery()
        )
    )
    invoice_count = invoice_count_result.scalar() or 0

    # 1. Field error rates: correction count per field
    field_counts_query = (
        select(
            CorrectionLog.field_name,
            func.count().label("correction_count"),
        )
        .where(*conditions)
        .group_by(CorrectionLog.field_name)
        .order_by(func.count().desc())
    )
    field_counts_result = await db.execute(field_counts_query)
    field_error_rates = [
        FieldErrorRate(
            field_name=row.field_name,
            correction_count=row.correction_count,
            invoice_count=invoice_count,
            error_rate=round(
                (row.correction_count / invoice_count * 100) if invoice_count > 0 else 0,
                2,
            ),
        )
        for row in field_counts_result
    ]

    # 2. High confidence errors: corrections where model was > 90% confident
    hce_query = (
        select(
            CorrectionLog.field_name,
            func.count().label("count"),
        )
        .where(*conditions, CorrectionLog.model_confidence > 0.90)
        .group_by(CorrectionLog.field_name)
        .order_by(func.count().desc())
    )
    hce_result = await db.execute(hce_query)
    high_confidence_errors = [
        HighConfidenceError(field_name=row.field_name, count=row.count) for row in hce_result
    ]

    # 3. Repeat patterns: same field + original → corrected appearing 2+ times
    repeat_query = (
        select(
            CorrectionLog.field_name,
            CorrectionLog.original_value,
            CorrectionLog.corrected_value,
            func.count().label("occurrences"),
        )
        .where(*conditions, CorrectionLog.original_value.isnot(None))
        .group_by(
            CorrectionLog.field_name,
            CorrectionLog.original_value,
            CorrectionLog.corrected_value,
        )
        .having(func.count() > 1)
        .order_by(func.count().desc())
        .limit(50)
    )
    repeat_result = await db.execute(repeat_query)
    repeat_patterns = [
        RepeatPattern(
            field_name=row.field_name,
            original_value=row.original_value,
            corrected_value=row.corrected_value,
            occurrences=row.occurrences,
        )
        for row in repeat_result
    ]

    return CorrectionAnalyticsResponse(
        field_error_rates=field_error_rates,
        high_confidence_errors=high_confidence_errors,
        repeat_patterns=repeat_patterns,
    )
