"""Unit tests for the NBS exchange rate service.

Tests cover fetch_rates_from_nbs, fetch_single_rate_from_nbs,
get_exchange_rate (4-tier cache lookup), convert_to_rsd, and
sync_exchange_rates. External dependencies (httpx, Redis) are mocked.
"""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.exchange_rate import ExchangeRate
from app.services.nbs import (
    _cache_key,
    convert_to_rsd,
    fetch_rates_from_nbs,
    fetch_single_rate_from_nbs,
    get_exchange_rate,
    sync_exchange_rates,
)

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

RATE_DATE = date(2026, 3, 1)

EUR_RATE_ITEM = {
    "code": "EUR",
    "date": "2026-03-01",
    "exchange_middle": "117.15",
    "exchange_buy": "116.90",
    "exchange_sell": "117.40",
    "parity": 1,
}

USD_RATE_ITEM = {
    "code": "USD",
    "date": "2026-03-01",
    "exchange_middle": "108.35",
    "exchange_buy": "108.10",
    "exchange_sell": "108.60",
    "parity": 1,
}

# Currency not in the supported list — should be filtered out
JPY_RATE_ITEM = {
    "code": "JPY",
    "date": "2026-03-01",
    "exchange_middle": "0.72",
    "exchange_buy": None,
    "exchange_sell": None,
    "parity": 100,
}

NBS_RESPONSE_MULTI = {"rates": [EUR_RATE_ITEM, USD_RATE_ITEM, JPY_RATE_ITEM]}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_httpx_response(payload: dict, status_code: int = 200) -> MagicMock:
    """Build a MagicMock that behaves like an httpx Response.

    Args:
        payload: Dict to return from .json().
        status_code: HTTP status code.

    Returns:
        MagicMock mimicking httpx.Response.
    """
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    if status_code >= 400:
        import httpx

        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    else:
        response.raise_for_status.return_value = None
    return response


def _make_async_http_client(response: MagicMock) -> MagicMock:
    """Wrap an httpx response in an async context-manager mock.

    Args:
        response: Mock response returned by client.get().

    Returns:
        MagicMock that can be used as ``async with httpx.AsyncClient() as client``.
    """
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _make_redis(cached_value: str | None = None) -> AsyncMock:
    """Create an AsyncMock that simulates a Redis client.

    Args:
        cached_value: JSON string to return from .get(), or None for a miss.

    Returns:
        AsyncMock with get/set/setex configured.
    """
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=cached_value)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    return redis


# ===========================================================================
# A. _cache_key
# ===========================================================================


def test_cache_key_format():
    """_cache_key returns the expected Redis key string."""
    key = _cache_key("EUR", date(2026, 3, 1))
    assert key == "nbs_rate:EUR:2026-03-01"


def test_cache_key_different_currencies():
    """_cache_key produces distinct keys for different currencies."""
    eur_key = _cache_key("EUR", RATE_DATE)
    usd_key = _cache_key("USD", RATE_DATE)
    assert eur_key != usd_key


# ===========================================================================
# B. fetch_rates_from_nbs
# ===========================================================================


async def test_fetch_rates_today():
    """fetch_rates_from_nbs with no date fetches /rates/today and filters currencies."""
    response = _make_httpx_response(NBS_RESPONSE_MULTI)
    ctx = _make_async_http_client(response)

    with patch("app.services.nbs.httpx.AsyncClient", return_value=ctx):
        rates = await fetch_rates_from_nbs()

    # EUR and USD are supported; JPY is not
    codes = {r["currency"] for r in rates}
    assert "EUR" in codes
    assert "USD" in codes
    assert "JPY" not in codes


async def test_fetch_rates_with_date():
    """fetch_rates_from_nbs with a date fetches /rates/{date}."""
    response = _make_httpx_response({"rates": [EUR_RATE_ITEM]})
    ctx = _make_async_http_client(response)

    with patch("app.services.nbs.httpx.AsyncClient", return_value=ctx):
        rates = await fetch_rates_from_nbs(rate_date=RATE_DATE)

    assert len(rates) == 1
    assert rates[0]["currency"] == "EUR"
    assert rates[0]["rate_date"] == RATE_DATE
    assert rates[0]["middle_rate"] == Decimal("117.15")


async def test_fetch_rates_decimal_fields():
    """Buying, middle, and selling rates are parsed as Decimals."""
    response = _make_httpx_response({"rates": [EUR_RATE_ITEM]})
    ctx = _make_async_http_client(response)

    with patch("app.services.nbs.httpx.AsyncClient", return_value=ctx):
        rates = await fetch_rates_from_nbs()

    eur = rates[0]
    assert isinstance(eur["middle_rate"], Decimal)
    assert isinstance(eur["buying_rate"], Decimal)
    assert isinstance(eur["selling_rate"], Decimal)


