"""Schemas for paušal revenue tracking and threshold alerts."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

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
