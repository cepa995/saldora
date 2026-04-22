"""Portfolio view schemas (M19.7)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PortfolioMonthlyPoint(BaseModel):
    """One point in the trailing monthly series used for the card sparkline."""

    period: str  # YYYY-MM
    invoice_count: int
    total_amount: str  # stringified Decimal to preserve precision


class PortfolioRow(BaseModel):
    """One client row in the agency portfolio grid.

    Period-scoped fields reflect the requested month. ``monthly_series`` is a
    trailing window (6 points) for the sparkline — always the same length so
    the axis is comparable across clients.
    """

    client_id: UUID
    name: str
    pib: str
    is_active: bool
    invoice_count: int
    pending_review_count: int
    blocked_count: int
    total_amount: str | None = None
    last_activity_at: datetime | None = None
    monthly_series: list[PortfolioMonthlyPoint] = []


class PortfolioResponse(BaseModel):
    """Agency portfolio — one row per active client."""

    period: str  # YYYY-MM
    data: list[PortfolioRow]
