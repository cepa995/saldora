"""Tests for organization settings endpoints."""

from io import BytesIO
from unittest.mock import patch

from httpx import AsyncClient


async def _auth_headers(
    client: AsyncClient,
    email: str = "test@example.com",
    org_name: str = "Test Org",
) -> dict[str, str]:
    """Register a user, create an organization, return auth headers."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    token = reg.json()["access_token"]
    org = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": org_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"Authorization": f"Bearer {org.json()['access_token']}"}


# ---------------------------------------------------------------------------
# GET /api/v1/organizations/current
# ---------------------------------------------------------------------------


async def test_get_current_organization_success(client: AsyncClient):
    """GET /api/v1/organizations/current returns the current organization details."""
    headers = await _auth_headers(client, "org-get@example.com", "Org Get Test")

    with patch("app.routers.organizations.get_presigned_url", return_value=None):
        resp = await client.get("/api/v1/organizations/current", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Org Get Test"
    assert "id" in data
    assert "slug" in data
    assert "plan" in data
    assert "settings" in data


async def test_get_current_organization_returns_correct_fields(client: AsyncClient):
    """GET /api/v1/organizations/current response includes all required fields."""
    headers = await _auth_headers(client, "org-fields@example.com", "Org Fields Test")

    with patch("app.routers.organizations.get_presigned_url", return_value=None):
        resp = await client.get("/api/v1/organizations/current", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    required_fields = {"id", "name", "slug", "plan", "settings"}
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


async def test_get_current_organization_requires_auth(client: AsyncClient):
    """GET /api/v1/organizations/current without token returns 401."""
    resp = await client.get("/api/v1/organizations/current")
    assert resp.status_code == 401


async def test_get_current_organization_slug_from_name(client: AsyncClient):
    """GET /api/v1/organizations/current returns a slug derived from the org name."""
    headers = await _auth_headers(client, "org-slug@example.com", "Slug Test Company")

    with patch("app.routers.organizations.get_presigned_url", return_value=None):
        resp = await client.get("/api/v1/organizations/current", headers=headers)

    assert resp.status_code == 200
    # Slug should be derived from "Slug Test Company"
    assert "slug-test-company" in resp.json()["slug"]


# ---------------------------------------------------------------------------
# PATCH /api/v1/organizations/current
# ---------------------------------------------------------------------------


async def test_update_organization_name(client: AsyncClient):
    """PATCH /api/v1/organizations/current updates the org name and slug."""
    headers = await _auth_headers(client, "org-update-name@example.com", "Before Update")

    with patch("app.routers.organizations.get_presigned_url", return_value=None):
        resp = await client.patch(
            "/api/v1/organizations/current",
            json={"name": "After Update"},
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "After Update"
    assert "after-update" in data["slug"]


async def test_update_organization_billing_email(client: AsyncClient):
    """PATCH /api/v1/organizations/current updates the billing email."""
    headers = await _auth_headers(client, "org-billing@example.com", "Billing Org")

    with patch("app.routers.organizations.get_presigned_url", return_value=None):
        resp = await client.patch(
            "/api/v1/organizations/current",
            json={"billing_email": "billing@company.com"},
            headers=headers,
        )

    assert resp.status_code == 200
    assert resp.json()["billing_email"] == "billing@company.com"


async def test_update_organization_pib(client: AsyncClient):
    """PATCH /api/v1/organizations/current updates the PIB."""
    headers = await _auth_headers(client, "org-pib@example.com", "PIB Org")

    with patch("app.routers.organizations.get_presigned_url", return_value=None):
        resp = await client.patch(
            "/api/v1/organizations/current",
            json={"pib": "123456789"},
            headers=headers,
        )

    assert resp.status_code == 200
    assert resp.json()["pib"] == "123456789"


async def test_update_organization_settings(client: AsyncClient):
    """PATCH /api/v1/organizations/current updates custom settings dict."""
    headers = await _auth_headers(client, "org-settings@example.com", "Settings Org")

    with patch("app.routers.organizations.get_presigned_url", return_value=None):
        resp = await client.patch(
            "/api/v1/organizations/current",
            json={"settings": {"currency": "RSD", "language": "sr"}},
            headers=headers,
        )

    assert resp.status_code == 200
    settings = resp.json()["settings"]
    assert settings["currency"] == "RSD"
    assert settings["language"] == "sr"


async def test_update_organization_requires_auth(client: AsyncClient):
    """PATCH /api/v1/organizations/current without token returns 401."""
    resp = await client.patch(
        "/api/v1/organizations/current",
        json={"name": "No Auth"},
    )
    assert resp.status_code == 401


async def test_update_organization_empty_body_is_noop(client: AsyncClient):
    """PATCH /api/v1/organizations/current with empty body returns unchanged org."""
    headers = await _auth_headers(client, "org-noop@example.com", "Noop Org")

    with patch("app.routers.organizations.get_presigned_url", return_value=None):
        original = await client.get("/api/v1/organizations/current", headers=headers)
        resp = await client.patch(
            "/api/v1/organizations/current",
            json={},
            headers=headers,
        )

    assert resp.status_code == 200
    assert resp.json()["name"] == original.json()["name"]
    assert resp.json()["slug"] == original.json()["slug"]


# ---------------------------------------------------------------------------
# POST /api/v1/organizations/current/logo
# ---------------------------------------------------------------------------


async def test_upload_logo_success(client: AsyncClient):
    """POST /api/v1/organizations/current/logo uploads a PNG logo successfully."""
    headers = await _auth_headers(client, "org-logo-upload@example.com", "Logo Upload Org")

    fake_logo = BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    with (
        patch(
            "app.routers.organizations.upload_logo",
            return_value="organizations/abc/logo.png",
        ) as mock_upload,
        patch(
            "app.routers.organizations.get_presigned_url",
            return_value="https://s3.example.com/logo.png",
        ),
        patch("app.routers.organizations.delete_document"),
    ):
        resp = await client.post(
            "/api/v1/organizations/current/logo",
            headers=headers,
            files={"file": ("logo.png", fake_logo, "image/png")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "logo_url" in data
    assert data["logo_url"] == "https://s3.example.com/logo.png"
    mock_upload.assert_called_once()


async def test_upload_logo_jpeg_accepted(client: AsyncClient):
    """POST /api/v1/organizations/current/logo accepts JPEG files."""
    headers = await _auth_headers(client, "org-logo-jpeg@example.com", "Logo JPEG Org")

    fake_jpeg = BytesIO(b"\xff\xd8\xff" + b"\x00" * 100)

    with (
        patch(
            "app.routers.organizations.upload_logo",
            return_value="organizations/abc/logo.jpg",
        ),
        patch(
            "app.routers.organizations.get_presigned_url",
            return_value="https://s3.example.com/logo.jpg",
        ),
        patch("app.routers.organizations.delete_document"),
    ):
        resp = await client.post(
            "/api/v1/organizations/current/logo",
            headers=headers,
            files={"file": ("logo.jpg", fake_jpeg, "image/jpeg")},
        )

    assert resp.status_code == 200
    assert "logo_url" in resp.json()


async def test_upload_logo_invalid_content_type(client: AsyncClient):
    """POST /api/v1/organizations/current/logo rejects non-image files."""
    headers = await _auth_headers(client, "org-logo-invalid@example.com", "Logo Invalid Org")

    fake_pdf = BytesIO(b"%PDF-1.4 test content")

    resp = await client.post(
        "/api/v1/organizations/current/logo",
        headers=headers,
        files={"file": ("document.pdf", fake_pdf, "application/pdf")},
    )

    assert resp.status_code == 400
    assert "png" in resp.json()["detail"].lower() or "jpg" in resp.json()["detail"].lower()


async def test_upload_logo_file_too_large(client: AsyncClient):
    """POST /api/v1/organizations/current/logo rejects files exceeding 2 MB."""
    headers = await _auth_headers(client, "org-logo-large@example.com", "Logo Large Org")

    # Create a file that exceeds the 2 MB limit
    oversized = BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * (2 * 1024 * 1024 + 1))

    resp = await client.post(
        "/api/v1/organizations/current/logo",
        headers=headers,
        files={"file": ("big.png", oversized, "image/png")},
    )

    assert resp.status_code == 400
    assert "2 mb" in resp.json()["detail"].lower() or "size" in resp.json()["detail"].lower()


async def test_upload_logo_requires_auth(client: AsyncClient):
    """POST /api/v1/organizations/current/logo without token returns 401."""
    fake_logo = BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    resp = await client.post(
        "/api/v1/organizations/current/logo",
        files={"file": ("logo.png", fake_logo, "image/png")},
    )

    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/v1/organizations/current/logo
# ---------------------------------------------------------------------------


async def test_delete_logo_success(client: AsyncClient, test_engine):
    """DELETE /api/v1/organizations/current/logo removes the logo when one exists."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.auth import decode_token

    headers = await _auth_headers(client, "org-logo-delete@example.com", "Logo Delete Org")
    token = headers["Authorization"].removeprefix("Bearer ")
    org_id = decode_token(token)["org"]

    # Set a fake logo_key directly in the DB
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            text("UPDATE organizations SET logo_key = :key WHERE id = :org_id"),
            {"key": "organizations/abc/logo.png", "org_id": org_id},
        )
        await session.commit()

    with patch("app.routers.organizations.delete_document") as mock_delete:
        resp = await client.delete(
            "/api/v1/organizations/current/logo",
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    mock_delete.assert_called_once_with("organizations/abc/logo.png")


async def test_delete_logo_when_no_logo_exists(client: AsyncClient):
    """DELETE /api/v1/organizations/current/logo returns 200 even when no logo set."""
    headers = await _auth_headers(client, "org-logo-nologo@example.com", "No Logo Org")

    with patch("app.routers.organizations.delete_document") as mock_delete:
        resp = await client.delete(
            "/api/v1/organizations/current/logo",
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    # S3 delete should NOT be called when no logo_key exists
    mock_delete.assert_not_called()


async def test_delete_logo_requires_auth(client: AsyncClient):
    """DELETE /api/v1/organizations/current/logo without token returns 401."""
    resp = await client.delete("/api/v1/organizations/current/logo")
    assert resp.status_code == 401
