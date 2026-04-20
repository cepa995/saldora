"""Tests for M14.2: KPO ledger service and API.

Covers auto-population from issued paušal invoices, manual back-fill
entries, storno (corrective) entries, and list filtering.
"""

from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token


async def _register_and_login(
    client: AsyncClient,
    email: str,
    password: str = "securepass123",
) -> dict[str, str]:
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Kpo",
            "last_name": "Tester",
        },
    )
    token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Kpo Org {email}"},
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


async def _create_pausalac(
    client: AsyncClient,
    headers: dict,
    *,
    pib: str = "123456789",
) -> str:
    resp = await client.post(
        "/api/v1/clients/",
        json={
            "name": "Test Paušalac",
            "pib": pib,
            "client_type": "pausalac",
            "bank_account": "160-0000000000000-11",
            "activity_code": "6201",
            "address": "Knez Mihailova 1",
            "city": "Beograd",
            "postal_code": "11000",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class _FakeS3:
    def put_object(self, **kwargs):
        pass

    def generate_presigned_url(self, *args, **kwargs):
        return "https://storage/fake-signed"


def _mock_s3():
    """Convenience patch for S3 calls in issuance flow."""
    return patch(
        "app.services.pausal_invoice_issuance.storage.get_s3_client",
        return_value=_FakeS3(),
    )


async def _issue_invoice(
    client: AsyncClient,
    headers: dict,
    pausalac_id: str,
    *,
    customer_pib: str,
    amount: str,
    invoice_date: str = "2026-04-20",
) -> dict:
    with _mock_s3():
        resp = await client.post(
            f"/api/v1/pausal/{pausalac_id}/invoices",
            json={
                "new_customer": {"name": f"Kupac {customer_pib}", "pib": customer_pib},
                "invoice_date": invoice_date,
                "place_of_issue": "Beograd",
                "items": [{"description": "Usluga", "quantity": "1", "unit_price": amount}],
            },
            headers=headers,
        )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Auto-population
# ---------------------------------------------------------------------------


async def test_issued_invoice_auto_creates_kpo_entry(client: AsyncClient, test_engine):
    """Issuing a paušal invoice creates exactly one KPO entry with matching fields."""
    headers = await _setup(client, test_engine, "kpo-auto@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100100100")

    invoice = await _issue_invoice(
        client, headers, paušalac_id, customer_pib="200200200", amount="7500.00"
    )

    list_resp = await client.get(f"/api/v1/pausal/{paušalac_id}/kpo", headers=headers)
    assert list_resp.status_code == 200
    entries = list_resp.json()["data"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["entry_number"] == invoice["invoice_number"]
    assert entry["invoice_number"] == invoice["invoice_number"]
    assert entry["customer_name"] == "Kupac 200200200"
    assert entry["customer_pib"] == "200200200"
    assert entry["amount"] == "7500.00"
    assert entry["is_cancelled"] is False
    assert entry["storno_of_id"] is None


async def test_kpo_entries_share_counter_with_invoices(client: AsyncClient, test_engine):
    """Manual and auto entries share one monotonic sequence per client per year."""
    headers = await _setup(client, test_engine, "kpo-counter@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="300300300")

    # Issue one invoice → KPO entry 2026-001 + counter at 1
    inv1 = await _issue_invoice(
        client, headers, paušalac_id, customer_pib="400400400", amount="1000.00"
    )
    assert inv1["invoice_number"] == "2026-001"

    # Manual entry → 2026-002
    manual = await client.post(
        f"/api/v1/pausal/{paušalac_id}/kpo",
        json={
            "entry_date": "2026-01-15",
            "customer_name": "Back-filled kupac",
            "amount": "2500.00",
        },
        headers=headers,
    )
    assert manual.status_code == 201
    assert manual.json()["entry_number"] == "2026-002"

    # Next issued invoice → 2026-003
    inv2 = await _issue_invoice(
        client, headers, paušalac_id, customer_pib="500500500", amount="3000.00"
    )
    assert inv2["invoice_number"] == "2026-003"


# ---------------------------------------------------------------------------
# Manual entries
# ---------------------------------------------------------------------------


async def test_manual_kpo_entry_creation(client: AsyncClient, test_engine):
    """Manual KPO entries create a ledger row without an invoice link."""
    headers = await _setup(client, test_engine, "kpo-manual@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="600600600")

    resp = await client.post(
        f"/api/v1/pausal/{paušalac_id}/kpo",
        json={
            "entry_date": "2026-02-01",
            "invoice_number": "LEGACY-007",
            "customer_name": "Stari Kupac",
            "customer_pib": "700700700",
            "amount": "12345.67",
            "notes": "Preneseno iz Excel",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    entry = resp.json()
    assert entry["invoice_id"] is None
    assert entry["invoice_number"] == "LEGACY-007"
    assert entry["customer_name"] == "Stari Kupac"
    assert entry["amount"] == "12345.67"
    assert entry["entry_number"] == "2026-001"


async def test_manual_entry_rejects_non_pausalac(client: AsyncClient, test_engine):
    """422 when client_type is not pausalac."""
    headers = await _setup(client, test_engine, "kpo-non-paus@example.com")
    resp = await client.post(
        "/api/v1/clients/",
        json={"name": "VAT", "pib": "700700701", "client_type": "vat_payer"},
        headers=headers,
    )
    vat_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/pausal/{vat_id}/kpo",
        json={
            "entry_date": "2026-02-01",
            "customer_name": "X",
            "amount": "100.00",
        },
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "client_not_pausalac"


# ---------------------------------------------------------------------------
# Storno
# ---------------------------------------------------------------------------


async def test_storno_marks_original_and_creates_reversal(client: AsyncClient, test_engine):
    """Storno cancels the original and inserts a negated-amount entry linked to it."""
    headers = await _setup(client, test_engine, "kpo-storno@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="800800800")

    await _issue_invoice(client, headers, paušalac_id, customer_pib="900900900", amount="5000.00")

    # Find the auto-created entry id
    list_resp = await client.get(f"/api/v1/pausal/{paušalac_id}/kpo", headers=headers)
    original_id = list_resp.json()["data"][0]["id"]

    storno = await client.post(
        f"/api/v1/pausal/{paušalac_id}/kpo/{original_id}/storno",
        json={"notes": "Pogrešno izdata"},
        headers=headers,
    )
    assert storno.status_code == 201, storno.text
    reversal = storno.json()
    assert Decimal(reversal["amount"]) == Decimal("-5000.00")
    assert reversal["storno_of_id"] == original_id
    assert reversal["notes"] == "Pogrešno izdata"
    assert reversal["entry_number"] == "2026-002"

    # Original should now be cancelled
    get_resp = await client.get(f"/api/v1/pausal/{paušalac_id}/kpo/{original_id}", headers=headers)
    assert get_resp.json()["is_cancelled"] is True


async def test_cannot_storno_cancelled_entry(client: AsyncClient, test_engine):
    """Stornoing an already-cancelled entry returns 422."""
    headers = await _setup(client, test_engine, "kpo-dup-storno@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="110110110")

    await _issue_invoice(client, headers, paušalac_id, customer_pib="120120120", amount="100.00")
    list_resp = await client.get(f"/api/v1/pausal/{paušalac_id}/kpo", headers=headers)
    original_id = list_resp.json()["data"][0]["id"]

    # First storno succeeds
    await client.post(
        f"/api/v1/pausal/{paušalac_id}/kpo/{original_id}/storno",
        json={"notes": "x"},
        headers=headers,
    )
    # Second storno on same id fails
    resp2 = await client.post(
        f"/api/v1/pausal/{paušalac_id}/kpo/{original_id}/storno",
        json={"notes": "y"},
        headers=headers,
    )
    assert resp2.status_code == 422
    assert resp2.json()["detail"]["code"] == "already_cancelled"


async def test_cannot_storno_a_storno_entry(client: AsyncClient, test_engine):
    """Storno of a storno entry returns 422."""
    headers = await _setup(client, test_engine, "kpo-recurse@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="130130130")

    await _issue_invoice(client, headers, paušalac_id, customer_pib="140140140", amount="100.00")
    list_resp = await client.get(f"/api/v1/pausal/{paušalac_id}/kpo", headers=headers)
    original_id = list_resp.json()["data"][0]["id"]

    storno = await client.post(
        f"/api/v1/pausal/{paušalac_id}/kpo/{original_id}/storno",
        json={"notes": "x"},
        headers=headers,
    )
    storno_id = storno.json()["id"]

    # Attempt to storno the storno
    resp = await client.post(
        f"/api/v1/pausal/{paušalac_id}/kpo/{storno_id}/storno",
        json={"notes": "z"},
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "cannot_storno_storno"


# ---------------------------------------------------------------------------
# Listing / filtering
# ---------------------------------------------------------------------------


async def test_list_filters_by_year(client: AsyncClient, test_engine):
    """?year=2025 returns only 2025 entries."""
    headers = await _setup(client, test_engine, "kpo-year@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="150150150")

    await _issue_invoice(
        client,
        headers,
        paušalac_id,
        customer_pib="160160160",
        amount="100.00",
        invoice_date="2025-05-05",
    )
    await _issue_invoice(
        client,
        headers,
        paušalac_id,
        customer_pib="170170170",
        amount="200.00",
        invoice_date="2026-05-05",
    )

    resp = await client.get(f"/api/v1/pausal/{paušalac_id}/kpo?year=2025", headers=headers)
    entries = resp.json()["data"]
    assert len(entries) == 1
    assert entries[0]["year"] == 2025


async def test_list_excludes_cancelled_when_asked(client: AsyncClient, test_engine):
    """include_cancelled=false hides cancelled originals but keeps storno rows."""
    headers = await _setup(client, test_engine, "kpo-hide-cancel@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="180180180")

    await _issue_invoice(client, headers, paušalac_id, customer_pib="190190190", amount="100.00")
    list_resp = await client.get(f"/api/v1/pausal/{paušalac_id}/kpo", headers=headers)
    original_id = list_resp.json()["data"][0]["id"]
    await client.post(
        f"/api/v1/pausal/{paušalac_id}/kpo/{original_id}/storno",
        json={"notes": "x"},
        headers=headers,
    )

    # include_cancelled=true (default) → both rows
    both = await client.get(f"/api/v1/pausal/{paušalac_id}/kpo", headers=headers)
    assert both.json()["pagination"]["total"] == 2

    # include_cancelled=false → only the storno row (original is cancelled)
    filtered = await client.get(
        f"/api/v1/pausal/{paušalac_id}/kpo?include_cancelled=false",
        headers=headers,
    )
    assert filtered.json()["pagination"]["total"] == 1
    assert filtered.json()["data"][0]["storno_of_id"] == original_id


async def test_kpo_org_isolation(client: AsyncClient, test_engine):
    """Org B cannot read org A's KPO entries."""
    headers_a = await _setup(client, test_engine, "kpo-org-a@example.com")
    headers_b = await _setup(client, test_engine, "kpo-org-b@example.com")
    paušalac_a = await _create_pausalac(client, headers_a, pib="210210210")

    await _issue_invoice(client, headers_a, paušalac_a, customer_pib="220220220", amount="50.00")

    # Org B hits 404 on the client lookup
    resp = await client.get(f"/api/v1/pausal/{paušalac_a}/kpo", headers=headers_b)
    assert resp.status_code == 404


async def test_get_nonexistent_entry_returns_404(client: AsyncClient, test_engine):
    """404 for an unknown KPO entry id."""
    headers = await _setup(client, test_engine, "kpo-404@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="230230230")

    resp = await client.get(f"/api/v1/pausal/{paušalac_id}/kpo/{uuid4()}", headers=headers)
    assert resp.status_code == 404
