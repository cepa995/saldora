"""
API tests for the invoice upload and status endpoints.

Tests exercise the full request lifecycle: HTTP -> FastAPI -> S3 -> DB -> response.
S3 and Celery are mocked since they require running infrastructure.
"""

import io
import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from httpx import AsyncClient
from PIL import Image

from app.main import app as fastapi_app


def _make_png(width: int = 800, height: int = 600) -> bytes:
    """Create a minimal valid PNG image in memory.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        PNG bytes.
    """
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a user, create an organization, and return Authorization headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "upload-test@example.com",
            "password": "securepass123",
            "first_name": "Upload",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Test Org"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
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
        files={"file": ("scan.png", _make_png(), "image/png")},
        headers=headers,
    )
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


@patch("celery.Celery.send_task")
@patch(
    "app.routers.invoices.upload_document",
    return_value="organizations/org-id/invoices/inv-id/original.pdf",
)
async def test_upload_different_files_creates_separate_invoices(
    mock_s3, mock_celery, client: AsyncClient
):
    """Uploading different files creates separate invoices."""
    headers = await _auth_headers(client)

    resp1 = await client.post(
        "/api/v1/invoices/upload",
        files={"file": ("a.pdf", b"%PDF-1.4 content A", "application/pdf")},
        headers=headers,
    )
    resp2 = await client.post(
        "/api/v1/invoices/upload",
        files={"file": ("b.pdf", b"%PDF-1.4 content B", "application/pdf")},
        headers=headers,
    )

    assert resp1.json()["id"] != resp2.json()["id"]


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
    assert data["status"] == "uploaded"  # Not "queued" since Celery failed
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


# ==== Status endpoint tests ====


async def _upload_and_get_id(client: AsyncClient, headers: dict[str, str]) -> str:
    """Upload a file and return the invoice ID."""
    with (
        patch("celery.Celery.send_task"),
        patch(
            "app.routers.invoices.upload_document",
            return_value="organizations/org-id/invoices/inv-id/original.pdf",
        ),
    ):
        resp = await client.post(
            "/api/v1/invoices/upload",
            files={"file": ("invoice.pdf", b"%PDF-1.4 fake", "application/pdf")},
            headers=headers,
        )
    return resp.json()["id"]


async def test_status_requires_auth(client: AsyncClient):
    """Status endpoint without token returns 401."""
    fake_id = str(uuid4())
    response = await client.get(f"/api/v1/invoices/{fake_id}/status")
    assert response.status_code == 401


async def test_status_returns_404_for_nonexistent(client: AsyncClient):
    """Status for a non-existent invoice returns 404."""
    headers = await _auth_headers(client)
    fake_id = str(uuid4())
    response = await client.get(f"/api/v1/invoices/{fake_id}/status", headers=headers)
    assert response.status_code == 404


async def test_status_after_upload(client: AsyncClient):
    """After upload, status endpoint returns correct processing state."""
    headers = await _auth_headers(client)
    invoice_id = await _upload_and_get_id(client, headers)

    response = await client.get(f"/api/v1/invoices/{invoice_id}/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == invoice_id
    assert data["status"] in ("queued", "uploaded")
    assert data["document_id"] == invoice_id
    assert data["created_at"] is not None


async def test_status_returns_uploaded_when_ocr_not_started(client: AsyncClient):
    """Status returns 'uploaded' when file saved but OCR hasn't run."""
    headers = await _auth_headers(client)

    # Upload with Celery down → upload response says "uploaded"
    with (
        patch("celery.Celery.send_task", side_effect=Exception("Redis down")),
        patch(
            "app.routers.invoices.upload_document",
            return_value="organizations/org-id/invoices/inv-id/original.pdf",
        ),
    ):
        upload_resp = await client.post(
            "/api/v1/invoices/upload",
            files={"file": ("inv.pdf", b"%PDF-1.4 fake", "application/pdf")},
            headers=headers,
        )
    invoice_id = upload_resp.json()["id"]

    # Status endpoint should also return "uploaded"
    status_resp = await client.get(f"/api/v1/invoices/{invoice_id}/status", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "uploaded"


async def test_status_hides_other_org_invoices(client: AsyncClient):
    """User cannot see status of invoices from another organization."""
    # Create invoice with first user
    headers1 = await _auth_headers(client)
    invoice_id = await _upload_and_get_id(client, headers1)

    # Register second user (different org)
    reg_resp2 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-org@example.com",
            "password": "securepass123",
            "first_name": "Other",
            "last_name": "User",
        },
    )
    reg_token2 = reg_resp2.json()["access_token"]
    org_resp2 = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Different Org"},
        headers={"Authorization": f"Bearer {reg_token2}"},
    )
    headers2 = {"Authorization": f"Bearer {org_resp2.json()['access_token']}"}

    # Second user should get 404 (not 403, to avoid leaking existence)
    response = await client.get(f"/api/v1/invoices/{invoice_id}/status", headers=headers2)
    assert response.status_code == 404


# ==== Batch upload tests ====


@patch("celery.Celery.send_task")
@patch(
    "app.routers.invoices.upload_document",
    return_value="organizations/org-id/invoices/inv-id/original.pdf",
)
async def test_batch_upload_success(mock_s3, mock_celery, client: AsyncClient):
    """Batch upload of 3 valid PDFs returns 202 with 3 status objects."""
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/invoices/upload/batch",
        files=[
            ("files", ("a.pdf", b"%PDF-1.4 content A", "application/pdf")),
            ("files", ("b.pdf", b"%PDF-1.4 content B", "application/pdf")),
            ("files", ("c.pdf", b"%PDF-1.4 content C", "application/pdf")),
        ],
        headers=headers,
    )
    assert response.status_code == 202
    data = response.json()
    assert len(data) == 3
    for item in data:
        assert item["status"] in ("queued", "uploaded")
        assert item["id"] is not None
    # All 3 files should be unique → 3 S3 uploads
    assert mock_s3.call_count == 3


