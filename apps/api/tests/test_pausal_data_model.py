"""Tests for M14.1: client_type on clients and direction on invoices.

These fields enable paušalci handling and incoming/outgoing invoice
differentiation. Existing rows default to ``vat_payer`` and ``incoming``.
"""

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token


async def _register_and_login(
    client: AsyncClient,
    email: str = "pausal-test@example.com",
    password: str = "securepass123",
) -> dict[str, str]:
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Pausal",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Pausal Test Org {email}"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    return {"Authorization": f"Bearer {org_resp.json()['access_token']}"}


def _get_org_id(headers: dict) -> str:
    token = headers["Authorization"].removeprefix("Bearer ")
    return decode_token(token)["org"]


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


# ---------------------------------------------------------------------------
# client_type
# ---------------------------------------------------------------------------


async def test_create_client_defaults_to_vat_payer(client: AsyncClient, test_engine):
    """Omitting client_type falls back to vat_payer."""
    headers = await _setup(client, test_engine, "default-type@example.com")
    resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Default Type", "pib": "100000207"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["client_type"] == "vat_payer"


async def test_create_client_with_each_valid_type(client: AsyncClient, test_engine):
    """All four client types are accepted on create."""
    headers = await _setup(client, test_engine, "all-types@example.com")
    # 4 distinct checksum-valid Serbian PIBs (the router enforces mod-11).
    valid_pibs = ["100000008", "200000005", "300000002", "400000000"]
    valid = ["vat_payer", "pausalac", "foreign_entity", "non_profit"]
    for ct, pib in zip(valid, valid_pibs, strict=True):
        resp = await client.post(
            "/api/v1/clients/",
            json={"name": f"Client {ct}", "pib": pib, "client_type": ct},
            headers=headers,
        )
        assert resp.status_code == 201, f"{ct} rejected: {resp.text}"
        assert resp.json()["client_type"] == ct


async def test_create_client_rejects_invalid_type(client: AsyncClient, test_engine):
    """Unknown client_type is rejected by schema validation (422)."""
    headers = await _setup(client, test_engine, "bad-type@example.com")
    resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Bad", "pib": "100000215", "client_type": "corporation"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_update_client_type(client: AsyncClient, test_engine):
    """client_type can be changed via PATCH (e.g., paušalac graduates to VAT)."""
    headers = await _setup(client, test_engine, "change-type@example.com")
    created = await client.post(
        "/api/v1/clients/",
        json={"name": "Grad", "pib": "100000223", "client_type": "pausalac"},
        headers=headers,
    )
    cid = created.json()["id"]

    resp = await client.patch(
        f"/api/v1/clients/{cid}",
        json={"client_type": "vat_payer"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["client_type"] == "vat_payer"


async def test_client_response_includes_type(client: AsyncClient, test_engine):
    """GET /clients/{id} returns client_type."""
    headers = await _setup(client, test_engine, "get-type@example.com")
    created = await client.post(
        "/api/v1/clients/",
        json={"name": "Foreign Co", "pib": "100000231", "client_type": "foreign_entity"},
        headers=headers,
    )
    cid = created.json()["id"]

    resp = await client.get(f"/api/v1/clients/{cid}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["client_type"] == "foreign_entity"


# ---------------------------------------------------------------------------
# invoice direction
# ---------------------------------------------------------------------------


async def test_existing_invoices_default_to_incoming(client: AsyncClient, test_engine):
    """Invoices inserted without direction get 'incoming' via server_default."""
    headers = await _setup(client, test_engine, "inv-default@example.com")
    org_id = _get_org_id(headers)

    # Insert invoice via raw SQL omitting direction — simulates pre-migration rows
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    inv_id = str(uuid4())
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO invoices (id, organization_id, status, currency,"
                " created_at, updated_at)"
                " VALUES (:id, :org, 'review', 'RSD', NOW(), NOW())"
            ),
            {"id": inv_id, "org": org_id},
        )
        await session.commit()

    resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["direction"] == "incoming"


async def test_invoice_direction_can_be_outgoing(client: AsyncClient, test_engine):
    """Invoices with direction='outgoing' (paušal issued) round-trip correctly."""
    headers = await _setup(client, test_engine, "inv-outgoing@example.com")
    org_id = _get_org_id(headers)

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    inv_id = str(uuid4())
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO invoices (id, organization_id, status, currency,"
                " direction, created_at, updated_at)"
                " VALUES (:id, :org, 'review', 'RSD', 'outgoing', NOW(), NOW())"
            ),
            {"id": inv_id, "org": org_id},
        )
        await session.commit()

    resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["direction"] == "outgoing"


async def test_invoice_direction_check_constraint(client: AsyncClient, test_engine):
    """DB-level CHECK constraint rejects invalid direction values."""
    import sqlalchemy.exc

    headers = await _setup(client, test_engine, "inv-bad-dir@example.com")
    org_id = _get_org_id(headers)

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        try:
            await session.execute(
                text(
                    "INSERT INTO invoices (id, organization_id, status, currency,"
                    " direction, created_at, updated_at)"
                    " VALUES (:id, :org, 'review', 'RSD', 'sideways', NOW(), NOW())"
                ),
                {"id": str(uuid4()), "org": org_id},
            )
            await session.commit()
            raise AssertionError("expected CHECK constraint violation")
        except sqlalchemy.exc.IntegrityError:
            pass
