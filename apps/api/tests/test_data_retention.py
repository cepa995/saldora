"""Tests for data retention automation (issue #71).

Verifies that the retention policy is enforced:
- Orgs canceled 90+ days ago → all data deleted
- Active orgs → untouched
- Recently canceled orgs (< 90 days) → untouched
- Expired export URLs → marked as expired
- Paddle webhook sets/clears canceled_at

Since the worker task runs in a separate process (Celery), we test
the retention logic directly using async SQL on the test DB.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token


async def _register_and_login(
    client: AsyncClient,
    email: str = "retention-test@example.com",
) -> dict[str, str]:
    """Register a user, create an organization, and return auth headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Retention",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Retention Org {email}"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


async def _cancel_org(test_engine, org_id: str, days_ago: int) -> None:
    """Simulate subscription cancellation N days ago."""
    canceled_at = datetime.now(UTC) - timedelta(days=days_ago)
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text(
                "UPDATE organizations SET subscription_status = 'canceled', "
                "subscription_canceled_at = :canceled_at WHERE id = :org_id"
            ),
            {"canceled_at": canceled_at, "org_id": org_id},
        )
        await session.commit()


async def _insert_invoice(test_engine, org_id: str) -> str:
    """Insert a test invoice for the org, return its ID."""
    inv_id = str(uuid4())
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO invoices (id, organization_id, status, currency, "
                "created_at, updated_at) VALUES (:id, :org_id, 'review', 'RSD', "
                "NOW(), NOW())"
            ),
            {"id": inv_id, "org_id": org_id},
        )
        await session.commit()
    return inv_id


async def _org_exists(test_engine, org_id: str) -> bool:
    """Check if an organization still exists."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM organizations WHERE id = :org_id"),
            {"org_id": org_id},
        )
        return (result.scalar() or 0) > 0


async def _count_invoices(test_engine, org_id: str) -> int:
    """Count invoices for an org."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM invoices WHERE organization_id = :org_id"),
            {"org_id": org_id},
        )
        return result.scalar() or 0


