"""Tests for API key authentication (issue #69)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token


async def _register_and_login(
    client: AsyncClient,
    email: str = "apikey-test@example.com",
) -> dict[str, str]:
    """Register a user, create an organization, and return auth headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Key",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Key Org {email}"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token."""
    token = headers["Authorization"].removeprefix("Bearer ")
    return decode_token(token)["org"]


def _get_user_id(headers: dict) -> str:
    """Extract user_id from the JWT token."""
    token = headers["Authorization"].removeprefix("Bearer ")
    return decode_token(token)["sub"]


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


async def test_create_api_key(client: AsyncClient, test_engine):
    """Create an API key, plain key returned with sk_live_ prefix."""
    headers = await _register_and_login(client, "key-create@test.com")
    resp = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Test Key"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Key"
    assert data["plain_key"].startswith("sk_live_")
    assert len(data["key_prefix"]) == 8
    assert data["is_active"] is True
    assert data["expires_at"] is None


async def test_create_api_key_with_expiry(client: AsyncClient, test_engine):
    """Create an API key with an expiration date."""
    headers = await _register_and_login(client, "key-expiry@test.com")
    future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    resp = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Expiring Key", "expires_at": future},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["expires_at"] is not None


async def test_list_api_keys(client: AsyncClient, test_engine):
    """List keys shows prefix but never the hash or full key."""
    headers = await _register_and_login(client, "key-list@test.com")

    # Create two keys
    await client.post(
        "/api/v1/api-keys/",
        json={"name": "Key A"},
        headers=headers,
    )
    await client.post(
        "/api/v1/api-keys/",
        json={"name": "Key B"},
        headers=headers,
    )

    resp = await client.get("/api/v1/api-keys/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] == 2
    assert len(data["data"]) == 2

    for key in data["data"]:
        assert "key_prefix" in key
        assert "plain_key" not in key
        assert "key_hash" not in key


async def test_revoke_api_key(client: AsyncClient, test_engine):
    """Revoke a key sets is_active to false."""
    headers = await _register_and_login(client, "key-revoke@test.com")
    create_resp = await client.post(
        "/api/v1/api-keys/",
        json={"name": "To Revoke"},
        headers=headers,
    )
    key_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/api-keys/{key_id}", headers=headers)
    assert resp.status_code == 204

    # Verify it shows as inactive
    list_resp = await client.get("/api/v1/api-keys/", headers=headers)
    keys = list_resp.json()["data"]
    revoked = [k for k in keys if k["id"] == key_id]
    assert len(revoked) == 1
    assert revoked[0]["is_active"] is False


async def test_revoke_nonexistent_key(client: AsyncClient, test_engine):
    """Revoking a nonexistent key returns 404."""
    headers = await _register_and_login(client, "key-404@test.com")
    resp = await client.delete(f"/api/v1/api-keys/{uuid4()}", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Authentication via X-API-Key
# ---------------------------------------------------------------------------


async def test_auth_via_api_key(client: AsyncClient, test_engine):
    """Request with X-API-Key header authenticates successfully."""
    headers = await _register_and_login(client, "key-auth@test.com")
    create_resp = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Auth Key"},
        headers=headers,
    )
    plain_key = create_resp.json()["plain_key"]

    # Use the API key instead of JWT
    resp = await client.get(
        "/api/v1/invoices",
        headers={"X-API-Key": plain_key},
    )
    assert resp.status_code == 200


async def test_auth_via_api_key_on_protected_endpoint(client: AsyncClient, test_engine):
    """API key works on role-protected endpoints (user inherits their role)."""
    headers = await _register_and_login(client, "key-role@test.com")
    create_resp = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Role Key"},
        headers=headers,
    )
    plain_key = create_resp.json()["plain_key"]

    # This endpoint requires get_current_user — should work with API key
    resp = await client.get(
        "/api/v1/users/me",
        headers={"X-API-Key": plain_key},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "key-role@test.com"


async def test_revoked_key_returns_401(client: AsyncClient, test_engine):
    """Revoked API key cannot authenticate."""
    headers = await _register_and_login(client, "key-revoked-auth@test.com")
    create_resp = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Revoke Me"},
        headers=headers,
    )
    plain_key = create_resp.json()["plain_key"]
    key_id = create_resp.json()["id"]

    # Revoke it
    await client.delete(f"/api/v1/api-keys/{key_id}", headers=headers)

    # Try to use it
    resp = await client.get(
        "/api/v1/invoices",
        headers={"X-API-Key": plain_key},
    )
    assert resp.status_code == 401


async def test_expired_key_returns_401(client: AsyncClient, test_engine):
    """Expired API key cannot authenticate."""
    headers = await _register_and_login(client, "key-expired@test.com")

    # Create key with past expiry
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    create_resp = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Expired Key", "expires_at": past},
        headers=headers,
    )
    plain_key = create_resp.json()["plain_key"]

    resp = await client.get(
        "/api/v1/invoices",
        headers={"X-API-Key": plain_key},
    )
    assert resp.status_code == 401


async def test_invalid_key_returns_401(client: AsyncClient, test_engine):
    """Completely invalid API key returns 401."""
    resp = await client.get(
        "/api/v1/invoices",
        headers={"X-API-Key": "sk_live_totallyinvalidkey12345678"},
    )
    assert resp.status_code == 401


async def test_no_auth_returns_401(client: AsyncClient, test_engine):
    """No auth header at all returns 401."""
    resp = await client.get("/api/v1/invoices")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Organization isolation
# ---------------------------------------------------------------------------


async def test_api_key_org_isolation(client: AsyncClient, test_engine):
    """Org A's API key cannot be revoked by Org B."""
    headers_a = await _register_and_login(client, "key-org-a@test.com")
    headers_b = await _register_and_login(client, "key-org-b@test.com")

    create_resp = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Org A Key"},
        headers=headers_a,
    )
    key_id = create_resp.json()["id"]

    # Org B tries to revoke Org A's key
    resp = await client.delete(f"/api/v1/api-keys/{key_id}", headers=headers_b)
    assert resp.status_code == 404

    # Org B's list doesn't include Org A's key
    list_resp = await client.get("/api/v1/api-keys/", headers=headers_b)
    assert all(k["id"] != key_id for k in list_resp.json()["data"])


