"""Authentication schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters")
    first_name: str | None = None
    last_name: str | None = None
    organization_name: str | None = Field(
        default=None,
        description="Company name (creates new organization)",
    )


class UserResponse(BaseModel):
    """Schema for user response."""

    id: UUID
    email: EmailStr
    first_name: str | None
    last_name: str | None
    organization_id: UUID
    role: str
    email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiry in seconds")


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str
    new_password: str = Field(min_length=8)
