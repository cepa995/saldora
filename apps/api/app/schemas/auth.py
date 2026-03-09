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


class UserResponse(BaseModel):
    """Schema for user response."""

    id: UUID
    email: EmailStr
    first_name: str | None
    last_name: str | None
    organization_id: UUID | None
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


class RefreshRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str


class CreateOrganizationRequest(BaseModel):
    """Schema for creating an organization after registration."""

    name: str = Field(min_length=1, max_length=255)
    pib: str | None = Field(default=None, max_length=20)


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str
    new_password: str = Field(min_length=8)
