"""MiniMax integration schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MiniMaxPushRequest(BaseModel):
    """Request to push invoices to MiniMax API."""

    invoice_ids: list[UUID] = Field(min_length=1)
    create_customers: bool = Field(
        default=True,
        description="Create customers in MiniMax if not found by PIB",
    )
    attach_documents: bool = Field(
        default=False,
        description="Attach original PDF documents to MiniMax invoices",
    )


class MiniMaxPushResult(BaseModel):
    """Result for a single invoice push."""

    invoice_id: UUID
    invoice_number: str | None = None
    minimax_id: int | None = None
    status: str = Field(description="'success' or 'error'")
    error: str | None = None


class MiniMaxPushResponse(BaseModel):
    """Response for batch push operation."""

    results: list[MiniMaxPushResult]
    total: int
    success_count: int
    error_count: int


class MiniMaxConfigCreate(BaseModel):
    """Create MiniMax configuration for an organization."""

    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    minimax_org_id: int = Field(gt=0, description="MiniMax organization ID")


class MiniMaxConfigUpdate(BaseModel):
    """Update MiniMax configuration."""

    client_id: str | None = None
    client_secret: str | None = None
    username: str | None = None
    password: str | None = None
    minimax_org_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class MiniMaxConfigResponse(BaseModel):
    """MiniMax configuration response (credentials masked)."""

    id: UUID
    organization_id: UUID
    client_id: str
    username: str
    minimax_org_id: int
    is_active: bool
    last_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
