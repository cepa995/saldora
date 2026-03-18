"""Extended authentication tests — password reset, logout, and org creation edge cases.

Covers the endpoints and branches in app/routers/auth.py that are not exercised
by the base test_auth_api.py file:

- POST /api/v1/auth/logout
- POST /api/v1/auth/password-reset/request
- POST /api/v1/auth/password-reset/confirm
- POST /api/v1/auth/create-organization — edge cases (already has org, PIB validation)
- GET  /api/v1/users/me — access via token with embedded org claim
"""

from httpx import AsyncClient

from app.auth import create_password_reset_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register(
    client: AsyncClient,
    email: str,
    password: str = "securepass123",
) -> dict:
    """Register a new user and return the full JSON response.

    Args:
        client: Async HTTP client.
        email: Unique email for this registration.
        password: Password to use (default satisfies min_length=8).

    Returns:
        Parsed JSON dict with access_token, refresh_token, etc.
    """
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Auth",
            "last_name": "Extended",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _register_with_org(
    client: AsyncClient,
    email: str,
    org_name: str,
    password: str = "securepass123",
) -> dict[str, str]:
    """Register a user, create an org, and return Bearer auth headers.

    Args:
        client: Async HTTP client.
        email: Unique email for this user.
        org_name: Organisation name to create.
        password: Password (default: 'securepass123').

    Returns:
        Dict with 'Authorization' header ready for use.
    """
    reg = await _register(client, email, password)
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": org_name},
        headers={"Authorization": f"Bearer {reg['access_token']}"},
    )
    assert org_resp.status_code == 200, org_resp.text
    return {"Authorization": f"Bearer {org_resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------


async def test_logout_returns_success_message(client: AsyncClient):
    """POST /api/v1/auth/logout returns 200 with a success message.

    The current implementation is a stub that always succeeds.  This test
    ensures the endpoint is reachable and returns the expected shape.

    Args:
        client: Async HTTP client fixture.
    """
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "logged out" in data["message"].lower()


# ---------------------------------------------------------------------------
# POST /api/v1/auth/password-reset/request
# ---------------------------------------------------------------------------


async def test_password_reset_request_existing_email(client: AsyncClient):
    """Requesting a reset for a known email returns 200 with generic message.

    The response must NOT reveal whether the email exists (prevents
    enumeration attacks).

    Args:
        client: Async HTTP client fixture.
    """
    await _register(client, "auth-pr-exists@example.com")

    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "auth-pr-exists@example.com"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "reset link" in data["message"].lower() or "email" in data["message"].lower()


async def test_password_reset_request_unknown_email(client: AsyncClient):
    """Requesting a reset for an unknown email still returns 200.

    The same generic response prevents email enumeration.

    Args:
        client: Async HTTP client fixture.
    """
    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "auth-pr-unknown@example.com"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data


async def test_password_reset_request_invalid_email_format(client: AsyncClient):
    """Submitting a malformed email address returns 422 validation error.

    Args:
        client: Async HTTP client fixture.
    """
    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "not-an-email"},
    )
    assert resp.status_code == 422


async def test_password_reset_request_missing_email_field(client: AsyncClient):
    """Omitting the email field entirely returns 422 validation error.

    Args:
        client: Async HTTP client fixture.
    """
    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/auth/password-reset/confirm
# ---------------------------------------------------------------------------


async def test_password_reset_confirm_success(client: AsyncClient):
    """Full password-reset flow: request token → confirm → login with new password.

    This is the happy-path integration test for the entire reset workflow.

    Args:
        client: Async HTTP client fixture.
    """
    email = "auth-pr-confirm@example.com"
    reg = await _register(client, email)
    user_id = None

    # Extract user_id from the access token payload to build a valid reset token
    from app.auth import decode_token

    payload = decode_token(reg["access_token"])
    user_id = payload["sub"]

    # Build a valid password-reset JWT directly (bypassing email delivery)
    reset_token = create_password_reset_token(user_id, email)

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "newpassword999"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "reset" in data["message"].lower() or "password" in data["message"].lower()

    # Verify login works with the new password
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "newpassword999"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


