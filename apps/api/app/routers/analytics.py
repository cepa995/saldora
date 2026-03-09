"""Analytics router — correction quality metrics for admin dashboard."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.correction_log import CorrectionLog
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.correction import (
    CorrectionAnalyticsResponse,
    FieldErrorRate,
    HighConfidenceError,
    RepeatPattern,
)

router = APIRouter()


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
