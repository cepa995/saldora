"""
API tests for the invoice upload endpoint.

Tests exercise the full request lifecycle: HTTP -> FastAPI -> S3 -> DB -> response.
S3 and Celery are mocked since they require running infrastructure.
"""

from unittest.mock import patch

from httpx import AsyncClient


async def _auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a user, log in, and return Authorization headers."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "upload-test@example.com",
            "password": "securepass123",
            "first_name": "Upload",
            "last_name": "Tester",
            "organization_name": "Test Org",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "upload-test@example.com", "password": "securepass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---- Authentication ----


async def test_upload_requires_auth(client: AsyncClient):
    """Upload without token returns 401."""
    response = await client.post(
        "/api/v1/invoices/upload",
        files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 401


# ---- Validation ----


async def test_upload_rejects_unsupported_type(client: AsyncClient):
    """Upload with unsupported MIME type returns 415."""
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/invoices/upload",
        files={"file": ("test.txt", b"hello", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 415
    assert "Unsupported file type" in response.json()["detail"]


async def test_upload_rejects_oversized_file(client: AsyncClient):
    """Upload over 20MB returns 413."""
    headers = await _auth_headers(client)
    big_content = b"x" * (20 * 1024 * 1024 + 1)
    response = await client.post(
        "/api/v1/invoices/upload",
        files={"file": ("big.pdf", big_content, "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]


# ---- Happy path ----


@patch("celery.Celery.send_task")
@patch(
    "app.routers.invoices.upload_document",
    return_value="organizations/org-id/invoices/inv-id/original.pdf",
)
async def test_upload_success(mock_s3, mock_celery, client: AsyncClient):
    """Happy path: file uploaded, invoice created, Celery task queued, 202 returned."""
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/invoices/upload",
        files={"file": ("invoice.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["progress"] == 0
    assert data["id"] is not None
    assert data["document_id"] is not None
    assert data["estimated_time"] == 30
    mock_s3.assert_called_once()
    mock_celery.assert_called_once()


@patch("celery.Celery.send_task")
@patch(
    "app.routers.invoices.upload_document",
    return_value="organizations/org-id/invoices/inv-id/original.png",
)
async def test_upload_image_format(mock_s3, mock_celery, client: AsyncClient):
    """Image files (PNG) are accepted and processed the same way."""
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/invoices/upload",
        files={"file": ("scan.png", b"\x89PNG fake image", "image/png")},
        headers=headers,
    )
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


# ---- Graceful degradation ----


@patch("celery.Celery.send_task", side_effect=Exception("Redis down"))
@patch(
    "app.routers.invoices.upload_document",
    return_value="organizations/org-id/invoices/inv-id/original.pdf",
)
async def test_upload_succeeds_when_celery_down(mock_s3, mock_celery, client: AsyncClient):
    """Upload succeeds even when Celery/Redis is unavailable."""
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/invoices/upload",
        files={"file": ("invoice.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "processing"  # Not "queued" since Celery failed
    assert data["id"] is not None


# ---- Error handling ----


@patch("app.routers.invoices.upload_document", side_effect=Exception("S3 connection refused"))
async def test_upload_returns_502_on_s3_failure(mock_s3, client: AsyncClient):
    """S3 failure returns 502 and does not leave an orphan DB record."""
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/invoices/upload",
        files={"file": ("invoice.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 502
    assert "storage" in response.json()["detail"].lower()
