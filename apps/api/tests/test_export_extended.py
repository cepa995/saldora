"""Extended tests for export endpoints: templates CRUD, audit export, MiniMax config.

Covers the portions of apps/api/app/routers/export.py not exercised by
test_exports.py:
- Export template CRUD (POST/GET/PATCH/DELETE /api/v1/export/templates)
- Audit export (POST /audit, GET /audit/preview, GET /audit/history)
- MiniMax config (PUT/GET/PATCH /api/v1/export/minimax/config)
- MiniMax push (POST /api/v1/export/minimax/push)

All tests use the agency plan which unlocks AUDIT_EXPORT, MINIMAX_DIRECT_PUSH,
and every other gated feature.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.models.invoice import Invoice

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _auth_headers(
    client: AsyncClient,
    test_engine,
    email: str = "exp-default@example.com",
    org_name: str = "Exp Org",
    plan: str = "agency",
) -> dict[str, str]:
    """Register a user, create an organization, upgrade plan, and return auth headers.

    Args:
        client: Test HTTP client.
        test_engine: SQLAlchemy async engine from conftest.
        email: Unique e-mail address for the user (use exp-* prefix).
        org_name: Organisation display name (must be unique per test).
        plan: Plan tier to assign (default: agency for full feature access).

    Returns:
        Dict suitable for use as the ``headers`` parameter in httpx calls.
    """
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Exp",
            "last_name": "Tester",
        },
    )
    reg_token = reg.json()["access_token"]
    org = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": org_name},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org.json()["access_token"]

    sf = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as db:
        await db.execute(
            sa_text(f"UPDATE organizations SET plan = '{plan}' WHERE name = '{org_name}'")
        )
        await db.commit()

    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token embedded in auth headers.

    Args:
        headers: Auth headers dict containing the Bearer token.

    Returns:
        Organization UUID as a string.
    """
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


async def _insert_invoice(test_engine, org_id: str, **overrides) -> str:
    """Insert a minimal test invoice directly into the DB.

    Args:
        test_engine: SQLAlchemy async engine (from conftest fixture).
        org_id: Organization UUID string.
        **overrides: Any Invoice column overrides.

    Returns:
        String UUID of the created invoice.
    """
    sf = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as session:
        invoice = Invoice(
            organization_id=org_id,
            status=overrides.get("status", "verified"),
            invoice_number=overrides.get("invoice_number", "INV-001"),
            invoice_date=overrides.get("invoice_date", date(2025, 3, 1)),
            due_date=overrides.get("due_date", date(2025, 4, 1)),
            seller=overrides.get(
                "seller",
                {"pib": "123456789", "name": "Prodavac DOO", "address": "Beograd"},
            ),
            buyer=overrides.get(
                "buyer",
                {"pib": "987654321", "name": "Kupac DOO", "address": "Novi Sad"},
            ),
            subtotal=overrides.get("subtotal", Decimal("10000.00")),
            tax_rate=overrides.get("tax_rate", Decimal("20.00")),
            tax_amount=overrides.get("tax_amount", Decimal("2000.00")),
            total_amount=overrides.get("total_amount", Decimal("12000.00")),
            currency=overrides.get("currency", "RSD"),
            line_items=overrides.get("line_items", []),
            tax_groups=overrides.get("tax_groups", None),
            document_hash=overrides.get("document_hash", uuid4().hex),
            document_path=overrides.get("document_path", "orgs/test/inv/original.pdf"),
            document_content_type=overrides.get("document_content_type", "application/pdf"),
            confidence_score=overrides.get("confidence_score", Decimal("0.95")),
            field_confidence=overrides.get("field_confidence", []),
            warnings=overrides.get("warnings", []),
            ocr_engine=overrides.get("ocr_engine", "dots"),
            processing_time_ms=overrides.get("processing_time_ms", 1000),
            raw_ocr_text=overrides.get("raw_ocr_text", ""),
        )
        session.add(invoice)
        await session.commit()
        await session.refresh(invoice)
        return str(invoice.id)


_VALID_FIELDS = [
    {"key": "invoice_number", "label": "Broj fakture", "order": 1},
    {"key": "total_amount", "label": "Ukupan iznos", "order": 2},
]

_MINIMAX_CONFIG_PAYLOAD = {
    "client_id": "test-client-id",
    "client_secret": "test-client-secret",
    "username": "test-user",
    "password": "test-password",
    "minimax_org_id": 12345,
}


