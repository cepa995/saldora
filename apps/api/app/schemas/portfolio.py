"""Portfolio view schemas (M19.7)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PortfolioRow(BaseModel):
    """One client row in the agency portfolio grid."""

    client_id: UUID
    name: str
    pib: str
    is_active: bool
    invoice_count: int
    pending_review_count: int
    blocked_count: int
    last_activity_at: datetime | None = None


class PortfolioResponse(BaseModel):
    """Agency portfolio — one row per active client."""

    period: str  # YYYY-MM
    data: list[PortfolioRow]
