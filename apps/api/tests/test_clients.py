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
        json={"name": "Test Company", "pib": "500000007"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Company"
    assert data["pib"] == "500000007"
    assert data["is_active"] is True
    assert data["invoice_count"] == 0


async def test_duplicate_pib_rejected(client: AsyncClient, test_engine):
    """Creating a client with duplicate PIB returns 409."""
    headers = await _setup_agency(client, test_engine, "dup-pib@example.com")
    await client.post(
        "/api/v1/clients/",
        json={"name": "Company A", "pib": "500000015"},
        headers=headers,
    )
    resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Company B", "pib": "500000015"},
        headers=headers,
    )
    assert resp.status_code == 409


async def test_list_clients_with_search(client: AsyncClient, test_engine):
    """List clients with search filter."""
    headers = await _setup_agency(client, test_engine, "list-search@example.com")
    await client.post(
        "/api/v1/clients/",
        json={"name": "Alfa Corp", "pib": "500000023"},
        headers=headers,
    )
    await client.post(
        "/api/v1/clients/",
        json={"name": "Beta LLC", "pib": "500000031"},
        headers=headers,
    )

    # Search by name
    resp = await client.get("/api/v1/clients/?search=Alfa", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == "Alfa Corp"

    # Search by PIB
    resp = await client.get("/api/v1/clients/?search=500000031", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


async def test_get_client(client: AsyncClient, test_engine):
    """Get a single client by ID."""
    headers = await _setup_agency(client, test_engine, "get-client@example.com")
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Get Test", "pib": "500000040"},
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
        json={"name": "Old Name", "pib": "500000058"},
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
    """Delete (hard delete) removes the client from the database."""
    headers = await _setup_agency(client, test_engine, "delete-client@example.com")
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"name": "To Delete", "pib": "500000066"},
        headers=headers,
    )
    client_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/clients/{client_id}", headers=headers)
    assert resp.status_code == 204

    # Verify it's gone entirely
    get_resp = await client.get(f"/api/v1/clients/{client_id}", headers=headers)
    assert get_resp.status_code == 404


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
        json={"name": "A Only", "pib": "500000074"},
        headers=headers_a,
    )
    client_id = create_resp.json()["id"]

    # Org B tries to access it
    resp = await client.get(f"/api/v1/clients/{client_id}", headers=headers_b)
    assert resp.status_code == 404

    # Org B's list doesn't include it
    list_resp = await client.get("/api/v1/clients/", headers=headers_b)
    assert all(c["pib"] != "500000074" for c in list_resp.json()["data"])


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
        json={"name": "Filter Client", "pib": "500000082"},
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
        json={"name": "Summary Client", "pib": "500000099"},
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
    assert data["client"]["pib"] == "500000099"


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
        json={"name": "Assign Client", "pib": "500000103"},
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


# ---------------------------------------------------------------------------
# 404 error paths
# ---------------------------------------------------------------------------


async def test_get_client_not_found(client: AsyncClient, test_engine):
    """GET /api/v1/clients/{id} with a non-existent UUID returns 404.

    Args:
        client: Async HTTP client fixture.
        test_engine: SQLAlchemy test engine fixture.
    """
    from uuid import uuid4

    headers = await _setup_agency(client, test_engine, "cl-get-404@example.com")
    non_existent = str(uuid4())

    resp = await client.get(f"/api/v1/clients/{non_existent}", headers=headers)
    assert resp.status_code == 404


async def test_update_client_not_found(client: AsyncClient, test_engine):
    """PATCH /api/v1/clients/{id} with a non-existent UUID returns 404.

    Args:
        client: Async HTTP client fixture.
        test_engine: SQLAlchemy test engine fixture.
    """
    from uuid import uuid4

    headers = await _setup_agency(client, test_engine, "cl-upd-404@example.com")
    non_existent = str(uuid4())

    resp = await client.patch(
        f"/api/v1/clients/{non_existent}",
        json={"name": "Ghost"},
        headers=headers,
    )
    assert resp.status_code == 404


