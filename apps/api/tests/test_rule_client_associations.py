"""Tests for per-client rule attachments (many-to-many).

Covers the attach/detach/list endpoints and the client-scoped variant of
the rules engine — a rule with zero client associations is global; a rule
with associations fires only for invoices whose client_id matches.
"""

from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token


async def _register_and_login(
    client: AsyncClient,
    email: str,
    org_name: str = "RCA Test Org",
) -> dict[str, str]:
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "RCA",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": org_name},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    return {"Authorization": f"Bearer {org_resp.json()['access_token']}"}


def _org_id(headers: dict) -> str:
    token = headers["Authorization"].removeprefix("Bearer ")
    return decode_token(token)["org"]


async def _set_plan(test_engine, org_id: str, plan: str) -> None:
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text("UPDATE organizations SET plan = :plan WHERE id = :org_id"),
            {"plan": plan, "org_id": org_id},
        )
        await session.commit()


async def _create_client(client: AsyncClient, headers: dict, name: str, pib: str) -> str:
    resp = await client.post(
        "/api/v1/clients/",
        headers=headers,
        json={"name": name, "pib": pib},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_rule(client: AsyncClient, headers: dict, name: str) -> dict:
    resp = await client.post(
        "/api/v1/rules/",
        headers=headers,
        json={
            "name": name,
            "rule_type": "FLAG_FOR_REVIEW",
            "priority": 50,
            "conditions": {"field": "amount.total", "operator": "gt", "value": 0},
            "actions": [{"action_type": "FLAG_FOR_REVIEW", "params": {"reason": "test"}}],
            "is_active": True,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# New-rule responses carry an empty client_ids list (= global)
# ---------------------------------------------------------------------------


async def test_fresh_rule_has_no_client_associations(client: AsyncClient, test_engine) -> None:
    headers = await _register_and_login(client, "fresh-rule@example.com")
    await _set_plan(test_engine, _org_id(headers), "agency")

    rule = await _create_rule(client, headers, "Global rule")
    assert rule["client_ids"] == []


# ---------------------------------------------------------------------------
# Attach / detach endpoints
# ---------------------------------------------------------------------------


async def test_attach_rule_to_client_sets_client_ids(client: AsyncClient, test_engine) -> None:
    headers = await _register_and_login(client, "attach@example.com")
    await _set_plan(test_engine, _org_id(headers), "agency")

    client_id = await _create_client(client, headers, "Aroma", "123456789")
    rule = await _create_rule(client, headers, "Scoped rule")

    resp = await client.post(
        f"/api/v1/clients/{client_id}/rules/{rule['id']}",
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["client_ids"] == [client_id]


async def test_attach_is_idempotent(client: AsyncClient, test_engine) -> None:
    headers = await _register_and_login(client, "idem@example.com")
    await _set_plan(test_engine, _org_id(headers), "agency")

    client_id = await _create_client(client, headers, "Foo", "111111111")
    rule = await _create_rule(client, headers, "R1")

    r1 = await client.post(f"/api/v1/clients/{client_id}/rules/{rule['id']}", headers=headers)
    r2 = await client.post(f"/api/v1/clients/{client_id}/rules/{rule['id']}", headers=headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    # Still only one association
    assert r2.json()["client_ids"] == [client_id]


async def test_detach_rule_from_client(client: AsyncClient, test_engine) -> None:
    headers = await _register_and_login(client, "detach@example.com")
    await _set_plan(test_engine, _org_id(headers), "agency")

    client_id = await _create_client(client, headers, "Bar", "222222222")
    rule = await _create_rule(client, headers, "R2")

    await client.post(f"/api/v1/clients/{client_id}/rules/{rule['id']}", headers=headers)

    resp = await client.delete(f"/api/v1/clients/{client_id}/rules/{rule['id']}", headers=headers)
    assert resp.status_code == 204

    # Fetch the rule and verify it's back to global
    rule_resp = await client.get(f"/api/v1/rules/{rule['id']}", headers=headers)
    assert rule_resp.json()["client_ids"] == []


async def test_detach_unattached_is_noop(client: AsyncClient, test_engine) -> None:
    """DELETE on a non-existent attachment still returns 204."""
    headers = await _register_and_login(client, "noop@example.com")
    await _set_plan(test_engine, _org_id(headers), "agency")

    client_id = await _create_client(client, headers, "Baz", "333333333")
    rule = await _create_rule(client, headers, "R3")

    resp = await client.delete(f"/api/v1/clients/{client_id}/rules/{rule['id']}", headers=headers)
    assert resp.status_code == 204


async def test_list_client_rules_excludes_global(client: AsyncClient, test_engine) -> None:
    """list_client_rules returns ONLY rules scoped to this client, not globals."""
    headers = await _register_and_login(client, "list-scoped@example.com")
    await _set_plan(test_engine, _org_id(headers), "agency")

    client_id = await _create_client(client, headers, "Kafić", "444444444")
    global_rule = await _create_rule(client, headers, "Global rule")
    scoped_rule = await _create_rule(client, headers, "Scoped rule")

    # Attach only the scoped one
    await client.post(f"/api/v1/clients/{client_id}/rules/{scoped_rule['id']}", headers=headers)

    resp = await client.get(f"/api/v1/clients/{client_id}/rules", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    ids = {r["id"] for r in items}
    assert scoped_rule["id"] in ids
    assert global_rule["id"] not in ids


# ---------------------------------------------------------------------------
# Org isolation
# ---------------------------------------------------------------------------


async def test_cross_org_attach_rejected(client: AsyncClient, test_engine) -> None:
    h_a = await _register_and_login(client, "org-a@example.com", "Org A")
    h_b = await _register_and_login(client, "org-b@example.com", "Org B")
    await _set_plan(test_engine, _org_id(h_a), "agency")
    await _set_plan(test_engine, _org_id(h_b), "agency")

    client_a = await _create_client(client, h_a, "A Kafić", "555555555")
    rule_b = await _create_rule(client, h_b, "B rule")

    # Try to attach B's rule to A's client using A's auth
    resp = await client.post(f"/api/v1/clients/{client_a}/rules/{rule_b['id']}", headers=h_a)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Scoped matching in the rules engine
# ---------------------------------------------------------------------------


async def test_scoped_rule_fires_only_for_attached_client(client: AsyncClient, test_engine) -> None:
    """A rule attached to client A should NOT fire for invoices belonging to B."""
    from datetime import date
    from decimal import Decimal

    from app.models.invoice import Invoice
    from app.services.rules_engine import _get_active_rules

    headers = await _register_and_login(client, "scoped-match@example.com")
    org_id = _org_id(headers)
    await _set_plan(test_engine, org_id, "agency")

    client_a = await _create_client(client, headers, "Client A", "666666666")
    client_b = await _create_client(client, headers, "Client B", "777777777")
    rule = await _create_rule(client, headers, "A-only rule")
    await client.post(f"/api/v1/clients/{client_a}/rules/{rule['id']}", headers=headers)

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        # Invoice for client A — should see the scoped rule
        inv_a = Invoice(
            id=uuid4(),
            organization_id=UUID(org_id),
            client_id=UUID(client_a),
            status="review",
            invoice_number="A-1",
            invoice_date=date(2026, 4, 1),
            seller={"name": "S", "pib": "100000001"},
            buyer={"name": "B", "pib": "100000002"},
            subtotal=Decimal("100"),
            tax_rate=Decimal("20"),
            tax_amount=Decimal("20"),
            total_amount=Decimal("120"),
            currency="RSD",
        )
        session.add(inv_a)
        await session.commit()

        rules_for_a = await _get_active_rules(
            session, UUID(org_id), invoice_client_id=UUID(client_a)
        )
        assert any(r.name == "A-only rule" for r in rules_for_a)

        rules_for_b = await _get_active_rules(
            session, UUID(org_id), invoice_client_id=UUID(client_b)
        )
        assert not any(r.name == "A-only rule" for r in rules_for_b)

        # Invoice with no client — should also NOT see scoped rules
        rules_unassigned = await _get_active_rules(session, UUID(org_id), invoice_client_id=None)
        assert not any(r.name == "A-only rule" for r in rules_unassigned)


async def test_global_rule_fires_for_all_invoices(client: AsyncClient, test_engine) -> None:
    """A rule with no client associations should fire regardless of invoice.client_id."""
    from uuid import UUID as _UUID

    from app.services.rules_engine import _get_active_rules

    headers = await _register_and_login(client, "global-match@example.com")
    org_id = _org_id(headers)
    await _set_plan(test_engine, org_id, "agency")

    client_a = await _create_client(client, headers, "Client A", "888888888")
    await _create_rule(client, headers, "Global")  # never attached

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        rules_assigned = await _get_active_rules(
            session, _UUID(org_id), invoice_client_id=_UUID(client_a)
        )
        assert any(r.name == "Global" for r in rules_assigned)

        rules_unassigned = await _get_active_rules(session, _UUID(org_id), invoice_client_id=None)
        assert any(r.name == "Global" for r in rules_unassigned)
