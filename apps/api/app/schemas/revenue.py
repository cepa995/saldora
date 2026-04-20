"""Schemas for paušal revenue tracking and threshold alerts."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

AlertLevel = Literal["ok", "warning", "critical", "exceeded"]


class ThresholdStatus(BaseModel):
    """State of a single legal revenue threshold."""

    limit: Decimal
    used_pct: float
    remaining: Decimal
    alert_level: AlertLevel


class RevenueStatusResponse(BaseModel):
    """Current-year revenue state for a paušalac against legal thresholds.

    The overall alert level is the worst of the per-threshold levels.
    Non-RSD entries are excluded from the sum; ``non_rsd_count`` flags
    if any were ignored so the UI can hint at manual verification.
    """

    year: int
    currency: str = "RSD"
    total_revenue: Decimal
    thresholds: dict[str, ThresholdStatus]
    overall_alert_level: AlertLevel
    non_rsd_count: int


class PortfolioRow(BaseModel):
    """One paušalac row in the agency portfolio view."""

    client_id: UUID
    name: str
    pib: str
    activity_code: str | None = None
    total_revenue: Decimal
    pausal_status_pct: float
    pdv_pct: float
    overall_alert_level: AlertLevel
    non_rsd_count: int


class PortfolioResponse(BaseModel):
    """Agency portfolio of all paušalci with their current revenue status."""

    year: int
    data: list[PortfolioRow]
