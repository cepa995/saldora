"""
Tests for the automation rules engine (Issues #36 and #37).

Unit tests for condition evaluation (all 13 operators, nested AND/OR,
field resolution), action application, conflict resolution, and
integration tests for CRUD API, pipeline integration, and accounting
intelligence pipeline steps.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.models.automation_rule import AutomationRule
from app.models.invoice import Invoice
from app.services.accounting_intent import (
    build_vat_breakdown,
    classify_document,
    detect_transaction_type,
    determine_vat_treatment,
    generate_pdv_book_entries,
    suggest_konta,
)
from app.services.rules_engine import (
    _apply_actions,
    _evaluate_condition,
    _evaluate_operator,
    _resolve_conflicts,
    _resolve_field,
    get_rule_templates,
)

# ---- Helpers ----

ORG_PIB = "100000016"


async def _register_and_login(
    client: AsyncClient,
    email: str = "rules-test@example.com",
    password: str = "securepass123",
) -> dict[str, str]:
    """Register a user, log in, and return auth headers."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Rules",
            "last_name": "Tester",
            "organization_name": "Rules Test Org",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


async def _insert_invoice(test_engine, org_id: str, **overrides) -> str:
    """Insert a test invoice directly into the DB and return its id."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        invoice_id = uuid4()
        invoice = Invoice(
            id=invoice_id,
            organization_id=org_id,
            status=overrides.get("status", "review"),
            invoice_number=overrides.get("invoice_number", "RE-001"),
            invoice_date=overrides.get("invoice_date", date(2026, 3, 1)),
            seller=overrides.get("seller", {"name": "Dobavljač DOO", "pib": "123456789"}),
            buyer=overrides.get("buyer", {"name": "Kupac DOO", "pib": ORG_PIB}),
            subtotal=overrides.get("subtotal", Decimal("10000.00")),
            tax_rate=overrides.get("tax_rate", Decimal("20.00")),
            tax_amount=overrides.get("tax_amount", Decimal("2000.00")),
            total_amount=overrides.get("total_amount", Decimal("12000.00")),
            currency=overrides.get("currency", "RSD"),
            line_items=overrides.get("line_items"),
            tax_groups=overrides.get("tax_groups"),
            raw_ocr_text=overrides.get("raw_ocr_text"),
        )
        session.add(invoice)
        await session.commit()
        return str(invoice_id)


def _make_invoice(**kwargs) -> Invoice:
    """Create an in-memory Invoice object for unit testing (no DB)."""
    inv = Invoice()
    inv.id = uuid4()
    inv.organization_id = uuid4()
    inv.status = "review"
    inv.invoice_number = kwargs.get("invoice_number", "RE-001")
    inv.invoice_date = kwargs.get("invoice_date", date(2026, 3, 1))
    inv.seller = kwargs.get("seller", {"name": "Dobavljač", "pib": "123456789"})
    inv.buyer = kwargs.get("buyer", {"name": "Kupac", "pib": ORG_PIB})
    inv.subtotal = kwargs.get("subtotal", Decimal("10000.00"))
    inv.tax_rate = kwargs.get("tax_rate", Decimal("20.00"))
    inv.tax_amount = kwargs.get("tax_amount", Decimal("2000.00"))
    inv.total_amount = kwargs.get("total_amount", Decimal("12000.00"))
    inv.currency = kwargs.get("currency", "RSD")
    inv.line_items = kwargs.get("line_items")
    inv.tax_groups = kwargs.get("tax_groups")
    return inv


def _sample_context(**overrides) -> dict:
    """Build a sample evaluation context for unit tests."""
    ctx = {
        "seller": {"pib": "123456789", "name": "Dobavljač DOO"},
        "buyer": {"pib": ORG_PIB, "name": "Kupac DOO"},
        "total_amount": Decimal("12000.00"),
        "subtotal": Decimal("10000.00"),
        "tax_rate": Decimal("20.00"),
        "tax_amount": Decimal("2000.00"),
        "currency": "RSD",
        "invoice_date": date(2026, 3, 1),
        "invoice_number": "RE-001",
        "line_items": [
            {"description": "IT usluge", "total": "10000.00"},
        ],
        "document_type": "INPUT_INVOICE",
        "is_first_from_supplier": False,
        "supplier_invoice_count": 5,
        "confidence": Decimal("0.92"),
    }
    ctx.update(overrides)
    return ctx


# ===========================================================================
# A. Condition Evaluation — Operators
# ===========================================================================


def test_operator_equals():
    """equals operator matches equal values."""
    assert _evaluate_operator("abc", "equals", "abc") is True
    assert _evaluate_operator("abc", "equals", "xyz") is False


def test_operator_equals_numeric():
    """equals operator works with numeric comparison."""
    assert _evaluate_operator(Decimal("100"), "equals", 100) is True
    assert _evaluate_operator(Decimal("100"), "equals", 200) is False


def test_operator_not_equals():
    """not_equals operator matches unequal values."""
    assert _evaluate_operator("abc", "not_equals", "xyz") is True
    assert _evaluate_operator("abc", "not_equals", "abc") is False


def test_operator_contains():
    """contains operator does substring matching (case-insensitive)."""
    assert _evaluate_operator("Dobavljač DOO", "contains", "dobavljač") is True
    assert _evaluate_operator("Dobavljač DOO", "contains", "xyz") is False


def test_operator_starts_with():
    """starts_with operator checks prefix (case-insensitive)."""
    assert _evaluate_operator("INV-2026-001", "starts_with", "inv-") is True
    assert _evaluate_operator("INV-2026-001", "starts_with", "xyz") is False


def test_operator_ends_with():
    """ends_with operator checks suffix (case-insensitive)."""
    assert _evaluate_operator("INV-2026-001", "ends_with", "-001") is True
    assert _evaluate_operator("INV-2026-001", "ends_with", "-999") is False


def test_operator_regex():
    """regex operator matches patterns (case-insensitive)."""
    assert _evaluate_operator("gorivo za vozilo", "regex", "(gorivo|benzin)") is True
    assert _evaluate_operator("kancelarijski materijal", "regex", "(gorivo|benzin)") is False


def test_operator_regex_invalid():
    """Invalid regex gracefully returns False."""
    assert _evaluate_operator("test", "regex", "[invalid") is False


def test_operator_greater_than():
    """greater_than works for numeric values."""
    assert _evaluate_operator(Decimal("15000"), "greater_than", 10000) is True
    assert _evaluate_operator(Decimal("5000"), "greater_than", 10000) is False


def test_operator_less_than():
    """less_than works for numeric values."""
    assert _evaluate_operator(Decimal("5000"), "less_than", 10000) is True
    assert _evaluate_operator(Decimal("15000"), "less_than", 10000) is False


def test_operator_between():
    """between operator checks inclusive range."""
    assert _evaluate_operator(Decimal("5000"), "between", [1000, 10000]) is True
    assert _evaluate_operator(Decimal("15000"), "between", [1000, 10000]) is False
    assert _evaluate_operator(Decimal("1000"), "between", [1000, 10000]) is True  # inclusive


def test_operator_in():
    """in operator checks list membership."""
    assert _evaluate_operator("100002534", "in", ["100002534", "100002535"]) is True
    assert _evaluate_operator("999999999", "in", ["100002534", "100002535"]) is False


def test_operator_not_in():
    """not_in operator checks list non-membership."""
    assert _evaluate_operator("999999999", "not_in", ["100002534", "100002535"]) is True
    assert _evaluate_operator("100002534", "not_in", ["100002534", "100002535"]) is False


def test_operator_is_null():
    """is_null matches None values."""
    assert _evaluate_operator(None, "is_null", None) is True
    assert _evaluate_operator("value", "is_null", None) is False


def test_operator_is_not_null():
    """is_not_null matches non-None values."""
    assert _evaluate_operator("value", "is_not_null", None) is True
    assert _evaluate_operator(None, "is_not_null", None) is False


# ===========================================================================
# A. Condition Evaluation — Field Resolution
# ===========================================================================


def test_resolve_simple_field():
    """Simple field resolution from context."""
    ctx = _sample_context()
    assert _resolve_field(ctx, "total_amount") == Decimal("12000.00")
    assert _resolve_field(ctx, "currency") == "RSD"


def test_resolve_nested_field():
    """Dot-path resolution for nested objects."""
    ctx = _sample_context()
    assert _resolve_field(ctx, "seller.pib") == "123456789"
    assert _resolve_field(ctx, "buyer.name") == "Kupac DOO"


def test_resolve_array_field():
    """Array accessor returns list of values."""
    ctx = _sample_context(
        line_items=[
            {"description": "gorivo", "total": "5000"},
            {"description": "ulje", "total": "3000"},
        ]
    )
    result = _resolve_field(ctx, "line_items[].description")
    assert isinstance(result, list)
    assert "gorivo" in result
    assert "ulje" in result


def test_resolve_missing_field():
    """Missing field returns None."""
    ctx = _sample_context()
    assert _resolve_field(ctx, "nonexistent") is None
    assert _resolve_field(ctx, "seller.nonexistent") is None


# ===========================================================================
# A. Condition Evaluation — Nested AND/OR
# ===========================================================================


def test_condition_and_all_true():
    """AND group matches when all conditions are true."""
    ctx = _sample_context()
    condition = {
        "operator": "AND",
        "rules": [
            {"field": "seller.pib", "operator": "equals", "value": "123456789"},
            {"field": "total_amount", "operator": "greater_than", "value": 10000},
        ],
    }
    assert _evaluate_condition(condition, ctx) is True


def test_condition_and_one_false():
    """AND group fails when any condition is false."""
    ctx = _sample_context()
    condition = {
        "operator": "AND",
        "rules": [
            {"field": "seller.pib", "operator": "equals", "value": "123456789"},
            {"field": "total_amount", "operator": "greater_than", "value": 99999},
        ],
    }
    assert _evaluate_condition(condition, ctx) is False


def test_condition_or_one_true():
    """OR group matches when any condition is true."""
    ctx = _sample_context()
    condition = {
        "operator": "OR",
        "rules": [
            {"field": "seller.pib", "operator": "equals", "value": "999999999"},
            {"field": "total_amount", "operator": "greater_than", "value": 10000},
        ],
    }
    assert _evaluate_condition(condition, ctx) is True


def test_condition_or_all_false():
    """OR group fails when all conditions are false."""
    ctx = _sample_context()
    condition = {
        "operator": "OR",
        "rules": [
            {"field": "seller.pib", "operator": "equals", "value": "999999999"},
            {"field": "total_amount", "operator": "greater_than", "value": 99999},
        ],
    }
    assert _evaluate_condition(condition, ctx) is False


def test_condition_nested_groups():
    """Nested AND/OR groups evaluate correctly."""
    ctx = _sample_context()
    condition = {
        "operator": "OR",
        "rules": [
            {
                "operator": "AND",
                "rules": [
                    {"field": "seller.pib", "operator": "equals", "value": "111111111"},
                    {"field": "total_amount", "operator": "greater_than", "value": 50000},
                ],
            },
            {
                "field": "line_items[].description",
                "operator": "contains",
                "value": "IT usluge",
            },
        ],
    }
    # First AND branch is false, but second leaf is true → OR = true
    assert _evaluate_condition(condition, ctx) is True


def test_condition_empty_rules():
    """Empty rules list returns True (vacuous truth)."""
    condition = {"operator": "AND", "rules": []}
    assert _evaluate_condition(condition, {}) is True


def test_condition_empty_dict():
    """Empty condition dict returns False."""
    assert _evaluate_condition({}, {}) is False


def test_condition_computed_field_is_first():
    """Computed field is_first_from_supplier works in conditions."""
    ctx = _sample_context(is_first_from_supplier=True)
    condition = {
        "operator": "AND",
        "rules": [
            {"field": "is_first_from_supplier", "operator": "equals", "value": True},
        ],
    }
    assert _evaluate_condition(condition, ctx) is True


def test_condition_computed_field_supplier_count():
    """Computed field supplier_invoice_count works in conditions."""
    ctx = _sample_context(supplier_invoice_count=10)
    condition = {
        "operator": "AND",
        "rules": [
            {"field": "supplier_invoice_count", "operator": "greater_than", "value": 5},
        ],
    }
    assert _evaluate_condition(condition, ctx) is True


# ===========================================================================
# B. Action Application
# ===========================================================================


def test_action_set_konto():
    """SET_KONTO action modifies suggested_konta."""
    modifications: dict = {}
    rule = AutomationRule()
    rule.name = "Test Rule"
    actions = [
        {"type": "SET_KONTO", "target": "expense", "value": "5330", "description": "IT usluge"},
    ]
    _apply_actions(actions, modifications, rule)
    assert "suggested_konta" in modifications
    assert any(e["konto"] == "5330" for e in modifications["suggested_konta"]["debit"])


def test_action_set_konto_credit():
    """SET_KONTO with vat_input target goes to credit side."""
    modifications: dict = {}
    rule = AutomationRule()
    rule.name = "Test Rule"
    actions = [
        {"type": "SET_KONTO", "target": "vat_input", "value": "2700"},
    ]
    _apply_actions(actions, modifications, rule)
    assert any(e["konto"] == "2700" for e in modifications["suggested_konta"]["credit"])


def test_action_set_vat_treatment():
    """SET_VAT_TREATMENT updates vat_treatment and is_deductible."""
    modifications: dict = {}
    rule = AutomationRule()
    rule.name = "Test Rule"
    actions = [
        {"type": "SET_VAT_TREATMENT", "value": "NON_DEDUCTIBLE"},
    ]
    _apply_actions(actions, modifications, rule)
    assert modifications["vat_treatment"] == "NON_DEDUCTIBLE"
    assert modifications["is_deductible"] is False


def test_action_set_vat_treatment_deductible():
    """SET_VAT_TREATMENT with deductible type sets is_deductible=True."""
    modifications: dict = {}
    rule = AutomationRule()
    rule.name = "Test Rule"
    actions = [
        {"type": "SET_VAT_TREATMENT", "value": "DEDUCTIBLE_FULL"},
    ]
    _apply_actions(actions, modifications, rule)
    assert modifications["vat_treatment"] == "DEDUCTIBLE_FULL"
    assert modifications["is_deductible"] is True


def test_action_flag_review():
    """FLAG_REVIEW sets requires_review and adds reason."""
    modifications: dict = {}
    rule = AutomationRule()
    rule.name = "Large Invoice"
    actions = [
        {"type": "FLAG_REVIEW", "reason": "Faktura prelazi 500.000 RSD"},
    ]
    _apply_actions(actions, modifications, rule)
    assert modifications["requires_review"] is True
    assert "Faktura prelazi 500.000 RSD" in modifications["review_reasons"]


def test_action_auto_approve():
    """AUTO_APPROVE sets auto_approve flag."""
    modifications: dict = {}
    rule = AutomationRule()
    rule.name = "Small Invoice"
    actions = [
        {"type": "AUTO_APPROVE"},
    ]
    _apply_actions(actions, modifications, rule)
    assert modifications["auto_approve"] is True


def test_action_set_custom_field():
    """SET_CUSTOM_FIELD adds to custom_fields dict."""
    modifications: dict = {}
    rule = AutomationRule()
    rule.name = "Custom"
    actions = [
        {"type": "SET_CUSTOM_FIELD", "field": "cost_center", "value": "IT-001"},
    ]
    _apply_actions(actions, modifications, rule)
    assert modifications["custom_fields"]["cost_center"] == "IT-001"


# ===========================================================================
# C. Conflict Resolution
# ===========================================================================


def test_conflict_flag_overrides_auto_approve():
    """FLAG_FOR_REVIEW overrides AUTO_APPROVE."""
    modifications = {"requires_review": True, "review_reasons": ["reason"], "auto_approve": True}
    applied_rules = [
        {"rule_type": "FLAG_FOR_REVIEW"},
        {"rule_type": "AUTO_APPROVE"},
    ]
    _resolve_conflicts(applied_rules, modifications)
    assert modifications["requires_review"] is True
    assert "auto_approve" not in modifications


def test_conflict_auto_approve_without_flag():
    """AUTO_APPROVE stays when no FLAG_FOR_REVIEW present."""
    modifications = {"auto_approve": True}
    applied_rules = [{"rule_type": "AUTO_APPROVE"}]
    _resolve_conflicts(applied_rules, modifications)
    assert modifications["auto_approve"] is True


# ===========================================================================
# D. Rule Templates
# ===========================================================================


def test_templates_count():
    """get_rule_templates returns 9 templates."""
    templates = get_rule_templates()
    assert len(templates) == 9


def test_templates_have_required_fields():
    """Each template has required fields."""
    templates = get_rule_templates()
    for t in templates:
        assert "template_id" in t
        assert "name" in t
        assert "rule_type" in t
        assert "conditions" in t
        assert "actions" in t


def test_templates_fuel_non_deductible():
    """fuel_non_deductible template has correct structure."""
    templates = get_rule_templates()
    fuel = next(t for t in templates if t["template_id"] == "fuel_non_deductible")
    assert fuel["rule_type"] == "VAT_TREATMENT"
    assert any(a["type"] == "SET_VAT_TREATMENT" for a in fuel["actions"])


# ===========================================================================
# E. CRUD API Tests
# ===========================================================================


async def test_create_rule(client: AsyncClient):
    """POST /api/v1/rules creates a rule."""
    headers = await _register_and_login(client, email="rule-create@example.com")
    resp = await client.post(
        "/api/v1/rules/",
        headers=headers,
        json={
            "name": "Test Rule",
            "rule_type": "KONTO_ASSIGNMENT",
            "priority": 10,
            "conditions": {
                "operator": "AND",
                "rules": [
                    {"field": "seller.pib", "operator": "equals", "value": "123456789"},
                ],
            },
            "actions": [
                {"type": "SET_KONTO", "target": "expense", "value": "5330"},
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Rule"
    assert data["rule_type"] == "KONTO_ASSIGNMENT"
    assert data["priority"] == 10
    assert data["is_active"] is True
    assert data["execution_count"] == 0


async def test_list_rules(client: AsyncClient):
    """GET /api/v1/rules returns org rules."""
    headers = await _register_and_login(client, email="rule-list@example.com")

    # Create two rules
    for name in ("Rule A", "Rule B"):
        await client.post(
            "/api/v1/rules/",
            headers=headers,
            json={
                "name": name,
                "rule_type": "KONTO_ASSIGNMENT",
                "conditions": {"operator": "AND", "rules": []},
                "actions": [],
            },
        )

    resp = await client.get("/api/v1/rules/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert len(data["items"]) == 2


async def test_list_rules_filter_type(client: AsyncClient):
    """GET /api/v1/rules?rule_type=X filters by type."""
    headers = await _register_and_login(client, email="rule-filter@example.com")

    await client.post(
        "/api/v1/rules/",
        headers=headers,
        json={
            "name": "Konto Rule",
            "rule_type": "KONTO_ASSIGNMENT",
            "conditions": {"operator": "AND", "rules": []},
            "actions": [],
        },
    )
    await client.post(
        "/api/v1/rules/",
        headers=headers,
        json={
            "name": "VAT Rule",
            "rule_type": "VAT_TREATMENT",
            "conditions": {"operator": "AND", "rules": []},
            "actions": [],
        },
    )

    resp = await client.get(
        "/api/v1/rules/", headers=headers, params={"rule_type": "KONTO_ASSIGNMENT"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["items"][0]["rule_type"] == "KONTO_ASSIGNMENT"


async def test_get_rule(client: AsyncClient):
    """GET /api/v1/rules/{id} returns a single rule."""
    headers = await _register_and_login(client, email="rule-get@example.com")

    create_resp = await client.post(
        "/api/v1/rules/",
        headers=headers,
        json={
            "name": "Get Test Rule",
            "rule_type": "FLAG_FOR_REVIEW",
            "conditions": {"operator": "AND", "rules": []},
            "actions": [{"type": "FLAG_REVIEW", "reason": "Test"}],
        },
    )
    rule_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/rules/{rule_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Get Test Rule"


async def test_update_rule(client: AsyncClient):
    """PATCH /api/v1/rules/{id} updates rule fields."""
    headers = await _register_and_login(client, email="rule-update@example.com")

    create_resp = await client.post(
        "/api/v1/rules/",
        headers=headers,
        json={
            "name": "Update Test Rule",
            "rule_type": "KONTO_ASSIGNMENT",
            "priority": 50,
            "conditions": {"operator": "AND", "rules": []},
            "actions": [],
        },
    )
    rule_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/rules/{rule_id}",
        headers=headers,
        json={"name": "Updated Name", "priority": 5, "is_active": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Name"
    assert data["priority"] == 5
    assert data["is_active"] is False


async def test_delete_rule(client: AsyncClient):
    """DELETE /api/v1/rules/{id} removes the rule."""
    headers = await _register_and_login(client, email="rule-delete@example.com")

    create_resp = await client.post(
        "/api/v1/rules/",
        headers=headers,
        json={
            "name": "Delete Test Rule",
            "rule_type": "KONTO_ASSIGNMENT",
            "conditions": {"operator": "AND", "rules": []},
            "actions": [],
        },
    )
    rule_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/rules/{rule_id}", headers=headers)
    assert resp.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/api/v1/rules/{rule_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_rule_org_isolation(client: AsyncClient):
    """Rules from one org are not visible to another org."""
    headers_a = await _register_and_login(client, email="org-a-rules@example.com")
    headers_b = await _register_and_login(client, email="org-b-rules@example.com")

    # Create rule in org A
    create_resp = await client.post(
        "/api/v1/rules/",
        headers=headers_a,
        json={
            "name": "Org A Rule",
            "rule_type": "KONTO_ASSIGNMENT",
            "conditions": {"operator": "AND", "rules": []},
            "actions": [],
        },
    )
    rule_id = create_resp.json()["id"]

    # Org B cannot see org A's rule
    resp = await client.get(f"/api/v1/rules/{rule_id}", headers=headers_b)
    assert resp.status_code == 404

    # Org B's list is empty
    list_resp = await client.get("/api/v1/rules/", headers=headers_b)
    assert list_resp.json()["count"] == 0


async def test_get_templates(client: AsyncClient):
    """GET /api/v1/rules/templates returns templates."""
    headers = await _register_and_login(client, email="rule-templates@example.com")
    resp = await client.get("/api/v1/rules/templates", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 9


async def test_rule_not_found(client: AsyncClient):
    """GET /api/v1/rules/{nonexistent} returns 404."""
    headers = await _register_and_login(client, email="rule-404@example.com")
    resp = await client.get(f"/api/v1/rules/{uuid4()}", headers=headers)
    assert resp.status_code == 404


# ===========================================================================
# F. Pipeline Integration Tests
# ===========================================================================


async def test_rule_modifies_konta_on_verify(client: AsyncClient, test_engine):
    """A KONTO_ASSIGNMENT rule modifies suggested_konta during verification."""
    headers = await _register_and_login(client, email="pipe-konto@example.com")
    org_id = _get_org_id(headers)

    # Create a rule targeting seller PIB
    await client.post(
        "/api/v1/rules/",
        headers=headers,
        json={
            "name": "IT Supplier Konto",
            "rule_type": "KONTO_ASSIGNMENT",
            "priority": 1,
            "conditions": {
                "operator": "AND",
                "rules": [
                    {"field": "seller.pib", "operator": "equals", "value": "123456789"},
                ],
            },
            "actions": [
                {"type": "SET_KONTO", "target": "expense", "value": "5330", "description": "IT"},
            ],
        },
    )

    # Insert invoice and verify
    invoice_id = await _insert_invoice(
        test_engine,
        org_id,
        seller={"name": "IT Firma", "pib": "123456789"},
    )

    resp = await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    assert resp.status_code == 200

    # Check accounting intent
    intent_resp = await client.get(
        f"/api/v1/invoices/{invoice_id}/accounting-intent", headers=headers
    )
    assert intent_resp.status_code == 200
    data = intent_resp.json()

    # applied_rules should contain our rule
    assert len(data["applied_rules"]) >= 1
    assert any(r["rule_name"] == "IT Supplier Konto" for r in data["applied_rules"])

    # suggested_konta should have our konto
    konta = data["suggested_konta"]
    debit_kontos = [e["konto"] for e in konta.get("debit", []) if isinstance(e, dict)]
    assert "5330" in debit_kontos


async def test_rule_flag_review_on_verify(client: AsyncClient, test_engine):
    """A FLAG_FOR_REVIEW rule adds review reasons during verification."""
    headers = await _register_and_login(client, email="pipe-flag@example.com")
    org_id = _get_org_id(headers)

    # Create a rule to flag all invoices for review
    await client.post(
        "/api/v1/rules/",
        headers=headers,
        json={
            "name": "Always Review",
            "rule_type": "FLAG_FOR_REVIEW",
            "priority": 1,
            "conditions": {
                "operator": "AND",
                "rules": [
                    {"field": "document_type", "operator": "equals", "value": "INPUT_INVOICE"},
                ],
            },
            "actions": [
                {"type": "FLAG_REVIEW", "reason": "Test: uvek pregledaj"},
            ],
        },
    )

    invoice_id = await _insert_invoice(
        test_engine,
        org_id,
        seller={"name": "Firm", "pib": "123456789"},
        total_amount=Decimal("1000.00"),
        subtotal=Decimal("833.33"),
        tax_amount=Decimal("166.67"),
    )

    resp = await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    assert resp.status_code == 200

    intent_resp = await client.get(
        f"/api/v1/invoices/{invoice_id}/accounting-intent", headers=headers
    )
    data = intent_resp.json()
    assert data["requires_review"] is True
    assert any("uvek pregledaj" in r for r in data["review_reasons"])


async def test_rule_vat_treatment_override(client: AsyncClient, test_engine):
    """A VAT_TREATMENT rule overrides the default treatment."""
    headers = await _register_and_login(client, email="pipe-vat@example.com")
    org_id = _get_org_id(headers)

    # Create rule to set NON_DEDUCTIBLE for specific supplier
    await client.post(
        "/api/v1/rules/",
        headers=headers,
        json={
            "name": "Fuel Non-Deductible",
            "rule_type": "VAT_TREATMENT",
            "priority": 1,
            "conditions": {
                "operator": "AND",
                "rules": [
                    {"field": "seller.pib", "operator": "equals", "value": "111222333"},
                ],
            },
            "actions": [
                {"type": "SET_VAT_TREATMENT", "value": "NON_DEDUCTIBLE"},
            ],
        },
    )

    invoice_id = await _insert_invoice(
        test_engine,
        org_id,
        seller={"name": "NIS Gazprom Neft", "pib": "111222333"},
        line_items=[{"description": "Gorivo dizel", "total": "10000.00"}],
    )

    resp = await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    assert resp.status_code == 200

    intent_resp = await client.get(
        f"/api/v1/invoices/{invoice_id}/accounting-intent", headers=headers
    )
    data = intent_resp.json()
    assert data["vat_treatment"] == "NON_DEDUCTIBLE"
    assert data["is_deductible"] is False


async def test_no_rules_produces_empty_applied(client: AsyncClient, test_engine):
    """Invoice verified without rules has empty applied_rules."""
    headers = await _register_and_login(client, email="pipe-empty@example.com")
    org_id = _get_org_id(headers)

    invoice_id = await _insert_invoice(test_engine, org_id)

    resp = await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    assert resp.status_code == 200

    intent_resp = await client.get(
        f"/api/v1/invoices/{invoice_id}/accounting-intent", headers=headers
    )
    data = intent_resp.json()
    assert data["applied_rules"] == []


# ===========================================================================
# G. Accounting Intelligence Tests (Issue #37)
# ===========================================================================


def test_classify_input_invoice():
    """Input invoice with buyer PIB matching org → INPUT_INVOICE."""
    inv = _make_invoice(buyer={"name": "Naša Firma", "pib": ORG_PIB})
    doc_type, conf = classify_document(inv, ORG_PIB)
    assert doc_type == "INPUT_INVOICE"


def test_classify_output_invoice():
    """Output invoice with seller PIB matching org → OUTPUT_INVOICE."""
    inv = _make_invoice(
        seller={"name": "Naša Firma", "pib": ORG_PIB},
        buyer={"name": "Kupac DOO", "pib": "987654321"},
    )
    doc_type, conf = classify_document(inv, ORG_PIB)
    assert doc_type == "OUTPUT_INVOICE"


def test_detect_domestic_transaction():
    """Serbian PIBs → DOMESTIC transaction."""
    inv = _make_invoice(currency="RSD")
    txn_type, conf = detect_transaction_type(inv, "INPUT_INVOICE")
    assert txn_type == "DOMESTIC"


def test_detect_foreign_transaction():
    """Foreign seller with non-Serbian PIB → FOREIGN_NON_EU."""
    inv = _make_invoice(
        currency="USD",
        seller={"name": "US Company", "pib": "US12345678901"},
    )
    txn_type, conf = detect_transaction_type(inv, "INPUT_INVOICE")
    assert txn_type in ("FOREIGN_EU", "FOREIGN_NON_EU")


def test_vat_treatment_deductible_full():
    """Standard domestic input → DEDUCTIBLE_FULL."""
    inv = _make_invoice(tax_rate=Decimal("20.00"))
    vat, deductible, conf = determine_vat_treatment(inv, "INPUT_INVOICE", "DOMESTIC")
    assert vat == "DEDUCTIBLE_FULL"
    assert deductible is True


def test_vat_treatment_output_standard():
    """Standard domestic output → OUTPUT_STANDARD."""
    inv = _make_invoice(tax_rate=Decimal("20.00"))
    vat, deductible, conf = determine_vat_treatment(inv, "OUTPUT_INVOICE", "DOMESTIC")
    assert vat == "OUTPUT_STANDARD"


def test_suggest_konta_input_invoice():
    """Input invoice gets debit expense + credit liability konta."""
    inv = _make_invoice()
    konta, conf = suggest_konta(inv, "INPUT_INVOICE", "DOMESTIC", "DEDUCTIBLE_FULL")
    assert "debit" in konta
    assert "credit" in konta
    assert len(konta["debit"]) > 0
    assert len(konta["credit"]) > 0


def test_build_vat_breakdown():
    """build_vat_breakdown extracts rate/base/tax info."""
    inv = _make_invoice(
        subtotal=Decimal("10000.00"),
        tax_rate=Decimal("20.00"),
        tax_amount=Decimal("2000.00"),
        total_amount=Decimal("12000.00"),
    )
    breakdown = build_vat_breakdown(inv)
    assert breakdown is not None
    assert "rate_20.00" in breakdown
    assert breakdown["rate_20.00"]["base"] == "10000.00"
    assert breakdown["rate_20.00"]["tax"] == "2000.00"


def test_generate_pdv_kpr_entry():
    """Input invoice generates KPR book entry."""
    inv = _make_invoice()
    vat_breakdown = build_vat_breakdown(inv)
    entry = generate_pdv_book_entries(
        inv, "INPUT_INVOICE", "DOMESTIC", "DEDUCTIBLE_FULL", vat_breakdown, 1
    )
    assert entry["book_type"] == "KPR"
    assert entry["sequence"] == 1


def test_generate_pdv_kir_entry():
    """Output invoice generates KIR book entry."""
    inv = _make_invoice(
        seller={"name": "Naša Firma", "pib": ORG_PIB},
        buyer={"name": "Kupac", "pib": "987654321"},
    )
    vat_breakdown = build_vat_breakdown(inv)
    entry = generate_pdv_book_entries(
        inv, "OUTPUT_INVOICE", "DOMESTIC", "OUTPUT_STANDARD", vat_breakdown, 1
    )
    assert entry["book_type"] == "KIR"
    assert entry["sequence"] == 1