# ---------------------------------------------------------------------------
# Export template — POST (create)
# ---------------------------------------------------------------------------


async def test_create_export_template_success(client: AsyncClient, test_engine):
    """POST /export/templates creates a template and returns 201 with full data."""
    headers = await _auth_headers(
        client, test_engine, "exp-tmpl-create@example.com", "ExpTmplCreate"
    )
    resp = await client.post(
        "/api/v1/export/templates",
        headers=headers,
        json={
            "name": "Moj sablon",
            "description": "Test sablon",
            "fields": _VALID_FIELDS,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Moj sablon"
    assert data["description"] == "Test sablon"
    assert len(data["fields"]) == 2
    assert data["is_default"] is False
    assert "id" in data


async def test_create_export_template_invalid_field_key(client: AsyncClient, test_engine):
    """POST /export/templates rejects unknown field keys with 422."""
    headers = await _auth_headers(
        client, test_engine, "exp-tmpl-badkey@example.com", "ExpTmplBadKey"
    )
    resp = await client.post(
        "/api/v1/export/templates",
        headers=headers,
        json={
            "name": "Bad sablon",
            "fields": [{"key": "non_existent_field", "label": "X", "order": 1}],
        },
    )
    assert resp.status_code == 422
    assert "non_existent_field" in resp.json()["detail"]


async def test_create_export_template_requires_auth(client: AsyncClient, test_engine):
    """POST /export/templates without auth returns 401."""
    resp = await client.post(
        "/api/v1/export/templates",
        json={"name": "No auth", "fields": _VALID_FIELDS},
    )
    assert resp.status_code == 401


async def test_create_export_template_with_format_options(client: AsyncClient, test_engine):
    """POST /export/templates accepts date_format and decimal_separator overrides."""
    headers = await _auth_headers(client, test_engine, "exp-tmpl-opts@example.com", "ExpTmplOpts")
    resp = await client.post(
        "/api/v1/export/templates",
        headers=headers,
        json={
            "name": "Sablon sa opcijama",
            "fields": _VALID_FIELDS,
            "date_format": "YYYY-MM-DD",
            "decimal_separator": ".",
            "supported_formats": ["xlsx", "csv"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["date_format"] == "YYYY-MM-DD"
    assert data["decimal_separator"] == "."
    assert data["supported_formats"] == ["xlsx", "csv"]


# ---------------------------------------------------------------------------
# Export template — GET list
# ---------------------------------------------------------------------------


async def test_list_export_templates_returns_created(client: AsyncClient, test_engine):
    """GET /export/templates includes the template just created."""
    headers = await _auth_headers(client, test_engine, "exp-tmpl-list@example.com", "ExpTmplList")
    # Create one template
    await client.post(
        "/api/v1/export/templates",
        headers=headers,
        json={"name": "Moj sablon za listu", "fields": _VALID_FIELDS},
    )
    resp = await client.get("/api/v1/export/templates", headers=headers)
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "Moj sablon za listu" in names


async def test_list_export_templates_requires_auth(client: AsyncClient, test_engine):
    """GET /export/templates without auth returns 401."""
    resp = await client.get("/api/v1/export/templates")
    assert resp.status_code == 401


async def test_list_export_templates_org_isolation(client: AsyncClient, test_engine):
    """Templates from another org are not returned in the listing."""
    headers_a = await _auth_headers(
        client, test_engine, "exp-tmpl-isol-a@example.com", "ExpTmplIsolA"
    )
    headers_b = await _auth_headers(
        client, test_engine, "exp-tmpl-isol-b@example.com", "ExpTmplIsolB"
    )

    # Org A creates a template
    await client.post(
        "/api/v1/export/templates",
        headers=headers_a,
        json={"name": "Sablon Org A", "fields": _VALID_FIELDS},
    )

    # Org B should not see Org A's template
    resp = await client.get("/api/v1/export/templates", headers=headers_b)
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "Sablon Org A" not in names


# ---------------------------------------------------------------------------
# Export template — GET single
# ---------------------------------------------------------------------------


async def test_get_export_template_success(client: AsyncClient, test_engine):
    """GET /export/templates/{id} returns the template for the owning org."""
    headers = await _auth_headers(client, test_engine, "exp-tmpl-get@example.com", "ExpTmplGet")
    create_resp = await client.post(
        "/api/v1/export/templates",
        headers=headers,
        json={"name": "Get me", "fields": _VALID_FIELDS},
    )
    tmpl_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/export/templates/{tmpl_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == tmpl_id
    assert resp.json()["name"] == "Get me"


async def test_get_export_template_not_found(client: AsyncClient, test_engine):
    """GET /export/templates/{id} returns 404 for unknown ID."""
    headers = await _auth_headers(client, test_engine, "exp-tmpl-404@example.com", "ExpTmpl404")
    resp = await client.get(f"/api/v1/export/templates/{uuid4()}", headers=headers)
    assert resp.status_code == 404


async def test_get_export_template_other_org_returns_404(client: AsyncClient, test_engine):
    """GET /export/templates/{id} returns 404 when the template belongs to another org."""
    headers_a = await _auth_headers(
        client, test_engine, "exp-tmpl-xorg-a@example.com", "ExpTmplXOrgA"
    )
    headers_b = await _auth_headers(
        client, test_engine, "exp-tmpl-xorg-b@example.com", "ExpTmplXOrgB"
    )

    create_resp = await client.post(
        "/api/v1/export/templates",
        headers=headers_a,
        json={"name": "Org A only", "fields": _VALID_FIELDS},
    )
    tmpl_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/export/templates/{tmpl_id}", headers=headers_b)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Export template — PATCH (update)
# ---------------------------------------------------------------------------


async def test_update_export_template_success(client: AsyncClient, test_engine):
    """PATCH /export/templates/{id} updates name and returns updated data."""
    headers = await _auth_headers(client, test_engine, "exp-tmpl-upd@example.com", "ExpTmplUpd")
    create_resp = await client.post(
        "/api/v1/export/templates",
        headers=headers,
        json={"name": "Originalno ime", "fields": _VALID_FIELDS},
    )
    tmpl_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/export/templates/{tmpl_id}",
        headers=headers,
        json={"name": "Izmenjeno ime"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Izmenjeno ime"


async def test_update_export_template_invalid_field_key(client: AsyncClient, test_engine):
    """PATCH /export/templates/{id} with unknown field key returns 422."""
    headers = await _auth_headers(
        client, test_engine, "exp-tmpl-upd-key@example.com", "ExpTmplUpdKey"
    )
    create_resp = await client.post(
        "/api/v1/export/templates",
        headers=headers,
        json={"name": "Za update", "fields": _VALID_FIELDS},
    )
    tmpl_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/export/templates/{tmpl_id}",
        headers=headers,
        json={"fields": [{"key": "bad_field", "label": "X", "order": 1}]},
    )
    assert resp.status_code == 422
    assert "bad_field" in resp.json()["detail"]


async def test_update_export_template_not_found(client: AsyncClient, test_engine):
    """PATCH /export/templates/{id} returns 404 for unknown ID."""
    headers = await _auth_headers(
        client, test_engine, "exp-tmpl-upd-404@example.com", "ExpTmplUpd404"
    )
    resp = await client.patch(
        f"/api/v1/export/templates/{uuid4()}",
        headers=headers,
        json={"name": "X"},
    )
    assert resp.status_code == 404


async def test_update_export_template_other_org_returns_404(client: AsyncClient, test_engine):
    """PATCH /export/templates/{id} returns 404 for another org's template."""
    headers_a = await _auth_headers(
        client, test_engine, "exp-tmpl-upd-xa@example.com", "ExpTmplUpdXA"
    )
    headers_b = await _auth_headers(
        client, test_engine, "exp-tmpl-upd-xb@example.com", "ExpTmplUpdXB"
    )

    create_resp = await client.post(
        "/api/v1/export/templates",
        headers=headers_a,
        json={"name": "Org A template", "fields": _VALID_FIELDS},
    )
    tmpl_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/export/templates/{tmpl_id}",
        headers=headers_b,
        json={"name": "Hijack"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Export template — DELETE
# ---------------------------------------------------------------------------


async def test_delete_export_template_success(client: AsyncClient, test_engine):
    """DELETE /export/templates/{id} removes the template and returns 204."""
    headers = await _auth_headers(client, test_engine, "exp-tmpl-del@example.com", "ExpTmplDel")
    create_resp = await client.post(
        "/api/v1/export/templates",
        headers=headers,
        json={"name": "Za brisanje", "fields": _VALID_FIELDS},
    )
    tmpl_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/export/templates/{tmpl_id}", headers=headers)
    assert del_resp.status_code == 204

    # Confirm it is gone
    get_resp = await client.get(f"/api/v1/export/templates/{tmpl_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_delete_export_template_not_found(client: AsyncClient, test_engine):
    """DELETE /export/templates/{id} returns 404 for unknown ID."""
    headers = await _auth_headers(
        client, test_engine, "exp-tmpl-del404@example.com", "ExpTmplDel404"
    )
    resp = await client.delete(f"/api/v1/export/templates/{uuid4()}", headers=headers)
    assert resp.status_code == 404


async def test_delete_export_template_other_org_returns_404(client: AsyncClient, test_engine):
    """DELETE /export/templates/{id} returns 404 for another org's template."""
    headers_a = await _auth_headers(
        client, test_engine, "exp-tmpl-del-xa@example.com", "ExpTmplDelXA"
    )
    headers_b = await _auth_headers(
        client, test_engine, "exp-tmpl-del-xb@example.com", "ExpTmplDelXB"
    )

    create_resp = await client.post(
        "/api/v1/export/templates",
        headers=headers_a,
        json={"name": "Org A za brisanje", "fields": _VALID_FIELDS},
    )
    tmpl_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/export/templates/{tmpl_id}", headers=headers_b)
    assert resp.status_code == 404

    # The original is still accessible by its owner
    get_resp = await client.get(f"/api/v1/export/templates/{tmpl_id}", headers=headers_a)
    assert get_resp.status_code == 200


async def test_delete_export_template_requires_auth(client: AsyncClient, test_engine):
    """DELETE /export/templates/{id} without auth returns 401."""
    resp = await client.delete(f"/api/v1/export/templates/{uuid4()}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Audit export — GET /audit/preview
# ---------------------------------------------------------------------------


async def test_audit_preview_empty_range(client: AsyncClient, test_engine):
    """GET /audit/preview returns zero count when no invoices exist in range."""
    headers = await _auth_headers(client, test_engine, "exp-audit-prev@example.com", "ExpAuditPrev")
    resp = await client.get(
        "/api/v1/export/audit/preview?date_from=2020-01-01&date_to=2020-12-31",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["invoice_count"] == 0


async def test_audit_preview_with_invoices(client: AsyncClient, test_engine):
    """GET /audit/preview counts invoices in the requested date range."""
    headers = await _auth_headers(
        client, test_engine, "exp-audit-prev2@example.com", "ExpAuditPrev2"
    )
    org_id = _get_org_id(headers)

    # Two invoices inside the range, one outside
    await _insert_invoice(test_engine, org_id, invoice_date=date(2025, 1, 10))
    await _insert_invoice(test_engine, org_id, invoice_date=date(2025, 1, 20))
    await _insert_invoice(test_engine, org_id, invoice_date=date(2026, 6, 1))

    resp = await client.get(
        "/api/v1/export/audit/preview?date_from=2025-01-01&date_to=2025-12-31",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["invoice_count"] == 2


async def test_audit_preview_requires_auth(client: AsyncClient, test_engine):
    """GET /audit/preview without auth returns 401."""
    resp = await client.get("/api/v1/export/audit/preview?date_from=2025-01-01&date_to=2025-12-31")
    assert resp.status_code == 401


async def test_audit_preview_invalid_dates_returns_zero(client: AsyncClient, test_engine):
    """GET /audit/preview with malformed dates returns invoice_count 0."""
    headers = await _auth_headers(
        client, test_engine, "exp-audit-inv-dt@example.com", "ExpAuditInvDt"
    )
    resp = await client.get(
        "/api/v1/export/audit/preview?date_from=not-a-date&date_to=also-bad",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["invoice_count"] == 0


# ---------------------------------------------------------------------------
# Audit export — POST /audit (create)
# ---------------------------------------------------------------------------


async def test_create_audit_export_success(client: AsyncClient, test_engine):
    """POST /audit creates an export record and returns download URL."""
    headers = await _auth_headers(
        client, test_engine, "exp-audit-create@example.com", "ExpAuditCreate"
    )
    org_id = _get_org_id(headers)
    await _insert_invoice(test_engine, org_id, invoice_date=date(2025, 3, 15))

    mock_result = {
        "download_url": "https://s3.example.com/audit.zip",
        "file_size": 4096,
        "invoice_count": 1,
        "period": {"from": "2025-01-01", "to": "2025-12-31"},
        "s3_key": f"organizations/{org_id}/exports/audit_2025-01-01_2025-12-31.zip",
    }

    with patch(
        "app.routers.export.generate_audit_export",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = await client.post(
            "/api/v1/export/audit",
            headers=headers,
            json={
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
                "reason": "Poreska kontrola",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["download_url"] == "https://s3.example.com/audit.zip"
    assert data["file_size"] == 4096
    assert data["invoice_count"] == 1
    assert data["reason"] == "Poreska kontrola"
    assert "id" in data


async def test_create_audit_export_date_from_after_date_to(client: AsyncClient, test_engine):
    """POST /audit with date_from after date_to returns 400."""
    headers = await _auth_headers(
        client, test_engine, "exp-audit-dates@example.com", "ExpAuditDates"
    )
    resp = await client.post(
        "/api/v1/export/audit",
        headers=headers,
        json={"date_from": "2025-12-31", "date_to": "2025-01-01"},
    )
    assert resp.status_code == 400


async def test_create_audit_export_invalid_date_format(client: AsyncClient, test_engine):
    """POST /audit with invalid date string returns 400."""
    headers = await _auth_headers(
        client, test_engine, "exp-audit-baddt@example.com", "ExpAuditBadDt"
    )
    resp = await client.post(
        "/api/v1/export/audit",
        headers=headers,
        json={"date_from": "01/01/2025", "date_to": "31/12/2025"},
    )
    assert resp.status_code == 400
    assert "YYYY-MM-DD" in resp.json()["detail"]


async def test_create_audit_export_requires_auth(client: AsyncClient, test_engine):
    """POST /audit without auth returns 401."""
    resp = await client.post(
        "/api/v1/export/audit",
        json={"date_from": "2025-01-01", "date_to": "2025-12-31"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Audit export — GET /audit/history
# ---------------------------------------------------------------------------


async def test_list_audit_exports_empty(client: AsyncClient, test_engine):
    """GET /audit/history returns empty list when no exports exist."""
    headers = await _auth_headers(client, test_engine, "exp-audit-hist@example.com", "ExpAuditHist")
    resp = await client.get("/api/v1/export/audit/history", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_audit_exports_returns_created(client: AsyncClient, test_engine):
    """GET /audit/history returns a record created via POST /audit."""
    headers = await _auth_headers(
        client, test_engine, "exp-audit-hist2@example.com", "ExpAuditHist2"
    )
    org_id = _get_org_id(headers)

    mock_result = {
        "download_url": "https://s3.example.com/audit2.zip",
        "file_size": 2048,
        "invoice_count": 0,
        "period": {"from": "2024-01-01", "to": "2024-12-31"},
        "s3_key": f"organizations/{org_id}/exports/audit_2024-01-01_2024-12-31.zip",
    }

    with patch(
        "app.routers.export.generate_audit_export",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        await client.post(
            "/api/v1/export/audit",
            headers=headers,
            json={"date_from": "2024-01-01", "date_to": "2024-12-31"},
        )

    with patch("app.routers.export.get_presigned_url", return_value="https://s3.example.com/new"):
        resp = await client.get("/api/v1/export/audit/history", headers=headers)

    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 1
    assert records[0]["status"] == "ready"


async def test_list_audit_exports_requires_auth(client: AsyncClient, test_engine):
    """GET /audit/history without auth returns 401."""
    resp = await client.get("/api/v1/export/audit/history")
    assert resp.status_code == 401


async def test_list_audit_exports_org_isolation(client: AsyncClient, test_engine):
    """GET /audit/history only returns records for the authenticated org."""
    headers_a = await _auth_headers(
        client, test_engine, "exp-audit-isol-a@example.com", "ExpAuditIsolA"
    )
    headers_b = await _auth_headers(
        client, test_engine, "exp-audit-isol-b@example.com", "ExpAuditIsolB"
    )
    org_a = _get_org_id(headers_a)

    mock_result = {
        "download_url": "https://s3.example.com/a.zip",
        "file_size": 512,
        "invoice_count": 0,
        "period": {"from": "2024-01-01", "to": "2024-06-30"},
        "s3_key": f"organizations/{org_a}/exports/audit_2024-01-01_2024-06-30.zip",
    }
    with patch(
        "app.routers.export.generate_audit_export",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        await client.post(
            "/api/v1/export/audit",
            headers=headers_a,
            json={"date_from": "2024-01-01", "date_to": "2024-06-30"},
        )

    resp = await client.get("/api/v1/export/audit/history", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# MiniMax config — PUT (upsert)
# ---------------------------------------------------------------------------


async def test_upsert_minimax_config_create(client: AsyncClient, test_engine):
    """PUT /export/minimax/config creates a new config and returns it."""
    headers = await _auth_headers(client, test_engine, "exp-mm-put@example.com", "ExpMmPut")
    resp = await client.put(
        "/api/v1/export/minimax/config",
        headers=headers,
        json=_MINIMAX_CONFIG_PAYLOAD,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["client_id"] == "test-client-id"
    assert data["username"] == "test-user"
    assert data["minimax_org_id"] == 12345
    assert data["is_active"] is True
    assert "id" in data


async def test_upsert_minimax_config_update(client: AsyncClient, test_engine):
    """PUT /export/minimax/config updates existing config when called twice."""
    headers = await _auth_headers(client, test_engine, "exp-mm-put2@example.com", "ExpMmPut2")
    # First call — create
    await client.put(
        "/api/v1/export/minimax/config",
        headers=headers,
        json=_MINIMAX_CONFIG_PAYLOAD,
    )
    # Second call — update with different org ID
    resp = await client.put(
        "/api/v1/export/minimax/config",
        headers=headers,
        json={**_MINIMAX_CONFIG_PAYLOAD, "minimax_org_id": 99999},
    )
    assert resp.status_code == 200
    assert resp.json()["minimax_org_id"] == 99999


async def test_upsert_minimax_config_requires_auth(client: AsyncClient, test_engine):
    """PUT /export/minimax/config without auth returns 401."""
    resp = await client.put(
        "/api/v1/export/minimax/config",
        json=_MINIMAX_CONFIG_PAYLOAD,
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# MiniMax config — GET
# ---------------------------------------------------------------------------


async def test_get_minimax_config_success(client: AsyncClient, test_engine):
    """GET /export/minimax/config returns config after it was created via PUT."""
    headers = await _auth_headers(client, test_engine, "exp-mm-get@example.com", "ExpMmGet")
    await client.put(
        "/api/v1/export/minimax/config",
        headers=headers,
        json=_MINIMAX_CONFIG_PAYLOAD,
    )

    resp = await client.get("/api/v1/export/minimax/config", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["client_id"] == "test-client-id"
    assert data["minimax_org_id"] == 12345


async def test_get_minimax_config_not_found(client: AsyncClient, test_engine):
    """GET /export/minimax/config returns 404 when no config has been set."""
    headers = await _auth_headers(client, test_engine, "exp-mm-get404@example.com", "ExpMmGet404")
    resp = await client.get("/api/v1/export/minimax/config", headers=headers)
    assert resp.status_code == 404


async def test_get_minimax_config_requires_auth(client: AsyncClient, test_engine):
    """GET /export/minimax/config without auth returns 401."""
    resp = await client.get("/api/v1/export/minimax/config")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# MiniMax config — PATCH (partial update)
# ---------------------------------------------------------------------------


async def test_patch_minimax_config_updates_field(client: AsyncClient, test_engine):
    """PATCH /export/minimax/config changes a single field without touching others."""
    headers = await _auth_headers(client, test_engine, "exp-mm-patch@example.com", "ExpMmPatch")
    await client.put(
        "/api/v1/export/minimax/config",
        headers=headers,
        json=_MINIMAX_CONFIG_PAYLOAD,
    )

    resp = await client.patch(
        "/api/v1/export/minimax/config",
        headers=headers,
        json={"minimax_org_id": 77777},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["minimax_org_id"] == 77777
    assert data["client_id"] == "test-client-id"  # unchanged


async def test_patch_minimax_config_deactivate(client: AsyncClient, test_engine):
    """PATCH /export/minimax/config with is_active=False deactivates config."""
    headers = await _auth_headers(client, test_engine, "exp-mm-deact@example.com", "ExpMmDeact")
    await client.put(
        "/api/v1/export/minimax/config",
        headers=headers,
        json=_MINIMAX_CONFIG_PAYLOAD,
    )

    resp = await client.patch(
        "/api/v1/export/minimax/config",
        headers=headers,
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_patch_minimax_config_not_found(client: AsyncClient, test_engine):
    """PATCH /export/minimax/config returns 404 when no config exists."""
    headers = await _auth_headers(
        client, test_engine, "exp-mm-patch404@example.com", "ExpMmPatch404"
    )
    resp = await client.patch(
        "/api/v1/export/minimax/config",
        headers=headers,
        json={"minimax_org_id": 1},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# MiniMax push — POST /export/minimax/push
# ---------------------------------------------------------------------------


async def test_minimax_push_success(client: AsyncClient, test_engine):
    """POST /export/minimax/push pushes invoices and returns success results."""
    headers = await _auth_headers(client, test_engine, "exp-mm-push@example.com", "ExpMmPush")
    org_id = _get_org_id(headers)

    # Create config
    await client.put(
        "/api/v1/export/minimax/config",
        headers=headers,
        json=_MINIMAX_CONFIG_PAYLOAD,
    )

    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        status="verified",
        seller={"pib": "111222333", "name": "Seller DOO", "address": "Beograd"},
    )

    mock_customer = {"CustomerId": 42}
    mock_currency = None
    # MiniMax POST returns [] on success
    mock_push_response = []
    # The code then fetches all invoices to find the ID
    mock_all_invoices = {
        "Rows": [{"ReceivedInvoiceId": 9001, "DocumentReference": "RE-2026-001"}]
    }

    mock_client = MagicMock()
    mock_client.find_or_create_customer = AsyncMock(return_value=mock_customer)
    mock_client.get_currency = AsyncMock(return_value=mock_currency)
    mock_client.push_received_invoice = AsyncMock(return_value=mock_push_response)
    mock_client._request = AsyncMock(return_value=mock_all_invoices)

    with patch("app.routers.export.MiniMaxClient", return_value=mock_client):
        resp = await client.post(
            "/api/v1/export/minimax/push",
            headers=headers,
            json={"invoice_ids": [inv_id]},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["success_count"] == 1
    assert data["error_count"] == 0
    assert data["results"][0]["status"] == "success"


async def test_minimax_push_missing_pib(client: AsyncClient, test_engine):
    """POST /export/minimax/push records error when seller PIB is missing."""
    headers = await _auth_headers(client, test_engine, "exp-mm-nopib@example.com", "ExpMmNoPib")
    org_id = _get_org_id(headers)

    await client.put(
        "/api/v1/export/minimax/config",
        headers=headers,
        json=_MINIMAX_CONFIG_PAYLOAD,
    )

    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        status="verified",
        seller={"name": "Bez PIB-a", "address": "Beograd"},  # no pib key
    )

    mock_client = MagicMock()
    with patch("app.routers.export.MiniMaxClient", return_value=mock_client):
        resp = await client.post(
            "/api/v1/export/minimax/push",
            headers=headers,
            json={"invoice_ids": [inv_id]},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["error_count"] == 1
    assert data["results"][0]["status"] == "error"
    assert "PIB" in data["results"][0]["error"]


async def test_minimax_push_no_config_returns_404(client: AsyncClient, test_engine):
    """POST /export/minimax/push returns 404 when MiniMax config is absent."""
    headers = await _auth_headers(client, test_engine, "exp-mm-nocfg@example.com", "ExpMmNoCfg")
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id)

    resp = await client.post(
        "/api/v1/export/minimax/push",
        headers=headers,
        json={"invoice_ids": [inv_id]},
    )
    assert resp.status_code == 404


async def test_minimax_push_invoice_not_found(client: AsyncClient, test_engine):
    """POST /export/minimax/push returns 404 for unknown invoice ID."""
    headers = await _auth_headers(client, test_engine, "exp-mm-inv404@example.com", "ExpMmInv404")
    await client.put(
        "/api/v1/export/minimax/config",
        headers=headers,
        json=_MINIMAX_CONFIG_PAYLOAD,
    )

    resp = await client.post(
        "/api/v1/export/minimax/push",
        headers=headers,
        json={"invoice_ids": [str(uuid4())]},
    )
    assert resp.status_code == 404


async def test_minimax_push_requires_auth(client: AsyncClient, test_engine):
    """POST /export/minimax/push without auth returns 401."""
    resp = await client.post(
        "/api/v1/export/minimax/push",
        json={"invoice_ids": [str(uuid4())]},
    )
    assert resp.status_code == 401