async def test_delete_client_not_found(client: AsyncClient, test_engine):
    """DELETE /api/v1/clients/{id} with a non-existent UUID returns 404.

    Args:
        client: Async HTTP client fixture.
        test_engine: SQLAlchemy test engine fixture.
    """
    from uuid import uuid4

    headers = await _setup_agency(client, test_engine, "cl-del-404@example.com")
    non_existent = str(uuid4())

    resp = await client.delete(f"/api/v1/clients/{non_existent}", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# is_active filter in list
# ---------------------------------------------------------------------------


async def test_list_clients_filter_by_is_active(client: AsyncClient, test_engine):
    """GET /api/v1/clients/?is_active= filters correctly by active status.

    Creates two clients, deactivates one via toggle-active, then verifies
    the is_active filter returns the correct subset.

    Args:
        client: Async HTTP client fixture.
        test_engine: SQLAlchemy test engine fixture.
    """
    headers = await _setup_agency(client, test_engine, "cl-list-active@example.com")

    # Create two clients
    await client.post(
        "/api/v1/clients/",
        json={"name": "Active One", "pib": "500000111"},
        headers=headers,
    )
    r2 = await client.post(
        "/api/v1/clients/",
        json={"name": "Inactive Two", "pib": "500000120"},
        headers=headers,
    )
    client_id_2 = r2.json()["id"]

    # Deactivate the second client via toggle-active (starts active, toggle → inactive)
    await client.post(f"/api/v1/clients/{client_id_2}/toggle-active", headers=headers)

    # Filter: only active clients
    resp_active = await client.get("/api/v1/clients/?is_active=true", headers=headers)
    assert resp_active.status_code == 200
    active_pibs = {c["pib"] for c in resp_active.json()["data"]}
    assert "500000111" in active_pibs
    assert "500000120" not in active_pibs

    # Filter: only inactive clients
    resp_inactive = await client.get("/api/v1/clients/?is_active=false", headers=headers)
    assert resp_inactive.status_code == 200
    inactive_pibs = {c["pib"] for c in resp_inactive.json()["data"]}
    assert "500000120" in inactive_pibs
    assert "500000111" not in inactive_pibs


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


async def test_list_clients_pagination(client: AsyncClient, test_engine):
    """GET /api/v1/clients/ respects page and per_page query parameters.

    Creates three clients and verifies that per_page=2 splits them over
    two pages and that pagination metadata is accurate.

    Args:
        client: Async HTTP client fixture.
        test_engine: SQLAlchemy test engine fixture.
    """
    headers = await _setup_agency(client, test_engine, "cl-paginate@example.com")

    # Use 3 distinct, checksum-valid Serbian PIBs (router enforces mod-11).
    pibs = ["500000200", "500000218", "500000226"]
    for i, pib in enumerate(pibs):
        await client.post(
            "/api/v1/clients/",
            json={"name": f"Page Client {i}", "pib": pib},
            headers=headers,
        )

    resp_p1 = await client.get("/api/v1/clients/?page=1&per_page=2", headers=headers)
    assert resp_p1.status_code == 200
    data_p1 = resp_p1.json()
    assert len(data_p1["data"]) == 2
    assert data_p1["pagination"]["total"] == 3
    assert data_p1["pagination"]["total_pages"] == 2
    assert data_p1["pagination"]["per_page"] == 2

    resp_p2 = await client.get("/api/v1/clients/?page=2&per_page=2", headers=headers)
    assert resp_p2.status_code == 200
    data_p2 = resp_p2.json()
    assert len(data_p2["data"]) == 1

    # Ensure pages are disjoint
    ids_p1 = {c["id"] for c in data_p1["data"]}
    ids_p2 = {c["id"] for c in data_p2["data"]}
    assert ids_p1.isdisjoint(ids_p2)


# ---------------------------------------------------------------------------
# Update with PIB conflict
# ---------------------------------------------------------------------------


async def test_update_client_duplicate_pib_conflict(client: AsyncClient, test_engine):
    """PATCH /api/v1/clients/{id} returns 409 when updating to a PIB already used.

    Args:
        client: Async HTTP client fixture.
        test_engine: SQLAlchemy test engine fixture.
    """
    headers = await _setup_agency(client, test_engine, "cl-upd-pib@example.com")

    # Create two clients with distinct PIBs
    await client.post(
        "/api/v1/clients/",
        json={"name": "Company X", "pib": "500000138"},
        headers=headers,
    )
    r2 = await client.post(
        "/api/v1/clients/",
        json={"name": "Company Y", "pib": "500000146"},
        headers=headers,
    )
    client_id_y = r2.json()["id"]

    # Try to update Y's PIB to X's PIB — should conflict
    resp = await client.patch(
        f"/api/v1/clients/{client_id_y}",
        json={"pib": "500000138"},
        headers=headers,
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Full-detail create — all optional fields
# ---------------------------------------------------------------------------


async def test_create_client_full_details(client: AsyncClient, test_engine):
    """Creating a client with all optional fields stores and returns them correctly.

    Args:
        client: Async HTTP client fixture.
        test_engine: SQLAlchemy test engine fixture.
    """
    headers = await _setup_agency(client, test_engine, "cl-full@example.com")

    payload = {
        "name": "Full Detail Corp",
        "pib": "500000154",
        "mb": "12345678",
        "address": "Knez Mihajlova 10",
        "city": "Beograd",
        "postal_code": "11000",
        "contact_email": "contact@fulldetail.rs",
        "contact_phone": "+381112345678",
        "notes": "VIP klijent",
    }
    resp = await client.post("/api/v1/clients/", json=payload, headers=headers)
    assert resp.status_code == 201

    data = resp.json()
    assert data["mb"] == "12345678"
    assert data["address"] == "Knez Mihajlova 10"
    assert data["city"] == "Beograd"
    assert data["postal_code"] == "11000"
    assert data["contact_email"] == "contact@fulldetail.rs"
    assert data["contact_phone"] == "+381112345678"
    assert data["notes"] == "VIP klijent"


# ---------------------------------------------------------------------------
# Reactivate a soft-deleted client via PATCH
# ---------------------------------------------------------------------------


async def test_reactivate_soft_deleted_client(client: AsyncClient, test_engine):
    """A deactivated client can be reactivated via POST /{id}/toggle-active.

    Args:
        client: Async HTTP client fixture.
        test_engine: SQLAlchemy test engine fixture.
    """
    headers = await _setup_agency(client, test_engine, "cl-reactivate@example.com")

    create_resp = await client.post(
        "/api/v1/clients/",
        json={"name": "Reactivate Me", "pib": "500000162"},
        headers=headers,
    )
    client_id = create_resp.json()["id"]

    # Deactivate via toggle-active (starts active → toggle → inactive)
    toggle_resp = await client.post(f"/api/v1/clients/{client_id}/toggle-active", headers=headers)
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["is_active"] is False

    # Reactivate via toggle-active again (inactive → toggle → active)
    reactivate_resp = await client.post(
        f"/api/v1/clients/{client_id}/toggle-active", headers=headers
    )
    assert reactivate_resp.status_code == 200
    assert reactivate_resp.json()["is_active"] is True
