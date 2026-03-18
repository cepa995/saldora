"""
API tests for exchange rate endpoints.

Tests exercise the full HTTP -> FastAPI -> DB -> response lifecycle.
Redis (app.state.redis) and NBS service calls are mocked so tests
never depend on running infrastructure.
"""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.main import app as fastapi_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _auth_headers(
    client: AsyncClient,
    email: str = "exr-default@example.com",
    org_name: str = "EXR Test Org",
) -> dict[str, str]:
    """Register a user, create an org, and return Authorization headers.

    The org creator is automatically assigned the admin role.

    Args:
        client: Async HTTP test client.
        email: Unique email address for the test user.
        org_name: Name of the organization to create.

    Returns:
        Dict with the Authorization Bearer header.
    """
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    token = reg.json()["access_token"]
    org = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": org_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"Authorization": f"Bearer {org.json()['access_token']}"}


async def _viewer_headers(
    client: AsyncClient,
    email: str,
    org_name: str,
) -> dict[str, str]:
    """Register a user, create an org, then downgrade the user to viewer role.

    Args:
        client: Async HTTP test client.
        email: Unique email address for the test user.
        org_name: Name of the organization to create.

    Returns:
        Dict with the Authorization Bearer header for a viewer-role user.
    """
    headers = await _auth_headers(client, email=email, org_name=org_name)

    from app.database import get_db

    db_gen = fastapi_app.dependency_overrides[get_db]()
    db = await db_gen.__anext__()
    await db.execute(
        text("UPDATE users SET role = 'viewer' WHERE email = :email"),
        {"email": email},
    )
    await db.commit()
    try:
        await db_gen.__anext__()
    except StopAsyncIteration:
        pass

    return headers


def _mock_redis() -> AsyncMock:
    """Build an AsyncMock that acts as a Redis client returning a cache miss.

    Returns:
        AsyncMock configured to simulate an empty Redis cache.
    """
    redis = AsyncMock()
    redis.get.return_value = None  # cache miss by default
    redis.set.return_value = True
    return redis


async def _seed_exchange_rate(
    client: AsyncClient,
    currency: str,
    rate_date: date,
    middle_rate: str,
    buying_rate: str | None = None,
    selling_rate: str | None = None,
    unit: int = 1,
) -> None:
    """Insert an exchange rate row directly into the test DB.

    Args:
        client: Async HTTP test client (unused but keeps fixture parity).
        currency: ISO 4217 currency code.
        rate_date: Date for the rate.
        middle_rate: Middle rate as a string decimal.
        buying_rate: Buying rate as a string decimal, or None.
        selling_rate: Selling rate as a string decimal, or None.
        unit: Unit multiplier.

    Returns:
        None
    """
    from app.database import get_db

    db_gen = fastapi_app.dependency_overrides[get_db]()
    db = await db_gen.__anext__()
    await db.execute(
        text(
            "INSERT INTO exchange_rates "
            "  (id, currency, rate_date, buying_rate, middle_rate, selling_rate, unit, source) "
            "VALUES "
            "  (:id, :currency, :rate_date, :buying_rate,"
            " :middle_rate, :selling_rate, :unit, 'NBS') "
            "ON CONFLICT ON CONSTRAINT uq_exchange_rate_currency_date DO NOTHING"
        ),
        {
            "id": str(uuid.uuid4()),
            "currency": currency,
            "rate_date": rate_date,
            "buying_rate": buying_rate,
            "middle_rate": middle_rate,
            "selling_rate": selling_rate,
            "unit": unit,
        },
    )
    await db.commit()
    try:
        await db_gen.__anext__()
    except StopAsyncIteration:
        pass


# ---------------------------------------------------------------------------
# GET /api/v1/exchange-rates  (no trailing slash — router uses "")
# ---------------------------------------------------------------------------


