"""Tests for PIB validation across clients, customers, and issuance.

Covers:
- POST /api/v1/clients/ — enforces Serbian mod-11 PIB
- PATCH /api/v1/clients/{id} — re-validates when PIB changes
- POST /api/v1/pausal/{id}/customers — enforces PIB only when country=RS
- POST /api/v1/pausal/{id}/invoices — inline new_customer with foreign
  country accepts arbitrary PIB string
- PDF identifier line label swap (unit level)
"""

from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.services.pausal_pdf import _identifier_line


async def _register_and_login(
    client: AsyncClient, email: str, password: str = "securepass123"
) -> dict[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Pib",
            "last_name": "Tester",
        },
    )
    token = reg.json()["access_token"]
    org = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Pib Org {email}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"Authorization": f"Bearer {org.json()['access_token']}"}


def _get_org_id(headers: dict) -> str:
    return decode_token(headers["Authorization"].removeprefix("Bearer "))["org"]


async def _set_agency(test_engine, org_id: str) -> None:
    f = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with f() as s:
        await s.execute(
            text("UPDATE organizations SET plan = 'agency' WHERE id = :id"),
            {"id": org_id},
        )
        await s.commit()


async def _setup(client: AsyncClient, test_engine, email: str) -> dict[str, str]:
    headers = await _register_and_login(client, email)
    await _set_agency(test_engine, _get_org_id(headers))
    return headers


