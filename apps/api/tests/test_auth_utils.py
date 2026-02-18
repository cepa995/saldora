"""
Unit tests for auth utility functions.

These tests verify passowrd hashing and JWT token logic in isolation
No database, no HTTP - just function calls
"""

from datetime import UTC, datetime

from jose import jwt

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import get_settings

settings = get_settings()

#######################################################
#                  PASSWORD HASHING                   #
#######################################################


def test_hash_password_returns_argon2_hash():
    """Argon2 hashes always start with `$argon2`."""
    hashed_password = hash_password("test_password")
    assert hashed_password.startswith("$argon2")


def test_hash_password_produces_unique_hashes():
    """
    Same password -> different hashes (due to the random salt).
    This is critical: if hashes were identical, na attacked who
    steals the DB could spot users with the same password at a glance
    """
    hash1 = hash_password("testpassword123")
    hash2 = hash_password("testpassword123")
    assert hash1 != hash2


def test_verify_password_correct():
    """Correct password verifies successfully."""
    hashed = hash_password("testpass123")
    assert verify_password("testpass123", hashed) is True


def test_verify_password_wrong():
    """Wrong password is rejected."""
    hashed = hash_password("testpass123")
    assert verify_password("wrongpass", hashed) is False


#######################################################
#                     JWT TOKEN                       #
#######################################################


def test_create_access_token_contains_correct_claims():
    """Access token payload must include sub, org, type, and exp."""
    token = create_access_token("user-123", "org-456")
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

    assert payload["sub"] == "user-123"
    assert payload["org"] == "org-456"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_refresh_token_has_no_org_claim():
    """
    Refresh tokens carry only the user ID, not the org.
    Why? Refresh tokens are long-lived. If a user switches orgs,
    the new access token should pick up the current org, not a stale one.
    """
    token = create_refresh_token("user-123")
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

    assert payload["sub"] == "user-123"
    assert payload["type"] == "refresh"
    assert "org" not in payload


def test_decode_token_roundtrip():
    """Encode → decode should return the same claims."""
    token = create_access_token("user-123", "org-456")
    payload = decode_token(token)

    assert payload["sub"] == "user-123"
    assert payload["org"] == "org-456"


def test_access_token_has_future_expiration():
    """Token expiration must be in the future."""
    token = create_access_token("user-123", "org-456")
    payload = decode_token(token)
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)

    assert exp > datetime.now(UTC)
