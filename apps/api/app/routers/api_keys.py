"""API key management router — create, list, revoke keys."""

import math
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password
from app.database import get_db
from app.dependencies import API_KEY_PREFIX, get_current_user, require_role
from app.models.api_key import APIKey
from app.models.user import User
from app.schemas.api_key import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyListResponse,
    APIKeyResponse,
)

router = APIRouter()


@router.post("/", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("manager")),
) -> dict:
    """Generate a new API key for the organization.

    The plain key is returned only in this response — it cannot
    be retrieved later. Store it securely.

    Args:
        body: Key creation request with name and optional expiry.
        db: Database session.
        user: Authenticated user (must be manager+).

    Returns:
        Created key details including the plain key (shown once).
    """
    # Generate the key: sk_live_ + 32 bytes of URL-safe randomness
    key_body = secrets.token_urlsafe(32)
    plain_key = f"{API_KEY_PREFIX}{key_body}"
    key_prefix = key_body[:8]

    api_key = APIKey(
        organization_id=user.organization_id,
        user_id=user.id,
        key_hash=hash_password(plain_key),
        key_prefix=key_prefix,
        name=body.name,
        expires_at=body.expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "plain_key": plain_key,
        "is_active": api_key.is_active,
        "expires_at": api_key.expires_at,
        "created_at": api_key.created_at,
    }


@router.get("/", response_model=APIKeyListResponse)
async def list_api_keys(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """List API keys for the current organization.

    Keys are masked — only the prefix is shown, never the hash.

    Args:
        page: Page number (1-indexed).
        per_page: Items per page.
        db: Database session.
        user: Authenticated user.

    Returns:
        Paginated list of API keys.
    """
    conditions = [APIKey.organization_id == user.organization_id]

    count_result = await db.execute(select(func.count(APIKey.id)).where(and_(*conditions)))
    total = count_result.scalar() or 0
    total_pages = math.ceil(total / per_page) if total > 0 else 0

    offset = (page - 1) * per_page
    result = await db.execute(
        select(APIKey)
        .where(and_(*conditions))
        .order_by(APIKey.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    keys = list(result.scalars().all())

    return {
        "data": [APIKeyResponse.model_validate(k) for k in keys],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
    }


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("manager")),
) -> None:
    """Revoke an API key (soft delete).

    Sets is_active to false. The key can no longer be used for authentication.

    Args:
        key_id: API key UUID.
        db: Database session.
        user: Authenticated user (must be manager+).

    Raises:
        HTTPException: 404 if key not found or not in user's org.
    """
    result = await db.execute(
        select(APIKey).where(
            and_(
                APIKey.id == key_id,
                APIKey.organization_id == user.organization_id,
            )
        )
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    await db.commit()
