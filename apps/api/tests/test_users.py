"""Tests for user profile and password management endpoints."""

from httpx import AsyncClient


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


# ---------------------------------------------------------------------------
# GET /api/v1/users/me — get profile
# ---------------------------------------------------------------------------


async def test_get_profile_success(client: AsyncClient):
    """GET /api/v1/users/me returns the current user's profile."""
    headers = await _auth_headers(client, "user-profile-get@example.com", "User Org 1")

    resp = await client.get("/api/v1/users/me", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "user-profile-get@example.com"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert "id" in data
    assert "organization_id" in data
    assert "role" in data
    assert "email_verified" in data
    assert "created_at" in data
    assert "password" not in data
    assert "password_hash" not in data


async def test_get_profile_requires_auth(client: AsyncClient):
    """GET /api/v1/users/me without token returns 401."""
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_get_profile_includes_role(client: AsyncClient):
    """GET /api/v1/users/me includes the user's role."""
    headers = await _auth_headers(client, "user-profile-role@example.com", "User Org 2")

    resp = await client.get("/api/v1/users/me", headers=headers)

    assert resp.status_code == 200
    # The org creator is assigned admin role
    assert resp.json()["role"] == "admin"


# ---------------------------------------------------------------------------
# PATCH /api/v1/users/me — update profile
# ---------------------------------------------------------------------------


async def test_update_profile_first_name(client: AsyncClient):
    """PATCH /api/v1/users/me updates first_name successfully."""
    headers = await _auth_headers(client, "user-update-fname@example.com", "User Org 3")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"first_name": "Updated"},
        headers=headers,
    )

    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Updated"


async def test_update_profile_last_name(client: AsyncClient):
    """PATCH /api/v1/users/me updates last_name successfully."""
    headers = await _auth_headers(client, "user-update-lname@example.com", "User Org 4")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"last_name": "Surname"},
        headers=headers,
    )

    assert resp.status_code == 200
    assert resp.json()["last_name"] == "Surname"


async def test_update_profile_both_names(client: AsyncClient):
    """PATCH /api/v1/users/me updates both first_name and last_name."""
    headers = await _auth_headers(client, "user-update-both@example.com", "User Org 5")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"first_name": "Jane", "last_name": "Doe"},
        headers=headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"


async def test_update_profile_returns_full_profile(client: AsyncClient):
    """PATCH /api/v1/users/me returns the complete updated profile."""
    headers = await _auth_headers(client, "user-update-full@example.com", "User Org 6")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"first_name": "Complete"},
        headers=headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "email" in data
    assert "organization_id" in data
    assert "role" in data
    assert "email_verified" in data


async def test_update_profile_requires_auth(client: AsyncClient):
    """PATCH /api/v1/users/me without token returns 401."""
    resp = await client.patch("/api/v1/users/me", json={"first_name": "Ghost"})
    assert resp.status_code == 401


async def test_update_profile_empty_body_is_noop(client: AsyncClient):
    """PATCH /api/v1/users/me with no fields returns 200 with unchanged profile."""
    headers = await _auth_headers(client, "user-update-noop@example.com", "User Org 7")

    # Get original
    original = await client.get("/api/v1/users/me", headers=headers)

    resp = await client.patch("/api/v1/users/me", json={}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["first_name"] == original.json()["first_name"]
    assert resp.json()["last_name"] == original.json()["last_name"]


# ---------------------------------------------------------------------------
# POST /api/v1/users/me/change-password — change password
# ---------------------------------------------------------------------------


async def test_change_password_success(client: AsyncClient):
    """POST /api/v1/users/me/change-password succeeds with correct current password."""
    headers = await _auth_headers(client, "user-chpw-ok@example.com", "User Org 8")

    resp = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "securepass123", "new_password": "newpassword456"},
        headers=headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "password" in data["message"].lower()


async def test_change_password_allows_login_with_new_password(client: AsyncClient):
    """After changing password, the user can log in with the new password."""
    headers = await _auth_headers(client, "user-chpw-login@example.com", "User Org 9")

    await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "securepass123", "new_password": "newpassword789"},
        headers=headers,
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "user-chpw-login@example.com", "password": "newpassword789"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


async def test_change_password_old_password_no_longer_works(client: AsyncClient):
    """After changing password, the old password is rejected on login."""
    headers = await _auth_headers(client, "user-chpw-old@example.com", "User Org 10")

    await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "securepass123", "new_password": "brandnewpass999"},
        headers=headers,
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "user-chpw-old@example.com", "password": "securepass123"},
    )
    assert login_resp.status_code == 401


async def test_change_password_wrong_current_password(client: AsyncClient):
    """POST /api/v1/users/me/change-password with wrong current password returns 400."""
    headers = await _auth_headers(client, "user-chpw-wrong@example.com", "User Org 11")

    resp = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "wrongpassword", "new_password": "newpassword456"},
        headers=headers,
    )

    assert resp.status_code == 400
    assert "incorrect" in resp.json()["detail"].lower()


async def test_change_password_too_short_new_password(client: AsyncClient):
    """POST /api/v1/users/me/change-password with short new password returns 422."""
    headers = await _auth_headers(client, "user-chpw-short@example.com", "User Org 12")

    resp = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "securepass123", "new_password": "short"},
        headers=headers,
    )

    assert resp.status_code == 422


async def test_change_password_requires_auth(client: AsyncClient):
    """POST /api/v1/users/me/change-password without token returns 401."""
    resp = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "securepass123", "new_password": "newpassword456"},
    )
    assert resp.status_code == 401
