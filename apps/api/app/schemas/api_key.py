"""Pydantic schemas for API key management."""

from datetime import datetime

from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    """Request body for creating a new API key."""

    name: str = Field(..., min_length=1, max_length=100, description="Label for the key")
    expires_at: datetime | None = Field(default=None, description="Optional expiration timestamp")


class APIKeyCreatedResponse(BaseModel):
    """Response returned when an API key is first created.

    The plain_key is shown only once — it cannot be retrieved later.
    """

    id: str
    name: str
    key_prefix: str
    plain_key: str
    is_active: bool
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyResponse(BaseModel):
    """API key details returned in list/detail views.

    Never includes the key hash or full key.
    """

    id: str
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True, "coerce_numbers_to_str": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Override to convert UUID id to string before validation."""
        if hasattr(obj, "id") and not isinstance(obj.id, str):
            # Create a dict copy with str id for validation
            data = {
                "id": str(obj.id),
                "name": obj.name,
                "key_prefix": obj.key_prefix,
                "is_active": obj.is_active,
                "last_used_at": obj.last_used_at,
                "expires_at": obj.expires_at,
                "created_at": obj.created_at,
            }
            return super().model_validate(data, **kwargs)
        return super().model_validate(obj, **kwargs)


class APIKeyListResponse(BaseModel):
    """Paginated list of API keys."""

    data: list[APIKeyResponse]
    pagination: dict
