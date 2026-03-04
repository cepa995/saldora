"""Automation rules CRUD router."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.automation_rule import AutomationRule, RuleExecution
from app.models.user import User
from app.schemas.automation_rule import (
    AutomationRuleCreate,
    AutomationRuleListResponse,
    AutomationRuleResponse,
    AutomationRuleUpdate,
    RuleExecutionResponse,
)
from app.services.rules_engine import get_rule_templates

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/templates")
async def list_templates(
    user: User = Depends(get_current_user),
) -> list[dict]:
    """Get pre-built rule templates for common Serbian accounting scenarios.

    Returns:
        List of template dicts with name, description, conditions, and actions.
    """
    return get_rule_templates()


@router.post("/", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    body: AutomationRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AutomationRule:
    """Create an automation rule for the current organization.

    Args:
        body: Rule creation schema.

    Returns:
        Created AutomationRule.
    """
    rule = AutomationRule(
        organization_id=user.organization_id,
        name=body.name,
        description=body.description,
        rule_type=body.rule_type,
        priority=body.priority,
        conditions=body.conditions,
        actions=body.actions,
        is_active=body.is_active,
        created_by=user.id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/", response_model=AutomationRuleListResponse)
async def list_rules(
    rule_type: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """List automation rules for the current organization.

    Args:
        rule_type: Optional filter by rule type.
        is_active: Optional filter by active status.

    Returns:
        Paginated list of rules.
    """
    conditions = [AutomationRule.organization_id == user.organization_id]
    if rule_type is not None:
        conditions.append(AutomationRule.rule_type == rule_type)
    if is_active is not None:
        conditions.append(AutomationRule.is_active == is_active)

    query = (
        select(AutomationRule)
        .where(and_(*conditions))
        .order_by(AutomationRule.priority.asc(), AutomationRule.created_at.asc())
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    count_query = select(func.count(AutomationRule.id)).where(and_(*conditions))
    count_result = await db.execute(count_query)
    count = count_result.scalar() or 0

    return {"items": items, "count": count}


@router.get("/{rule_id}", response_model=AutomationRuleResponse)
async def get_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AutomationRule:
    """Get a single automation rule by ID.

    Args:
        rule_id: Rule UUID.

    Returns:
        AutomationRule if found.

    Raises:
        HTTPException: 404 if rule not found or not in user's org.
    """
    result = await db.execute(
        select(AutomationRule).where(
            and_(
                AutomationRule.id == rule_id,
                AutomationRule.organization_id == user.organization_id,
            )
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Pravilo nije pronađeno")
    return rule


@router.patch("/{rule_id}", response_model=AutomationRuleResponse)
async def update_rule(
    rule_id: UUID,
    body: AutomationRuleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AutomationRule:
    """Update an automation rule.

    Args:
        rule_id: Rule UUID.
        body: Partial update schema.

    Returns:
        Updated AutomationRule.
    """
    result = await db.execute(
        select(AutomationRule).where(
            and_(
                AutomationRule.id == rule_id,
                AutomationRule.organization_id == user.organization_id,
            )
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Pravilo nije pronađeno")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)
    rule.updated_by = user.id

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Delete an automation rule.

    Args:
        rule_id: Rule UUID.

    Raises:
        HTTPException: 404 if rule not found or not in user's org.
    """
    result = await db.execute(
        select(AutomationRule).where(
            and_(
                AutomationRule.id == rule_id,
                AutomationRule.organization_id == user.organization_id,
            )
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Pravilo nije pronađeno")

    await db.delete(rule)
    await db.commit()


@router.get("/{rule_id}/executions", response_model=list[RuleExecutionResponse])
async def list_rule_executions(
    rule_id: UUID,
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RuleExecution]:
    """Get execution history for a rule.

    Args:
        rule_id: Rule UUID.
        limit: Max results to return.

    Returns:
        List of RuleExecution entries.
    """
    # Verify rule belongs to user's org
    rule_result = await db.execute(
        select(AutomationRule.id).where(
            and_(
                AutomationRule.id == rule_id,
                AutomationRule.organization_id == user.organization_id,
            )
        )
    )
    if rule_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Pravilo nije pronađeno")

    result = await db.execute(
        select(RuleExecution)
        .where(RuleExecution.rule_id == rule_id)
        .order_by(RuleExecution.executed_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
