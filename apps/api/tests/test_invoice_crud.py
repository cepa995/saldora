"""
API tests for invoice CRUD endpoints (list, detail, update, delete, verify).

Tests exercise the full request lifecycle. S3 is mocked since it requires
running infrastructure. Invoices are inserted directly into the test DB
to avoid coupling CRUD tests to the upload flow.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.models.invoice import Invoice


async def _auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a user, create an organization, and return Authorization headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "crud-test@example.com",
            "password": "securepass123",
            "first_name": "Crud",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Test Org"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _auth_headers_alt(client: AsyncClient) -> dict[str, str]:
    """Register a second user (different org) and return Authorization headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-org@example.com",
            "password": "securepass123",
            "first_name": "Other",
            "last_name": "User",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Other Org"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


async def _insert_invoice(test_engine, org_id: str, **overrides) -> str:
    """Insert a test invoice directly into the DB and return its id.

    Args:
        test_engine: SQLAlchemy async engine (from conftest fixture).
        org_id: Organization UUID string.
        **overrides: Any Invoice column overrides.

    Returns:
        String UUID of the created invoice.
    """
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        invoice = Invoice(
            organization_id=org_id,
            status=overrides.get("status", "review"),
            invoice_number=overrides.get("invoice_number", "INV-001"),
            invoice_date=overrides.get("invoice_date", date(2025, 1, 15)),
            due_date=overrides.get("due_date", date(2025, 2, 15)),
            seller=overrides.get(
                "seller",
                {"pib": "123456789", "name": "Prodavac DOO", "address": "Beograd"},
            ),
            buyer=overrides.get(
                "buyer",
                {"pib": "987654321", "name": "Kupac DOO", "address": "Novi Sad"},
            ),
            subtotal=overrides.get("subtotal", Decimal("10000.00")),
            tax_rate=overrides.get("tax_rate", Decimal("20.00")),
            tax_amount=overrides.get("tax_amount", Decimal("2000.00")),
            total_amount=overrides.get("total_amount", Decimal("12000.00")),
            currency=overrides.get("currency", "RSD"),
            line_items=overrides.get(
                "line_items",
                [
                    {
                        "description": "Usluga 1",
                        "quantity": "1.00",
                        "unit_price": "10000.00",
                        "total": "10000.00",
                    }
                ],
            ),
            tax_groups=overrides.get("tax_groups", None),
            document_hash=overrides.get("document_hash", uuid4().hex),
            document_path=overrides.get("document_path", "orgs/test/inv/original.pdf"),
            document_content_type=overrides.get("document_content_type", "application/pdf"),
            confidence_score=overrides.get("confidence_score", Decimal("0.85")),
            field_confidence=overrides.get(
                "field_confidence",
                [
                    {
                        "field_name": "invoice_number",
                        "value": "INV-001",
                        "confidence": 0.95,
                        "needs_review": False,
                    }
                ],
            ),
            warnings=overrides.get("warnings", []),
            ocr_engine=overrides.get("ocr_engine", "dots"),
            processing_time_ms=overrides.get("processing_time_ms", 3500),
            raw_ocr_text=overrides.get("raw_ocr_text", "Sample OCR text"),
        )
        session.add(invoice)
        await session.commit()
        await session.refresh(invoice)
        return str(invoice.id)


# ---- GET /invoices/{id} (detail) ----


async def test_get_invoice_success(client: AsyncClient, test_engine):
    """GET detail returns full invoice data."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id)

    with patch("app.routers.invoices.get_presigned_url", return_value="https://s3.example.com/doc"):
        resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == inv_id
    assert data["status"] == "review"
    assert data["invoice_number"] == "INV-001"
    assert data["seller"]["pib"] == "123456789"
    assert data["buyer"]["name"] == "Kupac DOO"
    assert data["total_amount"] == "12000.00"
    assert data["document_url"] == "https://s3.example.com/doc"


async def test_get_invoice_requires_auth(client: AsyncClient):
    """GET detail without token returns 401."""
    resp = await client.get(f"/api/v1/invoices/{uuid4()}")
    assert resp.status_code == 401


async def test_get_invoice_not_found(client: AsyncClient):
    """GET detail for nonexistent UUID returns 404."""
    headers = await _auth_headers(client)
    resp = await client.get(f"/api/v1/invoices/{uuid4()}", headers=headers)
    assert resp.status_code == 404


async def test_get_invoice_other_org_returns_404(client: AsyncClient, test_engine):
    """GET detail for another org's invoice returns 404 (not 403)."""
    headers = await _auth_headers(client)
    other_headers = await _auth_headers_alt(client)
    other_org_id = _get_org_id(other_headers)
    inv_id = await _insert_invoice(test_engine, other_org_id)

    resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)
    assert resp.status_code == 404


