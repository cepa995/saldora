"""
API tests for audit logging middleware (issue #33).

Verifies that authentication events and data mutations create audit log
entries, and that the admin-only GET /api/v1/audit-logs endpoint works
with multi-tenant isolation, filtering, and pagination.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.models.audit_log import AuditLog
from app.models.invoice import Invoice

# ---- Helpers ----


async def _register_and_login(
    client: AsyncClient,
    email: str = "audit-test@example.com",
    password: str = "securepass123",
    first_name: str = "Audit",
    last_name: str = "Tester",
    org_name: str = "Audit Org",
) -> dict[str, str]:
    """Register a user, log in, and return auth headers + token payload."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "organization_name": org_name,
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


def _get_user_id(headers: dict) -> str:
    """Extract user_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["sub"]


async def _get_audit_logs(test_engine, org_id: str | None = None) -> list[AuditLog]:
    """Fetch audit log entries from the DB, optionally filtered by org."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        query = select(AuditLog).order_by(AuditLog.created_at.desc())
        if org_id:
            query = query.where(AuditLog.organization_id == org_id)
        result = await session.execute(query)
        return list(result.scalars().all())


async def _insert_invoice(test_engine, org_id: str, **overrides) -> str:
    """Insert a test invoice directly into the DB and return its id."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        invoice_id = uuid4()
        invoice = Invoice(
            id=invoice_id,
            organization_id=org_id,
            status=overrides.get("status", "review"),
            invoice_number=overrides.get("invoice_number", "INV-001"),
            invoice_date=overrides.get("invoice_date", date(2026, 1, 15)),
            seller=overrides.get("seller", {"name": "Test Seller", "pib": "123456789"}),
            total_amount=overrides.get("total_amount", Decimal("1000.00")),
            document_path=overrides.get("document_path"),
        )
        session.add(invoice)
        await session.commit()
        return str(invoice_id)


# ---- Auth audit tests ----


async def test_login_success_creates_audit_log(client: AsyncClient, test_engine):
    """Successful login creates a login_success audit entry."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login-audit@example.com",
            "password": "securepass123",
            "first_name": "Login",
            "last_name": "Audit",
        },
    )
    await client.post(
        "/api/v1/auth/login",
        data={"username": "login-audit@example.com", "password": "securepass123"},
    )

    logs = await _get_audit_logs(test_engine)
    login_logs = [entry for entry in logs if entry.action == "login_success"]
    assert len(login_logs) >= 1
    assert login_logs[0].entity_type == "user"
    assert login_logs[0].user_id is not None


async def test_login_failure_creates_audit_log(client: AsyncClient, test_engine):
    """Failed login creates a login_failure audit entry."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "fail-audit@example.com",
            "password": "securepass123",
            "first_name": "Fail",
            "last_name": "Audit",
        },
    )
    await client.post(
        "/api/v1/auth/login",
        data={"username": "fail-audit@example.com", "password": "wrongpassword"},
    )

    logs = await _get_audit_logs(test_engine)
    fail_logs = [entry for entry in logs if entry.action == "login_failure"]
    assert len(fail_logs) >= 1
    assert fail_logs[0].new_values["email"] == "fail-audit@example.com"
    # user_id is None for failed logins (identity unknown)
    assert fail_logs[0].user_id is None


async def test_register_creates_audit_log(client: AsyncClient, test_engine):
    """User registration creates a user.register audit entry."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "reg-audit@example.com",
            "password": "securepass123",
            "first_name": "Reg",
            "last_name": "Audit",
        },
    )

    logs = await _get_audit_logs(test_engine)
    reg_logs = [entry for entry in logs if entry.action == "user.register"]
    assert len(reg_logs) >= 1
    assert reg_logs[0].entity_type == "user"
    assert reg_logs[0].new_values["email"] == "reg-audit@example.com"


# ---- Invoice audit tests ----


@patch("app.routers.invoices.upload_document", return_value="orgs/x/invoices/y/original.pdf")
async def test_invoice_upload_creates_audit_log(mock_upload, client: AsyncClient, test_engine):
    """Uploading an invoice creates an invoice.create audit entry."""
    headers = await _register_and_login(client, email="upload-audit@example.com")

    await client.post(
        "/api/v1/invoices/upload",
        headers=headers,
        files={"file": ("test.pdf", b"%PDF-1.4 test content", "application/pdf")},
    )

    org_id = _get_org_id(headers)
    logs = await _get_audit_logs(test_engine, org_id=org_id)
    create_logs = [entry for entry in logs if entry.action == "invoice.create"]
    assert len(create_logs) >= 1
    assert create_logs[0].entity_type == "invoice"