async def test_fetch_rates_missing_middle_rate_skipped():
    """Rates without exchange_middle are silently skipped."""
    item_no_middle = {
        "code": "EUR",
        "date": "2026-03-01",
        "exchange_middle": None,
        "parity": 1,
    }
    response = _make_httpx_response({"rates": [item_no_middle]})
    ctx = _make_async_http_client(response)

    with patch("app.services.nbs.httpx.AsyncClient", return_value=ctx):
        rates = await fetch_rates_from_nbs()

    assert rates == []


async def test_fetch_rates_http_error_returns_empty():
    """HTTP errors cause fetch_rates_from_nbs to return empty list."""
    import httpx

    ctx = MagicMock()
    client = AsyncMock()
    client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.nbs.httpx.AsyncClient", return_value=ctx):
        rates = await fetch_rates_from_nbs()

    assert rates == []


async def test_fetch_rates_empty_rates_list():
    """NBS response with no rates returns empty list."""
    response = _make_httpx_response({"rates": []})
    ctx = _make_async_http_client(response)

    with patch("app.services.nbs.httpx.AsyncClient", return_value=ctx):
        rates = await fetch_rates_from_nbs()

    assert rates == []


async def test_fetch_rates_none_buying_selling():
    """Optional buy/sell rates are None when missing from the response."""
    item = {
        "code": "EUR",
        "date": "2026-03-01",
        "exchange_middle": "117.15",
        "exchange_buy": None,
        "exchange_sell": None,
        "parity": 1,
    }
    response = _make_httpx_response({"rates": [item]})
    ctx = _make_async_http_client(response)

    with patch("app.services.nbs.httpx.AsyncClient", return_value=ctx):
        rates = await fetch_rates_from_nbs()

    assert rates[0]["buying_rate"] is None
    assert rates[0]["selling_rate"] is None


# ===========================================================================
# C. fetch_single_rate_from_nbs
# ===========================================================================


async def test_fetch_single_rate_today():
    """fetch_single_rate_from_nbs with no date uses /currencies/{cur}/rates/today."""
    response = _make_httpx_response(EUR_RATE_ITEM)
    ctx = _make_async_http_client(response)

    with patch("app.services.nbs.httpx.AsyncClient", return_value=ctx):
        rate = await fetch_single_rate_from_nbs("EUR")

    assert rate is not None
    assert rate["currency"] == "EUR"
    assert rate["middle_rate"] == Decimal("117.15")


async def test_fetch_single_rate_with_date():
    """fetch_single_rate_from_nbs with a date uses /currencies/{cur}/rates/{date}."""
    response = _make_httpx_response(EUR_RATE_ITEM)
    ctx = _make_async_http_client(response)

    with patch("app.services.nbs.httpx.AsyncClient", return_value=ctx):
        rate = await fetch_single_rate_from_nbs("EUR", rate_date=RATE_DATE)

    assert rate["rate_date"] == RATE_DATE


async def test_fetch_single_rate_missing_middle_returns_none():
    """fetch_single_rate_from_nbs returns None when middle rate is missing."""
    item = {"code": "EUR", "date": "2026-03-01", "exchange_middle": None}
    response = _make_httpx_response(item)
    ctx = _make_async_http_client(response)

    with patch("app.services.nbs.httpx.AsyncClient", return_value=ctx):
        rate = await fetch_single_rate_from_nbs("EUR")

    assert rate is None


async def test_fetch_single_rate_http_error_returns_none():
    """HTTP error causes fetch_single_rate_from_nbs to return None."""
    import httpx

    ctx = MagicMock()
    client = AsyncMock()
    client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.nbs.httpx.AsyncClient", return_value=ctx):
        rate = await fetch_single_rate_from_nbs("EUR")

    assert rate is None


# ===========================================================================
# D. get_exchange_rate — 4-tier cache lookup
# ===========================================================================


async def test_get_exchange_rate_rsd_returns_one():
    """RSD currency short-circuits and returns rate of 1."""
    redis = _make_redis()
    db = AsyncMock(spec=AsyncSession)

    result = await get_exchange_rate(db, redis, "RSD", RATE_DATE)

    assert result is not None
    assert result["middle_rate"] == Decimal("1")
    assert result["unit"] == 1
    # Redis and DB should not be queried for RSD
    redis.get.assert_not_called()
    db.execute.assert_not_called()


async def test_get_exchange_rate_rsd_case_insensitive():
    """Currency code is uppercased so 'rsd' behaves like 'RSD'."""
    redis = _make_redis()
    db = AsyncMock(spec=AsyncSession)

    result = await get_exchange_rate(db, redis, "rsd", RATE_DATE)

    assert result["middle_rate"] == Decimal("1")