async def test_list_rates_requires_auth(client: AsyncClient) -> None:
    """List exchange rates without a token returns 401.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    response = await client.get("/api/v1/exchange-rates")
    assert response.status_code == 401


async def test_list_rates_returns_empty_when_no_data(client: AsyncClient) -> None:
    """List exchange rates returns an empty list when no rates exist in DB or cache.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client, email="exr-list-empty@example.com", org_name="EXR List Empty"
    )
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    # NBS API also unavailable — cache miss, no DB data, NBS returns nothing
    with patch("app.services.nbs.fetch_single_rate_from_nbs", return_value=None):
        response = await client.get("/api/v1/exchange-rates", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert "rate_date" in data


async def test_list_rates_returns_seeded_eur_rate(client: AsyncClient) -> None:
    """List exchange rates includes a row that was seeded directly into the DB.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(client, email="exr-list-db@example.com", org_name="EXR List DB")
    today = date.today()

    await _seed_exchange_rate(
        client,
        currency="EUR",
        rate_date=today,
        middle_rate="117.123456",
        buying_rate="116.500000",
        selling_rate="117.800000",
    )

    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    # NBS API not needed — data already in DB
    with patch("app.services.nbs.fetch_single_rate_from_nbs", return_value=None):
        response = await client.get("/api/v1/exchange-rates", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["data"], list)
    currencies = [r["currency"] for r in data["data"]]
    assert "EUR" in currencies

    eur_row = next(r for r in data["data"] if r["currency"] == "EUR")
    assert float(eur_row["middle_rate"]) == pytest.approx(117.123456, abs=0.0001)
    assert eur_row["source"] == "NBS"
    assert str(eur_row["rate_date"]) == today.isoformat()


async def test_list_rates_accepts_date_query_param(client: AsyncClient) -> None:
    """List exchange rates accepts a ?rate_date= query parameter.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client, email="exr-list-date@example.com", org_name="EXR List Date"
    )
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    with patch("app.services.nbs.fetch_single_rate_from_nbs", return_value=None):
        response = await client.get(
            "/api/v1/exchange-rates",
            params={"rate_date": "2025-01-15"},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["rate_date"] == "2025-01-15"


async def test_list_rates_redis_called_per_currency(client: AsyncClient) -> None:
    """List rates calls Redis.get once per supported currency.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client, email="exr-redis-calls@example.com", org_name="EXR Redis Calls"
    )

    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    with patch("app.services.nbs.fetch_single_rate_from_nbs", return_value=None):
        await client.get("/api/v1/exchange-rates", headers=headers)

    # Default supported currencies: EUR, USD, CHF, GBP → 4 cache checks
    from app.config import get_settings

    expected_calls = len(get_settings().nbs_supported_currencies)
    assert mock_redis.get.call_count == expected_calls


# ---------------------------------------------------------------------------
# GET /api/v1/exchange-rates/{currency}
# ---------------------------------------------------------------------------


async def test_get_single_rate_requires_auth(client: AsyncClient) -> None:
    """Get single rate without a token returns 401.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    response = await client.get("/api/v1/exchange-rates/EUR")
    assert response.status_code == 401


async def test_get_single_rate_returns_404_when_not_found(client: AsyncClient) -> None:
    """Get single rate returns 404 when currency has no data in cache, DB, or NBS.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client, email="exr-single-404@example.com", org_name="EXR Single 404"
    )
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    with patch("app.services.nbs.fetch_single_rate_from_nbs", return_value=None):
        response = await client.get("/api/v1/exchange-rates/EUR", headers=headers)

    assert response.status_code == 404
    assert "EUR" in response.json()["detail"]


async def test_get_single_rate_from_db_when_cache_miss(client: AsyncClient) -> None:
    """Get single rate falls back to DB when Redis cache is cold.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    today = date.today()
    headers = await _auth_headers(
        client, email="exr-db-fallback@example.com", org_name="EXR DB Fallback"
    )

    await _seed_exchange_rate(
        client,
        currency="CHF",
        rate_date=today,
        middle_rate="130.250000",
        buying_rate="129.100000",
        selling_rate="131.400000",
    )

    mock_redis = _mock_redis()
    mock_redis.get.return_value = None  # cache miss
    fastapi_app.state.redis = mock_redis

    # NBS fetch should not be called — data is in DB
    with patch("app.services.nbs.fetch_single_rate_from_nbs") as mock_nbs:
        response = await client.get("/api/v1/exchange-rates/CHF", headers=headers)
        mock_nbs.assert_not_called()

    assert response.status_code == 200
    data = response.json()
    assert data["currency"] == "CHF"
    assert float(data["middle_rate"]) == pytest.approx(130.25, abs=0.01)


async def test_get_single_rate_normalises_currency_to_uppercase(client: AsyncClient) -> None:
    """Currency code in the URL path is normalised to uppercase before lookup.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(client, email="exr-upper@example.com", org_name="EXR Upper")
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    # No data → 404, but the detail message should reference the uppercased code
    with patch("app.services.nbs.fetch_single_rate_from_nbs", return_value=None):
        response = await client.get("/api/v1/exchange-rates/eur", headers=headers)

    assert response.status_code == 404
    assert "EUR" in response.json()["detail"]


async def test_get_single_rate_accepts_date_query_param(client: AsyncClient) -> None:
    """Get single rate accepts and uses the ?rate_date= query parameter.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client, email="exr-single-date@example.com", org_name="EXR Single Date"
    )
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    with patch("app.services.nbs.fetch_single_rate_from_nbs", return_value=None):
        response = await client.get(
            "/api/v1/exchange-rates/EUR",
            params={"rate_date": "2025-06-01"},
            headers=headers,
        )

    # No data for that date → 404; the important thing is no 422/500
    assert response.status_code == 404