# ---------------------------------------------------------------------------
# Role enforcement
# ---------------------------------------------------------------------------


async def test_create_key_requires_manager(client: AsyncClient, test_engine):
    """Only manager+ can create API keys."""
    headers = await _register_and_login(client, "key-member@test.com")
    user_id = _get_user_id(headers)

    # Downgrade to member
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text("UPDATE users SET role = 'member' WHERE id = :uid"),
            {"uid": user_id},
        )
        await session.commit()

    resp = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Should Fail"},
        headers=headers,
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# last_used_at tracking
# ---------------------------------------------------------------------------


async def test_last_used_at_updates(client: AsyncClient, test_engine):
    """last_used_at is updated when the key is used for authentication."""
    headers = await _register_and_login(client, "key-lastused@test.com")
    create_resp = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Track Usage"},
        headers=headers,
    )
    plain_key = create_resp.json()["plain_key"]
    key_id = create_resp.json()["id"]

    # Initially last_used_at should be null
    list_resp = await client.get("/api/v1/api-keys/", headers=headers)
    key_data = [k for k in list_resp.json()["data"] if k["id"] == key_id][0]
    assert key_data["last_used_at"] is None

    # Use the key
    await client.get("/api/v1/invoices", headers={"X-API-Key": plain_key})

    # Now last_used_at should be set
    list_resp2 = await client.get("/api/v1/api-keys/", headers=headers)
    key_data2 = [k for k in list_resp2.json()["data"] if k["id"] == key_id][0]
    assert key_data2["last_used_at"] is not None