async def test_password_reset_confirm_old_password_no_longer_works(client: AsyncClient):
    """After resetting, the old password is rejected on login.

    Args:
        client: Async HTTP client fixture.
    """
    email = "auth-pr-oldpw@example.com"
    old_password = "securepass123"
    reg = await _register(client, email, old_password)

    from app.auth import decode_token

    user_id = decode_token(reg["access_token"])["sub"]
    reset_token = create_password_reset_token(user_id, email)

    await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "totallynewpass1"},
    )

    # Old password should now fail
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": old_password},
    )
    assert login_resp.status_code == 401


async def test_password_reset_confirm_invalid_token(client: AsyncClient):
    """Submitting a garbage token returns 400.

    Args:
        client: Async HTTP client fixture.
    """
    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "this.is.not.valid", "new_password": "newpassword123"},
    )
    assert resp.status_code == 400
    assert "invalid" in resp.json()["detail"].lower() or "expired" in resp.json()["detail"].lower()


async def test_password_reset_confirm_with_access_token_rejected(client: AsyncClient):
    """Submitting an access token (wrong type) returns 400.

    The confirm endpoint requires a 'password_reset' typed JWT.

    Args:
        client: Async HTTP client fixture.
    """
    reg = await _register(client, "auth-pr-wrongtype@example.com")
    access_token = reg["access_token"]

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": access_token, "new_password": "newpassword123"},
    )
    assert resp.status_code == 400
    assert "invalid token type" in resp.json()["detail"].lower()


async def test_password_reset_confirm_short_new_password(client: AsyncClient):
    """A new_password shorter than 8 chars returns 422 validation error.

    Args:
        client: Async HTTP client fixture.
    """
    email = "auth-pr-shortpw@example.com"
    reg = await _register(client, email)

    from app.auth import decode_token

    user_id = decode_token(reg["access_token"])["sub"]
    reset_token = create_password_reset_token(user_id, email)

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "short"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/auth/create-organization — edge cases
# ---------------------------------------------------------------------------


async def test_create_organization_user_already_has_org(client: AsyncClient):
    """Trying to create a second org for a user that already has one returns 400.

    Args:
        client: Async HTTP client fixture.
    """
    reg = await _register(client, "auth-org-double@example.com")
    first_token = reg["access_token"]

    # Create the first org successfully
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "First Org for Double Test"},
        headers={"Authorization": f"Bearer {first_token}"},
    )
    assert org_resp.status_code == 200
    second_token = org_resp.json()["access_token"]

    # Attempt to create a second org — should fail
    resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Second Org for Double Test"},
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert resp.status_code == 400
    assert "already belongs" in resp.json()["detail"].lower()


async def test_create_organization_with_valid_pib(client: AsyncClient):
    """Creating an org with a well-formed PIB succeeds and returns tokens.

    The PIB used here passes the ISO 7064 Mod 11,10 checksum.

    Args:
        client: Async HTTP client fixture.
    """
    reg = await _register(client, "auth-org-pib-ok@example.com")

    # PIB 101134702 is a known valid Serbian PIB (passes checksum)
    resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Org With PIB", "pib": "101134702"},
        headers={"Authorization": f"Bearer {reg['access_token']}"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_create_organization_with_invalid_pib_rejected(client: AsyncClient):
    """Creating an org with an invalid PIB checksum returns 422.

    Args:
        client: Async HTTP client fixture.
    """
    reg = await _register(client, "auth-org-pib-bad@example.com")

    resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Org Bad PIB", "pib": "123456789"},
        headers={"Authorization": f"Bearer {reg['access_token']}"},
    )
    assert resp.status_code == 422


async def test_create_organization_pib_non_digits_rejected(client: AsyncClient):
    """A PIB containing non-digit characters returns 422.

    Args:
        client: Async HTTP client fixture.
    """
    reg = await _register(client, "auth-org-pib-alpha@example.com")

    resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Org Alpha PIB", "pib": "ABCDEFGHI"},
        headers={"Authorization": f"Bearer {reg['access_token']}"},
    )
    assert resp.status_code == 422


async def test_create_organization_pib_wrong_length_rejected(client: AsyncClient):
    """A PIB that is not exactly 9 digits returns 422.

    Args:
        client: Async HTTP client fixture.
    """
    reg = await _register(client, "auth-org-pib-len@example.com")

    resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Org Short PIB", "pib": "12345"},
        headers={"Authorization": f"Bearer {reg['access_token']}"},
    )
    assert resp.status_code == 422


