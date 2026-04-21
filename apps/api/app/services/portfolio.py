"""Portfolio aggregation service (M19.7).

Single-query aggregation over clients × invoices × client_events to
produce the agency-wide portfolio grid. Avoids N+1 when rendering
lots of clients.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.client_event import ClientEvent
from app.models.invoice import Invoice
from app.schemas.portfolio import PortfolioResponse, PortfolioRow


async def compute_portfolio(
    db: AsyncSession,
    organization_id: UUID,
    period: str,
) -> PortfolioResponse:
    """Compute one row per active client with health indicators.

    The indicators are intentionally minimal for launch:
    - ``invoice_count``          total invoices for this client (all time)
    - ``pending_review_count``   status=review
    - ``blocked_count``          status=error
    - ``last_activity_at``       max(event_date) across client's events

    New indicator types (form-coverage, close status, etc.) will plug in
    later as additional aggregations.
    """
    pending = case((Invoice.status == "review", 1), else_=0)
    blocked = case((Invoice.status == "error", 1), else_=0)

    invoice_stats = (
        select(
            Invoice.client_id.label("client_id"),
            func.count(Invoice.id).label("invoice_count"),
            func.coalesce(func.sum(pending), 0).label("pending_review_count"),
            func.coalesce(func.sum(blocked), 0).label("blocked_count"),
            func.coalesce(func.sum(Invoice.total_amount), 0).label("total_amount"),
        )
        .where(Invoice.organization_id == organization_id)
        .group_by(Invoice.client_id)
        .subquery()
    )

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
            activity_stats.c.last_activity_at,
        )
        .outerjoin(invoice_stats, invoice_stats.c.client_id == Client.id)
        .outerjoin(activity_stats, activity_stats.c.client_id == Client.id)
        .where(
            Client.organization_id == organization_id,
            Client.is_active.is_(True),
        )
        .order_by(Client.name.asc())
    )

    rows = (await db.execute(stmt)).all()
    data: list[PortfolioRow] = []
    for row in rows:
        last_activity = row.last_activity_at
        # SQLAlchemy returns naive-style datetimes for some drivers; the
        # response schema takes Pydantic's datetime, which tolerates either.
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
                total_amount=str(total_amount_raw) if total_amount_raw is not None else None,
                last_activity_at=last_activity,
            )
        )
    return PortfolioResponse(period=period, data=data)