async def test_get_single_rate_populates_redis_after_db_hit(client: AsyncClient) -> None:
    """After a DB lookup the rate is written into Redis cache.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    today = date.today()
    headers = await _auth_headers(
        client, email="exr-redis-populate@example.com", org_name="EXR Redis Populate"
    )

    await _seed_exchange_rate(
        client,
        currency="USD",
        rate_date=today,
        middle_rate="108.500000",
        buying_rate="107.000000",
        selling_rate="109.000000",
    )

    mock_redis = _mock_redis()
    mock_redis.get.return_value = None  # cold cache
    fastapi_app.state.redis = mock_redis

    response = await client.get("/api/v1/exchange-rates/USD", headers=headers)
    assert response.status_code == 200
    # After a DB lookup _cache_set writes back to Redis
    assert mock_redis.set.called


# ---------------------------------------------------------------------------
# POST /api/v1/exchange-rates/sync
# ---------------------------------------------------------------------------


async def test_sync_requires_auth(client: AsyncClient) -> None:
    """Sync endpoint without a token returns 401.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    response = await client.post("/api/v1/exchange-rates/sync")
    assert response.status_code == 401


async def test_sync_requires_admin_role(client: AsyncClient) -> None:
    """Sync endpoint with a viewer-role user returns 403.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _viewer_headers(
        client,
        email="exr-sync-viewer@example.com",
        org_name="EXR Sync Viewer",
    )
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    with patch("app.services.nbs.fetch_rates_from_nbs", return_value=[]):
        response = await client.post("/api/v1/exchange-rates/sync", headers=headers)

    assert response.status_code == 403


async def test_sync_succeeds_for_admin(client: AsyncClient) -> None:
    """Admin can trigger sync; response contains count of synced rates.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    # org creator is always admin
    headers = await _auth_headers(
        client, email="exr-sync-admin@example.com", org_name="EXR Sync Admin"
    )
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    today = date.today()
    fake_rates = [
        {
            "currency": "EUR",
            "rate_date": today,
            "buying_rate": Decimal("116.500000"),
            "middle_rate": Decimal("117.123456"),
            "selling_rate": Decimal("117.800000"),
            "unit": 1,
        },
        {
            "currency": "USD",
            "rate_date": today,
            "buying_rate": Decimal("107.000000"),
            "middle_rate": Decimal("108.500000"),
            "selling_rate": Decimal("109.000000"),
            "unit": 1,
        },
    ]

    with patch("app.services.nbs.fetch_rates_from_nbs", return_value=fake_rates):
        response = await client.post("/api/v1/exchange-rates/sync", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["synced"] == 2
    assert "2" in data["message"]


async def test_sync_returns_zero_when_nbs_unavailable(client: AsyncClient) -> None:
    """Sync returns synced=0 when NBS API returns no data.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client,
        email="exr-sync-nbs-down@example.com",
        org_name="EXR Sync NBS Down",
    )
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    with patch("app.services.nbs.fetch_rates_from_nbs", return_value=[]):
        response = await client.post("/api/v1/exchange-rates/sync", headers=headers)

    assert response.status_code == 200
    assert response.json()["synced"] == 0


async def test_sync_persists_rates_to_db(client: AsyncClient) -> None:
    """After sync, the synced rate is retrievable via the GET endpoint.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client,
        email="exr-sync-persist@example.com",
        org_name="EXR Sync Persist",
    )
    today = date.today()
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    fake_rates = [
        {
            "currency": "GBP",
            "rate_date": today,
            "buying_rate": Decimal("150.000000"),
            "middle_rate": Decimal("152.500000"),
            "selling_rate": Decimal("155.000000"),
            "unit": 1,
        },
    ]

    with patch("app.services.nbs.fetch_rates_from_nbs", return_value=fake_rates):
        sync_resp = await client.post("/api/v1/exchange-rates/sync", headers=headers)

    assert sync_resp.status_code == 200
    assert sync_resp.json()["synced"] == 1

    # Retrieve the newly synced rate
    get_resp = await client.get("/api/v1/exchange-rates/GBP", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["currency"] == "GBP"
    assert float(get_resp.json()["middle_rate"]) == pytest.approx(152.5, abs=0.01)


async def test_sync_and_list_end_to_end(client: AsyncClient) -> None:
    """Full cycle: sync rates then list them — data flows DB -> list response.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client, email="exr-e2e-admin@example.com", org_name="EXR E2E Admin"
    )
    today = date.today()
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    fake_rates = [
        {
            "currency": "EUR",
            "rate_date": today,
            "buying_rate": Decimal("116.000000"),
            "middle_rate": Decimal("117.000000"),
            "selling_rate": Decimal("118.000000"),
            "unit": 1,
        },
    ]

    with patch("app.services.nbs.fetch_rates_from_nbs", return_value=fake_rates):
        sync_resp = await client.post("/api/v1/exchange-rates/sync", headers=headers)

    assert sync_resp.status_code == 200
    assert sync_resp.json()["synced"] == 1

    with patch("app.services.nbs.fetch_single_rate_from_nbs", return_value=None):
        list_resp = await client.get("/api/v1/exchange-rates", headers=headers)

    assert list_resp.status_code == 200
    currencies = [r["currency"] for r in list_resp.json()["data"]]
    assert "EUR" in currencies


# ---------------------------------------------------------------------------
# POST /api/v1/exchange-rates/convert
# ---------------------------------------------------------------------------


async def test_convert_requires_auth(client: AsyncClient) -> None:
    """Convert endpoint without a token returns 401.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    response = await client.post(
        "/api/v1/exchange-rates/convert",
        json={"amount": "100.00", "currency": "EUR"},
    )
    assert response.status_code == 401


async def test_convert_eur_to_rsd(client: AsyncClient) -> None:
    """Convert EUR amount to RSD using a mocked exchange rate.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    today = date.today()
    headers = await _auth_headers(
        client, email="exr-convert-eur@example.com", org_name="EXR Convert EUR"
    )
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    fake_conversion = {
        "rsd_amount": Decimal("11712.35"),
        "exchange_rate": Decimal("117.1235"),
        "rate_date": today,
        "source": "NBS srednji kurs",
        "error": None,
    }

    # Patch the name as it exists in the router's namespace
    with patch("app.routers.exchange_rates.convert_to_rsd", return_value=fake_conversion):
        response = await client.post(
            "/api/v1/exchange-rates/convert",
            json={"amount": "100.00", "currency": "EUR"},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["error"] is None
    assert float(data["rsd_amount"]) == pytest.approx(11712.35, abs=0.01)
    assert data["source"] == "NBS srednji kurs"


async def test_convert_rsd_to_rsd_returns_same_amount(client: AsyncClient) -> None:
    """Converting RSD to RSD returns the amount unchanged with exchange rate 1.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client, email="exr-convert-rsd@example.com", org_name="EXR Convert RSD"
    )
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    # The real convert_to_rsd handles RSD natively — no NBS call needed
    response = await client.post(
        "/api/v1/exchange-rates/convert",
        json={"amount": "5000.00", "currency": "RSD"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["error"] is None
    assert float(data["rsd_amount"]) == pytest.approx(5000.0, abs=0.01)
    assert float(data["exchange_rate"]) == pytest.approx(1.0, abs=0.001)
    assert data["source"] == "RSD"


async def test_convert_returns_error_when_rate_unavailable(client: AsyncClient) -> None:
    """Convert returns an error payload (200, not 4xx) when rate is unavailable.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client,
        email="exr-convert-nodata@example.com",
        org_name="EXR Convert No Data",
    )
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    fake_error = {
        "rsd_amount": None,
        "exchange_rate": None,
        "rate_date": None,
        "source": None,
        "error": "Exchange rate unavailable for USD on 2020-01-01",
    }

    with patch("app.routers.exchange_rates.convert_to_rsd", return_value=fake_error):
        response = await client.post(
            "/api/v1/exchange-rates/convert",
            json={"amount": "250.00", "currency": "USD", "rate_date": "2020-01-01"},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["rsd_amount"] is None
    assert "unavailable" in data["error"].lower()


async def test_convert_validates_currency_length(client: AsyncClient) -> None:
    """Convert endpoint rejects currency codes that are not exactly 3 characters.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client,
        email="exr-convert-badcur@example.com",
        org_name="EXR Convert Bad Currency",
    )

    response = await client.post(
        "/api/v1/exchange-rates/convert",
        json={"amount": "100.00", "currency": "EU"},  # 2 chars — invalid
        headers=headers,
    )
    assert response.status_code == 422


async def test_convert_validates_positive_amount(client: AsyncClient) -> None:
    """Convert endpoint rejects non-positive (zero) amounts.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client,
        email="exr-convert-badamt@example.com",
        org_name="EXR Convert Bad Amount",
    )

    response = await client.post(
        "/api/v1/exchange-rates/convert",
        json={"amount": "0", "currency": "EUR"},
        headers=headers,
    )
    assert response.status_code == 422


async def test_convert_accepts_optional_rate_date(client: AsyncClient) -> None:
    """Convert uses the supplied rate_date when present.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client,
        email="exr-convert-rdate@example.com",
        org_name="EXR Convert Rate Date",
    )
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    fake_conversion = {
        "rsd_amount": Decimal("9500.00"),
        "exchange_rate": Decimal("95.00"),
        "rate_date": date(2024, 6, 15),
        "source": "NBS srednji kurs",
        "error": None,
    }

    with patch(
        "app.routers.exchange_rates.convert_to_rsd", return_value=fake_conversion
    ) as mock_conv:
        response = await client.post(
            "/api/v1/exchange-rates/convert",
            json={"amount": "100.00", "currency": "USD", "rate_date": "2024-06-15"},
            headers=headers,
        )
        # Verify the service was called with the correct date
        call_args = mock_conv.call_args
        assert call_args.args[4] == date(2024, 6, 15)

    assert response.status_code == 200


