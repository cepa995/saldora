"""Tests for plan enforcement — feature gates, invoice quota, and member quota."""

import io
from unittest.mock import patch

from httpx import AsyncClient
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app as fastapi_app


def _make_png(width: int = 800, height: int = 600) -> bytes:
    """Create a minimal valid PNG image in memory."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _create_user_with_plan(
    client: AsyncClient,
    email: str,
    plan: str = "free",
) -> dict[str, str]:
    """Register a user, create an organization, set plan, return auth headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Org-{email}"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update org plan directly via DB if not free
    if plan != "free":
        from app.database import get_db

        db_gen = fastapi_app.dependency_overrides[get_db]()
        db: AsyncSession = await db_gen.__anext__()
        await db.execute(
            text(
                "UPDATE organizations SET plan = :plan "
                "WHERE id = (SELECT organization_id FROM users WHERE email = :email)"
            ),
            {"plan": plan, "email": email},
        )
        await db.commit()
        try:
            await db_gen.__anext__()
        except StopAsyncIteration:
            pass

    return headers


# ---------------------------------------------------------------------------
# Feature gate tests
# ---------------------------------------------------------------------------


async def test_free_user_blocked_from_rules(client: AsyncClient):
    """Free user accessing rules endpoints gets 403 with feature_unavailable code."""
    headers = await _create_user_with_plan(client, "free-rules@test.com", "free")
    response = await client.get("/api/v1/rules/", headers=headers)

    assert response.status_code == 403
    body = response.json()
    detail = body["detail"]
    assert detail["code"] == "feature_unavailable"
    assert "Agency" in detail["required_plan"]


async def test_agency_user_can_access_rules(client: AsyncClient):
    """Agency user can access rules endpoints."""
    headers = await _create_user_with_plan(client, "agency-rules@test.com", "agency")
    response = await client.get("/api/v1/rules/", headers=headers)

    assert response.status_code != 403


# ---------------------------------------------------------------------------
# Invoice quota tests
# ---------------------------------------------------------------------------


@patch("app.routers.invoices.upload_document", return_value="fake/key.pdf")
@patch("app.services.email.send_invoice_processed_email", return_value=None)
async def test_free_user_invoice_limit(mock_email, mock_upload, client: AsyncClient):
    """Free user gets 402 after exceeding 10 invoice limit."""
    headers = await _create_user_with_plan(client, "free-quota@test.com", "free")
    png_bytes = _make_png()

    # Upload 10 invoices (free limit)
    for i in range(10):
        resp = await client.post(
            "/api/v1/invoices/upload",
            files={"file": (f"invoice{i}.png", png_bytes, "image/png")},
            headers=headers,
        )
        assert resp.status_code == 202, f"Upload {i + 1} failed: {resp.text}"

    # 11th upload should be rejected with 402
    resp = await client.post(
        "/api/v1/invoices/upload",
        files={"file": ("invoice11.png", png_bytes, "image/png")},
        headers=headers,
    )
    assert resp.status_code == 402
    body = resp.json()
    detail = body["detail"]
    assert detail["code"] == "invoice_limit_exceeded"
    assert detail["limit"] == 10
    assert detail["usage"] >= 10


@patch("app.routers.invoices.upload_document", return_value="fake/key.pdf")
@patch("app.services.email.send_invoice_processed_email", return_value=None)
async def test_starter_user_blocked_at_limit(mock_email, mock_upload, client: AsyncClient):
    """Starter user gets 402 after exceeding 100 invoice limit."""
    headers = await _create_user_with_plan(client, "starter-quota@test.com", "starter")
    png_bytes = _make_png()

    # Upload 100 invoices (starter limit)
    for i in range(100):
        resp = await client.post(
            "/api/v1/invoices/upload",
            files={"file": (f"invoice{i}.png", png_bytes, "image/png")},
            headers=headers,
        )
        assert resp.status_code == 202, f"Upload {i + 1} failed: {resp.text}"

    # 101st upload should be rejected with 402
    resp = await client.post(
        "/api/v1/invoices/upload",
        files={"file": ("invoice101.png", png_bytes, "image/png")},
        headers=headers,
    )
    assert resp.status_code == 402
    body = resp.json()
    detail = body["detail"]
    assert detail["code"] == "invoice_limit_exceeded"
    assert detail["limit"] == 100
    assert detail["required_plan"] == "Pro"


# ---------------------------------------------------------------------------
# Member quota tests
# ---------------------------------------------------------------------------


async def test_free_user_member_limit(client: AsyncClient):
    """Free user (1-member limit) gets 402 when inviting a 2nd member."""
    headers = await _create_user_with_plan(client, "free-member@test.com", "free")

    # Try to invite a second member — should be blocked (free plan: 1 user)
    resp = await client.post(
        "/api/v1/invitations",
        json={"email": "newmember@test.com", "role": "operator"},
        headers=headers,
    )
    assert resp.status_code == 402
    body = resp.json()
    detail = body["detail"]
    assert detail["code"] == "member_limit_exceeded"
    assert detail["limit"] == 1


# ---------------------------------------------------------------------------
# Error message language tests
# ---------------------------------------------------------------------------


async def test_feature_gate_error_is_serbian(client: AsyncClient):
    """Feature gate error messages are in Serbian."""
    headers = await _create_user_with_plan(client, "serbian-test@test.com", "free")
    response = await client.get("/api/v1/rules/", headers=headers)

    assert response.status_code == 403
    body = response.json()
    detail = body["detail"]
    # Check that the message is in Serbian
    assert "plan" in detail["detail"].lower() or "funkcionalnost" in detail["detail"].lower()
