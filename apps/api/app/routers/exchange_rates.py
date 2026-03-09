"""Exchange rate API endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.exchange_rate import ExchangeRate
from app.models.user import User
from app.schemas.exchange_rate import (
    ConversionRequest,
    ConversionResponse,
    ExchangeRateListResponse,
    ExchangeRateResponse,
)
from app.services.nbs import convert_to_rsd, get_exchange_rate, sync_exchange_rates

router = APIRouter()


@router.get("", response_model=ExchangeRateListResponse)
async def list_exchange_rates(
    request: Request,
    rate_date: date | None = Query(default=None, description="Date for rates (default: today)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExchangeRateListResponse:
    """List exchange rates for all supported currencies.

    Args:
        request: FastAPI request (for Redis access).
        rate_date: Date to get rates for. Defaults to today.
        db: Database session.
        user: Authenticated user.

    Returns:
        List of exchange rates for the requested date.
    """
    target_date = rate_date or date.today()
    redis = request.app.state.redis

    from app.config import get_settings

    settings = get_settings()

    rates = []
    for currency in settings.nbs_supported_currencies:
        rate_data = await get_exchange_rate(db, redis, currency, target_date)
        if rate_data:
            # Check if we have a DB record for response
            result = await db.execute(
                select(ExchangeRate).where(
                    ExchangeRate.currency == currency,
                    ExchangeRate.rate_date == rate_data["rate_date"],
                )
            )
            db_rate = result.scalar_one_or_none()
            if db_rate:
                rates.append(ExchangeRateResponse.model_validate(db_rate))

    return ExchangeRateListResponse(data=rates, rate_date=target_date)


@router.get("/{currency}", response_model=ExchangeRateResponse)
async def get_rate(
    currency: str,
    request: Request,
    rate_date: date | None = Query(default=None, description="Date for rate (default: today)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExchangeRateResponse:
    """Get exchange rate for a specific currency.

    Args:
        currency: ISO 4217 currency code (e.g. EUR, USD).
        request: FastAPI request (for Redis access).
        rate_date: Date for rate lookup. Defaults to today.
        db: Database session.
        user: Authenticated user.

    Returns:
        Exchange rate for the requested currency and date.
    """
    target_date = rate_date or date.today()
    redis = request.app.state.redis
    currency = currency.upper()

    rate_data = await get_exchange_rate(db, redis, currency, target_date)
    if not rate_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exchange rate not found for {currency} on {target_date}",
        )

    # Fetch DB record for full response with id
    result = await db.execute(
        select(ExchangeRate).where(
            ExchangeRate.currency == currency,
            ExchangeRate.rate_date == rate_data["rate_date"],
        )
    )
    db_rate = result.scalar_one_or_none()
    if not db_rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exchange rate not found for {currency} on {target_date}",
        )

    return ExchangeRateResponse.model_validate(db_rate)


@router.post("/sync", status_code=status.HTTP_200_OK)
async def trigger_sync(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> dict:
    """Manually trigger NBS exchange rate sync.

    Args:
        request: FastAPI request (for Redis access).
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Dict with count of synced rates.
    """
    redis = request.app.state.redis
    count = await sync_exchange_rates(db, redis)
    return {"synced": count, "message": f"Synced {count} exchange rates from NBS"}


@router.post("/convert", response_model=ConversionResponse)
async def convert_currency(
    body: ConversionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConversionResponse:
    """Convert an amount from foreign currency to RSD.

    Args:
        body: Conversion request with amount, currency, and optional date.
        request: FastAPI request (for Redis access).
        db: Database session.
        user: Authenticated user.

    Returns:
        Conversion result with RSD amount and rate used.
    """
    redis = request.app.state.redis
    target_date = body.rate_date or date.today()

    result = await convert_to_rsd(db, redis, body.amount, body.currency, target_date)
    return ConversionResponse(**result)
