"""Automation rules engine for invoice processing.

Evaluates organization-specific rules against invoice data during
verification (SRS Section 4.11). Supports condition evaluation with
13 operators, nested AND/OR logic, action application, conflict
resolution, and execution logging.
"""

import logging
import re
import time
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation_rule import AutomationRule, RuleExecution
from app.models.invoice import Invoice

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def evaluate_rules(
    db: AsyncSession,
    invoice: Invoice,
    organization_id: UUID,
    document_type: str,
    suggested_konta: dict,
    vat_treatment: str,
    confidence: Decimal,
) -> tuple[dict, list[dict]]:
    """Evaluate all active rules for an invoice.

    Fetches active rules for the organization, evaluates each in priority
    order, applies matching actions, resolves conflicts, and logs executions.

    Args:
        db: Database session.
        invoice: Invoice being verified.
        organization_id: Organization UUID.
        document_type: Classified document type from step 1.
        suggested_konta: Suggested konta dict from step 4.
        vat_treatment: VAT treatment from step 3.
        confidence: Overall pipeline confidence.

    Returns:
        Tuple of (modifications dict, applied_rules list).
        modifications keys: suggested_konta, vat_treatment, is_deductible,
            requires_review, review_reasons, auto_approve, custom_fields.
        applied_rules: list of {rule_id, rule_name, actions_applied} dicts.
    """
    rules = await _get_active_rules(db, organization_id)
    if not rules:
        return {}, []

    context = await _build_context(db, invoice, organization_id, document_type, confidence)

    modifications: dict[str, Any] = {}
    applied_rules: list[dict] = []

    for rule in rules:
        start = time.perf_counter()
        matched = _evaluate_condition(rule.conditions, context)

        if matched:
            _apply_actions(rule.actions, modifications, rule)
            exec_time_ms = int((time.perf_counter() - start) * 1000)

            applied_rules.append(
                {
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "rule_type": rule.rule_type,
                    "actions_applied": rule.actions,
                }
            )

            await _log_execution(db, rule, invoice, rule.actions, exec_time_ms)

            logger.info(
                "Rule '%s' (id=%s) matched invoice %s",
                rule.name,
                rule.id,
                invoice.id,
            )

    # Resolve conflicts between applied rules
    if applied_rules:
        _resolve_conflicts(applied_rules, modifications)

    return modifications, applied_rules


# ---------------------------------------------------------------------------
# Rule fetching
# ---------------------------------------------------------------------------