async def test_get_exchange_rate_from_redis_cache():
    """Cache hit: Redis returns a cached rate; DB is never queried."""
    cached = json.dumps(
        {
            "middle_rate": "117.15",
            "buying_rate": "116.90",
            "selling_rate": "117.40",
            "unit": 1,
        }
    )
    redis = _make_redis(cached_value=cached)
    db = AsyncMock(spec=AsyncSession)

    result = await get_exchange_rate(db, redis, "EUR", RATE_DATE)

    assert result is not None
    assert result["middle_rate"] == Decimal("117.15")
    assert result["rate_date"] == RATE_DATE
    db.execute.assert_not_called()


async def test_get_exchange_rate_from_db(test_engine):
    """Cache miss + DB hit: rate is fetched from DB and cached in Redis."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        rate_row = ExchangeRate(
            currency="EUR",
            rate_date=RATE_DATE,
            middle_rate=Decimal("117.15"),
            buying_rate=Decimal("116.90"),
            selling_rate=Decimal("117.40"),
            unit=1,
            source="NBS",
        )
        session.add(rate_row)
        await session.commit()

    redis = _make_redis(cached_value=None)  # Cache miss

    async with session_factory() as session:
        result = await get_exchange_rate(session, redis, "EUR", RATE_DATE)

    assert result is not None
    assert result["middle_rate"] == Decimal("117.15")
    # Should have written to Redis cache
    redis.set.assert_called_once()


async def test_get_exchange_rate_from_api(test_engine):
    """Cache miss + DB miss: rate is fetched from NBS API and persisted."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    redis = _make_redis(cached_value=None)

    api_rate = {
        "currency": "USD",
        "rate_date": date(2026, 3, 2),
        "middle_rate": Decimal("108.35"),
        "buying_rate": Decimal("108.10"),
        "selling_rate": Decimal("108.60"),
        "unit": 1,
    }

    with patch("app.services.nbs.fetch_single_rate_from_nbs", return_value=api_rate):
        async with session_factory() as session:
            result = await get_exchange_rate(session, redis, "USD", date(2026, 3, 2))

    assert result is not None
    assert result["middle_rate"] == Decimal("108.35")
    redis.set.assert_called_once()


async def test_get_exchange_rate_fallback_to_latest(test_engine):
    """All tiers miss for the exact date → falls back to latest known rate."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    # Insert a rate for an older date
    old_date = date(2026, 2, 1)
    async with session_factory() as session:
        rate_row = ExchangeRate(
            currency="CHF",
            rate_date=old_date,
            middle_rate=Decimal("122.50"),
            buying_rate=None,
            selling_rate=None,
            unit=1,
            source="NBS",
        )
        session.add(rate_row)
        await session.commit()

    redis = _make_redis(cached_value=None)
    future_date = date(2026, 3, 15)

    with patch("app.services.nbs.fetch_single_rate_from_nbs", return_value=None):
        async with session_factory() as session:
            result = await get_exchange_rate(session, redis, "CHF", future_date)

    assert result is not None
    assert result["middle_rate"] == Decimal("122.50")
    assert result["rate_date"] == old_date  # Fallback date, not the requested one


async def test_get_exchange_rate_all_tiers_miss(test_engine):
    """All 4 tiers miss → None is returned."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    redis = _make_redis(cached_value=None)

    with patch("app.services.nbs.fetch_single_rate_from_nbs", return_value=None):
        async with session_factory() as session:
            result = await get_exchange_rate(session, redis, "GBP", date(2026, 1, 1))

    assert result is None


# ===========================================================================
# E. convert_to_rsd
# ===========================================================================


async def test_convert_rsd_to_rsd():
    """Converting RSD → RSD returns the original amount unchanged."""
    redis = _make_redis()
    db = AsyncMock(spec=AsyncSession)

    result = await convert_to_rsd(db, redis, Decimal("5000.00"), "RSD", RATE_DATE)

    assert result["rsd_amount"] == Decimal("5000.00")
    assert result["exchange_rate"] == Decimal("1")
    assert result["error"] is None
    assert result["source"] == "RSD"


async def test_convert_eur_to_rsd():
    """EUR amount is correctly converted using the middle rate."""
    redis = _make_redis()
    db = AsyncMock(spec=AsyncSession)

    mock_rate = {
        "middle_rate": Decimal("117.15"),
        "unit": 1,
        "rate_date": RATE_DATE,
    }

    with patch("app.services.nbs.get_exchange_rate", return_value=mock_rate):
        result = await convert_to_rsd(db, redis, Decimal("100.00"), "EUR", RATE_DATE)

    assert result["rsd_amount"] == Decimal("11715.00")
    assert result["exchange_rate"] == Decimal("117.15")
    assert result["error"] is None
    assert result["source"] == "NBS srednji kurs"


