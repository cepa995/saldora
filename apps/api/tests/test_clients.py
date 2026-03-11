"""Tests for client management (Agency plan feature)."""

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token


async def _register_and_login(
    client: AsyncClient,
    email: str = "client-test@example.com",
    password: str = "securepass123",
) -> dict[str, str]:
    """Register a user, create an organization, and return auth headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Client",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Client Test Org {email}"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


async def _set_org_plan(test_engine, org_id: str, plan: str) -> None:
    """Update organization plan directly in the database."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        from sqlalchemy import text

        await session.execute(
            text("UPDATE organizations SET plan = :plan WHERE id = :org_id"),
            {"plan": plan, "org_id": org_id},
        )
        await session.commit()


# ---------------------------------------------------------------------------
# Feature gate tests
# ---------------------------------------------------------------------------


async def test_free_plan_blocked(client: AsyncClient, test_engine):
    """Free plan cannot access clients endpoint."""
    headers = await _register_and_login(client, "free-client@example.com")
    # Default plan is 'free'
    resp = await client.get("/api/v1/clients/", headers=headers)
    assert resp.status_code == 403
    data = resp.json()["detail"]
    assert data["code"] == "feature_unavailable"


async def test_starter_plan_blocked(client: AsyncClient, test_engine):
    """Starter plan cannot access clients endpoint."""
    headers = await _register_and_login(client, "starter-client@example.com")
    org_id = _get_org_id(headers)
    await _set_org_plan(test_engine, org_id, "starter")
    resp = await client.get("/api/v1/clients/", headers=headers)
    assert resp.status_code == 403


async def test_pro_plan_blocked(client: AsyncClient, test_engine):
    """Pro plan cannot access clients endpoint."""
    headers = await _register_and_login(client, "pro-client@example.com")
    org_id = _get_org_id(headers)
    await _set_org_plan(test_engine, org_id, "pro")
    resp = await client.get("/api/v1/clients/", headers=headers)
    assert resp.status_code == 403


async def test_agency_plan_allowed(client: AsyncClient, test_engine):
    """Agency plan can access clients endpoint."""
    headers = await _register_and_login(client, "agency-client@example.com")
    org_id = _get_org_id(headers)
    await _set_org_plan(test_engine, org_id, "agency")
    resp = await client.get("/api/v1/clients/", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"] == []


# ---------------------------------------------------------------------------
# CRUD tests (all use agency plan)
# ---------------------------------------------------------------------------


async def _setup_agency(client: AsyncClient, test_engine, email: str) -> dict[str, str]:
    """Register, create org, set agency plan, return headers."""
    headers = await _register_and_login(client, email)
    org_id = _get_org_id(headers)
    await _set_org_plan(test_engine, org_id, "agency")
    return headers


async def test_create_client(client: AsyncClient, test_engine):
    """Create a client successfully."""
    headers = await _setup_agency(client, test_engine, "create-client@example.com")
    resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Test Company", "pib": "123456789"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Company"
    assert data["pib"] == "123456789"
    assert data["is_active"] is True
    assert data["invoice_count"] == 0


async def test_duplicate_pib_rejected(client: AsyncClient, test_engine):
    """Creating a client with duplicate PIB returns 409."""
    headers = await _setup_agency(client, test_engine, "dup-pib@example.com")
    await client.post(
        "/api/v1/clients/",
        json={"name": "Company A", "pib": "111222333"},
        headers=headers,
    )
    resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Company B", "pib": "111222333"},
        headers=headers,
    )
    assert resp.status_code == 409


async def test_list_clients_with_search(client: AsyncClient, test_engine):
    """List clients with search filter."""
    headers = await _setup_agency(client, test_engine, "list-search@example.com")
    await client.post(
        "/api/v1/clients/",
        json={"name": "Alfa Corp", "pib": "100000001"},
        headers=headers,
    )
    await client.post(
        "/api/v1/clients/",
        json={"name": "Beta LLC", "pib": "200000002"},
        headers=headers,
    )

    # Search by name
    resp = await client.get("/api/v1/clients/?search=Alfa", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == "Alfa Corp"

    # Search by PIB
    resp = await client.get("/api/v1/clients/?search=200000002", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


async def test_get_client(client: AsyncClient, test_engine):
    """Get a single client by ID."""
    headers = await _setup_agency(client, test_engine, "get-client@example.com")
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Get Test", "pib": "300000003"},
        headers=headers,
    )
    client_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/clients/{client_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Get Test"


async def test_update_client(client: AsyncClient, test_engine):
    """Partial update of a client."""
    headers = await _setup_agency(client, test_engine, "update-client@example.com")
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Old Name", "pib": "400000004"},
        headers=headers,
    )
    client_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/clients/{client_id}",
        json={"name": "New Name", "city": "Beograd"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["city"] == "Beograd"


async def test_soft_delete_client(client: AsyncClient, test_engine):
    """Delete (soft-delete) sets is_active=false."""
    headers = await _setup_agency(client, test_engine, "delete-client@example.com")
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"name": "To Delete", "pib": "500000005"},
        headers=headers,
    )
    client_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/clients/{client_id}", headers=headers)
    assert resp.status_code == 204

    # Verify it's inactive
    get_resp = await client.get(f"/api/v1/clients/{client_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["is_active"] is False


# ---------------------------------------------------------------------------
# Cross-org isolation
# ---------------------------------------------------------------------------


async def test_cross_org_isolation(client: AsyncClient, test_engine):
    """Org A cannot see Org B's clients."""
    headers_a = await _setup_agency(client, test_engine, "org-a-client@example.com")
    headers_b = await _setup_agency(client, test_engine, "org-b-client@example.com")

    # Org A creates a client
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"name": "A Only", "pib": "600000006"},
        headers=headers_a,
    )
    client_id = create_resp.json()["id"]

    # Org B tries to access it
    resp = await client.get(f"/api/v1/clients/{client_id}", headers=headers_b)
    assert resp.status_code == 404

    # Org B's list doesn't include it
    list_resp = await client.get("/api/v1/clients/", headers=headers_b)
    assert all(c["pib"] != "600000006" for c in list_resp.json()["data"])


