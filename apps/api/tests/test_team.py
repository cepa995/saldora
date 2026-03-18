"""Tests for team member management endpoints."""

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token


async def _auth_headers(
    client: AsyncClient,
    email: str = "test@example.com",
    org_name: str = "Test Org",
) -> dict[str, str]:
    """Register a user, create an organization, return auth headers."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    token = reg.json()["access_token"]
    org = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": org_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"Authorization": f"Bearer {org.json()['access_token']}"}


def _get_user_id(headers: dict) -> str:
    """Extract user_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["sub"]


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


async def _add_member_to_org(
    test_engine,
    org_id: str,
    email: str,
    role: str = "viewer",
) -> str:
    """Register a second user and move them into the given org. Returns their user_id."""
    # We need to create the user directly in the DB so we can assign them
    # to an existing org without going through the full auth/org creation flow.
    from uuid import uuid4

    from app.auth import hash_password

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        user_id = str(uuid4())
        await session.execute(
            text(
                "INSERT INTO users"
                " (id, email, password_hash, first_name, last_name,"
                "  role, email_verified, organization_id, created_at, updated_at)"
                " VALUES (:id, :email, :pw, 'Second', 'User',"
                "  :role, false, :org_id, NOW(), NOW())"
            ),
            {
                "id": user_id,
                "email": email,
                "pw": hash_password("securepass123"),
                "role": role,
                "org_id": org_id,
            },
        )
        await session.commit()
    return user_id


# ---------------------------------------------------------------------------
# List members
# ---------------------------------------------------------------------------


async def test_list_members_returns_creator(client: AsyncClient, test_engine):
    """GET /api/v1/team/members returns at least the admin who created the org."""
    headers = await _auth_headers(client, "team-list-creator@example.com", "Team Org 1")

    resp = await client.get("/api/v1/team/members", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    emails = [m["email"] for m in data]
    assert "team-list-creator@example.com" in emails


async def test_list_members_includes_all_org_members(client: AsyncClient, test_engine):
    """GET /api/v1/team/members lists all members of the organization."""
    headers = await _auth_headers(client, "team-list-all@example.com", "Team Org 2")
    org_id = _get_org_id(headers)

    await _add_member_to_org(test_engine, org_id, "team-member-extra@example.com")

    resp = await client.get("/api/v1/team/members", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    emails = [m["email"] for m in data]
    assert "team-list-all@example.com" in emails
    assert "team-member-extra@example.com" in emails


async def test_list_members_requires_auth(client: AsyncClient):
    """GET /api/v1/team/members without token returns 401."""
    resp = await client.get("/api/v1/team/members")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Update member role
# ---------------------------------------------------------------------------


async def test_update_member_role_success(client: AsyncClient, test_engine):
    """PATCH /api/v1/team/members/{user_id}/role updates the role of another member."""
    headers = await _auth_headers(client, "team-role-admin@example.com", "Team Org 3")
    org_id = _get_org_id(headers)

    member_id = await _add_member_to_org(
        test_engine, org_id, "team-role-target@example.com", role="viewer"
    )

    resp = await client.patch(
        f"/api/v1/team/members/{member_id}/role",
        json={"role": "manager"},
        headers=headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == member_id
    assert data["role"] == "manager"


async def test_update_member_role_cannot_change_own_role(client: AsyncClient, test_engine):
    """PATCH /api/v1/team/members/{user_id}/role returns 400 when changing own role."""
    headers = await _auth_headers(client, "team-self-role@example.com", "Team Org 4")
    user_id = _get_user_id(headers)

    resp = await client.patch(
        f"/api/v1/team/members/{user_id}/role",
        json={"role": "viewer"},
        headers=headers,
    )

    assert resp.status_code == 400
    assert "own role" in resp.json()["detail"].lower()


async def test_update_member_role_not_found(client: AsyncClient, test_engine):
    """PATCH /api/v1/team/members/{user_id}/role returns 404 for unknown member."""
    headers = await _auth_headers(client, "team-role-404@example.com", "Team Org 5")
    nonexistent_id = "00000000-0000-0000-0000-000000000001"

    resp = await client.patch(
        f"/api/v1/team/members/{nonexistent_id}/role",
        json={"role": "operator"},
        headers=headers,
    )

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_update_member_role_same_role_is_noop(client: AsyncClient, test_engine):
    """PATCH with the same role as current returns 200 without error."""
    headers = await _auth_headers(client, "team-role-noop@example.com", "Team Org 6")
    org_id = _get_org_id(headers)

    member_id = await _add_member_to_org(
        test_engine, org_id, "team-role-noop-target@example.com", role="operator"
    )

    resp = await client.patch(
        f"/api/v1/team/members/{member_id}/role",
        json={"role": "operator"},
        headers=headers,
    )

    assert resp.status_code == 200
    assert resp.json()["role"] == "operator"


async def test_update_member_role_invalid_role(client: AsyncClient, test_engine):
    """PATCH with an invalid role value returns 422."""
    headers = await _auth_headers(client, "team-invalid-role@example.com", "Team Org 7")
    org_id = _get_org_id(headers)

    member_id = await _add_member_to_org(
        test_engine, org_id, "team-invalid-role-target@example.com"
    )

    resp = await client.patch(
        f"/api/v1/team/members/{member_id}/role",
        json={"role": "superuser"},
        headers=headers,
    )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Remove member
# ---------------------------------------------------------------------------


async def test_remove_member_success(client: AsyncClient, test_engine):
    """DELETE /api/v1/team/members/{user_id} removes the specified member."""
    headers = await _auth_headers(client, "team-remove-admin@example.com", "Team Org 8")
    org_id = _get_org_id(headers)

    member_id = await _add_member_to_org(test_engine, org_id, "team-remove-target@example.com")

    resp = await client.delete(
        f"/api/v1/team/members/{member_id}",
        headers=headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "removed" in data["message"].lower()

    # Verify the member no longer appears in the list
    list_resp = await client.get("/api/v1/team/members", headers=headers)
    member_ids = [m["id"] for m in list_resp.json()]
    assert member_id not in member_ids


async def test_remove_member_cannot_remove_self(client: AsyncClient, test_engine):
    """DELETE /api/v1/team/members/{user_id} returns 400 when removing self."""
    headers = await _auth_headers(client, "team-remove-self@example.com", "Team Org 9")
    user_id = _get_user_id(headers)

    resp = await client.delete(
        f"/api/v1/team/members/{user_id}",
        headers=headers,
    )

    assert resp.status_code == 400
    assert "yourself" in resp.json()["detail"].lower()


async def test_remove_member_not_found(client: AsyncClient, test_engine):
    """DELETE /api/v1/team/members/{user_id} returns 404 for unknown member."""
    headers = await _auth_headers(client, "team-del-404@example.com", "Team Org 10")
    nonexistent_id = "00000000-0000-0000-0000-000000000002"

    resp = await client.delete(
        f"/api/v1/team/members/{nonexistent_id}",
        headers=headers,
    )

    assert resp.status_code == 404
