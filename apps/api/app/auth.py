"""Authentication utilities - JWT Tokens and password hashing"""

from datetime import UTC, datetime, timedelta

from jose import jwt
from passlib.hash import argon2

from app.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2

    Arguments:
        password (str): password to be hashed

    Returns:
        hashed password (str)
    """
    return argon2.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Arguments:
        plain_password (str): password which user inserted
        hashed_password (str): hashed password from the DB

    Returns:
        True if the passwords match, False otherwise
    """
    return argon2.verify(plain_password, hashed_password)


def create_access_token(
    user_id: str,
    organization_id: str | None,
    email: str = "",
    first_name: str | None = None,
    last_name: str | None = None,
    role: str = "viewer",
    org_slug: str | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        user_id: User ID from the DB.
        organization_id: Organization ID (None if user has no org yet).
        email: User email.
        first_name: User first name.
        last_name: User last name.
        role: User role in organization.
        org_slug: Organization URL slug.

    Returns:
        Encoded JWT token.
    """
    expires = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload = {
        "sub": user_id,  # Subject (who the token is for)
        "org": organization_id or "",  # Organization (multi-tenancy)
        "org_slug": org_slug or "",  # Organization slug (URL routing)
        "email": email,
        "first_name": first_name or "",
        "last_name": last_name or "",
        "role": role,
        "exp": expires,  # Expiration time
        "type": "access",
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """
    Create a JWT refresh token (longer-lived)

    Arguments:
        user_id (str): who the token is for

    Returns:
        JWT refresh token (str)
    """
    expires = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)

    payload = {
        "sub": user_id,  # who the token is for
        "exp": expires,  # Expiration time
        "type": "refresh",
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_password_reset_token(user_id: str, email: str) -> str:
    """Create a short-lived JWT for password reset.

    Args:
        user_id: User's database ID.
        email: User's email (embedded for auditing).

    Returns:
        Encoded JWT token valid for 1 hour.
    """
    expires = datetime.now(UTC) + timedelta(hours=1)

    payload = {
        "sub": user_id,
        "email": email,
        "exp": expires,
        "type": "password_reset",
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str:
    """
    Decode and validate a JKWT token.

    Raises JWT Error ron failure

    Arguments:
        token (str): JWT token to be decoded

    Returns:
        decoded JWT token (str)
    """
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
