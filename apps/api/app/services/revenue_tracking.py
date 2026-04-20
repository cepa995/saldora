"""Paušal revenue tracking against the legal thresholds.

Revenue is summed from KPO ledger entries (the source of truth for what
a paušalac has invoiced) rather than from the invoices table directly
so that manual back-fill entries and storno corrections are reflected
automatically. Summing ``amount`` across all entries for a (client,
year) pair gives net revenue because storno rows (negative amount)
exactly cancel the originals (still present with ``is_cancelled=true``).

The computation is pure: no side effects, no persistence. The watchdog
(M18) will call ``compute_revenue_status`` on a schedule and persist
alerts separately.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.kpo_entry import KPOEntry
from app.schemas.revenue import (
    AlertLevel,
    PortfolioResponse,
    PortfolioRow,
    RevenueStatusResponse,
    ThresholdStatus,
)

# Serbian legal thresholds (RSD, per calendar year)
PAUSAL_STATUS_LIMIT = Decimal("6000000.00")
PDV_REGISTRATION_LIMIT = Decimal("8000000.00")

# Alert level thresholds as fractions of the legal limit
_WARNING_PCT = Decimal("75")
_CRITICAL_PCT = Decimal("90")


def _level_for_pct(pct: Decimal) -> AlertLevel:
    """Map a used-percentage to an alert level."""
    if pct >= 100:
        return "exceeded"
    if pct >= _CRITICAL_PCT:
        return "critical"
    if pct >= _WARNING_PCT:
        return "warning"
    return "ok"


def _worst(levels: list[AlertLevel]) -> AlertLevel:
    """Return the most severe level from a list."""
    order = ["ok", "warning", "critical", "exceeded"]
    worst = "ok"
    for level in levels:
        if order.index(level) > order.index(worst):
            worst = level
    return worst  # type: ignore[return-value]


def _threshold_status(total: Decimal, limit: Decimal) -> ThresholdStatus:
    """Build a per-threshold status object from total revenue and limit."""
    pct = (total / limit * Decimal("100")).quantize(Decimal("0.01")) if limit else Decimal("0")
    remaining = max(limit - total, Decimal("0"))
    return ThresholdStatus(
        limit=limit,
        used_pct=float(pct),
        remaining=remaining,
        alert_level=_level_for_pct(pct),
    )


async def compute_revenue_status(
    db: AsyncSession,
    paušalac: Client,
    year: int,
) -> RevenueStatusResponse:
    """Compute a paušalac's current-year revenue state against legal thresholds.

    Sums KPO entries for the given year filtered to RSD, classifies each
    threshold independently, then reports the worse of the two as the
    overall level.

    Args:
        db: Database session.
        paušalac: The paušalac Client (caller must verify the ``client_type``).
        year: Calendar year to compute (e.g. 2026).

    Returns:
        Full revenue status payload.
    """
    total_result = await db.execute(
        select(func.coalesce(func.sum(KPOEntry.amount), Decimal("0"))).where(
            KPOEntry.client_id == paušalac.id,
            KPOEntry.year == year,
            KPOEntry.currency == "RSD",
        )
    )
    total: Decimal = total_result.scalar() or Decimal("0")

    non_rsd_result = await db.execute(
        select(func.count(KPOEntry.id)).where(
            KPOEntry.client_id == paušalac.id,
            KPOEntry.year == year,
            KPOEntry.currency != "RSD",
        )
    )
    non_rsd_count = int(non_rsd_result.scalar() or 0)

    pausal_status = _threshold_status(total, PAUSAL_STATUS_LIMIT)
    pdv_status = _threshold_status(total, PDV_REGISTRATION_LIMIT)

    return RevenueStatusResponse(
        year=year,
        currency="RSD",
        total_revenue=total,
        thresholds={
            "pausal_status": pausal_status,
            "pdv": pdv_status,
        },
        overall_alert_level=_worst([pausal_status.alert_level, pdv_status.alert_level]),
        non_rsd_count=non_rsd_count,
    )


async def compute_portfolio_status(
    db: AsyncSession,
    organization_id: UUID,
    year: int,
) -> PortfolioResponse:
    """Compute revenue status for every paušalac in the organization.

    Single-query aggregation over Client LEFT JOIN KPO_Entry filtered by
    year, avoiding N+1 when rendering the agency portfolio view.

    Args:
        db: Database session.
        organization_id: Agency organization scope.
        year: Calendar year to compute.

    Returns:
        Portfolio response with one row per paušalac in the org.
    """
    rsd_amount = case(
        (KPOEntry.currency == "RSD", KPOEntry.amount),
        else_=Decimal("0"),
    )
    non_rsd_one = case(
        (KPOEntry.currency != "RSD", 1),
        else_=0,
    )

    stmt = (
        select(
            Client.id,
            Client.name,
            Client.pib,
            Client.activity_code,
            func.coalesce(func.sum(rsd_amount), Decimal("0")).label("total"),
            func.coalesce(func.sum(non_rsd_one), 0).label("non_rsd_count"),
        )
        .select_from(Client)
        .outerjoin(
            KPOEntry,
            (KPOEntry.client_id == Client.id) & (KPOEntry.year == year),
        )
        .where(
            Client.organization_id == organization_id,
            Client.client_type == "pausalac",
            Client.is_active.is_(True),
        )
        .group_by(Client.id, Client.name, Client.pib, Client.activity_code)
        .order_by(Client.name.asc())
    )
    rows = (await db.execute(stmt)).all()

    portfolio: list[PortfolioRow] = []
    for row in rows:
        total: Decimal = row.total or Decimal("0")
        pausal_status = _threshold_status(total, PAUSAL_STATUS_LIMIT)
        pdv_status = _threshold_status(total, PDV_REGISTRATION_LIMIT)
        portfolio.append(
            PortfolioRow(
                client_id=row.id,
                name=row.name,
                pib=row.pib,
                activity_code=row.activity_code,
                total_revenue=total,
                pausal_status_pct=pausal_status.used_pct,
                pdv_pct=pdv_status.used_pct,
                overall_alert_level=_worst([pausal_status.alert_level, pdv_status.alert_level]),
                non_rsd_count=int(row.non_rsd_count or 0),
            )
        )
    return PortfolioResponse(year=year, data=portfolio)
