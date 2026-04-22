"""Portfolio aggregation service (M19.7).

Aggregates per-client invoice stats scoped to a calendar month, plus a
short trailing monthly series (last 6 months) per client for sparkline
rendering on the /klijenti grid.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.client_event import ClientEvent
from app.models.invoice import Invoice
from app.schemas.portfolio import (
    PortfolioMonthlyPoint,
    PortfolioResponse,
    PortfolioRow,
)

SERIES_MONTHS = 6


def _parse_period(period: str) -> tuple[date, date]:
    """Return (first-day, last-day) of a YYYY-MM period."""
    year, month = (int(part) for part in period.split("-", 1))
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    return first, last


def _shift_month(period: str, delta: int) -> str:
    """Shift a YYYY-MM period by ``delta`` months (can be negative)."""
    year, month = (int(part) for part in period.split("-", 1))
    idx = year * 12 + (month - 1) + delta
    y, m = divmod(idx, 12)
    return f"{y}-{m + 1:02d}"


async def compute_portfolio(
    db: AsyncSession,
    organization_id: UUID,
    period: str,
) -> PortfolioResponse:
    """Compute one row per active client with period-scoped indicators.

    Scope rules:

    * ``invoice_count`` / ``total_amount`` — counts and sums over invoices
      whose ``invoice_date`` falls inside ``period``.
    * ``pending_review_count`` / ``blocked_count`` — same period window, but
      filtered by the invoice's current status. "In March, 3 invoices are
      still stuck" rather than "3 invoices have ever been stuck."
    * ``last_activity_at`` — max event_date for the client, regardless of
      period (it's a freshness signal, not a volume signal).
    * ``monthly_series`` — trailing SERIES_MONTHS entries ending at ``period``,
      each with count + total_amount, used for the card sparkline.
    """
    first_day, last_day = _parse_period(period)
    series_start_period = _shift_month(period, -(SERIES_MONTHS - 1))
    series_first_day, _ = _parse_period(series_start_period)

    pending = case((Invoice.status == "review", 1), else_=0)
    blocked = case((Invoice.status == "error", 1), else_=0)

    # Period-scoped invoice stats
    invoice_stats = (
        select(
            Invoice.client_id.label("client_id"),
            func.count(Invoice.id).label("invoice_count"),
            func.coalesce(func.sum(pending), 0).label("pending_review_count"),
            func.coalesce(func.sum(blocked), 0).label("blocked_count"),
            func.coalesce(func.sum(Invoice.total_amount), 0).label("total_amount"),
        )
        .where(
            and_(
                Invoice.organization_id == organization_id,
                Invoice.invoice_date >= first_day,
                Invoice.invoice_date <= last_day,
            )
        )
        .group_by(Invoice.client_id)
        .subquery()
    )

    # Past-due count — period-agnostic. "Late RIGHT NOW, regardless of which
    # month you're browsing" is the useful semantic; scoping this to period
    # would hide old-and-still-late invoices when viewing a newer month.
    today = datetime.now(UTC).date()
    past_due_stats = (
        select(
            Invoice.client_id.label("client_id"),
            func.count(Invoice.id).label("past_due_count"),
        )
        .where(
            and_(
                Invoice.organization_id == organization_id,
                Invoice.status != "exported",
                func.coalesce(Invoice.due_date, Invoice.invoice_date) < today,
            )
        )
        .group_by(Invoice.client_id)
        .subquery()
    )

    # Last-activity is period-agnostic — it's a freshness cue.
    activity_stats = (
        select(
            ClientEvent.client_id.label("client_id"),
            func.max(ClientEvent.event_date).label("last_activity_at"),
        )
        .where(ClientEvent.organization_id == organization_id)
        .group_by(ClientEvent.client_id)
        .subquery()
    )

    stmt = (
        select(
            Client.id,
            Client.name,
            Client.pib,
            Client.is_active,
            func.coalesce(invoice_stats.c.invoice_count, 0).label("invoice_count"),
            func.coalesce(invoice_stats.c.pending_review_count, 0).label("pending_review_count"),
            func.coalesce(invoice_stats.c.blocked_count, 0).label("blocked_count"),
            func.coalesce(invoice_stats.c.total_amount, 0).label("total_amount"),
            func.coalesce(past_due_stats.c.past_due_count, 0).label("past_due_count"),
            activity_stats.c.last_activity_at,
        )
        .outerjoin(invoice_stats, invoice_stats.c.client_id == Client.id)
        .outerjoin(past_due_stats, past_due_stats.c.client_id == Client.id)
        .outerjoin(activity_stats, activity_stats.c.client_id == Client.id)
        .where(
            Client.organization_id == organization_id,
            Client.is_active.is_(True),
        )
        .order_by(Client.name.asc())
    )

    rows = (await db.execute(stmt)).all()

    # Monthly series — one query over the window, grouped by (client, month).
    # Empty months are filled with zeros in Python so every card has the same
    # number of points (stable sparkline axis).
    month_expr = func.to_char(func.date_trunc("month", Invoice.invoice_date), "YYYY-MM").label(
        "period"
    )
    series_stmt = (
        select(
            Invoice.client_id.label("client_id"),
            month_expr,
            func.count(Invoice.id).label("invoice_count"),
            func.coalesce(func.sum(Invoice.total_amount), 0).label("total_amount"),
        )
        .where(
            and_(
                Invoice.organization_id == organization_id,
                Invoice.client_id.is_not(None),
                Invoice.invoice_date >= series_first_day,
                Invoice.invoice_date <= last_day,
            )
        )
        .group_by(Invoice.client_id, month_expr)
    )
    series_rows = (await db.execute(series_stmt)).all()

    # Pre-compute the full month list (oldest → newest) so every client gets
    # SERIES_MONTHS points, zero-padded where no data exists.
    all_periods = [_shift_month(period, -i) for i in range(SERIES_MONTHS - 1, -1, -1)]
    series_by_client: dict[UUID, dict[str, tuple[int, str]]] = {}
    for row in series_rows:
        series_by_client.setdefault(row.client_id, {})[row.period] = (
            int(row.invoice_count or 0),
            str(row.total_amount or 0),
        )

    def _build_series(client_id: UUID) -> list[PortfolioMonthlyPoint]:
        per_client = series_by_client.get(client_id, {})
        return [
            PortfolioMonthlyPoint(
                period=p,
                invoice_count=per_client.get(p, (0, "0"))[0],
                total_amount=per_client.get(p, (0, "0"))[1],
            )
            for p in all_periods
        ]

    data: list[PortfolioRow] = []
    for row in rows:
        last_activity = row.last_activity_at
        # Some async drivers return naive datetimes; Pydantic tolerates either.
        if isinstance(last_activity, datetime):
            pass
        total_amount_raw = row.total_amount
        data.append(
            PortfolioRow(
                client_id=row.id,
                name=row.name,
                pib=row.pib,
                is_active=row.is_active,
                invoice_count=int(row.invoice_count or 0),
                pending_review_count=int(row.pending_review_count or 0),
                blocked_count=int(row.blocked_count or 0),
                past_due_count=int(row.past_due_count or 0),
                total_amount=str(total_amount_raw) if total_amount_raw is not None else None,
                last_activity_at=last_activity,
                monthly_series=_build_series(row.id),
            )
        )
    return PortfolioResponse(period=period, data=data)
