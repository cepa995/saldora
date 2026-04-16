"""Tests for email verification flow (issue #70)."""

from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import create_email_verification_token, decode_token


async def _register(
    client: AsyncClient,
    email: str = "verify-test@example.com",
) -> dict:
    """Register a user and return the full response + headers."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Verify",
            "last_name": "Tester",
        },
    )
    token = resp.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "token": token,
        "response": resp.json(),
    }


def _get_user_id(token: str) -> str:
    """Extract user_id from JWT."""
    return decode_token(token)["sub"]


# ---------------------------------------------------------------------------
# Registration sends verification email
# ---------------------------------------------------------------------------


async def test_register_sends_verification_email(client: AsyncClient, test_engine):
    """Organization creation triggers a verification email."""
    # Register first (no email sent at this step)
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "verify-send@test.com",
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]

    # Create org — this is where verification email is sent
    with patch("app.routers.auth.send_verification_email") as mock_send:
        org_resp = await client.post(
            "/api/v1/auth/create-organization",
            json={"name": "Verify Test Org"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert org_resp.status_code == 200
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] == "verify-send@test.com"
        assert "verify-email?token=" in call_args[0][2]


async def test_new_user_email_not_verified(client: AsyncClient, test_engine):
    """Newly registered user has email_verified=false in JWT."""
    reg = await _register(client, "verify-false@test.com")
    payload = decode_token(reg["token"])
    assert payload["email_verified"] is False


# ---------------------------------------------------------------------------
# Verify endpoint
# ---------------------------------------------------------------------------


async def test_verify_email_success(client: AsyncClient, test_engine):
    """Valid verification token sets email_verified=true."""
    reg = await _register(client, "verify-ok@test.com")
    user_id = _get_user_id(reg["token"])

    token = create_email_verification_token(user_id, "verify-ok@test.com")
    resp = await client.get(f"/api/v1/auth/verify?token={token}")
    assert resp.status_code == 200
    assert "uspešno" in resp.json()["message"]

    # Verify DB state
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        row = await session.execute(
            text("SELECT email_verified FROM users WHERE id = :uid"),
            {"uid": user_id},
        )
        assert row.scalar() is True


async def test_verify_email_already_verified(client: AsyncClient, test_engine):
    """Verifying an already-verified email returns appropriate message."""
    reg = await _register(client, "verify-already@test.com")
    user_id = _get_user_id(reg["token"])

    token = create_email_verification_token(user_id, "verify-already@test.com")

    # Verify once
    await client.get(f"/api/v1/auth/verify?token={token}")

    # Verify again with new token
    token2 = create_email_verification_token(user_id, "verify-already@test.com")
    resp = await client.get(f"/api/v1/auth/verify?token={token2}")
    assert resp.status_code == 200
    assert "već" in resp.json()["message"]


async def test_verify_email_invalid_token(client: AsyncClient, test_engine):
    """Invalid token returns 400."""
    resp = await client.get("/api/v1/auth/verify?token=totally.invalid.token")
    assert resp.status_code == 400


async def test_verify_email_wrong_type(client: AsyncClient, test_engine):
    """Password reset token cannot be used for email verification."""
    from app.auth import create_password_reset_token

    reg = await _register(client, "verify-wrongtype@test.com")
    user_id = _get_user_id(reg["token"])

    token = create_password_reset_token(user_id, "verify-wrongtype@test.com")
    resp = await client.get(f"/api/v1/auth/verify?token={token}")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Resend verification
# ---------------------------------------------------------------------------


async def test_resend_verification(client: AsyncClient, test_engine):
    """Resend verification sends a new email."""
    reg = await _register(client, "verify-resend@test.com")

    with patch("app.routers.auth.send_verification_email") as mock_send:
        resp = await client.post(
            "/api/v1/auth/resend-verification",
            headers=reg["headers"],
        )
        assert resp.status_code == 200
        assert "ponovo" in resp.json()["message"]
        mock_send.assert_called_once()


async def test_resend_when_already_verified(client: AsyncClient, test_engine):
    """Resend for already-verified user returns success without sending."""
    reg = await _register(client, "verify-resend-done@test.com")
    user_id = _get_user_id(reg["token"])

    # Verify first
    token = create_email_verification_token(user_id, "verify-resend-done@test.com")
    await client.get(f"/api/v1/auth/verify?token={token}")

    with patch("app.routers.auth.send_verification_email") as mock_send:
        resp = await client.post(
            "/api/v1/auth/resend-verification",
            headers=reg["headers"],
        )
        assert resp.status_code == 200
        assert "već" in resp.json()["message"]
        mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# Export restriction for unverified users
# ---------------------------------------------------------------------------


async def test_unverified_user_blocked_from_export(client: AsyncClient, test_engine):
    """Unverified user cannot use export endpoints."""
    reg = await _register(client, "verify-export@test.com")

    # Create org first (export requires org)
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Export Test Org"},
        headers=reg["headers"],
    )
    new_token = org_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {new_token}"}

    resp = await client.post(
        "/api/v1/export",
        json={"invoice_ids": [], "format": "xlsx"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "email_not_verified"


async def test_verified_user_can_export(client: AsyncClient, test_engine):
    """Verified user can access export (blocked by other rules, not email)."""
    reg = await _register(client, "verify-export-ok@test.com")
    user_id = _get_user_id(reg["token"])

    # Verify email
    token = create_email_verification_token(user_id, "verify-export-ok@test.com")
    await client.get(f"/api/v1/auth/verify?token={token}")

    # Create org
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Export OK Org"},
        headers=reg["headers"],
    )
    new_token = org_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {new_token}"}

    # Export with empty list — should get 404 (no invoices), not 403
    resp = await client.post(
        "/api/v1/export",
        json={"invoice_ids": [], "format": "xlsx"},
        headers=headers,
    )
    # Any status except 403 means the email gate passed
    assert resp.status_code != 403