async def test_get_invoice_includes_document_url(client: AsyncClient, test_engine):
    """GET detail includes presigned document URL."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id)

    with patch(
        "app.routers.invoices.get_presigned_url",
        return_value="https://s3.example.com/signed-url",
    ):
        resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["document_url"] == "https://s3.example.com/signed-url"


async def test_get_invoice_confidence_scaled(client: AsyncClient, test_engine):
    """Confidence 0.85 in DB shows as 85.0 in response."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id, confidence_score=Decimal("0.85"))

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["confidence_score"] == 85.0


# ---- GET /invoices (list) ----


async def test_list_invoices_success(client: AsyncClient, test_engine):
    """GET list returns paginated invoices."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)

    # Create 3 invoices
    for i in range(3):
        await _insert_invoice(test_engine, org_id, invoice_number=f"INV-{i:03d}")

    resp = await client.get("/api/v1/invoices", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 3
    assert data["pagination"]["total"] == 3
    assert data["pagination"]["page"] == 1


async def test_list_invoices_requires_auth(client: AsyncClient):
    """GET list without token returns 401."""
    resp = await client.get("/api/v1/invoices")
    assert resp.status_code == 401


async def test_list_invoices_pagination(client: AsyncClient, test_engine):
    """Pagination returns correct slice."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)

    for i in range(5):
        await _insert_invoice(test_engine, org_id, invoice_number=f"PAGE-{i:03d}")

    resp = await client.get("/api/v1/invoices?page=2&per_page=2", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 2
    assert data["pagination"]["page"] == 2
    assert data["pagination"]["total"] == 5
    assert data["pagination"]["total_pages"] == 3


async def test_list_invoices_filter_by_status(client: AsyncClient, test_engine):
    """Status filter returns only matching invoices."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)

    await _insert_invoice(test_engine, org_id, status="review")
    await _insert_invoice(test_engine, org_id, status="verified")
    await _insert_invoice(test_engine, org_id, status="review")

    resp = await client.get("/api/v1/invoices?status=verified", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] == 1
    assert data["data"][0]["status"] == "verified"


async def test_list_invoices_filter_by_date_range(client: AsyncClient, test_engine):
    """Date range filter returns invoices within the range."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)

    await _insert_invoice(test_engine, org_id, invoice_date=date(2025, 1, 10))
    await _insert_invoice(test_engine, org_id, invoice_date=date(2025, 3, 20))
    await _insert_invoice(test_engine, org_id, invoice_date=date(2025, 6, 1))

    resp = await client.get(
        "/api/v1/invoices?date_from=2025-01-01&date_to=2025-03-31",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 2


async def test_list_invoices_search(client: AsyncClient, test_engine):
    """Search finds invoices by invoice number."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)

    await _insert_invoice(test_engine, org_id, invoice_number="FAKTURA-2025-001")
    await _insert_invoice(test_engine, org_id, invoice_number="FAKTURA-2025-002")
    await _insert_invoice(test_engine, org_id, invoice_number="RACUN-999")

    resp = await client.get("/api/v1/invoices?search=FAKTURA", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 2


async def test_list_invoices_sort_by_total(client: AsyncClient, test_engine):
    """Sorting by total_amount works."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)

    await _insert_invoice(test_engine, org_id, total_amount=Decimal("5000.00"))
    await _insert_invoice(test_engine, org_id, total_amount=Decimal("15000.00"))
    await _insert_invoice(test_engine, org_id, total_amount=Decimal("1000.00"))

    resp = await client.get("/api/v1/invoices?sort=total_amount&order=asc", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    amounts = [d["total_amount"] for d in data]
    assert amounts == sorted(amounts, key=lambda x: Decimal(x))


async def test_list_invoices_filter_unassigned(client: AsyncClient, test_engine):
    """?unassigned=true returns only invoices with no client_id (inbox view)."""
    from uuid import UUID, uuid4

    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.models.client import Client
    from app.models.invoice import Invoice

    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)

    # Create a client so we can attach one invoice to it
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        c = Client(
            id=uuid4(),
            organization_id=UUID(org_id),
            name="Aroma",
            pib="123456789",
            is_active=True,
        )
        session.add(c)
        await session.commit()
        attached_client_id = c.id

    await _insert_invoice(test_engine, org_id, invoice_number="ORPHAN-1")
    await _insert_invoice(test_engine, org_id, invoice_number="ORPHAN-2")
    attached_id = await _insert_invoice(test_engine, org_id, invoice_number="ASSIGNED-1")
    # The helper doesn't accept client_id; attach it directly after creation.
    async with factory() as session:
        await session.execute(
            update(Invoice)
            .where(Invoice.id == UUID(attached_id))
            .values(client_id=attached_client_id)
        )
        await session.commit()

    resp = await client.get("/api/v1/invoices?unassigned=true", headers=headers)
    assert resp.status_code == 200
    numbers = {d["invoice_number"] for d in resp.json()["data"]}
    assert numbers == {"ORPHAN-1", "ORPHAN-2"}
    assert resp.json()["pagination"]["total"] == 2

    # Without the filter, all three come back
    resp_all = await client.get("/api/v1/invoices", headers=headers)
    assert resp_all.json()["pagination"]["total"] == 3


async def test_list_invoices_org_isolation(client: AsyncClient, test_engine):
    """User cannot see invoices from another organization."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    other_headers = await _auth_headers_alt(client)
    other_org_id = _get_org_id(other_headers)

    await _insert_invoice(test_engine, org_id, invoice_number="MINE")
    await _insert_invoice(test_engine, other_org_id, invoice_number="OTHER")

    resp = await client.get("/api/v1/invoices", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # Should only see own invoice
    numbers = [d["invoice_number"] for d in data["data"]]
    assert "MINE" in numbers
    assert "OTHER" not in numbers


# ---- PATCH /invoices/{id} (update) ----


async def test_update_invoice_success(client: AsyncClient, test_engine):
    """PATCH updates invoice fields."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id, status="review")

    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}",
        headers=headers,
        json={"invoice_number": "UPDATED-001", "total_amount": "99999.99"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["invoice_number"] == "UPDATED-001"
    assert data["total_amount"] == "99999.99"


async def test_update_invoice_requires_auth(client: AsyncClient):
    """PATCH without token returns 401."""
    resp = await client.patch(
        f"/api/v1/invoices/{uuid4()}",
        json={"invoice_number": "X"},
    )
    assert resp.status_code == 401


async def test_update_invoice_not_found(client: AsyncClient):
    """PATCH for nonexistent UUID returns 404."""
    headers = await _auth_headers(client)
    resp = await client.patch(
        f"/api/v1/invoices/{uuid4()}",
        headers=headers,
        json={"invoice_number": "X"},
    )
    assert resp.status_code == 404


async def test_update_invoice_seller_fields(client: AsyncClient, test_engine):
    """PATCH seller_pib and seller_name merge into seller JSON."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id, status="review")

    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}",
        headers=headers,
        json={"seller_pib": "111222333", "seller_name": "Novi Prodavac"},
    )
    assert resp.status_code == 200
    seller = resp.json()["seller"]
    assert seller["pib"] == "111222333"
    assert seller["name"] == "Novi Prodavac"
    # Original address should be preserved
    assert seller["address"] == "Beograd"


async def test_update_invoice_reverts_verified_to_review(client: AsyncClient, test_engine):
    """Editing a verified invoice reverts status to review."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id, status="verified")

    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}",
        headers=headers,
        json={"invoice_number": "CHANGED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "review"


async def test_update_invoice_tax_groups(client: AsyncClient, test_engine):
    """PATCH with tax_groups saves and returns the groups."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id, status="review")

    tax_groups = [
        {"rate": "20", "base_amount": "97950.00", "tax_amount": "19590.00"},
        {"rate": "20", "base_amount": "56000.00", "tax_amount": "11200.00"},
    ]
    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}",
        headers=headers,
        json={"tax_groups": tax_groups},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tax_groups"]) == 2
    assert data["tax_groups"][0]["rate"] == "20"
    assert data["tax_groups"][0]["base_amount"] == "97950.00"
    assert data["tax_groups"][1]["tax_amount"] == "11200.00"


async def test_get_invoice_with_tax_groups(client: AsyncClient, test_engine):
    """GET detail returns tax_groups when present in DB."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        tax_groups=[
            {"rate": "10", "base_amount": "5000.00", "tax_amount": "500.00"},
        ],
    )

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tax_groups"]) == 1
    assert data["tax_groups"][0]["rate"] == "10"
    assert data["tax_groups"][0]["base_amount"] == "5000.00"


