"""
API tests for authentication endpoints.

These tests exercise the full request lifecycle: HTTP → FastAPI → DB → response.
They catch issues that unit tests can't: wrong status codes, missing fields
in responses, broken DB queries, and incorrect error messages.
"""

from httpx import AsyncClient

# ---- Registration ----


async def test_register_success(client: AsyncClient):
    """Happy path: new user gets 201 with correct response shape."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
            "organization_name": "Test Corp",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["role"] == "admin"  # First user in org is admin
    assert data["email_verified"] is False
    # Password must NEVER appear in the response
    assert "password" not in data
    assert "password_hash" not in data


async def test_register_duplicate_email(client: AsyncClient):
    """
    Registering with an existing email returns 409 Conflict.

    Why test this? Without this check, a duplicate INSERT would raise
    a database IntegrityError → 500, which leaks internal details.
    """
    payload = {
        "email": "dupe@example.com",
        "password": "securepass123",
        "first_name": "First",
        "last_name": "User",
    }
    # First registration succeeds
    await client.post("/api/v1/auth/register", json=payload)
    # Second registration with same email must fail
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409
    assert "already registered" in response.json()["detail"].lower()


async def test_register_short_password(client: AsyncClient):
    """
    Password shorter than 8 chars returns 422 (validation error).

    Pydantic's Field(min_length=8) handles this automatically.
    This test makes sure we haven't accidentally removed that constraint.
    """
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "abc"},
    )

    assert response.status_code == 422


# ---- Login ----


async def test_login_success(client: AsyncClient):
    """Registered user can log in and receives a JWT token pair."""
    # Setup: register a user first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "securepass123",
            "first_name": "Login",
            "last_name": "User",
        },
    )

    # Login uses OAuth2 form encoding (username + password), not JSON
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "securepass123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


async def test_login_wrong_password(client: AsyncClient):
    """
    Wrong password returns 401.

    SECURITY: The error message says "Incorrect email or password" — never
    "user not found" vs "wrong password".  Distinguishing the two would let
    an attacker enumerate which emails are registered.
    """
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrong@example.com",
            "password": "securepass123",
            "first_name": "Wrong",
            "last_name": "User",
        },
    )

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "wrong@example.com", "password": "badpassword"},
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


async def test_login_nonexistent_user(client: AsyncClient):
    """
    Login with email that doesn't exist also returns 401 — same error
    message as wrong password (prevents email enumeration).
    """
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "ghost@example.com", "password": "doesntmatter"},
    )

    assert response.status_code == 401


# ---- Protected endpoints ----


async def test_protected_endpoint_without_token(client: AsyncClient):
    """
    Accessing a protected endpoint without a token returns 401.

    This is the simplest auth test, but also the most important: it
    verifies that the `Depends(get_current_user)` guard is in place.
    """
    response = await client.get("/api/v1/invoices")
    assert response.status_code == 401


async def test_protected_endpoint_with_valid_token(client: AsyncClient):
    """Full round-trip: register → login → access protected endpoint."""
    # Register
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "auth@example.com",
            "password": "securepass123",
            "first_name": "Auth",
            "last_name": "User",
        },
    )
    # Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "auth@example.com", "password": "securepass123"},
    )
    token = login_resp.json()["access_token"]

    # Access protected endpoint
    response = await client.get(
        "/api/v1/invoices",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should not be 401 (we're authenticated) — the exact status depends
    # on whether the invoices endpoint is fully implemented yet
    assert response.status_code != 401
