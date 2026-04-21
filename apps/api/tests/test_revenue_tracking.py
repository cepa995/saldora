"""Tests for M14.3: paušal revenue tracking and threshold alerts."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token


async def _register_and_login(
    client: AsyncClient, email: str, password: str = "securepass123"
) -> dict[str, str]:
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Rev",
            "last_name": "Tester",
        },
    )
    token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Rev Org {email}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"Authorization": f"Bearer {org_resp.json()['access_token']}"}


def _get_org_id(headers: dict) -> str:
    return decode_token(headers["Authorization"].removeprefix("Bearer "))["org"]


async def _set_agency(test_engine, org_id: str) -> None:
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            text("UPDATE organizations SET plan = 'agency' WHERE id = :id"),
            {"id": org_id},
        )
        await session.commit()


async def _setup(client: AsyncClient, test_engine, email: str) -> dict[str, str]:
    headers = await _register_and_login(client, email)
    await _set_agency(test_engine, _get_org_id(headers))
    return headers


async def _create_pausalac(client: AsyncClient, headers: dict, *, pib: str) -> str:
    resp = await client.post(
        "/api/v1/clients/",
        json={
            "name": "Rev Paušalac",
            "pib": pib,
            "client_type": "pausalac",
            "bank_account": "160-0000000000000-11",
            "activity_code": "6201",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _seed_manual_entry(
    client: AsyncClient,
    headers: dict,
    pausalac_id: str,
    *,
    amount: str,
    year: int = 2026,
) -> None:
    """Insert a manual KPO entry of the given amount in the given year."""
    resp = await client.post(
        f"/api/v1/pausal/{pausalac_id}/kpo",
        json={
            "entry_date": f"{year}-06-15",
            "customer_name": "Kupac",
            "customer_pib": "100000032",
            "amount": amount,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text


# ---------------------------------------------------------------------------
# Happy path + alert levels
# ---------------------------------------------------------------------------


async def test_revenue_status_empty_returns_ok(client: AsyncClient, test_engine):
    """No KPO entries → total_revenue=0, both thresholds ok."""
    headers = await _setup(client, test_engine, "rev-empty@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100000104")

    resp = await client.get(
        f"/api/v1/pausal/{paušalac_id}/revenue-status?year=2026", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["year"] == 2026
    assert Decimal(body["total_revenue"]) == Decimal("0")
    assert body["overall_alert_level"] == "ok"
    assert body["thresholds"]["pausal_status"]["alert_level"] == "ok"
    assert body["thresholds"]["pdv"]["alert_level"] == "ok"
    assert body["non_rsd_count"] == 0


async def test_warning_level_at_75_percent_of_pausal_limit(client: AsyncClient, test_engine):
    """75% of 6M = 4.5M → pausal_status warning; pdv still ok (56.25%)."""
    headers = await _setup(client, test_engine, "rev-warn@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100000112")

    await _seed_manual_entry(client, headers, paušalac_id, amount="4500000.00")

    resp = await client.get(
        f"/api/v1/pausal/{paušalac_id}/revenue-status?year=2026", headers=headers
    )
    body = resp.json()
    assert body["thresholds"]["pausal_status"]["alert_level"] == "warning"
    assert body["thresholds"]["pausal_status"]["used_pct"] == 75.0
    assert body["thresholds"]["pdv"]["alert_level"] == "ok"
    assert body["overall_alert_level"] == "warning"


async def test_critical_level_at_90_percent(client: AsyncClient, test_engine):
    """90% of 6M = 5.4M → critical for pausal_status."""
    headers = await _setup(client, test_engine, "rev-crit@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100000129")

    await _seed_manual_entry(client, headers, paušalac_id, amount="5400000.00")

    resp = await client.get(
        f"/api/v1/pausal/{paušalac_id}/revenue-status?year=2026", headers=headers
    )
    body = resp.json()
    assert body["thresholds"]["pausal_status"]["alert_level"] == "critical"
    assert body["overall_alert_level"] == "critical"


async def test_exceeded_level_over_pausal_limit(client: AsyncClient, test_engine):
    """Over 6M → pausal_status exceeded."""
    headers = await _setup(client, test_engine, "rev-exceed@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100000137")

    await _seed_manual_entry(client, headers, paušalac_id, amount="6500000.00")

    resp = await client.get(
        f"/api/v1/pausal/{paušalac_id}/revenue-status?year=2026", headers=headers
    )
    body = resp.json()
    assert body["thresholds"]["pausal_status"]["alert_level"] == "exceeded"
    assert Decimal(body["thresholds"]["pausal_status"]["remaining"]) == Decimal("0")
    assert body["overall_alert_level"] == "exceeded"


async def test_overall_alert_is_worst_of_two(client: AsyncClient, test_engine):
    """At 8.5M: pausal_status exceeded, pdv also exceeded → exceeded overall."""
    headers = await _setup(client, test_engine, "rev-worst@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100000145")

    await _seed_manual_entry(client, headers, paušalac_id, amount="8500000.00")

    resp = await client.get(
        f"/api/v1/pausal/{paušalac_id}/revenue-status?year=2026", headers=headers
    )
    body = resp.json()
    assert body["thresholds"]["pausal_status"]["alert_level"] == "exceeded"
    assert body["thresholds"]["pdv"]["alert_level"] == "exceeded"
    assert body["overall_alert_level"] == "exceeded"


# ---------------------------------------------------------------------------
# Storno handling
# ---------------------------------------------------------------------------


async def test_storno_cancels_out_in_revenue(client: AsyncClient, test_engine):
    """A storno'd entry contributes 0 net revenue."""
    headers = await _setup(client, test_engine, "rev-storno@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100000153")

    # Two manual entries: 3M and 2M
    await _seed_manual_entry(client, headers, paušalac_id, amount="3000000.00")
    await _seed_manual_entry(client, headers, paušalac_id, amount="2000000.00")

    # Storno the first one
    list_resp = await client.get(f"/api/v1/pausal/{paušalac_id}/kpo", headers=headers)
    first_id = list_resp.json()["data"][0]["id"]
    await client.post(
        f"/api/v1/pausal/{paušalac_id}/kpo/{first_id}/storno",
        json={"notes": "mistake"},
        headers=headers,
    )

    # Expect only 2M left
    resp = await client.get(
        f"/api/v1/pausal/{paušalac_id}/revenue-status?year=2026", headers=headers
    )
    body = resp.json()
    assert Decimal(body["total_revenue"]) == Decimal("2000000.00")