async def test_invoice_update_creates_audit_log(client: AsyncClient, test_engine):
    """Updating an invoice creates an invoice.update entry with old/new values."""
    headers = await _register_and_login(client, email="update-audit@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(test_engine, org_id)

    await client.patch(
        f"/api/v1/invoices/{invoice_id}",
        headers=headers,
        json={"invoice_number": "INV-UPDATED"},
    )

    logs = await _get_audit_logs(test_engine, org_id=org_id)
    update_logs = [entry for entry in logs if entry.action == "invoice.update"]
    assert len(update_logs) >= 1
    assert update_logs[0].old_values is not None
    assert update_logs[0].new_values["invoice_number"] == "INV-UPDATED"


@patch("app.routers.invoices.delete_document")
async def test_invoice_delete_creates_audit_log(mock_delete, client: AsyncClient, test_engine):
    """Deleting an invoice creates an invoice.delete entry with old values."""
    headers = await _register_and_login(client, email="delete-audit@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(test_engine, org_id, invoice_number="INV-DEL")

    resp = await client.delete(f"/api/v1/invoices/{invoice_id}", headers=headers)
    assert resp.status_code == 204

    logs = await _get_audit_logs(test_engine, org_id=org_id)
    delete_logs = [entry for entry in logs if entry.action == "invoice.delete"]
    assert len(delete_logs) >= 1
    assert delete_logs[0].old_values["invoice_number"] == "INV-DEL"


async def test_invoice_verify_creates_audit_log(client: AsyncClient, test_engine):
    """Verifying an invoice creates an invoice.verify audit entry."""
    headers = await _register_and_login(client, email="verify-audit@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(test_engine, org_id)

    resp = await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    assert resp.status_code == 200

    logs = await _get_audit_logs(test_engine, org_id=org_id)
    verify_logs = [entry for entry in logs if entry.action == "invoice.verify"]
    assert len(verify_logs) >= 1
    assert verify_logs[0].old_values == {"status": "review"}
    assert verify_logs[0].new_values == {"status": "verified"}


# ---- Audit logs endpoint tests ----


async def test_list_audit_logs_admin_only(client: AsyncClient, test_engine):
    """Non-admin users get 403 when accessing audit logs."""
    # Register an admin user first (first user in org is admin)
    admin_headers = await _register_and_login(client, email="admin-al@example.com")

    # Downgrade to member role to verify 403
    user_id = _get_user_id(admin_headers)
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            text("UPDATE users SET role = 'member' WHERE id = :uid"),
            {"uid": user_id},
        )
        await session.commit()

    resp = await client.get("/api/v1/audit-logs", headers=admin_headers)
    assert resp.status_code == 403


async def test_list_audit_logs_success(client: AsyncClient, test_engine):
    """Admin can see audit logs for their organization."""
    headers = await _register_and_login(client, email="admin-list@example.com")

    # The register + login above already created audit entries
    resp = await client.get("/api/v1/audit-logs", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) > 0


async def test_list_audit_logs_org_isolation(client: AsyncClient, test_engine):
    """Admin can only see logs from their own organization."""
    # Create two orgs
    headers_a = await _register_and_login(client, email="org-a-audit@example.com", org_name="Org A")
    await _register_and_login(client, email="org-b-audit@example.com", org_name="Org B")
    org_a_id = _get_org_id(headers_a)

    # Org A listing should not contain Org B entries
    resp = await client.get("/api/v1/audit-logs", headers=headers_a)
    assert resp.status_code == 200
    data = resp.json()
    for entry in data["data"]:
        assert entry["organization_id"] == org_a_id


async def test_list_audit_logs_filter_by_entity_type(client: AsyncClient, test_engine):
    """Filtering by entity_type returns only matching entries."""
    headers = await _register_and_login(client, email="filter-et@example.com")

    # Get only user-related logs
    resp = await client.get(
        "/api/v1/audit-logs",
        headers=headers,
        params={"entity_type": "user"},
    )
    assert resp.status_code == 200
    data = resp.json()
    for entry in data["data"]:
        assert entry["entity_type"] == "user"


async def test_list_audit_logs_pagination(client: AsyncClient, test_engine):
    """Pagination works correctly on audit logs endpoint."""
    headers = await _register_and_login(client, email="paginate-al@example.com")

    # Request page 1 with 1 item per page
    resp = await client.get(
        "/api/v1/audit-logs",
        headers=headers,
        params={"page": 1, "per_page": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) <= 1
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["per_page"] == 1
    assert data["pagination"]["total"] >= 1
