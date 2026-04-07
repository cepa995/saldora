"""Tests for payment tracking and aging/open-items reports."""

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token


async def _register_and_login(
    client: AsyncClient,
    email: str = "pay-test@example.com",
    password: str = "securepass123",
) -> dict[str, str]:
    """Register a user, create an organization, and return auth headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Payment",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Payment Test Org {email}"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


async def _create_verified_invoice(
    test_engine,
    org_id: str,
    total_amount: float = 100000,
    due_date: str = "2026-03-01",
    seller_pib: str = "123456789",
    seller_name: str = "Dobavljač DOO",
) -> str:
    """Insert a verified invoice directly in the DB and return its ID."""
    import json
    from datetime import date

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    inv_id = str(uuid4())
    async with session_factory() as session:
        from sqlalchemy import text

        await session.execute(
            text("""
                INSERT INTO invoices
                (id, organization_id, status, total_amount, currency, due_date,
                 invoice_number, invoice_date, seller, payment_status, created_at, updated_at)
                VALUES (:id, :org_id, 'verified', :total, 'RSD', :due_date,
                 :inv_num, :inv_date, :seller, 'unpaid', NOW(), NOW())
            """),
            {
                "id": inv_id,
                "org_id": org_id,
                "total": total_amount,
                "due_date": date.fromisoformat(due_date),
                "inv_num": f"INV-{inv_id[:8]}",
                "inv_date": date.fromisoformat("2026-02-15"),
                "seller": json.dumps({"pib": seller_pib, "name": seller_name}, ensure_ascii=False),
            },
        )
        await session.commit()
    return inv_id


# ---------------------------------------------------------------------------
# Single payment tests
# ---------------------------------------------------------------------------


async def test_record_full_payment(client: AsyncClient, test_engine):
    """Full payment sets status to 'paid'."""
    headers = await _register_and_login(client, "pay-full@example.com")
    org_id = _get_org_id(headers)
    inv_id = await _create_verified_invoice(test_engine, org_id, total_amount=50000)

    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}/payment",
        json={"amount": 50000},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["payment_status"] == "paid"
    assert float(data["paid_amount"]) == 50000
    assert data["paid_date"] is not None


async def test_record_partial_payment(client: AsyncClient, test_engine):
    """Partial payment sets status to 'partially_paid'."""
    headers = await _register_and_login(client, "pay-partial@example.com")
    org_id = _get_org_id(headers)
    inv_id = await _create_verified_invoice(test_engine, org_id, total_amount=100000)

    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}/payment",
        json={"amount": 30000},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["payment_status"] == "partially_paid"
    assert float(data["paid_amount"]) == 30000


async def test_multiple_partial_payments(client: AsyncClient, test_engine):
    """Multiple partial payments accumulate correctly."""
    headers = await _register_and_login(client, "pay-multi@example.com")
    org_id = _get_org_id(headers)
    inv_id = await _create_verified_invoice(test_engine, org_id, total_amount=100000)

    # First partial
    await client.patch(
        f"/api/v1/invoices/{inv_id}/payment",
        json={"amount": 30000},
        headers=headers,
    )

    # Second partial
    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}/payment",
        json={"amount": 70000},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["payment_status"] == "paid"
    assert float(data["paid_amount"]) == 100000


async def test_payment_exceeds_total(client: AsyncClient, test_engine):
    """Payment that would exceed total_amount is rejected."""
    headers = await _register_and_login(client, "pay-exceed@example.com")
    org_id = _get_org_id(headers)
    inv_id = await _create_verified_invoice(test_engine, org_id, total_amount=50000)

    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}/payment",
        json={"amount": 60000},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_payment_on_processing_invoice_rejected(client: AsyncClient, test_engine):
    """Cannot record payment on a processing invoice."""
    headers = await _register_and_login(client, "pay-proc@example.com")
    org_id = _get_org_id(headers)

    # Insert a processing invoice
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    inv_id = str(uuid4())
    async with session_factory() as session:
        from sqlalchemy import text

        await session.execute(
            text("""
                INSERT INTO invoices
                (id, organization_id, status, total_amount, currency, payment_status,
                 created_at, updated_at)
                VALUES (:id, :org_id, 'processing', 50000, 'RSD', 'unpaid', NOW(), NOW())
            """),
            {"id": inv_id, "org_id": org_id},
        )
        await session.commit()

    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}/payment",
        json={"amount": 50000},
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Batch payment tests
# ---------------------------------------------------------------------------


async def test_batch_payment(client: AsyncClient, test_engine):
    """Batch payment marks multiple invoices as paid."""
    headers = await _register_and_login(client, "pay-batch@example.com")
    org_id = _get_org_id(headers)

    inv1 = await _create_verified_invoice(test_engine, org_id, total_amount=10000)
    inv2 = await _create_verified_invoice(test_engine, org_id, total_amount=20000)

    resp = await client.post(
        "/api/v1/invoices/batch-payment",
        json={"invoice_ids": [inv1, inv2]},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 2
    assert data["skipped"] == 0

    # Verify both are paid
    for inv_id in [inv1, inv2]:
        get_resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)
        assert get_resp.json()["payment_status"] == "paid"


async def test_batch_payment_skips_processing(client: AsyncClient, test_engine):
    """Batch payment skips non-verified invoices."""
    headers = await _register_and_login(client, "pay-batch-skip@example.com")
    org_id = _get_org_id(headers)

    verified = await _create_verified_invoice(test_engine, org_id, total_amount=10000)

    # Insert a processing invoice
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    processing_id = str(uuid4())
    async with session_factory() as session:
        from sqlalchemy import text

        await session.execute(
            text("""
                INSERT INTO invoices
                (id, organization_id, status, total_amount, currency, payment_status,
                 created_at, updated_at)
                VALUES (:id, :org_id, 'processing', 10000, 'RSD', 'unpaid', NOW(), NOW())
            """),
            {"id": processing_id, "org_id": org_id},
        )
        await session.commit()

    resp = await client.post(
        "/api/v1/invoices/batch-payment",
        json={"invoice_ids": [verified, processing_id]},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 1
    assert data["skipped"] == 1


# ---------------------------------------------------------------------------
# Payment status filter on invoice list
# ---------------------------------------------------------------------------


async def test_filter_by_payment_status(client: AsyncClient, test_engine):
    """Invoice list can be filtered by payment_status."""
    headers = await _register_and_login(client, "pay-filter@example.com")
    org_id = _get_org_id(headers)

    inv1 = await _create_verified_invoice(test_engine, org_id, total_amount=10000)
    inv2 = await _create_verified_invoice(test_engine, org_id, total_amount=20000)

    # Pay one
    await client.patch(
        f"/api/v1/invoices/{inv1}/payment",
        json={"amount": 10000},
        headers=headers,
    )

    # Filter unpaid
    resp = await client.get("/api/v1/invoices?payment_status=unpaid", headers=headers)
    assert resp.status_code == 200
    ids = [inv["id"] for inv in resp.json()["data"]]
    assert inv2 in ids
    assert inv1 not in ids

    # Filter paid
    resp = await client.get("/api/v1/invoices?payment_status=paid", headers=headers)
    ids = [inv["id"] for inv in resp.json()["data"]]
    assert inv1 in ids
    assert inv2 not in ids


# ---------------------------------------------------------------------------
# Open items report
# ---------------------------------------------------------------------------


async def test_open_items_report(client: AsyncClient, test_engine):
    """Open items report shows unpaid invoices with days overdue."""
    headers = await _register_and_login(client, "pay-open@example.com")
    org_id = _get_org_id(headers)

    # Create 2 invoices: one paid, one unpaid (overdue)
    inv_unpaid = await _create_verified_invoice(
        test_engine, org_id, total_amount=50000, due_date="2026-01-15"
    )
    inv_paid = await _create_verified_invoice(
        test_engine, org_id, total_amount=30000, due_date="2026-03-15"
    )

    # Pay the second one
    await client.patch(
        f"/api/v1/invoices/{inv_paid}/payment",
        json={"amount": 30000},
        headers=headers,
    )

    resp = await client.get("/api/v1/reports/open-items", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["items"][0]["invoice_id"] == inv_unpaid
    assert data["items"][0]["days_overdue"] > 0
    assert data["total_open_amount"] == 50000


# ---------------------------------------------------------------------------
# Aging report
# ---------------------------------------------------------------------------


async def test_aging_report(client: AsyncClient, test_engine):
    """Aging report groups unpaid invoices into buckets."""
    headers = await _register_and_login(client, "pay-aging@example.com")
    org_id = _get_org_id(headers)

    # Create invoices with different due dates
    await _create_verified_invoice(
        test_engine,
        org_id,
        total_amount=10000,
        due_date="2026-04-01",  # 0-30 days
    )
    await _create_verified_invoice(
        test_engine,
        org_id,
        total_amount=20000,
        due_date="2026-01-01",  # 90+ days
    )

    resp = await client.get("/api/v1/reports/aging", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Should have 4 buckets
    assert len(data["buckets"]) == 4
    assert data["grand_total"] == 30000

    # Find buckets
    bucket_map = {b["bucket"]: b for b in data["buckets"]}
    assert bucket_map["90+"]["count"] == 1
    assert bucket_map["90+"]["total_amount"] == 20000


# ---------------------------------------------------------------------------
# Organization isolation
# ---------------------------------------------------------------------------


async def test_payment_org_isolation(client: AsyncClient, test_engine):
    """Org A cannot record payment on Org B's invoice."""
    headers_a = await _register_and_login(client, "pay-org-a@example.com")
    headers_b = await _register_and_login(client, "pay-org-b@example.com")
    org_a = _get_org_id(headers_a)

    inv = await _create_verified_invoice(test_engine, org_a, total_amount=50000)

    # Org B tries to pay Org A's invoice
    resp = await client.patch(
        f"/api/v1/invoices/{inv}/payment",
        json={"amount": 50000},
        headers=headers_b,
    )
    assert resp.status_code == 404
