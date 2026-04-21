"""Tests for M14.4: paušal invoice issuance.

Covers customer CRUD, sequential numbering, invoice issuance (with existing
and inline new customer), PDF generation smoke test, rejection paths, and
the new ``direction`` filter on ``/api/v1/invoices``.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token


class _FakeS3:
    """No-op S3 client used as the default in tests.

    CI has no MinIO/S3 reachable; real put_object calls would attempt
    AWS DNS resolution. Tests that need to assert on put_object args
    should patch again inside the test with their own spy.
    """

    def put_object(self, **kwargs):
        pass

    def generate_presigned_url(self, *args, **kwargs):
        return "https://storage/fake-signed"


@pytest.fixture(autouse=True)
def _mock_s3_for_all_issuance_tests():
    """Stub out S3 so issuance tests don't reach out to AWS in CI."""
    with (
        patch(
            "app.services.pausal_invoice_issuance.storage.get_s3_client",
            return_value=_FakeS3(),
        ),
        patch(
            "app.services.storage._get_public_s3_client",
            return_value=_FakeS3(),
        ),
        patch(
            "app.services.storage.get_s3_client",
            return_value=_FakeS3(),
        ),
    ):
        yield


async def _register_and_login(
    client: AsyncClient,
    email: str = "pausal-issue@example.com",
    password: str = "securepass123",
) -> dict[str, str]:
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Pausal",
            "last_name": "Issuer",
        },
    )
    token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Pausal Org {email}"},
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
    pib: str = "100000008",
    bank: str | None = "160-0000000000000-11",
    activity: str | None = "6201",
) -> str:
    """Create a paušalac client and return its id."""
    resp = await client.post(
        "/api/v1/clients/",
        json={
            "name": "Test Paušalac",
            "pib": pib,
            "client_type": "pausalac",
            "bank_account": bank,
            "activity_code": activity,
            "address": "Knez Mihailova 1",
            "city": "Beograd",
            "postal_code": "11000",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Customer CRUD
# ---------------------------------------------------------------------------


async def test_create_and_list_customer(client: AsyncClient, test_engine):
    """Customer can be created under a paušalac and listed back."""
    headers = await _setup(client, test_engine, "cust-crud@example.com")
    paušalac_id = await _create_pausalac(client, headers)

    resp = await client.post(
        f"/api/v1/pausal/{paušalac_id}/customers",
        json={"name": "Kupac DOO", "pib": "100000016"},
        headers=headers,
    )
    assert resp.status_code == 201
    customer = resp.json()
    assert customer["name"] == "Kupac DOO"
    assert customer["client_id"] == paušalac_id

    list_resp = await client.get(f"/api/v1/pausal/{paušalac_id}/customers", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["pagination"]["total"] == 1


async def test_customer_endpoints_reject_non_pausalac(client: AsyncClient, test_engine):
    """Customer endpoints return 422 when the client is not a paušalac."""
    headers = await _setup(client, test_engine, "not-pausalac@example.com")
    resp = await client.post(
        "/api/v1/clients/",
        json={"name": "VAT Co", "pib": "200300400", "client_type": "vat_payer"},
        headers=headers,
    )
    vat_client_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/pausal/{vat_client_id}/customers",
        json={"name": "X"},
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "client_not_pausalac"


async def test_customer_org_isolation(client: AsyncClient, test_engine):
    """Customers from another org are 404 for a different user."""
    headers_a = await _setup(client, test_engine, "cust-org-a@example.com")
    headers_b = await _setup(client, test_engine, "cust-org-b@example.com")
    paušalac_a = await _create_pausalac(client, headers_a, pib="100000024")

    resp = await client.get(f"/api/v1/pausal/{paušalac_a}/customers", headers=headers_b)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Sequential numbering
# ---------------------------------------------------------------------------


async def test_sequential_numbering_three_invoices(client: AsyncClient, test_engine):
    """Three issued invoices in the same year get 001, 002, 003."""
    headers = await _setup(client, test_engine, "seq-num@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="400500600")

    payload_template = {
        "new_customer": {"name": "Kupac", "pib": "100000032"},
        "invoice_date": "2026-04-20",
        "place_of_issue": "Beograd",
        "items": [{"description": "Usluga", "quantity": "1", "unit_price": "1000.00"}],
    }

    # Use foreign customers so we can use arbitrary distinct tax IDs without
    # having to derive 3 checksum-valid Serbian PIBs.
    numbers = []
    for i in range(3):
        payload = dict(payload_template)
        payload["new_customer"] = {
            "name": f"Kupac {i}",
            "pib": f"EIN-{i:07d}",
            "country": "US",
        }
        resp = await client.post(
            f"/api/v1/pausal/{paušalac_id}/invoices", json=payload, headers=headers
        )
        assert resp.status_code == 201, resp.text
        numbers.append(resp.json()["invoice_number"])

    assert numbers == ["2026-001", "2026-002", "2026-003"]


async def test_numbering_resets_across_years(client: AsyncClient, test_engine):
    """Counter is scoped by year; different years start at 001 independently."""
    headers = await _setup(client, test_engine, "seq-year@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100000049")

    base = {
        "new_customer": {"name": "Kupac", "pib": "100000032"},
        "place_of_issue": "Beograd",
        "items": [{"description": "Usluga", "quantity": "1", "unit_price": "500.00"}],
    }

    r2025 = await client.post(
        f"/api/v1/pausal/{paušalac_id}/invoices",
        json={
            **base,
            "invoice_date": "2025-12-15",
            "new_customer": {"name": "A", "pib": "100000057"},
        },
        headers=headers,
    )
    r2026 = await client.post(
        f"/api/v1/pausal/{paušalac_id}/invoices",
        json={
            **base,
            "invoice_date": "2026-01-10",
            "new_customer": {"name": "B", "pib": "100000065"},
        },
        headers=headers,
    )
    assert r2025.json()["invoice_number"] == "2025-001"
    assert r2026.json()["invoice_number"] == "2026-001"


# ---------------------------------------------------------------------------
# Issuance happy path + snapshots + PDF
# ---------------------------------------------------------------------------


async def test_issue_invoice_with_existing_customer(client: AsyncClient, test_engine):
    """Can issue using an existing customer_id; customer snapshot is embedded."""
    headers = await _setup(client, test_engine, "issue-existing@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100000073")

    cust_resp = await client.post(
        f"/api/v1/pausal/{paušalac_id}/customers",
        json={"name": "Postojeći Kupac", "pib": "100000081"},
        headers=headers,
    )
    customer_id = cust_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/pausal/{paušalac_id}/invoices",
        json={
            "customer_id": customer_id,
            "invoice_date": "2026-04-20",
            "due_date": "2026-05-04",
            "place_of_issue": "Beograd",
            "items": [{"description": "Konsulting", "quantity": "10", "unit_price": "5000.00"}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["direction"] == "outgoing"
    assert body["status"] == "issued"
    assert body["total_amount"] == "50000.00"
    assert body["customer_snapshot"]["name"] == "Postojeći Kupac"
    assert body["seller_snapshot"]["bank_account"] == "160-0000000000000-11"
    assert body["pdf_url"] is not None


async def test_issue_invoice_with_inline_new_customer(client: AsyncClient, test_engine):
    """Inline new_customer creates a Customer record and issues the invoice."""
    headers = await _setup(client, test_engine, "issue-inline@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100000081")

    resp = await client.post(
        f"/api/v1/pausal/{paušalac_id}/invoices",
        json={
            "new_customer": {"name": "Novi Kupac", "pib": "100000090"},
            "invoice_date": "2026-04-20",
            "place_of_issue": "Novi Sad",
            "items": [
                {"description": "Razvoj softvera", "quantity": "40", "unit_price": "2500.00"}
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    list_resp = await client.get(f"/api/v1/pausal/{paušalac_id}/customers", headers=headers)
    assert list_resp.json()["pagination"]["total"] == 1
    assert list_resp.json()["data"][0]["name"] == "Novi Kupac"


async def test_issue_invoice_writes_pdf_to_storage(client: AsyncClient, test_engine):
    """The issuance flow uploads a PDF via the storage client."""
    headers = await _setup(client, test_engine, "issue-pdf@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100000090")

    captured: dict = {}

    class _FakeS3:
        def put_object(self, **kwargs):
            captured.update(kwargs)

        def generate_presigned_url(self, *args, **kwargs):
            return "https://storage/fake-signed"

    with patch(
        "app.services.pausal_invoice_issuance.storage.get_s3_client",
        return_value=_FakeS3(),
    ):
        with patch(
            "app.services.storage._get_public_s3_client",
            return_value=_FakeS3(),
        ):
            resp = await client.post(
                f"/api/v1/pausal/{paušalac_id}/invoices",
                json={
                    "new_customer": {"name": "K", "pib": "900100200"},
                    "invoice_date": "2026-04-20",
                    "place_of_issue": "Beograd",
                    "items": [{"description": "X", "quantity": "1", "unit_price": "500.00"}],
                },
                headers=headers,
            )
    assert resp.status_code == 201
    assert captured.get("ContentType") == "application/pdf"
    assert captured["Key"].endswith("/issued.pdf")
    assert captured["Body"].startswith(b"%PDF")


# ---------------------------------------------------------------------------
# Rejection paths
# ---------------------------------------------------------------------------


async def test_issue_rejects_missing_bank_account(client: AsyncClient, test_engine):
    """422 when paušalac has no bank_account."""
    headers = await _setup(client, test_engine, "miss-bank@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="900100200", bank=None)

    resp = await client.post(
        f"/api/v1/pausal/{paušalac_id}/invoices",
        json={
            "new_customer": {"name": "K", "pib": "100000016"},
            "invoice_date": "2026-04-20",
            "place_of_issue": "Beograd",
            "items": [{"description": "X", "quantity": "1", "unit_price": "1.00"}],
        },
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "pausal_client_incomplete"
    assert "bank_account" in resp.json()["detail"]["missing_fields"]


async def test_issue_rejects_missing_activity_code(client: AsyncClient, test_engine):
    """422 when paušalac has no activity_code."""
    headers = await _setup(client, test_engine, "miss-act@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100000016", activity=None)

    resp = await client.post(
        f"/api/v1/pausal/{paušalac_id}/invoices",
        json={
            "new_customer": {"name": "K", "pib": "200300400"},
            "invoice_date": "2026-04-20",
            "place_of_issue": "Beograd",
            "items": [{"description": "X", "quantity": "1", "unit_price": "1.00"}],
        },
        headers=headers,
    )
    assert resp.status_code == 422
    assert "activity_code" in resp.json()["detail"]["missing_fields"]


async def test_issue_rejects_non_pausalac_client(client: AsyncClient, test_engine):
    """422 when client_type is not pausalac."""
    headers = await _setup(client, test_engine, "non-paus@example.com")
    resp = await client.post(
        "/api/v1/clients/",
        json={"name": "VAT", "pib": "200300400", "client_type": "vat_payer"},
        headers=headers,
    )
    vat_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/pausal/{vat_id}/invoices",
        json={
            "new_customer": {"name": "K", "pib": "100000024"},
            "invoice_date": "2026-04-20",
            "place_of_issue": "Beograd",
            "items": [{"description": "X", "quantity": "1", "unit_price": "1.00"}],
        },
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "client_not_pausalac"


async def test_issue_rejects_both_customer_options(client: AsyncClient, test_engine):
    """Providing both customer_id and new_customer is 422."""
    headers = await _setup(client, test_engine, "both-cust@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="100000024")

    resp = await client.post(
        f"/api/v1/pausal/{paušalac_id}/invoices",
        json={
            "customer_id": str(uuid4()),
            "new_customer": {"name": "K", "pib": "100000032"},
            "invoice_date": "2026-04-20",
            "place_of_issue": "Beograd",
            "items": [{"description": "X", "quantity": "1", "unit_price": "1.00"}],
        },
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Invoice list direction filter
# ---------------------------------------------------------------------------


async def test_invoice_list_defaults_to_incoming(client: AsyncClient, test_engine):
    """GET /invoices with no direction filter hides outgoing invoices."""
    headers = await _setup(client, test_engine, "dir-default@example.com")
    paušalac_id = await _create_pausalac(client, headers, pib="400500600")

    # Issue an outgoing invoice
    await client.post(
        f"/api/v1/pausal/{paušalac_id}/invoices",
        json={
            "new_customer": {"name": "K", "pib": "100000049"},
            "invoice_date": "2026-04-20",
            "place_of_issue": "Beograd",
            "items": [{"description": "X", "quantity": "1", "unit_price": "1.00"}],
        },
        headers=headers,
    )

    # Default list excludes outgoing
    list_resp = await client.get("/api/v1/invoices", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["pagination"]["total"] == 0

    # direction=outgoing returns it
    out_resp = await client.get("/api/v1/invoices?direction=outgoing", headers=headers)
    assert out_resp.json()["pagination"]["total"] == 1

    # direction=all returns both
    all_resp = await client.get("/api/v1/invoices?direction=all", headers=headers)
    assert all_resp.json()["pagination"]["total"] == 1