async def test_convert_uses_today_when_rate_date_omitted(client: AsyncClient) -> None:
    """Convert defaults to today's date when rate_date is not provided.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    headers = await _auth_headers(
        client,
        email="exr-convert-nodate@example.com",
        org_name="EXR Convert No Date",
    )
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    today = date.today()
    fake_conversion = {
        "rsd_amount": Decimal("11750.00"),
        "exchange_rate": Decimal("117.50"),
        "rate_date": today,
        "source": "NBS srednji kurs",
        "error": None,
    }

    with patch(
        "app.routers.exchange_rates.convert_to_rsd", return_value=fake_conversion
    ) as mock_conv:
        response = await client.post(
            "/api/v1/exchange-rates/convert",
            json={"amount": "100.00", "currency": "EUR"},
            headers=headers,
        )
        # Service should be called with today's date
        call_args = mock_conv.call_args
        assert call_args.args[4] == today

    assert response.status_code == 200


async def test_convert_large_amount(client: AsyncClient) -> None:
    """Convert handles large invoice amounts without precision loss.

    Args:
        client: Async HTTP test client.

    Returns:
        None
    """
    today = date.today()
    headers = await _auth_headers(
        client, email="exr-convert-large@example.com", org_name="EXR Convert Large"
    )
    mock_redis = _mock_redis()
    fastapi_app.state.redis = mock_redis

    fake_conversion = {
        "rsd_amount": Decimal("11712350.00"),
        "exchange_rate": Decimal("117.1235"),
        "rate_date": today,
        "source": "NBS srednji kurs",
        "error": None,
    }

    with patch("app.routers.exchange_rates.convert_to_rsd", return_value=fake_conversion):
        response = await client.post(
            "/api/v1/exchange-rates/convert",
            json={"amount": "100000.00", "currency": "EUR"},
            headers=headers,
        )

    assert response.status_code == 200
    assert float(response.json()["rsd_amount"]) == pytest.approx(11712350.0, rel=1e-4)