async def _run_retention(test_engine) -> dict:
    """Run retention logic using async SQL (mirrors the Celery task logic).

    Returns:
        Dict with organizations_deleted and exports_expired counts.
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=90)
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    orgs_deleted = 0
    exports_expired = 0

    async with factory() as session:
        # Find expired orgs
        result = await session.execute(
            text(
                "SELECT id FROM organizations "
                "WHERE subscription_status = 'canceled' "
                "AND subscription_canceled_at IS NOT NULL "
                "AND subscription_canceled_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )
        expired_orgs = [str(row[0]) for row in result.fetchall()]

        for org_id in expired_orgs:
            # Delete in FK order
            for table in [
                "invoice_line_items",
                "correction_logs",
                "accounting_intents",
                "scheduled_export_logs",
                "automation_rules",
                "consent_records",
                "deletion_requests",
                "data_processing_agreements",
                "export_templates",
                "minimax_configs",
                "clients",
                "audit_logs",
                "invoices",
                "usage_records",
                "invitations",
                "join_requests",
            ]:
                await session.execute(
                    text(f"DELETE FROM {table} WHERE organization_id = :org_id"),
                    {"org_id": org_id},
                )
            # Delete audit logs referencing users in this org
            await session.execute(
                text(
                    "DELETE FROM audit_logs WHERE user_id IN "
                    "(SELECT id FROM users WHERE organization_id = :org_id)"
                ),
                {"org_id": org_id},
            )
            await session.execute(
                text("DELETE FROM users WHERE organization_id = :org_id"),
                {"org_id": org_id},
            )
            await session.execute(
                text("DELETE FROM organizations WHERE id = :org_id"),
                {"org_id": org_id},
            )
            orgs_deleted += 1

        # Expire old export URLs
        result = await session.execute(
            text(
                "UPDATE scheduled_export_logs "
                "SET status = 'expired', download_url = NULL "
                "WHERE status = 'ready' "
                "AND expires_at IS NOT NULL "
                "AND expires_at < :now"
            ),
            {"now": now},
        )
        exports_expired = result.rowcount or 0

        await session.commit()

    return {"organizations_deleted": orgs_deleted, "exports_expired": exports_expired}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_retention_deletes_expired_org(client: AsyncClient, test_engine):
    """Org canceled 91 days ago → all data deleted."""
    headers = await _register_and_login(client, "expired-org@test.com")
    org_id = _get_org_id(headers)

    await _insert_invoice(test_engine, org_id)
    assert await _count_invoices(test_engine, org_id) == 1

    await _cancel_org(test_engine, org_id, days_ago=91)

    result = await _run_retention(test_engine)

    assert result["organizations_deleted"] >= 1
    assert not await _org_exists(test_engine, org_id)


async def test_retention_keeps_active_org(client: AsyncClient, test_engine):
    """Active org → untouched."""
    headers = await _register_and_login(client, "active-org@test.com")
    org_id = _get_org_id(headers)

    await _insert_invoice(test_engine, org_id)

    await _run_retention(test_engine)

    assert await _org_exists(test_engine, org_id)
    assert await _count_invoices(test_engine, org_id) == 1


async def test_retention_keeps_recently_canceled_org(client: AsyncClient, test_engine):
    """Org canceled 30 days ago → within grace period, untouched."""
    headers = await _register_and_login(client, "recent-cancel@test.com")
    org_id = _get_org_id(headers)

    await _insert_invoice(test_engine, org_id)
    await _cancel_org(test_engine, org_id, days_ago=30)

    await _run_retention(test_engine)

    assert await _org_exists(test_engine, org_id)
    assert await _count_invoices(test_engine, org_id) == 1


async def test_retention_expires_old_export_urls(client: AsyncClient, test_engine):
    """Export logs with expired URLs → status set to 'expired'."""
    headers = await _register_and_login(client, "export-expire@test.com")
    org_id = _get_org_id(headers)

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO scheduled_export_logs "
                "(id, organization_id, period, delivery_method, delivered_to, "
                "status, download_url, expires_at) "
                "VALUES (:id, :org_id, '2026-03', 'email', 'test@test.com', "
                "'ready', 'https://example.com/dl', :expires_at)"
            ),
            {
                "id": str(uuid4()),
                "org_id": org_id,
                "expires_at": datetime.now(UTC) - timedelta(days=1),
            },
        )
        await session.commit()

    result = await _run_retention(test_engine)

    assert result["exports_expired"] >= 1

    async with factory() as session:
        row = await session.execute(
            text(
                "SELECT status, download_url FROM scheduled_export_logs "
                "WHERE organization_id = :org_id"
            ),
            {"org_id": org_id},
        )
        record = row.fetchone()
        assert record[0] == "expired"
        assert record[1] is None


async def test_paddle_cancel_sets_canceled_at(client: AsyncClient, test_engine):
    """Paddle subscription.canceled webhook sets subscription_canceled_at."""
    headers = await _register_and_login(client, "paddle-cancel@test.com")
    org_id = _get_org_id(headers)

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        from app.services.paddle import _update_org_subscription

        await _update_org_subscription(session, org_id=org_id, subscription_status="canceled")

    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT subscription_status, subscription_canceled_at "
                "FROM organizations WHERE id = :org_id"
            ),
            {"org_id": org_id},
        )
        row = result.fetchone()
        assert row[0] == "canceled"
        assert row[1] is not None


async def test_paddle_reactivate_clears_canceled_at(client: AsyncClient, test_engine):
    """Reactivating subscription clears subscription_canceled_at."""
    headers = await _register_and_login(client, "paddle-reactivate@test.com")
    org_id = _get_org_id(headers)

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        from app.services.paddle import _update_org_subscription

        await _update_org_subscription(session, org_id=org_id, subscription_status="canceled")

    async with factory() as session:
        from app.services.paddle import _update_org_subscription

        await _update_org_subscription(session, org_id=org_id, subscription_status="active")

    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT subscription_status, subscription_canceled_at "
                "FROM organizations WHERE id = :org_id"
            ),
            {"org_id": org_id},
        )
        row = result.fetchone()
        assert row[0] == "active"
        assert row[1] is None
