"""Pydantic schemas for user profile management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserProfileResponse(BaseModel):
    """Response schema for user profile."""

    id: UUID = Field(description="User UUID")
    email: EmailStr = Field(description="User email address")
    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")
    role: str = Field(description="Role within the organization")
    email_verified: bool = Field(description="Whether email has been verified")
    organization_id: UUID | None = Field(
        default=None, description="Organization UUID (null until org is created)"
    )
    subscription_status: str | None = Field(
        default=None,
        description=(
            "Subscription status of the user's organization "
            '("active"/"trial"/"pending"/"canceled"). Null if user has no org yet.'
        ),
    )
    created_at: datetime = Field(description="Account creation timestamp")

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    """Request schema for updating user profile."""

    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="First name",
    )
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Last name",
    )


class PasswordChangeRequest(BaseModel):
    """Request schema for changing password."""

    current_password: str = Field(description="Current password for verification")
    new_password: str = Field(
        min_length=8,
        description="New password (minimum 8 characters)",
    )