# ---------------------------------------------------------------------------
# Year filter
# ---------------------------------------------------------------------------


async def test_year_filter_scopes_revenue(client: AsyncClient, test_engine):
    """Revenue in 2025 does not leak into 2026 status."""
    headers = await _setup(client, test_engine, "rev-year@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100000161")

    await _seed_manual_entry(client, headers, paušalac_id, amount="3000000.00", year=2025)
    await _seed_manual_entry(client, headers, paušalac_id, amount="1000000.00", year=2026)

    resp_2025 = await client.get(
        f"/api/v1/pausal/{paušalac_id}/revenue-status?year=2025", headers=headers
    )
    resp_2026 = await client.get(
        f"/api/v1/pausal/{paušalac_id}/revenue-status?year=2026", headers=headers
    )
    assert Decimal(resp_2025.json()["total_revenue"]) == Decimal("3000000.00")
    assert Decimal(resp_2026.json()["total_revenue"]) == Decimal("1000000.00")


async def test_year_defaults_to_current_year(client: AsyncClient, test_engine):
    """Omitting ?year uses the current year."""
    headers = await _setup(client, test_engine, "rev-default-year@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="800800808")

    current_year = datetime.now(UTC).year
    await _seed_manual_entry(client, headers, paušalac_id, amount="1234567.00", year=current_year)

    resp = await client.get(f"/api/v1/pausal/{paušalac_id}/revenue-status", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["year"] == current_year
    assert Decimal(body["total_revenue"]) == Decimal("1234567.00")


# ---------------------------------------------------------------------------
# Rejection paths + isolation
# ---------------------------------------------------------------------------


async def test_endpoint_rejects_non_pausalac(client: AsyncClient, test_engine):
    """Non-paušalac clients get 422 on revenue-status."""
    headers = await _setup(client, test_engine, "rev-non-paus@example.com")
    resp = await client.post(
        "/api/v1/clients/",
        json={"name": "VAT", "pib": "900900909", "client_type": "vat_payer"},
        headers=headers,
    )
    vat_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/pausal/{vat_id}/revenue-status", headers=headers)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "client_not_pausalac"


async def test_endpoint_404_for_unknown_client(client: AsyncClient, test_engine):
    """Unknown client id returns 404."""
    headers = await _setup(client, test_engine, "rev-404@example.com")
    resp = await client.get(f"/api/v1/pausal/{uuid4()}/revenue-status", headers=headers)
    assert resp.status_code == 404


async def test_org_isolation(client: AsyncClient, test_engine):
    """Org B cannot read org A's paušalac revenue status."""
    headers_a = await _setup(client, test_engine, "rev-org-a@example.com")
    headers_b = await _setup(client, test_engine, "rev-org-b@example.com")
    paušalac_a = await _create_pausalac(client, headers_a, pib="101010101")

    resp = await client.get(f"/api/v1/pausal/{paušalac_a}/revenue-status", headers=headers_b)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Non-RSD handling
# ---------------------------------------------------------------------------


async def test_portfolio_returns_one_row_per_pausalac(client: AsyncClient, test_engine):
    """GET /pausal/portfolio aggregates revenue in a single response."""
    headers = await _setup(client, test_engine, "rev-portfolio@example.com")
    paušalac_a = await _create_pausalac(client, headers, pib="100000170")
    paušalac_b = await _create_pausalac(client, headers, pib="404040404")

    await _seed_manual_entry(client, headers, paušalac_a, amount="1000000.00")
    await _seed_manual_entry(client, headers, paušalac_b, amount="5500000.00")

    resp = await client.get("/api/v1/pausal/portfolio?year=2026", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["year"] == 2026
    assert len(body["data"]) == 2
    by_id = {row["client_id"]: row for row in body["data"]}
    assert Decimal(by_id[paušalac_a]["total_revenue"]) == Decimal("1000000.00")
    assert by_id[paušalac_a]["overall_alert_level"] == "ok"
    assert Decimal(by_id[paušalac_b]["total_revenue"]) == Decimal("5500000.00")
    assert by_id[paušalac_b]["overall_alert_level"] == "critical"


async def test_portfolio_excludes_non_pausalac_clients(client: AsyncClient, test_engine):
    """Regular VAT-payer clients don't appear in the paušalci portfolio."""
    headers = await _setup(client, test_engine, "rev-portfolio-filter@example.com")
    await _create_pausalac(client, headers, pib="100000188")
    await client.post(
        "/api/v1/clients/",
        json={"name": "VAT", "pib": "100000196", "client_type": "vat_payer"},
        headers=headers,
    )

    resp = await client.get("/api/v1/pausal/portfolio", headers=headers)
    assert len(resp.json()["data"]) == 1
    assert resp.json()["data"][0]["pib"] == "100000188"


async def test_non_rsd_entries_excluded_and_counted(client: AsyncClient, test_engine):
    """Non-RSD entries do not inflate the RSD total but are reported via non_rsd_count."""
    headers = await _setup(client, test_engine, "rev-nonrsd@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="202020202")

    # RSD baseline
    await _seed_manual_entry(client, headers, paušalac_id, amount="1000000.00")

    # Insert a non-RSD KPO entry directly (the router forces RSD via default,
    # so we bypass it to simulate a legacy/foreign entry).
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO kpo_entries (id, created_at, updated_at, client_id,"
                " organization_id, year, entry_number, entry_date, customer_name,"
                " amount, currency, is_cancelled)"
                " VALUES (gen_random_uuid(), NOW(), NOW(), :cid, :oid,"
                " 2026, '2026-EUR', '2026-06-01', 'EU Customer',"
                " 500, 'EUR', false)"
            ),
            {"cid": paušalac_id, "oid": _get_org_id(headers)},
        )
        await session.commit()

    resp = await client.get(
        f"/api/v1/pausal/{paušalac_id}/revenue-status?year=2026", headers=headers
    )
    body = resp.json()
    assert Decimal(body["total_revenue"]) == Decimal("1000000.00")
    assert body["non_rsd_count"] == 1