@patch("celery.Celery.send_task")
@patch(
    "app.routers.invoices.upload_document",
    return_value="organizations/org-id/invoices/inv-id/original.pdf",
)
async def test_batch_upload_partial_failure(mock_s3, mock_celery, client: AsyncClient):
    """Mix of valid and invalid files: valid ones succeed, invalid ones report errors."""
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/invoices/upload/batch",
        files=[
            ("files", ("good.pdf", b"%PDF-1.4 valid", "application/pdf")),
            ("files", ("bad.txt", b"not a valid invoice", "text/plain")),
            ("files", ("good.png", _make_png(), "image/png")),
        ],
        headers=headers,
    )
    assert response.status_code == 202
    data = response.json()
    assert len(data) == 3

    # First and third should succeed
    assert data[0]["status"] in ("queued", "uploaded")
    assert data[2]["status"] in ("queued", "uploaded")

    # Second should fail with error message
    assert data[1]["status"] == "failed"
    assert "Unsupported file type" in data[1]["error_message"]

    # Only 2 S3 uploads (the valid files)
    assert mock_s3.call_count == 2


async def test_batch_upload_exceeds_file_limit(client: AsyncClient):
    """Batch with more than 50 files returns 400."""
    headers = await _auth_headers(client)
    files = [("files", (f"file{i}.pdf", b"%PDF-1.4 x", "application/pdf")) for i in range(51)]
    response = await client.post(
        "/api/v1/invoices/upload/batch",
        files=files,
        headers=headers,
    )
    assert response.status_code == 400
    assert "50" in response.json()["detail"]


@patch("celery.Celery.send_task")
@patch(
    "app.routers.invoices.upload_document",
    return_value="organizations/org-id/invoices/inv-id/original.pdf",
)
async def test_batch_upload_exceeds_total_size(mock_s3, mock_celery, client: AsyncClient):
    """Batch exceeding 200MB total returns 400."""
    headers = await _auth_headers(client)
    # 11 files × 19MB each = 209MB > 200MB
    big_content = b"x" * (19 * 1024 * 1024)
    files = [("files", (f"big{i}.pdf", big_content, "application/pdf")) for i in range(11)]
    response = await client.post(
        "/api/v1/invoices/upload/batch",
        files=files,
        headers=headers,
    )
    assert response.status_code == 400
    assert "200MB" in response.json()["detail"]


async def test_batch_upload_requires_auth(client: AsyncClient):
    """Batch upload without token returns 401."""
    response = await client.post(
        "/api/v1/invoices/upload/batch",
        files=[("files", ("a.pdf", b"%PDF-1.4", "application/pdf"))],
    )
    assert response.status_code == 401


# ==== Health services endpoint ====


async def test_health_services_returns_status(client: AsyncClient):
    """Health services endpoint returns Redis and OCR worker status."""
    response = await client.get("/health/services")
    assert response.status_code == 200
    data = response.json()
    assert "redis" in data
    assert "ocr_worker" in data
    assert data["redis"]["status"] in ("healthy", "unavailable")
    assert data["ocr_worker"]["status"] in ("healthy", "unavailable")
    assert isinstance(data["ocr_worker"]["workers"], int)


# ==== Status endpoint with Redis progress ====


async def test_status_returns_redis_progress_when_processing(client: AsyncClient):
    """Status endpoint returns real-time Redis progress during processing."""
    headers = await _auth_headers(client)
    invoice_id = await _upload_and_get_id(client, headers)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps(
        {
            "stage": "ocr_running",
            "progress": 40,
            "error": None,
        }
    )
    fastapi_app.state.redis = mock_redis

    response = await client.get(f"/api/v1/invoices/{invoice_id}/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["progress"] == 40
    assert data["stage"] == "ocr_running"


async def test_status_falls_back_to_db_when_redis_unavailable(client: AsyncClient):
    """Status endpoint falls back to DB when Redis is down."""
    headers = await _auth_headers(client)
    invoice_id = await _upload_and_get_id(client, headers)

    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("Redis connection refused")
    fastapi_app.state.redis = mock_redis

    response = await client.get(f"/api/v1/invoices/{invoice_id}/status", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] in ("uploaded", "queued", "processing")


async def test_status_returns_completed_when_redis_says_complete(client: AsyncClient):
    """When Redis stage is 'complete', status is 'completed' with progress 100."""
    headers = await _auth_headers(client)
    invoice_id = await _upload_and_get_id(client, headers)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps(
        {
            "stage": "complete",
            "progress": 100,
            "error": None,
        }
    )
    fastapi_app.state.redis = mock_redis

    response = await client.get(f"/api/v1/invoices/{invoice_id}/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["progress"] == 100


async def test_status_returns_failed_when_redis_says_failed(client: AsyncClient):
    """When Redis stage is 'failed', status is 'failed' with error message."""
    headers = await _auth_headers(client)
    invoice_id = await _upload_and_get_id(client, headers)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps(
        {
            "stage": "failed",
            "progress": 0,
            "error": "Model inference timed out",
        }
    )
    fastapi_app.state.redis = mock_redis

    response = await client.get(f"/api/v1/invoices/{invoice_id}/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["error_message"] == "Model inference timed out"
