"""Security utilities: rate limiting, account lockout, token blacklisting."""

import logging

import redis.asyncio as aioredis
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# Rate limiting (slowapi)
# ---------------------------------------------------------------------------

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    storage_uri=settings.redis_url,
    in_memory_fallback_enabled=True,
)

# ---------------------------------------------------------------------------
# Shared Redis connection pool for security operations
# ---------------------------------------------------------------------------

_redis_pool: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    """Get or create a shared Redis connection pool.

    Returns:
        Reusable async Redis client.
    """
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis_pool


# ---------------------------------------------------------------------------
# Account lockout
# ---------------------------------------------------------------------------

_LOCKOUT_PREFIX = "lockout:"
_LOCKOUT_MAX_ATTEMPTS = 5
_LOCKOUT_WINDOW_SECONDS = 900  # 15 minutes


async def record_failed_login(email: str) -> None:
    """Increment failed login counter for an email.

    Args:
        email: The email address that failed authentication.
    """
    try:
        r = _get_redis()
        key = f"{_LOCKOUT_PREFIX}{email.lower()}"
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, _LOCKOUT_WINDOW_SECONDS)
        await pipe.execute()
    except Exception:
        logger.warning("Redis unavailable for login lockout tracking")


async def clear_failed_logins(email: str) -> None:
    """Clear failed login counter after successful authentication.

    Args:
        email: The email address that authenticated successfully.
    """
    try:
        r = _get_redis()
        key = f"{_LOCKOUT_PREFIX}{email.lower()}"
        await r.delete(key)
    except Exception:
        logger.warning("Redis unavailable for clearing login lockout")


async def is_account_locked(email: str) -> bool:
    """Check if an account is locked due to too many failed attempts.

    Fails open (returns False) if Redis is unavailable.

    Args:
        email: The email address to check.

    Returns:
        True if the account is locked.
    """
    try:
        r = _get_redis()
        key = f"{_LOCKOUT_PREFIX}{email.lower()}"
        attempts = await r.get(key)
        if attempts and int(attempts) >= _LOCKOUT_MAX_ATTEMPTS:
            return True
    except Exception:
        logger.warning("Redis unavailable for lockout check — allowing login")
    return False


# ---------------------------------------------------------------------------
# Token blacklisting (for logout)
# ---------------------------------------------------------------------------

_BLACKLIST_PREFIX = "token_blacklist:"


async def blacklist_token(jti: str, ttl_seconds: int) -> None:
    """Add a token to the blacklist.

    Args:
        jti: The JWT ID (token identifier).
        ttl_seconds: How long to keep in blacklist (match token expiry).
    """
    try:
        r = _get_redis()
        key = f"{_BLACKLIST_PREFIX}{jti}"
        await r.setex(key, ttl_seconds, "1")
    except Exception:
        logger.warning("Redis unavailable for token blacklisting")


async def is_token_blacklisted(jti: str) -> bool:
    """Check if a token has been blacklisted.

    Fails open (returns False) if Redis is unavailable.

    Args:
        jti: The JWT ID to check.

    Returns:
        True if the token is blacklisted.
    """
    try:
        r = _get_redis()
        key = f"{_BLACKLIST_PREFIX}{jti}"
        return await r.exists(key) > 0
    except Exception:
        logger.warning("Redis unavailable for blacklist check — allowing token")
        return False


# ---------------------------------------------------------------------------
# PII masking for logs
# ---------------------------------------------------------------------------

_PII_FIELDS = {"password", "password_hash", "client_secret", "api_key", "token", "refresh_token"}


def mask_pii(data: dict) -> dict:
    """Mask sensitive fields in a dictionary for safe logging.

    Args:
        data: Dictionary that may contain PII.

    Returns:
        Copy with sensitive values replaced by '***'.
    """
    if not isinstance(data, dict):
        return data
    masked = {}
    for key, value in data.items():
        if key.lower() in _PII_FIELDS:
            masked[key] = "***"
        elif isinstance(value, dict):
            masked[key] = mask_pii(value)
        else:
            masked[key] = value
    return masked


def mask_email(email: str) -> str:
    """Mask an email address for logging (show first 2 chars + domain).

    Args:
        email: Full email address.

    Returns:
        Masked email like 'st***@gmail.com'.
    """
    if not email or "@" not in email:
        return "***"
    local, domain = email.rsplit("@", 1)
    return f"{local[:2]}***@{domain}"


def mask_pib(pib: str) -> str:
    """Mask a PIB for logging (show first 3 and last 2 digits).

    Args:
        pib: Full PIB string.

    Returns:
        Masked PIB like '123***89'.
    """
    if not pib or len(pib) < 5:
        return "***"
    return f"{pib[:3]}***{pib[-2:]}"
