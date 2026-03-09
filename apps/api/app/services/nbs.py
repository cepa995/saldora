"""NBS (National Bank of Serbia) exchange rate service.

Provides exchange rate lookup, caching, and currency conversion using
the NBS middle rate via the kurs.resenje.org public JSON API wrapper.
"""

import json
import logging
from datetime import date
from decimal import Decimal

import httpx
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.exchange_rate import ExchangeRate

logger = logging.getLogger(__name__)
settings = get_settings()

CACHE_KEY_PREFIX = "nbs_rate"


def _cache_key(currency: str, rate_date: date) -> str:
    """Build Redis cache key for a rate.

    Args:
        currency: ISO 4217 currency code.
        rate_date: Date of the exchange rate.

    Returns:
        Redis key string.
    """
    return f"{CACHE_KEY_PREFIX}:{currency}:{rate_date.isoformat()}"


async def fetch_rates_from_nbs(
    rate_date: date | None = None,
) -> list[dict]:
    """Fetch exchange rates from NBS API for all currencies.

    Args:
        rate_date: Date to fetch rates for. Defaults to today.

    Returns:
        List of rate dicts with keys: currency, rate_date, buying_rate,
        middle_rate, selling_rate, unit. Empty list on failure.
    """
    if rate_date:
        url = f"{settings.nbs_api_url}/rates/{rate_date.isoformat()}"
    else:
        url = f"{settings.nbs_api_url}/rates/today"

    try:
        async with httpx.AsyncClient(timeout=settings.nbs_request_timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Failed to fetch NBS rates: %s", exc)
        return []

    rates_list = data.get("rates", [])
    supported = set(settings.nbs_supported_currencies)
    results = []

    for item in rates_list:
        code = item.get("code", "")
        if code not in supported:
            continue

        middle = item.get("exchange_middle")
        if middle is None:
            continue

        buy = item.get("exchange_buy")
        sell = item.get("exchange_sell")
        results.append(
            {
                "currency": code,
                "rate_date": date.fromisoformat(item["date"]),
                "buying_rate": Decimal(str(buy)) if buy else None,
                "middle_rate": Decimal(str(middle)),
                "selling_rate": Decimal(str(sell)) if sell else None,
                "unit": item.get("parity", 1),
            }
        )

    return results


async def fetch_single_rate_from_nbs(
    currency: str,
    rate_date: date | None = None,
) -> dict | None:
    """Fetch a single currency rate from NBS API.

    Args:
        currency: ISO 4217 currency code (e.g. EUR, USD).
        rate_date: Date to fetch rate for. Defaults to today.

    Returns:
        Rate dict or None on failure.
    """
    if rate_date:
        url = f"{settings.nbs_api_url}/currencies/{currency}/rates/{rate_date.isoformat()}"
    else:
        url = f"{settings.nbs_api_url}/currencies/{currency}/rates/today"

    try:
        async with httpx.AsyncClient(timeout=settings.nbs_request_timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            item = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Failed to fetch NBS rate for %s: %s", currency, exc)
        return None

    middle = item.get("exchange_middle")
    if middle is None:
        return None

    buy = item.get("exchange_buy")
    sell = item.get("exchange_sell")
    return {
        "currency": item["code"],
        "rate_date": date.fromisoformat(item["date"]),
        "buying_rate": Decimal(str(buy)) if buy else None,
        "middle_rate": Decimal(str(middle)),
        "selling_rate": Decimal(str(sell)) if sell else None,
        "unit": item.get("parity", 1),
    }


async def _cache_get(redis: Redis, currency: str, rate_date: date) -> ExchangeRate | None:
    """Try to load a rate from Redis cache.

    Args:
        redis: Async Redis client.
        currency: Currency code.
        rate_date: Rate date.

    Returns:
        Deserialized ExchangeRate-like dict or None.
    """
    try:
        cached = await redis.get(_cache_key(currency, rate_date))
    except Exception:
        return None

    if not cached:
        return None

    data = json.loads(cached)
    return data


async def _cache_set(redis: Redis, currency: str, rate_date: date, rate_data: dict) -> None:
    """Store a rate in Redis cache.

    Args:
        redis: Async Redis client.
        currency: Currency code.
        rate_date: Rate date.
        rate_data: Dict with middle_rate, buying_rate, selling_rate, unit.
    """
    try:
        buy = rate_data.get("buying_rate")
        sell = rate_data.get("selling_rate")
        serializable = {
            "middle_rate": str(rate_data["middle_rate"]),
            "buying_rate": str(buy) if buy else None,
            "selling_rate": str(sell) if sell else None,
            "unit": rate_data.get("unit", 1),
        }
        await redis.set(
            _cache_key(currency, rate_date),
            json.dumps(serializable),
            ex=settings.nbs_cache_ttl,
        )
    except Exception:
        logger.warning("Failed to cache NBS rate for %s", currency)


async def get_exchange_rate(
    db: AsyncSession,
    redis: Redis,
    currency: str,
    rate_date: date,
) -> dict | None:
    """Get NBS middle rate using 4-tier lookup.

    Lookup order: Redis cache -> database -> NBS API -> fallback to
    latest known rate. Each successful fetch populates upstream caches.

    Args:
        db: Async database session.
        redis: Async Redis client.
        currency: ISO 4217 currency code.
        rate_date: Date of the desired rate.

    Returns:
        Dict with middle_rate (Decimal), buying_rate, selling_rate, unit,
        rate_date, or None if unavailable.
    """
    currency = currency.upper()

    if currency == "RSD":
        return {
            "middle_rate": Decimal("1"),
            "buying_rate": Decimal("1"),
            "selling_rate": Decimal("1"),
            "unit": 1,
            "rate_date": rate_date,
        }

    # 1. Redis cache
    cached = await _cache_get(redis, currency, rate_date)
    if cached:
        cached["rate_date"] = rate_date
        cached["middle_rate"] = Decimal(cached["middle_rate"])
        if cached.get("buying_rate"):
            cached["buying_rate"] = Decimal(cached["buying_rate"])
        if cached.get("selling_rate"):
            cached["selling_rate"] = Decimal(cached["selling_rate"])
        return cached

    # 2. Database
    result = await db.execute(
        select(ExchangeRate).where(
            ExchangeRate.currency == currency,
            ExchangeRate.rate_date == rate_date,
        )
    )
    db_rate = result.scalar_one_or_none()
    if db_rate:
        rate_data = {
            "middle_rate": db_rate.middle_rate,
            "buying_rate": db_rate.buying_rate,
            "selling_rate": db_rate.selling_rate,
            "unit": db_rate.unit,
            "rate_date": db_rate.rate_date,
        }
        await _cache_set(redis, currency, rate_date, rate_data)
        return rate_data

    # 3. NBS API
    api_rate = await fetch_single_rate_from_nbs(currency, rate_date)
    if api_rate:
        await _upsert_rate(db, api_rate)
        await _cache_set(redis, currency, api_rate["rate_date"], api_rate)
        return api_rate

    # 4. Fallback: latest known rate for this currency
    result = await db.execute(
        select(ExchangeRate)
        .where(ExchangeRate.currency == currency)
        .order_by(ExchangeRate.rate_date.desc())
        .limit(1)
    )
    fallback = result.scalar_one_or_none()
    if fallback:
        logger.warning(
            "Using fallback rate for %s: date=%s (requested %s)",
            currency,
            fallback.rate_date,
            rate_date,
        )
        return {
            "middle_rate": fallback.middle_rate,
            "buying_rate": fallback.buying_rate,
            "selling_rate": fallback.selling_rate,
            "unit": fallback.unit,
            "rate_date": fallback.rate_date,
        }

    return None


async def convert_to_rsd(
    db: AsyncSession,
    redis: Redis,
    amount: Decimal,
    currency: str,
    invoice_date: date,
) -> dict:
    """Convert a foreign currency amount to RSD using NBS middle rate.

    Args:
        db: Async database session.
        redis: Async Redis client.
        amount: Amount in the source currency.
        currency: ISO 4217 source currency code.
        invoice_date: Date for rate lookup (typically invoice date).

    Returns:
        Dict with rsd_amount, exchange_rate, rate_date, source, error.
    """
    currency = currency.upper()

    if currency == "RSD":
        return {
            "rsd_amount": amount,
            "exchange_rate": Decimal("1"),
            "rate_date": invoice_date,
            "source": "RSD",
            "error": None,
        }

    rate = await get_exchange_rate(db, redis, currency, invoice_date)
    if not rate:
        return {
            "rsd_amount": None,
            "exchange_rate": None,
            "rate_date": None,
            "source": None,
            "error": f"Exchange rate unavailable for {currency} on {invoice_date}",
        }

    middle_rate = rate["middle_rate"]
    unit = rate.get("unit", 1)
    rsd_amount = (amount * middle_rate / Decimal(str(unit))).quantize(Decimal("0.01"))

    return {
        "rsd_amount": rsd_amount,
        "exchange_rate": middle_rate,
        "rate_date": rate["rate_date"],
        "source": "NBS srednji kurs",
        "error": None,
    }


async def _upsert_rate(db: AsyncSession, rate_data: dict) -> None:
    """Insert or update an exchange rate in the database.

    Args:
        db: Async database session.
        rate_data: Dict with currency, rate_date, buying_rate,
            middle_rate, selling_rate, unit.
    """
    stmt = pg_insert(ExchangeRate).values(
        currency=rate_data["currency"],
        rate_date=rate_data["rate_date"],
        buying_rate=rate_data.get("buying_rate"),
        middle_rate=rate_data["middle_rate"],
        selling_rate=rate_data.get("selling_rate"),
        unit=rate_data.get("unit", 1),
        source="NBS",
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_exchange_rate_currency_date",
        set_={
            "buying_rate": stmt.excluded.buying_rate,
            "middle_rate": stmt.excluded.middle_rate,
            "selling_rate": stmt.excluded.selling_rate,
            "unit": stmt.excluded.unit,
        },
    )
    await db.execute(stmt)


async def sync_exchange_rates(db: AsyncSession, redis: Redis) -> int:
    """Fetch and store today's rates for all supported currencies.

    Args:
        db: Async database session.
        redis: Async Redis client.

    Returns:
        Number of rates synced.
    """
    rates = await fetch_rates_from_nbs()
    if not rates:
        logger.warning("No rates returned from NBS API during sync")
        return 0

    count = 0
    for rate_data in rates:
        await _upsert_rate(db, rate_data)
        await _cache_set(redis, rate_data["currency"], rate_data["rate_date"], rate_data)
        count += 1

    await db.commit()
    logger.info("Synced %d NBS exchange rates", count)
    return count
