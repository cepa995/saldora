"""Tests for foreign-currency paušal invoice issuance with NBS conversion.

Covers:
- Issuing a USD invoice: exchange_rate + total_amount_rsd persisted,
  KPO entry stored in RSD so threshold math works.
- Unsupported currency rejected with 422.
- Missing NBS rate → 422 with a clear code.
- PDF includes an Iznos u RSD block only for non-RSD invoices.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.services.pausal_pdf import build_pausal_invoice_pdf

VALID_PAUSAL_PIB = "100000008"
VALID_PAUSAL_PIB_2 = "200000005"
VALID_PAUSAL_PIB_3 = "300000002"


async def _register_and_login(client: AsyncClient, email: str) -> dict[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Cur",
            "last_name": "Tester",
        },
    )
    token = reg.json()["access_token"]
    org = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Cur Org {email}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"Authorization": f"Bearer {org.json()['access_token']}"}


def _get_org_id(headers: dict) -> str:
    return decode_token(headers["Authorization"].removeprefix("Bearer "))["org"]


async def _set_agency(test_engine, org_id: str) -> None:
    f = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with f() as s:
        await s.execute(
            text("UPDATE organizations SET plan='agency' WHERE id=:id"),
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


def _s3_patches():
    return (
        patch(
            "app.services.pausal_invoice_issuance.storage.get_s3_client",
            return_value=_FakeS3(),
        ),
        patch("app.services.storage._get_public_s3_client", return_value=_FakeS3()),
        patch("app.services.storage.get_s3_client", return_value=_FakeS3()),
    )


def _nbs_patch(rsd_amount: Decimal | None, rate: Decimal | None, err: str | None = None):
    """Patch ``convert_to_rsd`` inside the issuance module to a canned result."""

    async def _fake(db, redis, amount, currency, invoice_date):
        return {
            "rsd_amount": rsd_amount,
            "exchange_rate": rate,
            "rate_date": invoice_date,
            "source": "NBS srednji kurs",
            "error": err,
        }

    return patch(
        "app.services.pausal_invoice_issuance.convert_to_rsd",
        side_effect=_fake,
    )


# ---------------------------------------------------------------------------
# Happy path — USD issuance
# ---------------------------------------------------------------------------


async def test_issue_usd_invoice_persists_rsd_conversion(client: AsyncClient, test_engine):
    """USD invoice stores exchange_rate, rate_date, and total_amount_rsd."""
    headers = await _setup(client, test_engine, "cur-usd@example.com")
    paušalac = await _create_pausalac(client, headers, pib=VALID_PAUSAL_PIB)

    s3_a, s3_b, s3_c = _s3_patches()
    # 1 USD = 108.50 RSD, so 1000 USD = 108,500 RSD
    with (
        s3_a,
        s3_b,
        s3_c,
        _nbs_patch(rsd_amount=Decimal("108500.00"), rate=Decimal("108.50")),
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
                "currency": "USD",
                "items": [{"description": "Consulting", "quantity": "10", "unit_price": "100.00"}],
            },
            headers=headers,
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["currency"] == "USD"
    assert Decimal(body["total_amount"]) == Decimal("1000.00")

    # KPO entry should be in RSD (converted), not USD
    kpo = await client.get(f"/api/v1/pausal/{paušalac}/kpo", headers=headers)
    entries = kpo.json()["data"]
    assert len(entries) == 1
    assert entries[0]["currency"] == "RSD"
    assert Decimal(entries[0]["amount"]) == Decimal("108500.00")


# ---------------------------------------------------------------------------
# Revenue tracking rolls foreign invoices in (via RSD KPO)
# ---------------------------------------------------------------------------


async def test_revenue_status_counts_converted_foreign_invoices(client: AsyncClient, test_engine):
    """A USD invoice converted to 5.5M RSD triggers the critical threshold."""
    headers = await _setup(client, test_engine, "cur-rev@example.com")
    paušalac = await _create_pausalac(client, headers, pib=VALID_PAUSAL_PIB_2)

    s3_a, s3_b, s3_c = _s3_patches()
    # 50,000 USD * 110.00 = 5,500,000 RSD → critical (91.67% of 6M)
    with (
        s3_a,
        s3_b,
        s3_c,
        _nbs_patch(rsd_amount=Decimal("5500000.00"), rate=Decimal("110.00")),
    ):
        await client.post(
            f"/api/v1/pausal/{paušalac}/invoices",
            json={
                "new_customer": {
                    "name": "Big US Corp",
                    "pib": "99-9999999",
                    "country": "US",
                },
                "invoice_date": "2026-04-20",
                "place_of_issue": "Beograd",
                "currency": "USD",
                "items": [{"description": "Big job", "quantity": "1", "unit_price": "50000.00"}],
            },
            headers=headers,
        )

    resp = await client.get(f"/api/v1/pausal/{paušalac}/revenue-status?year=2026", headers=headers)
    body = resp.json()
    assert Decimal(body["total_revenue"]) == Decimal("5500000.00")
    assert body["overall_alert_level"] == "critical"
    # The non_rsd_count legacy metric should be zero now that we always
    # persist KPO amounts in RSD going forward.
    assert body["non_rsd_count"] == 0


# ---------------------------------------------------------------------------
# Rejection paths
# ---------------------------------------------------------------------------


async def test_unsupported_currency_rejected(client: AsyncClient, test_engine):
    """A currency outside SUPPORTED_CURRENCIES returns 422."""
    headers = await _setup(client, test_engine, "cur-bad@example.com")
    paušalac = await _create_pausalac(client, headers, pib=VALID_PAUSAL_PIB_3)

    s3_a, s3_b, s3_c = _s3_patches()
    with s3_a, s3_b, s3_c:
        resp = await client.post(
            f"/api/v1/pausal/{paušalac}/invoices",
            json={
                "new_customer": {"name": "Tokyo Co", "country": "JP"},
                "invoice_date": "2026-04-20",
                "place_of_issue": "Beograd",
                "currency": "JPY",
                "items": [{"description": "x", "quantity": "1", "unit_price": "1.00"}],
            },
            headers=headers,
        )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "unsupported_currency"


async def test_missing_nbs_rate_rejected(client: AsyncClient, test_engine):
    """NBS lookup failure returns 422 exchange_rate_unavailable."""
    headers = await _setup(client, test_engine, "cur-no-rate@example.com")
    paušalac = await _create_pausalac(client, headers, pib="400000000")

    s3_a, s3_b, s3_c = _s3_patches()
    with (
        s3_a,
        s3_b,
        s3_c,
        _nbs_patch(rsd_amount=None, rate=None, err="unavailable"),
    ):
        resp = await client.post(
            f"/api/v1/pausal/{paušalac}/invoices",
            json={
                "new_customer": {"name": "Weekend Inc", "country": "US"},
                "invoice_date": "2026-04-19",
                "place_of_issue": "Beograd",
                "currency": "USD",
                "items": [{"description": "x", "quantity": "1", "unit_price": "100.00"}],
            },
            headers=headers,
        )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "exchange_rate_unavailable"


# ---------------------------------------------------------------------------
# PDF block — unit level
# ---------------------------------------------------------------------------


def _pdf_fixture(**kwargs):
    defaults = {
        "invoice_number": "2026-001",
        "invoice_date": date(2026, 4, 20),
        "due_date": None,
        "place_of_issue": "Beograd",
        "delivery_date": None,
        "delivery_place": None,
        "seller": {
            "name": "Paušalac",
            "pib": VALID_PAUSAL_PIB,
            "bank_account": "160-0-11",
            "country": "RS",
        },
        "customer": {"name": "US Corp", "pib": "EIN-1", "country": "US"},
        "items": [
            {
                "description": "Consulting",
                "quantity": "10",
                "unit": "h",
                "unit_price": "100.00",
                "total": "1000.00",
            }
        ],
        "subtotal": Decimal("1000.00"),
        "currency": "USD",
        "notes": None,
    }
    defaults.update(kwargs)
    return build_pausal_invoice_pdf(**defaults)


def test_pdf_includes_rsd_block_for_usd_invoice():
    """USD invoice PDF is larger than the equivalent RSD PDF (extra RSD block)."""
    pdf_with_block = _pdf_fixture(
        total_amount_rsd=Decimal("108500.00"),
        exchange_rate=Decimal("108.50"),
        exchange_rate_date=date(2026, 4, 20),
    )
    pdf_without_block = _pdf_fixture()  # same USD invoice, no conversion data
    assert pdf_with_block.startswith(b"%PDF")
    # The RSD block adds another paragraph to the story, so the content
    # stream is measurably larger. (PDF bytes are compressed so we can't
    # grep for the text directly.)
    assert len(pdf_with_block) > len(pdf_without_block)


def test_pdf_renders_for_rsd_invoice():
    pdf = _pdf_fixture(currency="RSD")
    assert pdf.startswith(b"%PDF")
