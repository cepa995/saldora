"""Automation rule schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ---- Condition schemas ----


class ConditionRule(BaseModel):
    """A single field condition (leaf node in condition tree)."""

    field: str = Field(description="Dot-path to invoice field (e.g. 'seller.pib')")
    operator: Literal[
        "equals",
        "not_equals",
        "contains",
        "starts_with",
        "ends_with",
        "regex",
        "greater_than",
        "less_than",
        "between",
        "in",
        "not_in",
        "is_null",
        "is_not_null",
    ]
    value: Any = Field(default=None, description="Comparison value")


class ConditionGroup(BaseModel):
    """A logical group of conditions (AND/OR node in condition tree).

    Supports nesting: rules can contain ConditionRule or ConditionGroup dicts.
    """

    operator: Literal["AND", "OR"]
    rules: list[dict] = Field(description="List of ConditionRule or nested ConditionGroup dicts")


# ---- Action schemas ----


class RuleAction(BaseModel):
    """An action to execute when a rule matches."""

    type: Literal[
        "SET_KONTO",
        "SET_VAT_TREATMENT",
        "FLAG_REVIEW",
        "AUTO_APPROVE",
        "SET_CUSTOM_FIELD",
    ]
    target: str | None = Field(default=None, description="Target field (e.g. 'expense')")
    value: Any = Field(default=None, description="Value to set")
    description: str | None = None
    reason: str | None = None


# ---- CRUD schemas ----


class AutomationRuleCreate(BaseModel):
    """Schema for creating an automation rule."""

    name: str = Field(max_length=255)
    description: str | None = None
    rule_type: Literal[
        "KONTO_ASSIGNMENT",
        "VAT_TREATMENT",
        "AUTO_APPROVE",
        "FLAG_FOR_REVIEW",
        "DOCUMENT_TYPE",
        "CUSTOM_FIELD",
    ]
    priority: int = Field(default=50, ge=1, le=1000)
    conditions: dict = Field(description="ConditionGroup JSON")
    actions: list[dict] = Field(description="List of RuleAction dicts")
    is_active: bool = True


class AutomationRuleUpdate(BaseModel):
    """Schema for updating an automation rule (all fields optional)."""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    rule_type: (
        Literal[
            "KONTO_ASSIGNMENT",
            "VAT_TREATMENT",
            "AUTO_APPROVE",
            "FLAG_FOR_REVIEW",
            "DOCUMENT_TYPE",
            "CUSTOM_FIELD",
        ]
        | None
    ) = None
    priority: int | None = Field(default=None, ge=1, le=1000)
    conditions: dict | None = None
    actions: list[dict] | None = None
    is_active: bool | None = None


class AutomationRuleResponse(BaseModel):
    """Full automation rule response."""

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    rule_type: str
    priority: int
    conditions: dict
    actions: list
    is_active: bool
    created_by: UUID
    updated_by: UUID | None
    execution_count: int
    last_executed_at: datetime | None
    # Client scoping: empty list = global (fires for all invoices). Non-empty =
    # scoped — fires only for invoices whose client_id is in this list.
    client_ids: list[UUID] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AutomationRuleListResponse(BaseModel):
    """Paginated list of automation rules."""

    items: list[AutomationRuleResponse]
    count: int


class RuleExecutionResponse(BaseModel):
    """Rule execution audit trail entry."""

    id: UUID
    rule_id: UUID
    invoice_id: UUID
    accounting_intent_id: UUID | None
    conditions_matched: dict
    actions_applied: list
    executed_at: datetime
    execution_time_ms: int | None

    model_config = {"from_attributes": True}