async def test_get_invoice_without_tax_groups(client: AsyncClient, test_engine):
    """GET detail returns empty tax_groups when null in DB."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id)

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["tax_groups"] == []


async def test_update_invoice_rejects_processing_status(client: AsyncClient, test_engine):
    """Cannot edit an invoice that is still processing."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id, status="processing")

    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}",
        headers=headers,
        json={"invoice_number": "X"},
    )
    assert resp.status_code == 400


# ---- DELETE /invoices/{id} ----


async def test_delete_invoice_success(client: AsyncClient, test_engine):
    """DELETE removes invoice from DB and returns 204."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id)

    with patch("app.routers.invoices.delete_document"):
        resp = await client.delete(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 204

    # Confirm gone
    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        get_resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_delete_invoice_requires_auth(client: AsyncClient):
    """DELETE without token returns 401."""
    resp = await client.delete(f"/api/v1/invoices/{uuid4()}")
    assert resp.status_code == 401


async def test_delete_invoice_not_found(client: AsyncClient):
    """DELETE for nonexistent UUID returns 404."""
    headers = await _auth_headers(client)
    resp = await client.delete(f"/api/v1/invoices/{uuid4()}", headers=headers)
    assert resp.status_code == 404


async def test_delete_invoice_other_org(client: AsyncClient, test_engine):
    """DELETE for another org's invoice returns 404."""
    headers = await _auth_headers(client)
    other_headers = await _auth_headers_alt(client)
    other_org_id = _get_org_id(other_headers)
    inv_id = await _insert_invoice(test_engine, other_org_id)

    resp = await client.delete(f"/api/v1/invoices/{inv_id}", headers=headers)
    assert resp.status_code == 404


