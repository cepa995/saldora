"""Tests for invoice template CRUD."""

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token


async def _register_and_login(
    client: AsyncClient,
    email: str = "tmpl-test@example.com",
) -> dict[str, str]:
    """Register a user, create an organization, return auth headers."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Template",
            "last_name": "Tester",
        },
    )
    token = reg.json()["access_token"]
    org = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Template Org {email}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"Authorization": f"Bearer {org.json()['access_token']}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from JWT."""
    token = headers["Authorization"].removeprefix("Bearer ")
    return decode_token(token)["org"]


def _template_payload(**overrides) -> dict:
    """Build a valid template creation payload."""
    base = {
        "seller_pib": "123456789",
        "seller_name": "Test DOO",
        "layout_fingerprint": "a" * 64,
        "field_mappings": {
            "invoice_number": {
                "field_name": "invoice_number",
                "label_text": "Broj fakture:",
                "bbox": [0.1, 0.05, 0.4, 0.08],
                "regex_pattern": r"\d{1,6}/\d{4}",
                "value_format": "string",
                "confidence": 0.95,
            }
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def test_create_template(client: AsyncClient, test_engine):
    """Create a template and verify all fields returned."""
    headers = await _register_and_login(client, "tmpl-create@example.com")
    resp = await client.post(
        "/api/v1/invoice-templates/",
        json=_template_payload(),
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["seller_pib"] == "123456789"
    assert data["seller_name"] == "Test DOO"
    assert data["layout_fingerprint"] == "a" * 64
    assert "invoice_number" in data["field_mappings"]
    assert data["usage_count"] == 0
    assert data["success_rate"] == 0.0
    assert data["is_active"] is True


async def test_create_duplicate_returns_409(client: AsyncClient, test_engine):
    """Creating a template with same seller PIB and fingerprint returns 409."""
    headers = await _register_and_login(client, "tmpl-dup@example.com")
    await client.post(
        "/api/v1/invoice-templates/",
        json=_template_payload(),
        headers=headers,
    )
    resp = await client.post(
        "/api/v1/invoice-templates/",
        json=_template_payload(),
        headers=headers,
    )
    assert resp.status_code == 409


async def test_list_templates(client: AsyncClient, test_engine):
    """List templates with pagination."""
    headers = await _register_and_login(client, "tmpl-list@example.com")
    # Create 3 templates with different fingerprints
    for i in range(3):
        await client.post(
            "/api/v1/invoice-templates/",
            json=_template_payload(layout_fingerprint=f"{chr(ord('a') + i)}" * 64),
            headers=headers,
        )

    resp = await client.get("/api/v1/invoice-templates/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] == 3
    assert len(data["data"]) == 3


async def test_list_templates_filter_by_seller_pib(client: AsyncClient, test_engine):
    """Filter templates by seller PIB."""
    headers = await _register_and_login(client, "tmpl-filter@example.com")
    await client.post(
        "/api/v1/invoice-templates/",
        json=_template_payload(seller_pib="111111111"),
        headers=headers,
    )
    await client.post(
        "/api/v1/invoice-templates/",
        json=_template_payload(seller_pib="222222222", layout_fingerprint="b" * 64),
        headers=headers,
    )

    resp = await client.get("/api/v1/invoice-templates/?seller_pib=111111111", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 1
    assert resp.json()["data"][0]["seller_pib"] == "111111111"


async def test_get_template(client: AsyncClient, test_engine):
    """Get a single template by ID."""
    headers = await _register_and_login(client, "tmpl-get@example.com")
    create_resp = await client.post(
        "/api/v1/invoice-templates/",
        json=_template_payload(),
        headers=headers,
    )
    template_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/invoice-templates/{template_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == template_id


async def test_get_nonexistent_template(client: AsyncClient, test_engine):
    """Getting a nonexistent template returns 404."""
    headers = await _register_and_login(client, "tmpl-404@example.com")
    resp = await client.get(f"/api/v1/invoice-templates/{uuid4()}", headers=headers)
    assert resp.status_code == 404


async def test_update_template(client: AsyncClient, test_engine):
    """Update template field mappings and name."""
    headers = await _register_and_login(client, "tmpl-update@example.com")
    create_resp = await client.post(
        "/api/v1/invoice-templates/",
        json=_template_payload(),
        headers=headers,
    )
    template_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/invoice-templates/{template_id}",
        json={"seller_name": "Updated DOO", "is_active": False},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["seller_name"] == "Updated DOO"
    assert resp.json()["is_active"] is False


async def test_deactivate_and_reactivate_resets_stats(client: AsyncClient, test_engine):
    """Reactivating a template resets usage stats."""
    headers = await _register_and_login(client, "tmpl-reactivate@example.com")
    create_resp = await client.post(
        "/api/v1/invoice-templates/",
        json=_template_payload(),
        headers=headers,
    )
    template_id = create_resp.json()["id"]

    # Simulate usage by updating DB directly
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        from sqlalchemy import text

        await session.execute(
            text(
                "UPDATE invoice_templates SET usage_count = 50, success_count = 40, "
                "success_rate = 0.8 WHERE id = :id"
            ),
            {"id": template_id},
        )
        await session.commit()

    # Deactivate then reactivate
    await client.patch(
        f"/api/v1/invoice-templates/{template_id}",
        json={"is_active": False},
        headers=headers,
    )
    resp = await client.patch(
        f"/api/v1/invoice-templates/{template_id}",
        json={"is_active": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True
    assert resp.json()["usage_count"] == 0
    assert resp.json()["success_count"] == 0
    assert resp.json()["success_rate"] == 0.0


async def test_delete_template(client: AsyncClient, test_engine):
    """Delete a template returns 204."""
    headers = await _register_and_login(client, "tmpl-delete@example.com")
    create_resp = await client.post(
        "/api/v1/invoice-templates/",
        json=_template_payload(),
        headers=headers,
    )
    template_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/invoice-templates/{template_id}", headers=headers)
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/v1/invoice-templates/{template_id}", headers=headers)
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Organization isolation
# ---------------------------------------------------------------------------


async def test_template_org_isolation(client: AsyncClient, test_engine):
    """Org A cannot see or modify Org B's templates."""
    headers_a = await _register_and_login(client, "tmpl-org-a@example.com")
    headers_b = await _register_and_login(client, "tmpl-org-b@example.com")

    create_resp = await client.post(
        "/api/v1/invoice-templates/",
        json=_template_payload(),
        headers=headers_a,
    )
    template_id = create_resp.json()["id"]

    # Org B cannot get it
    assert (
        await client.get(f"/api/v1/invoice-templates/{template_id}", headers=headers_b)
    ).status_code == 404

    # Org B cannot update it
    assert (
        await client.patch(
            f"/api/v1/invoice-templates/{template_id}",
            json={"is_active": False},
            headers=headers_b,
        )
    ).status_code == 404

    # Org B cannot delete it
    assert (
        await client.delete(f"/api/v1/invoice-templates/{template_id}", headers=headers_b)
    ).status_code == 404

    # Org B's list doesn't include it
    list_resp = await client.get("/api/v1/invoice-templates/", headers=headers_b)
    assert all(t["id"] != template_id for t in list_resp.json()["data"])


# ---------------------------------------------------------------------------
# Role enforcement
# ---------------------------------------------------------------------------


async def test_create_requires_admin(client: AsyncClient, test_engine):
    """Non-admin cannot create templates."""
    headers = await _register_and_login(client, "tmpl-role@example.com")
    user_id = decode_token(headers["Authorization"].removeprefix("Bearer "))["sub"]

    # Downgrade to member
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        from sqlalchemy import text

        await session.execute(
            text("UPDATE users SET role = 'member' WHERE id = :uid"),
            {"uid": user_id},
        )
        await session.commit()

    resp = await client.post(
        "/api/v1/invoice-templates/",
        json=_template_payload(),
        headers=headers,
    )
    assert resp.status_code == 403

    # But can read
    list_resp = await client.get("/api/v1/invoice-templates/", headers=headers)
    assert list_resp.status_code == 200


# ---------------------------------------------------------------------------
# Inactive templates excluded by default
# ---------------------------------------------------------------------------


async def test_list_excludes_inactive_by_default(client: AsyncClient, test_engine):
    """Inactive templates are excluded from list by default."""
    headers = await _register_and_login(client, "tmpl-inactive@example.com")
    create_resp = await client.post(
        "/api/v1/invoice-templates/",
        json=_template_payload(),
        headers=headers,
    )
    template_id = create_resp.json()["id"]

    # Deactivate
    await client.patch(
        f"/api/v1/invoice-templates/{template_id}",
        json={"is_active": False},
        headers=headers,
    )

    # Default list excludes inactive
    resp = await client.get("/api/v1/invoice-templates/", headers=headers)
    assert resp.json()["pagination"]["total"] == 0

    # With active_only=false includes it
    resp = await client.get("/api/v1/invoice-templates/?active_only=false", headers=headers)
    assert resp.json()["pagination"]["total"] == 1