async def test_convert_with_unit_multiplier():
    """Currency with parity != 1 is divided correctly (e.g., 100 JPY = X RSD)."""
    redis = _make_redis()
    db = AsyncMock(spec=AsyncSession)

    mock_rate = {
        "middle_rate": Decimal("72.50"),
        "unit": 100,
        "rate_date": RATE_DATE,
    }

    with patch("app.services.nbs.get_exchange_rate", return_value=mock_rate):
        result = await convert_to_rsd(db, redis, Decimal("1000.00"), "JPY", RATE_DATE)

    # 1000 * 72.50 / 100 = 725.00
    assert result["rsd_amount"] == Decimal("725.00")


async def test_convert_unavailable_rate_returns_error():
    """Unavailable rate returns error dict with None amounts."""
    redis = _make_redis()
    db = AsyncMock(spec=AsyncSession)

    with patch("app.services.nbs.get_exchange_rate", return_value=None):
        result = await convert_to_rsd(db, redis, Decimal("500.00"), "XXX", RATE_DATE)

    assert result["rsd_amount"] is None
    assert result["exchange_rate"] is None
    assert result["error"] is not None
    assert "XXX" in result["error"]


async def test_convert_case_insensitive_currency():
    """Currency code is uppercased before lookup."""
    redis = _make_redis()
    db = AsyncMock(spec=AsyncSession)

    result = await convert_to_rsd(db, redis, Decimal("100.00"), "rsd", RATE_DATE)

    assert result["rsd_amount"] == Decimal("100.00")
    assert result["source"] == "RSD"


async def test_convert_rsd_quantizes_to_two_decimals():
    """RSD amount from foreign conversion is rounded to 2 decimal places."""
    redis = _make_redis()
    db = AsyncMock(spec=AsyncSession)

    mock_rate = {
        "middle_rate": Decimal("117.1234567"),
        "unit": 1,
        "rate_date": RATE_DATE,
    }

    with patch("app.services.nbs.get_exchange_rate", return_value=mock_rate):
        result = await convert_to_rsd(db, redis, Decimal("1.00"), "EUR", RATE_DATE)

    # Must have at most 2 decimal places
    assert result["rsd_amount"] == result["rsd_amount"].quantize(Decimal("0.01"))


# ===========================================================================
# F. sync_exchange_rates
# ===========================================================================


async def test_sync_exchange_rates_success(test_engine):
    """sync_exchange_rates persists rates and returns count."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    redis = _make_redis()

    fake_rates = [
        {
            "currency": "EUR",
            "rate_date": RATE_DATE,
            "middle_rate": Decimal("117.15"),
            "buying_rate": Decimal("116.90"),
            "selling_rate": Decimal("117.40"),
            "unit": 1,
        },
        {
            "currency": "USD",
            "rate_date": RATE_DATE,
            "middle_rate": Decimal("108.35"),
            "buying_rate": Decimal("108.10"),
            "selling_rate": Decimal("108.60"),
            "unit": 1,
        },
    ]

    with patch("app.services.nbs.fetch_rates_from_nbs", return_value=fake_rates):
        async with session_factory() as session:
            count = await sync_exchange_rates(session, redis)

    assert count == 2
    # Redis should have been populated for each rate
    assert redis.set.call_count == 2


async def test_sync_exchange_rates_no_rates_returns_zero(test_engine):
    """sync_exchange_rates returns 0 when NBS API returns nothing."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    redis = _make_redis()

    with patch("app.services.nbs.fetch_rates_from_nbs", return_value=[]):
        async with session_factory() as session:
            count = await sync_exchange_rates(session, redis)

    assert count == 0
    redis.set.assert_not_called()


async def test_sync_exchange_rates_upserts_on_conflict(test_engine):
    """Syncing the same date twice performs an upsert, not a duplicate insert."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    redis = _make_redis()

    rate = {
        "currency": "EUR",
        "rate_date": date(2026, 3, 10),
        "middle_rate": Decimal("117.15"),
        "buying_rate": Decimal("116.90"),
        "selling_rate": Decimal("117.40"),
        "unit": 1,
    }
    updated_rate = {**rate, "middle_rate": Decimal("118.00")}

    with patch("app.services.nbs.fetch_rates_from_nbs", return_value=[rate]):
        async with session_factory() as session:
            await sync_exchange_rates(session, redis)

    # Second sync with an updated middle rate
    with patch("app.services.nbs.fetch_rates_from_nbs", return_value=[updated_rate]):
        async with session_factory() as session:
            await sync_exchange_rates(session, redis)
            # Verify the value was updated, not duplicated
            from sqlalchemy import select

            result = await session.execute(
                select(ExchangeRate).where(
                    ExchangeRate.currency == "EUR",
                    ExchangeRate.rate_date == date(2026, 3, 10),
                )
            )
            rows = result.scalars().all()

    assert len(rows) == 1
    assert rows[0].middle_rate == Decimal("118.00")