async def _get_active_rules(db: AsyncSession, organization_id: UUID) -> list[AutomationRule]:
    """Fetch active rules for an organization, ordered by priority.

    Args:
        db: Database session.
        organization_id: Organization UUID.

    Returns:
        List of active AutomationRule instances sorted by priority ASC,
        then created_at ASC.
    """
    result = await db.execute(
        select(AutomationRule)
        .where(
            and_(
                AutomationRule.organization_id == organization_id,
                AutomationRule.is_active.is_(True),
            )
        )
        .order_by(AutomationRule.priority.asc(), AutomationRule.created_at.asc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Context building
# ---------------------------------------------------------------------------


async def _build_context(
    db: AsyncSession,
    invoice: Invoice,
    organization_id: UUID,
    document_type: str,
    confidence: Decimal,
) -> dict[str, Any]:
    """Build evaluation context from invoice and computed fields.

    Args:
        db: Database session.
        invoice: Invoice model instance.
        organization_id: Organization UUID.
        document_type: Classified document type.
        confidence: Pipeline confidence score.

    Returns:
        Context dict with all evaluatable fields.
    """
    # Extract seller/buyer info
    seller = invoice.seller if isinstance(invoice.seller, dict) else {}
    buyer = invoice.buyer if isinstance(invoice.buyer, dict) else {}

    # Extract line items
    line_items = invoice.line_items if isinstance(invoice.line_items, list) else []

    # Compute supplier history
    supplier_pib = seller.get("pib")
    supplier_invoice_count = 0
    is_first_from_supplier = True

    if supplier_pib:
        count_result = await db.execute(
            select(func.count(Invoice.id)).where(
                and_(
                    Invoice.organization_id == organization_id,
                    Invoice.id != invoice.id,
                    Invoice.seller["pib"].as_string() == supplier_pib,
                )
            )
        )
        supplier_invoice_count = count_result.scalar() or 0
        is_first_from_supplier = supplier_invoice_count == 0

    return {
        "seller": seller,
        "buyer": buyer,
        "total_amount": invoice.total_amount,
        "subtotal": invoice.subtotal,
        "tax_rate": invoice.tax_rate,
        "tax_amount": invoice.tax_amount,
        "currency": invoice.currency,
        "invoice_date": invoice.invoice_date,
        "invoice_number": invoice.invoice_number,
        "line_items": line_items,
        "document_type": document_type,
        "is_first_from_supplier": is_first_from_supplier,
        "supplier_invoice_count": supplier_invoice_count,
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------


def _evaluate_condition(condition: dict, context: dict) -> bool:
    """Recursively evaluate a condition tree against context.

    Args:
        condition: ConditionGroup or ConditionRule dict.
        context: Evaluation context dict.

    Returns:
        True if the condition matches.
    """
    if not condition:
        return False

    # Logical group (AND/OR)
    if "rules" in condition:
        operator = condition.get("operator", "AND")
        rules = condition.get("rules", [])

        if not rules:
            return True

        if operator == "OR":
            return any(_evaluate_condition(r, context) for r in rules)
        else:  # AND
            return all(_evaluate_condition(r, context) for r in rules)

    # Leaf condition
    field_path = condition.get("field")
    op = condition.get("operator")
    value = condition.get("value")

    if not field_path or not op:
        return False

    field_value = _resolve_field(context, field_path)

    # For array fields (line_items[].description), check any-match
    if isinstance(field_value, list):
        return any(_evaluate_operator(v, op, value) for v in field_value)

    return _evaluate_operator(field_value, op, value)


def _resolve_field(context: dict, field_path: str) -> Any:
    """Resolve a dot-path field reference from context.

    Supports:
    - Simple: "total_amount" → context["total_amount"]
    - Nested: "seller.pib" → context["seller"]["pib"]
    - Array: "line_items[].description" → [item["description"] for item in line_items]

    Args:
        context: Evaluation context dict.
        field_path: Dot-separated field path.

    Returns:
        Field value, list of values for array fields, or None if not found.
    """
    # Handle array accessor (line_items[].field)
    if "[]." in field_path:
        array_part, field_part = field_path.split("[].", 1)
        array_data = context.get(array_part, [])
        if not isinstance(array_data, list):
            return None
        values = []
        for item in array_data:
            if isinstance(item, dict):
                val = item.get(field_part)
                if val is not None:
                    values.append(val)
        return values if values else None

    # Handle dot notation
    parts = field_path.split(".")
    current = context
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def _evaluate_operator(field_value: Any, operator: str, condition_value: Any) -> bool:
    """Evaluate a single operator against a field value.

    Args:
        field_value: Actual value from invoice context.
        operator: Comparison operator string.
        condition_value: Expected value from rule condition.

    Returns:
        True if the comparison matches.
    """
    if operator == "is_null":
        return field_value is None
    if operator == "is_not_null":
        return field_value is not None

    if field_value is None:
        return False

    if operator == "equals":
        return _coerce_compare(field_value, condition_value) == 0
    if operator == "not_equals":
        return _coerce_compare(field_value, condition_value) != 0
    if operator == "contains":
        return str(condition_value).lower() in str(field_value).lower()
    if operator == "starts_with":
        return str(field_value).lower().startswith(str(condition_value).lower())
    if operator == "ends_with":
        return str(field_value).lower().endswith(str(condition_value).lower())
    if operator == "regex":
        try:
            return bool(re.search(str(condition_value), str(field_value), re.IGNORECASE))
        except re.error:
            logger.warning("Invalid regex in rule condition: %s", condition_value)
            return False
    if operator == "greater_than":
        cmp = _coerce_compare(field_value, condition_value)
        return cmp is not None and cmp > 0
    if operator == "less_than":
        cmp = _coerce_compare(field_value, condition_value)
        return cmp is not None and cmp < 0
    if operator == "between":
        if not isinstance(condition_value, list) or len(condition_value) != 2:
            return False
        low = _coerce_compare(field_value, condition_value[0])
        high = _coerce_compare(field_value, condition_value[1])
        return low is not None and high is not None and low >= 0 and high <= 0
    if operator == "in":
        if not isinstance(condition_value, list):
            return False
        return any(_coerce_compare(field_value, v) == 0 for v in condition_value)
    if operator == "not_in":
        if not isinstance(condition_value, list):
            return True
        return all(_coerce_compare(field_value, v) != 0 for v in condition_value)

    logger.warning("Unknown operator: %s", operator)
    return False


def _coerce_compare(a: Any, b: Any) -> int | None:
    """Compare two values with type coercion.

    Attempts Decimal comparison for numeric values, falls back to
    case-insensitive string comparison.

    Args:
        a: Left-hand value.
        b: Right-hand value.

    Returns:
        -1, 0, or 1 for <, =, > comparison. None if incomparable.
    """
    # Try numeric comparison
    try:
        da = Decimal(str(a))
        db = Decimal(str(b))
        if da < db:
            return -1
        if da > db:
            return 1
        return 0
    except (InvalidOperation, ValueError, TypeError):
        pass

    # Try boolean comparison
    if isinstance(a, bool) or isinstance(b, bool):
        ba = bool(a) if not isinstance(a, bool) else a
        bb = bool(b) if not isinstance(b, bool) else b
        if ba == bb:
            return 0
        return 1 if ba else -1

    # String comparison (case-insensitive)
    sa = str(a).lower()
    sb = str(b).lower()
    if sa < sb:
        return -1
    if sa > sb:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Action application
# ---------------------------------------------------------------------------


def _apply_actions(actions: list[dict], modifications: dict, rule: AutomationRule) -> None:
    """Apply rule actions to the modifications dict.

    Args:
        actions: List of action dicts from the rule.
        modifications: Accumulated modifications dict (mutated in place).
        rule: The matching AutomationRule (for metadata).
    """
    for action in actions:
        action_type = action.get("type")

        if action_type == "SET_KONTO":
            target = action.get("target", "expense")
            value = action.get("value")
            description = action.get("description", "")
            if value:
                konta = modifications.get("suggested_konta", {})
                # Build konto entry
                entry = {"konto": value, "description": description}
                # Accept both semantic names and raw debit/credit
                if target in ("expense", "revenue", "asset", "debit"):
                    konta.setdefault("debit", [])
                    # Replace existing entry for same target or append
                    konta["debit"] = [e for e in konta["debit"] if e.get("description") != target]
                    konta["debit"].append(entry)
                elif target in ("vat_input", "vat_output", "liability", "credit"):
                    konta.setdefault("credit", [])
                    konta["credit"] = [e for e in konta["credit"] if e.get("description") != target]
                    konta["credit"].append(entry)
                modifications["suggested_konta"] = konta

        elif action_type == "SET_VAT_TREATMENT":
            value = action.get("value")
            if value:
                modifications["vat_treatment"] = value
                # Update deductibility
                non_deductible = ("NON_DEDUCTIBLE", "OUTPUT_EXEMPT")
                modifications["is_deductible"] = value not in non_deductible

        elif action_type == "FLAG_REVIEW":
            modifications["requires_review"] = True
            reason = action.get("reason", f"Pravilo: {rule.name}")
            modifications.setdefault("review_reasons", [])
            modifications["review_reasons"].append(reason)

        elif action_type == "AUTO_APPROVE":
            modifications["auto_approve"] = True

        elif action_type == "SET_CUSTOM_FIELD":
            field = action.get("field")
            value = action.get("value")
            if field:
                modifications.setdefault("custom_fields", {})
                modifications["custom_fields"][field] = value


# ---------------------------------------------------------------------------
# Conflict resolution
# ---------------------------------------------------------------------------


def _resolve_conflicts(applied_rules: list[dict], modifications: dict) -> None:
    """Resolve conflicts between applied rules.

    Per SRS 4.11.7:
    - FLAG_FOR_REVIEW always applies (additive)
    - AUTO_APPROVE can be overridden by FLAG_FOR_REVIEW
    - KONTO_ASSIGNMENT: first matching rule wins (lowest priority)
    - VAT_TREATMENT: first matching rule wins

    Args:
        applied_rules: List of applied rule dicts.
        modifications: Modifications dict (mutated in place).
    """
    # FLAG_FOR_REVIEW overrides AUTO_APPROVE
    if modifications.get("requires_review") and modifications.get("auto_approve"):
        del modifications["auto_approve"]
        logger.info("Conflict resolved: FLAG_FOR_REVIEW overrides AUTO_APPROVE")


# ---------------------------------------------------------------------------
# Execution logging
# ---------------------------------------------------------------------------


async def _log_execution(
    db: AsyncSession,
    rule: AutomationRule,
    invoice: Invoice,
    actions_applied: list[dict],
    execution_time_ms: int,
) -> None:
    """Log rule execution and update rule statistics.

    Args:
        db: Database session.
        rule: Matched AutomationRule.
        invoice: Invoice that triggered the rule.
        actions_applied: Actions that were applied.
        execution_time_ms: Time taken to evaluate and apply.
    """
    execution = RuleExecution(
        rule_id=rule.id,
        invoice_id=invoice.id,
        conditions_matched=rule.conditions,
        actions_applied=actions_applied,
        execution_time_ms=execution_time_ms,
    )
    db.add(execution)

    # Update rule statistics
    await db.execute(
        update(AutomationRule)
        .where(AutomationRule.id == rule.id)
        .values(
            execution_count=AutomationRule.execution_count + 1,
            last_executed_at=func.now(),
        )
    )


# ---------------------------------------------------------------------------
# Rule templates
# ---------------------------------------------------------------------------


def get_rule_templates() -> list[dict]:
    """Return pre-built rule templates for common Serbian accounting scenarios.

    Templates provide starting points for common rules. Users can customize
    conditions and actions after creating from a template.

    Returns:
        List of template dicts with name, description, rule_type,
        conditions, and actions.
    """
    return [
        {
            "template_id": "fuel_non_deductible",
            "name": "Gorivo - putnička vozila",
            "description": "PDV na gorivo za putnička vozila nije priznat",
            "rule_type": "VAT_TREATMENT",
            "priority": 5,
            "conditions": {
                "operator": "AND",
                "rules": [
                    {
                        "field": "line_items[].description",
                        "operator": "regex",
                        "value": "(gorivo|benzin|dizel|nafta)",
                    },
                    {
                        "field": "seller.name",
                        "operator": "regex",
                        "value": "(NIS|MOL|OMV|Petrol|Lukoil)",
                    },
                ],
            },
            "actions": [
                {
                    "type": "SET_VAT_TREATMENT",
                    "value": "NON_DEDUCTIBLE",
                    "reason": "Gorivo za putnička vozila - PDV se ne priznaje",
                },
                {
                    "type": "SET_KONTO",
                    "target": "expense",
                    "value": "5130",
                    "description": "Troškovi goriva",
                },
            ],
        },
        {
            "template_id": "telecom_expenses",
            "name": "Telekom Srbija - Telefonija",
            "description": "Fakture od telekom provajdera na konto PTT troškova",
            "rule_type": "KONTO_ASSIGNMENT",
            "priority": 10,
            "conditions": {
                "operator": "AND",
                "rules": [
                    {
                        "field": "seller.pib",
                        "operator": "in",
                        "value": ["100002534", "100002535"],
                    },
                    {
                        "field": "document_type",
                        "operator": "equals",
                        "value": "INPUT_INVOICE",
                    },
                ],
            },
            "actions": [
                {
                    "type": "SET_KONTO",
                    "target": "expense",
                    "value": "5210",
                    "description": "PTT troškovi",
                },
            ],
        },
        {
            "template_id": "office_supplies",
            "name": "Kancelarijski materijal",
            "description": "Fakture za kancelarijski materijal",
            "rule_type": "KONTO_ASSIGNMENT",
            "priority": 20,
            "conditions": {
                "operator": "OR",
                "rules": [
                    {
                        "field": "line_items[].description",
                        "operator": "regex",
                        "value": "(papir|toner|olovk|svesk|fascikl|kancelarij)",
                    },
                ],
            },
            "actions": [
                {
                    "type": "SET_KONTO",
                    "target": "expense",
                    "value": "5120",
                    "description": "Kancelarijski materijal",
                },
            ],
        },
        {
            "template_id": "professional_services",
            "name": "Profesionalne usluge",
            "description": "Konsultantske i pravne usluge",
            "rule_type": "KONTO_ASSIGNMENT",
            "priority": 20,
            "conditions": {
                "operator": "OR",
                "rules": [
                    {
                        "field": "line_items[].description",
                        "operator": "regex",
                        "value": "(konsulta|pravne usluge|advokatsk|revizij|knjigovodstv)",
                    },
                ],
            },
            "actions": [
                {
                    "type": "SET_KONTO",
                    "target": "expense",
                    "value": "5330",
                    "description": "Usluge po ugovoru",
                },
            ],
        },
        {
            "template_id": "utilities",
            "name": "Komunalne usluge",
            "description": "Računi za struju, vodu, grejanje",
            "rule_type": "KONTO_ASSIGNMENT",
            "priority": 15,
            "conditions": {
                "operator": "OR",
                "rules": [
                    {
                        "field": "seller.name",
                        "operator": "regex",
                        "value": "(EPS|Elektroprivreda|Vodovod|Beogradske elektrane"
                        "|Toplane|Infostan)",
                    },
                ],
            },
            "actions": [
                {
                    "type": "SET_KONTO",
                    "target": "expense",
                    "value": "5131",
                    "description": "Troškovi energije",
                },
            ],
        },
        {
            "template_id": "rent_payments",
            "name": "Zakupnina",
            "description": "Fakture za zakup poslovnog prostora",
            "rule_type": "KONTO_ASSIGNMENT",
            "priority": 15,
            "conditions": {
                "operator": "OR",
                "rules": [
                    {
                        "field": "line_items[].description",
                        "operator": "regex",
                        "value": "(zakup|rent|najam|korišćenje prostora)",
                    },
                ],
            },
            "actions": [
                {
                    "type": "SET_KONTO",
                    "target": "expense",
                    "value": "5230",
                    "description": "Zakupnina",
                },
            ],
        },
        {
            "template_id": "large_invoice_review",
            "name": "Velike fakture - pregled",
            "description": "Fakture preko 500.000 RSD zahtevaju pregled",
            "rule_type": "FLAG_FOR_REVIEW",
            "priority": 1,
            "conditions": {
                "operator": "AND",
                "rules": [
                    {
                        "field": "total_amount",
                        "operator": "greater_than",
                        "value": 500000,
                    },
                    {
                        "field": "currency",
                        "operator": "equals",
                        "value": "RSD",
                    },
                ],
            },
            "actions": [
                {
                    "type": "FLAG_REVIEW",
                    "reason": "Faktura prelazi 500.000 RSD",
                },
            ],
        },
        {
            "template_id": "new_supplier_review",
            "name": "Novi dobavljač",
            "description": "Prve fakture od novih dobavljača uvek pregledati",
            "rule_type": "FLAG_FOR_REVIEW",
            "priority": 2,
            "conditions": {
                "operator": "AND",
                "rules": [
                    {
                        "field": "is_first_from_supplier",
                        "operator": "equals",
                        "value": True,
                    },
                ],
            },
            "actions": [
                {
                    "type": "FLAG_REVIEW",
                    "reason": "Prvi put primamo fakturu od ovog dobavljača",
                },
            ],
        },
        {
            "template_id": "foreign_supplier_review",
            "name": "Inostrani dobavljač",
            "description": "Fakture od inostranih dobavljača zahtevaju pregled",
            "rule_type": "FLAG_FOR_REVIEW",
            "priority": 3,
            "conditions": {
                "operator": "AND",
                "rules": [
                    {
                        "field": "document_type",
                        "operator": "equals",
                        "value": "INPUT_INVOICE",
                    },
                    {
                        "field": "currency",
                        "operator": "not_equals",
                        "value": "RSD",
                    },
                ],
            },
            "actions": [
                {
                    "type": "FLAG_REVIEW",
                    "reason": "Faktura u stranoj valuti - potrebna dodatna provera",
                },
            ],
        },
    ]
