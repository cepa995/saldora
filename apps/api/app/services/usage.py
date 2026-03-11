"""Usage tracking service.

Handles incrementing usage counters when invoices are created
and provides current-period usage queries.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_record import UsageRecord


def current_period() -> tuple[date, date]:
    """Return (period_start, period_end) for the current calendar month.

    Returns:
        Tuple of (first day of month, last day of month).
    """
    today = datetime.now(UTC).date()
    start = today.replace(day=1)
    if today.month == 12:
        next_month_first = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month_first = today.replace(month=today.month + 1, day=1)
    end = next_month_first - timedelta(days=1)
    return start, end


async def get_or_create_current_record(
    db: AsyncSession,
    organization_id: UUID,
) -> UsageRecord:
    """Get or create the usage record for the current billing period.

    Args:
        db: Database session.
        organization_id: Organization UUID.

    Returns:
        The UsageRecord for the current month.
    """
    start, end = current_period()
    result = await db.execute(
        select(UsageRecord).where(
            UsageRecord.organization_id == organization_id,
            UsageRecord.period_start == start,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        record = UsageRecord(
            organization_id=organization_id,
            period_start=start,
            period_end=end,
            invoices_count=0,
            api_calls_count=0,
            storage_bytes=0,
        )
        db.add(record)
        await db.flush()
    return record


async def increment_invoice_count(
    db: AsyncSession,
    organization_id: UUID,
    storage_delta_bytes: int = 0,
) -> None:
    """Increment the invoice count for the current period.

    Uses atomic SQL increment to avoid race conditions with concurrent uploads.

    Args:
        db: Database session.
        organization_id: Organization UUID.
        storage_delta_bytes: Additional storage consumed by this invoice.
    """
    # Ensure the record exists first
    record = await get_or_create_current_record(db, organization_id)

    # Atomic increment via SQL UPDATE
    await db.execute(
        update(UsageRecord)
        .where(UsageRecord.id == record.id)
        .values(
            invoices_count=UsageRecord.invoices_count + 1,
            storage_bytes=UsageRecord.storage_bytes + storage_delta_bytes,
        )
    )
