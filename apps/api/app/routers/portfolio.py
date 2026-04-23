"""Portfolio view endpoint (M19.7)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_feature, require_role
from app.models.user import User
from app.plans import Feature
from app.schemas.portfolio import PortfolioResponse
from app.services.portfolio import compute_portfolio

router = APIRouter(dependencies=[Depends(require_feature(Feature.CLIENT_MANAGEMENT))])


def _validate_period(period: str | None) -> str:
    """Return a validated YYYY-MM period string; defaults to current month."""
    if period is None:
        now = datetime.now(UTC)
        return f"{now.year}-{now.month:02d}"
    try:
        year_str, month_str = period.split("-", 1)
        year = int(year_str)
        month = int(month_str)
        if not 1 <= month <= 12:
            raise ValueError
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period format; expected YYYY-MM",
        ) from None
    return f"{year}-{month:02d}"


@router.get("", response_model=PortfolioResponse)
async def get_portfolio(
    period: str | None = Query(default=None, description="YYYY-MM, defaults to current month"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> PortfolioResponse:
    """Return a row per active client with current-period health indicators.

    Scoped to the authenticated user's organization.
    """
    effective = _validate_period(period)
    return await compute_portfolio(db, user.organization_id, effective)