# ---------------------------------------------------------------------------
# Invoice client_id filter
# ---------------------------------------------------------------------------


async def test_invoice_client_id_filter(client: AsyncClient, test_engine):
    """Invoice list can be filtered by client_id."""
    headers = await _setup_agency(client, test_engine, "inv-filter@example.com")
    org_id = _get_org_id(headers)

    # Create a client
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Filter Client", "pib": "700000007"},
        headers=headers,
    )
    client_id = create_resp.json()["id"]

    # Insert an invoice with that client_id
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        from sqlalchemy import text

        inv_id = str(uuid4())
        await session.execute(
            text(
                "INSERT INTO invoices"
                " (id, organization_id, client_id, status, currency, created_at, updated_at)"
                " VALUES (:id, :org_id, :client_id, 'review', 'RSD', NOW(), NOW())"
            ),
            {"id": inv_id, "org_id": org_id, "client_id": client_id},
        )
        # Insert another invoice without client
        await session.execute(
            text("""
                INSERT INTO invoices (id, organization_id, status, currency, created_at, updated_at)
                VALUES (:id, :org_id, 'review', 'RSD', NOW(), NOW())
            """),
            {"id": str(uuid4()), "org_id": org_id},
        )
        await session.commit()

    # Filter by client_id
    resp = await client.get(
        f"/api/v1/invoices?client_id={client_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] == 1
    assert data["data"][0]["client_id"] == client_id

    # No filter returns both
    resp_all = await client.get("/api/v1/invoices", headers=headers)
    assert resp_all.json()["pagination"]["total"] == 2


async def test_invoice_response_includes_client(client: AsyncClient, test_engine):
    """Invoice response includes client summary when client_id is set."""
    headers = await _setup_agency(client, test_engine, "inv-client@example.com")
    org_id = _get_org_id(headers)

    # Create a client
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Summary Client", "pib": "800000008"},
        headers=headers,
    )
    client_id = create_resp.json()["id"]

    # Insert an invoice with that client_id
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        from sqlalchemy import text

        inv_id = str(uuid4())
        await session.execute(
            text(
                "INSERT INTO invoices"
                " (id, organization_id, client_id, status, currency, created_at, updated_at)"
                " VALUES (:id, :org_id, :client_id, 'review', 'RSD', NOW(), NOW())"
            ),
            {"id": inv_id, "org_id": org_id, "client_id": client_id},
        )
        await session.commit()

    # Get the invoice and check client summary
    resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["client_id"] == client_id
    assert data["client"]["name"] == "Summary Client"
    assert data["client"]["pib"] == "800000008"


# ---------------------------------------------------------------------------
# Manual client assignment
# ---------------------------------------------------------------------------


async def test_assign_client_to_invoice(client: AsyncClient, test_engine):
    """PATCH /invoices/{id}/client assigns a client."""
    headers = await _setup_agency(client, test_engine, "assign-client@example.com")
    org_id = _get_org_id(headers)

    # Create client
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Assign Client", "pib": "900000009"},
        headers=headers,
    )
    client_id = create_resp.json()["id"]

    # Insert invoice
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        from sqlalchemy import text

        inv_id = str(uuid4())
        await session.execute(
            text("""
                INSERT INTO invoices (id, organization_id, status, currency, created_at, updated_at)
                VALUES (:id, :org_id, 'review', 'RSD', NOW(), NOW())
            """),
            {"id": inv_id, "org_id": org_id},
        )
        await session.commit()

    # Assign client
    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}/client?client_id={client_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["client_id"] == client_id
    assert resp.json()["client"]["name"] == "Assign Client"