async def _create_pausalac(client: AsyncClient, headers: dict, pib: str) -> str:
    resp = await client.post(
        "/api/v1/clients/",
        json={
            "name": "Paušalac",
            "pib": pib,
            "client_type": "pausalac",
            "bank_account": "160-0000000000000-11",
            "activity_code": "6201",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class _FakeS3:
    def put_object(self, **kwargs):
        pass

    def generate_presigned_url(self, *args, **kwargs):
        return "https://storage/fake-signed"


# ---------------------------------------------------------------------------
# Clients router
# ---------------------------------------------------------------------------

# 9-digit PIBs with valid mod-11 check digit (see validate_pib):
# "123456789" is NOT valid. We use values that actually pass the checksum.
VALID_PIB_A = "100000008"
VALID_PIB_B = "200000005"
VALID_PIB_C = "300000002"


async def test_create_client_rejects_invalid_pib(client: AsyncClient, test_engine):
    """POST /clients/ 422s when the PIB checksum fails."""
    headers = await _setup(client, test_engine, "pib-bad@example.com")
    resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Bad", "pib": "123456789"},
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "invalid_pib"


async def test_create_client_accepts_valid_pib(client: AsyncClient, test_engine):
    """POST /clients/ succeeds for a checksum-valid Serbian PIB."""
    headers = await _setup(client, test_engine, "pib-ok@example.com")
    resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Good", "pib": VALID_PIB_A},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text


async def test_update_client_revalidates_pib(client: AsyncClient, test_engine):
    """PATCH /clients/{id} 422s when the new PIB fails the checksum."""
    headers = await _setup(client, test_engine, "pib-patch@example.com")
    created = await client.post(
        "/api/v1/clients/",
        json={"name": "Good", "pib": VALID_PIB_A},
        headers=headers,
    )
    cid = created.json()["id"]

    resp = await client.patch(
        f"/api/v1/clients/{cid}",
        json={"pib": "999999999"},
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Customers (paušal) — PIB only enforced when country == 'RS'
# ---------------------------------------------------------------------------


async def test_customer_pib_required_valid_for_rs(client: AsyncClient, test_engine):
    """Customer with country=RS must have a checksum-valid PIB."""
    headers = await _setup(client, test_engine, "cust-rs@example.com")
    paušalac = await _create_pausalac(client, headers, pib=VALID_PIB_A)

    resp = await client.post(
        f"/api/v1/pausal/{paušalac}/customers",
        json={"name": "Serbian Buyer", "pib": "123456789", "country": "RS"},
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "invalid_pib"


async def test_customer_pib_skipped_for_foreign_country(client: AsyncClient, test_engine):
    """Customer with country=US accepts an arbitrary tax identifier."""
    headers = await _setup(client, test_engine, "cust-us@example.com")
    paušalac = await _create_pausalac(client, headers, pib=VALID_PIB_B)

    resp = await client.post(
        f"/api/v1/pausal/{paušalac}/customers",
        json={
            "name": "Acme Inc.",
            "pib": "12-3456789",  # EIN shape — would fail Serbian checksum
            "country": "US",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text


async def test_customer_update_revalidates_when_country_stays_rs(client: AsyncClient, test_engine):
    """PATCH a customer still under country=RS must keep a valid PIB."""
    headers = await _setup(client, test_engine, "cust-patch-rs@example.com")
    paušalac = await _create_pausalac(client, headers, pib=VALID_PIB_C)

    create = await client.post(
        f"/api/v1/pausal/{paušalac}/customers",
        json={"name": "OK Buyer", "pib": VALID_PIB_A, "country": "RS"},
        headers=headers,
    )
    cust_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/pausal/{paušalac}/customers/{cust_id}",
        json={"pib": "999999999"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_customer_update_skips_pib_when_changing_to_foreign(client: AsyncClient, test_engine):
    """Changing country RS → US skips PIB re-validation."""
    headers = await _setup(client, test_engine, "cust-patch-foreign@example.com")
    paušalac = await _create_pausalac(client, headers, pib=VALID_PIB_C)

    create = await client.post(
        f"/api/v1/pausal/{paušalac}/customers",
        json={"name": "OK Buyer", "pib": VALID_PIB_A, "country": "RS"},
        headers=headers,
    )
    cust_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/pausal/{paušalac}/customers/{cust_id}",
        json={"country": "US", "pib": "12-3456789"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Inline new_customer during issuance
# ---------------------------------------------------------------------------


async def test_inline_new_customer_foreign_issuance_succeeds(client: AsyncClient, test_engine):
    """Issuing to a freshly-created foreign customer works with non-Serbian ID."""
    headers = await _setup(client, test_engine, "issue-foreign@example.com")
    paušalac = await _create_pausalac(client, headers, pib=VALID_PIB_A)

    with (
        patch(
            "app.services.pausal_invoice_issuance.storage.get_s3_client",
            return_value=_FakeS3(),
        ),
        patch("app.services.storage._get_public_s3_client", return_value=_FakeS3()),
        patch("app.services.storage.get_s3_client", return_value=_FakeS3()),
    ):
        resp = await client.post(
            f"/api/v1/pausal/{paušalac}/invoices",
            json={
                "new_customer": {
                    "name": "US Corp",
                    "pib": "12-3456789",
                    "country": "US",
                },
                "invoice_date": "2026-04-20",
                "place_of_issue": "Beograd",
                "items": [{"description": "Consulting", "quantity": "1", "unit_price": "1000.00"}],
            },
            headers=headers,
        )
    assert resp.status_code == 201, resp.text


async def test_inline_new_customer_rs_invalid_pib_rejected(client: AsyncClient, test_engine):
    """Inline RS customer with a bad PIB during issuance returns 422."""
    headers = await _setup(client, test_engine, "issue-rs-bad@example.com")
    paušalac = await _create_pausalac(client, headers, pib=VALID_PIB_A)

    with (
        patch(
            "app.services.pausal_invoice_issuance.storage.get_s3_client",
            return_value=_FakeS3(),
        ),
        patch("app.services.storage._get_public_s3_client", return_value=_FakeS3()),
        patch("app.services.storage.get_s3_client", return_value=_FakeS3()),
    ):
        resp = await client.post(
            f"/api/v1/pausal/{paušalac}/invoices",
            json={
                "new_customer": {
                    "name": "RS Buyer",
                    "pib": "123456789",
                    "country": "RS",
                },
                "invoice_date": "2026-04-20",
                "place_of_issue": "Beograd",
                "items": [{"description": "Usluga", "quantity": "1", "unit_price": "1000.00"}],
            },
            headers=headers,
        )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "invalid_pib"


# ---------------------------------------------------------------------------
# PDF identifier line — unit-level
# ---------------------------------------------------------------------------


def test_identifier_line_rs_company():
    assert _identifier_line({"pib": "111", "mb": "222", "country": "RS"}) == "PIB: 111   MB: 222"


def test_identifier_line_foreign_company_uses_tax_id_label():
    assert (
        _identifier_line({"pib": "12-3456789", "mb": "ignored", "country": "US"})
        == "Tax ID: 12-3456789"
    )


def test_identifier_line_natural_person_uses_jmbg():
    assert (
        _identifier_line({"jmbg": "0101990710001", "is_natural_person": True, "country": "RS"})
        == "JMBG: 0101990710001"
    )


def test_identifier_line_defaults_to_rs_when_country_missing():
    assert _identifier_line({"pib": "100"}) == "PIB: 100"