# ---- POST /invoices/{id}/verify ----


async def test_verify_invoice_success(client: AsyncClient, test_engine):
    """POST verify sets status to verified."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id, status="review")

    resp = await client.post(f"/api/v1/invoices/{inv_id}/verify", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "verified"


async def test_verify_invoice_requires_auth(client: AsyncClient):
    """POST verify without token returns 401."""
    resp = await client.post(f"/api/v1/invoices/{uuid4()}/verify")
    assert resp.status_code == 401


async def test_verify_invoice_missing_fields(client: AsyncClient, test_engine):
    """POST verify rejects invoice with missing required fields."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    # Invoice without invoice_number and seller
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        status="review",
        invoice_number=None,
        seller=None,
    )

    resp = await client.post(f"/api/v1/invoices/{inv_id}/verify", headers=headers)
    assert resp.status_code == 400
    assert "Broj fakture" in resp.json()["detail"]
    assert "Podaci o prodavcu" in resp.json()["detail"]


async def test_verify_invoice_wrong_status(client: AsyncClient, test_engine):
    """POST verify rejects invoice not in review status."""
    headers = await _auth_headers(client)
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id, status="processing")

    resp = await client.post(f"/api/v1/invoices/{inv_id}/verify", headers=headers)
    assert resp.status_code == 400
    assert "processing" in resp.json()["detail"]