async def test_create_organization_pib_leading_zero_rejected(client: AsyncClient):
    """A PIB starting with 0 returns 422 (Serbian PIBs cannot start with 0).

    Args:
        client: Async HTTP client fixture.
    """
    reg = await _register(client, "auth-org-pib-zero@example.com")

    resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Org Zero PIB", "pib": "012345678"},
        headers={"Authorization": f"Bearer {reg['access_token']}"},
    )
    assert resp.status_code == 422


async def test_create_organization_requires_auth(client: AsyncClient):
    """POST /api/v1/auth/create-organization without a token returns 401.

    Args:
        client: Async HTTP client fixture.
    """
    resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "No Auth Org"},
    )
    assert resp.status_code == 401


async def test_create_organization_tokens_include_org_claim(client: AsyncClient):
    """After creating an org the returned access token carries the org claim.

    Args:
        client: Async HTTP client fixture.
    """
    from app.auth import decode_token

    reg = await _register(client, "auth-org-claim@example.com")
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Auth Org Claim Test"},
        headers={"Authorization": f"Bearer {reg['access_token']}"},
    )
    assert org_resp.status_code == 200
    payload = decode_token(org_resp.json()["access_token"])
    assert payload.get("org")  # non-empty org UUID
    assert payload.get("role") == "admin"


# ---------------------------------------------------------------------------
# GET /api/v1/users/me — via token obtained after org creation
# ---------------------------------------------------------------------------


async def test_me_reflects_org_membership(client: AsyncClient):
    """After creating an org, GET /api/v1/users/me shows the org in the profile.

    Args:
        client: Async HTTP client fixture.
    """
    headers = await _register_with_org(client, "auth-me-org@example.com", "Auth Me Org Test")

    resp = await client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_id"] is not None
    assert data["role"] == "admin"
    assert data["email"] == "auth-me-org@example.com"


async def test_me_token_type_is_bearer(client: AsyncClient):
    """GET /api/v1/users/me returns 200 and the response contains no sensitive fields.

    Verifies that password_hash and other sensitive attributes are never
    included in the profile response, using a fully-formed token (user with org).

    Args:
        client: Async HTTP client fixture.
    """
    headers = await _register_with_org(client, "auth-me-safe@example.com", "Auth Safe Fields Org")

    resp = await client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "password" not in data
    assert "password_hash" not in data
    # Basic fields must be present
    assert "id" in data
    assert "email" in data
    assert "role" in data
    assert "created_at" in data


async def test_me_without_token_returns_401(client: AsyncClient):
    """GET /api/v1/users/me without Authorization header returns 401.

    Args:
        client: Async HTTP client fixture.
    """
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_me_with_malformed_token_returns_401(client: AsyncClient):
    """GET /api/v1/users/me with a garbage token returns 401.

    Args:
        client: Async HTTP client fixture.
    """
    resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not.a.real.token"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Login with org — token contains org slug after org creation
# ---------------------------------------------------------------------------


async def test_login_after_org_creation_token_includes_org(client: AsyncClient):
    """Logging in after org creation returns a token with org and role claims.

    Args:
        client: Async HTTP client fixture.
    """
    from app.auth import decode_token

    email = "auth-login-org@example.com"
    await _register_with_org(client, email, "Auth Login Org Test")

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "securepass123"},
    )
    assert login_resp.status_code == 200
    payload = decode_token(login_resp.json()["access_token"])
    assert payload.get("org")
    assert payload.get("role") == "admin"
    assert payload.get("org_slug")


async def test_login_before_org_creation_token_has_empty_org(client: AsyncClient):
    """Logging in before creating an org returns a token with empty org claim.

    Args:
        client: Async HTTP client fixture.
    """
    from app.auth import decode_token

    email = "auth-login-noorg@example.com"
    await _register(client, email)

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "securepass123"},
    )
    assert login_resp.status_code == 200
    payload = decode_token(login_resp.json()["access_token"])
    # No org yet — claim should be empty string or None
    assert not payload.get("org")
