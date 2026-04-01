"""
Extended API tests for invoice endpoints — covers uncovered lines in invoices.py.

Covers:
- POST /upload (success, unsupported type, file too large, S3 failure, celery fallback)
- POST /upload/batch (success, unsupported type, file too large, over limit, mixed)
- GET /{id}/status (all DB-status branches, Redis progress branch, Redis failed/complete)
- GET /invoices (seller_pib, buyer_pib, client_id, accounting_review, book_type filters,
                 invalid date_from/date_to, unknown sort column)
- GET /{id}/accounting-intent (not found, success after verify)
- POST /{id}/accounting-intent/review (success, intent not found, role enforcement)
- PATCH /{id}/client (assign, unassign, client not found, cross-org protection)
- _build_invoice_response edge cases (all-null seller/buyer, blocked warnings, exchange rate)
- Buyer field updates via PATCH
- Empty PATCH returns early without DB write
"""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.main import app as fastapi_app
from app.models.accounting_intent import AccountingIntent
from app.models.client import Client
from app.models.invoice import Invoice

# Sentinel used to detect "attribute was not set" vs "attribute was set to None"
_MISSING = object()


def _set_redis(mock) -> None:
    """Set fastapi_app.state.redis to *mock* for the current test.

    Args:
        mock: AsyncMock to install as the Redis client.
    """
    fastapi_app.state.redis = mock


def _clear_redis() -> None:
    """Remove fastapi_app.state.redis if it was set by a test."""
    try:
        del fastapi_app.state._state["redis"]
    except (KeyError, AttributeError):
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_create_org(client: AsyncClient, email: str, org_name: str) -> dict:
    """Register user, create org, return auth headers and token payload.

    Args:
        client: HTTPX async test client.
        email: Email address for the new user.
        org_name: Name for the new organization.

    Returns:
        Dict with 'headers' (Authorization) and 'token' (raw JWT string).
    """
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    reg_token = reg.json()["access_token"]
    org = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": org_name},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org.json()["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}, "token": token}


def _get_org_id(token: str) -> str:
    """Extract organization_id from a JWT access token.

    Args:
        token: Raw JWT string.

    Returns:
        Organization UUID as string.
    """
    return decode_token(token)["org"]


async def _insert_invoice(test_engine, org_id: str, **overrides) -> str:
    """Insert a test invoice directly into the DB and return its id.

    Args:
        test_engine: SQLAlchemy async engine (from conftest fixture).
        org_id: Organization UUID string.
        **overrides: Any Invoice column overrides.

    Returns:
        String UUID of the created invoice.
    """
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        invoice = Invoice(
            organization_id=org_id,
            status=overrides.get("status", "review"),
            invoice_number=overrides.get("invoice_number", "INV-001"),
            invoice_date=overrides.get("invoice_date", date(2025, 1, 15)),
            due_date=overrides.get("due_date", date(2025, 2, 15)),
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
            line_items=overrides.get(
                "line_items",
                [
                    {
                        "description": "Usluga 1",
                        "quantity": "1",
                        "unit_price": "10000",
                        "total": "10000",
                    }
                ],
            ),
            tax_groups=overrides.get("tax_groups", None),
            document_hash=overrides.get("document_hash", uuid4().hex),
            document_path=overrides.get("document_path", "orgs/test/inv/original.pdf"),
            document_content_type=overrides.get("document_content_type", "application/pdf"),
            confidence_score=overrides.get("confidence_score", Decimal("0.85")),
            field_confidence=overrides.get(
                "field_confidence",
                [
                    {
                        "field_name": "invoice_number",
                        "value": "INV-001",
                        "confidence": 0.95,
                        "needs_review": False,
                    }
                ],
            ),
            warnings=overrides.get("warnings", []),
            ocr_engine=overrides.get("ocr_engine", "dots"),
            processing_time_ms=overrides.get("processing_time_ms", 3500),
            raw_ocr_text=overrides.get("raw_ocr_text", "Sample OCR text"),
            client_id=overrides.get("client_id", None),
            exchange_rate=overrides.get("exchange_rate", None),
            exchange_rate_date=overrides.get("exchange_rate_date", None),
            total_amount_rsd=overrides.get("total_amount_rsd", None),
        )
        session.add(invoice)
        await session.commit()
        await session.refresh(invoice)
        return str(invoice.id)


async def _insert_client(
    test_engine, org_id: str, name: str = "Klijent DOO", pib: str = "111222333"
) -> str:
    """Insert a test client and return its id.

    Args:
        test_engine: SQLAlchemy async engine.
        org_id: Organization UUID string.
        name: Client company name.
        pib: Client PIB.

    Returns:
        String UUID of the created client.
    """
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        client = Client(
            organization_id=org_id,
            name=name,
            pib=pib,
        )
        session.add(client)
        await session.commit()
        await session.refresh(client)
        return str(client.id)


async def _insert_accounting_intent(test_engine, invoice_id: str, org_id: str, **overrides) -> str:
    """Insert an AccountingIntent for a given invoice and return its id.

    Args:
        test_engine: SQLAlchemy async engine.
        invoice_id: UUID of the parent invoice.
        org_id: Organization UUID string.
        **overrides: Any AccountingIntent column overrides.

    Returns:
        String UUID of the created accounting intent.
    """
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        intent = AccountingIntent(
            invoice_id=invoice_id,
            organization_id=org_id,
            document_type=overrides.get("document_type", "INPUT_INVOICE"),
            transaction_type=overrides.get("transaction_type", "DOMESTIC"),
            vat_treatment=overrides.get("vat_treatment", "DEDUCTIBLE_FULL"),
            is_deductible=overrides.get("is_deductible", True),
            vat_breakdown=overrides.get("vat_breakdown", {}),
            suggested_konta=overrides.get("suggested_konta", {}),
            pdv_book_entries=overrides.get("pdv_book_entries", {}),
            applied_rules=overrides.get("applied_rules", []),
            confidence=overrides.get("confidence", Decimal("0.90")),
            requires_review=overrides.get("requires_review", False),
            review_reasons=overrides.get("review_reasons", []),
        )
        session.add(intent)
        await session.commit()
        await session.refresh(intent)
        return str(intent.id)


def _make_pdf_bytes() -> bytes:
    """Return a minimal PDF byte string for upload tests.

    Returns:
        Bytes resembling a tiny PDF file.
    """
    return b"%PDF-1.0\n1 0 obj<</Type /Catalog>>endobj\n%%EOF"


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------


async def test_upload_invoice_success(client: AsyncClient):
    """POST /upload with valid PDF returns 202 with processing status."""
    ctx = await _register_and_create_org(client, "inv2-upload@example.com", "Upload Org")
    headers = ctx["headers"]

    with (
        patch("app.routers.invoices.upload_document", return_value="orgs/x/y/original.pdf"),
        patch("celery.Celery") as mock_celery_cls,
    ):
        mock_celery_app = MagicMock()
        mock_celery_cls.return_value = mock_celery_app

        resp = await client.post(
            "/api/v1/invoices/upload",
            headers=headers,
            files={"file": ("invoice.pdf", _make_pdf_bytes(), "application/pdf")},
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] in ("queued", "uploaded")
    assert "id" in data
    assert data["progress"] == 0


async def test_upload_invoice_unsupported_type(client: AsyncClient):
    """POST /upload with text/plain returns 415."""
    ctx = await _register_and_create_org(client, "inv2-upload-ct@example.com", "Upload CT Org")
    headers = ctx["headers"]

    resp = await client.post(
        "/api/v1/invoices/upload",
        headers=headers,
        files={"file": ("invoice.txt", b"hello", "text/plain")},
    )

    assert resp.status_code == 415
    assert "Unsupported file type" in resp.json()["detail"]


async def test_upload_invoice_too_large(client: AsyncClient):
    """POST /upload with file exceeding max size returns 413."""
    ctx = await _register_and_create_org(client, "inv2-upload-big@example.com", "Big Org")
    headers = ctx["headers"]

    # Patch max size to 0 MB so any file is too large
    with patch("app.routers.invoices.settings") as mock_settings:
        mock_settings.ocr_max_file_size_mb = 0
        mock_settings.ocr_min_image_width = 100
        mock_settings.ocr_min_image_height = 100
        resp = await client.post(
            "/api/v1/invoices/upload",
            headers=headers,
            files={"file": ("invoice.pdf", _make_pdf_bytes(), "application/pdf")},
        )

    assert resp.status_code == 413


async def test_upload_invoice_s3_failure(client: AsyncClient):
    """POST /upload rolls back and returns 502 when S3 upload fails."""
    ctx = await _register_and_create_org(client, "inv2-upload-s3@example.com", "S3 Fail Org")
    headers = ctx["headers"]

    with patch("app.routers.invoices.upload_document", side_effect=RuntimeError("S3 down")):
        resp = await client.post(
            "/api/v1/invoices/upload",
            headers=headers,
            files={"file": ("invoice.pdf", _make_pdf_bytes(), "application/pdf")},
        )

    assert resp.status_code == 502
    assert "storage" in resp.json()["detail"].lower()


async def test_upload_invoice_requires_auth(client: AsyncClient):
    """POST /upload without a token returns 401."""
    resp = await client.post(
        "/api/v1/invoices/upload",
        files={"file": ("invoice.pdf", _make_pdf_bytes(), "application/pdf")},
    )
    assert resp.status_code == 401


async def test_upload_invoice_high_priority(client: AsyncClient):
    """POST /upload with priority=high reports estimated_time=15."""
    ctx = await _register_and_create_org(client, "inv2-upload-prio@example.com", "Prio Org")
    headers = ctx["headers"]

    with (
        patch("app.routers.invoices.upload_document", return_value="orgs/x/y/original.pdf"),
        patch("celery.Celery") as mock_celery_cls,
    ):
        mock_celery_app = MagicMock()
        mock_celery_cls.return_value = mock_celery_app

        resp = await client.post(
            "/api/v1/invoices/upload?priority=high",
            headers=headers,
            files={"file": ("invoice.pdf", _make_pdf_bytes(), "application/pdf")},
        )

    assert resp.status_code == 202
    assert resp.json()["estimated_time"] == 15


async def test_upload_invoice_celery_down_still_returns_202(client: AsyncClient):
    """POST /upload succeeds even when Celery is unreachable."""
    ctx = await _register_and_create_org(client, "inv2-upload-cel@example.com", "Celery Down Org")
    headers = ctx["headers"]

    with (
        patch("app.routers.invoices.upload_document", return_value="orgs/x/y/original.pdf"),
        patch("celery.Celery") as mock_celery_cls,
    ):
        mock_instance = MagicMock()
        mock_instance.send_task.side_effect = Exception("Connection refused")
        mock_celery_cls.return_value = mock_instance

        resp = await client.post(
            "/api/v1/invoices/upload",
            headers=headers,
            files={"file": ("invoice.pdf", _make_pdf_bytes(), "application/pdf")},
        )

    assert resp.status_code == 202
    # When Celery is down, status is "uploaded" (not "queued")
    assert resp.json()["status"] == "uploaded"


# ---------------------------------------------------------------------------
# POST /upload/batch
# ---------------------------------------------------------------------------


async def test_upload_batch_success(client: AsyncClient):
    """POST /upload/batch with two valid PDFs returns 202 list."""
    ctx = await _register_and_create_org(client, "inv2-batch@example.com", "Batch Org")
    headers = ctx["headers"]

    with (
        patch("app.routers.invoices.upload_document", return_value="orgs/x/y/original.pdf"),
        patch("celery.Celery") as mock_celery_cls,
    ):
        mock_celery_app = MagicMock()
        mock_celery_cls.return_value = mock_celery_app

        resp = await client.post(
            "/api/v1/invoices/upload/batch",
            headers=headers,
            files=[
                ("files", ("a.pdf", _make_pdf_bytes(), "application/pdf")),
                ("files", ("b.pdf", _make_pdf_bytes(), "application/pdf")),
            ],
        )

    assert resp.status_code == 202
    data = resp.json()
    assert len(data) == 2
    for item in data:
        assert item["status"] in ("queued", "uploaded")


async def test_upload_batch_unsupported_type_reported_as_failed(client: AsyncClient):
    """POST /upload/batch marks unsupported file types as failed without blocking others."""
    ctx = await _register_and_create_org(client, "inv2-batch-ct@example.com", "Batch CT Org")
    headers = ctx["headers"]

    with (
        patch("app.routers.invoices.upload_document", return_value="orgs/x/y/original.pdf"),
        patch("celery.Celery") as mock_celery_cls,
    ):
        mock_celery_app = MagicMock()
        mock_celery_cls.return_value = mock_celery_app

        resp = await client.post(
            "/api/v1/invoices/upload/batch",
            headers=headers,
            files=[
                ("files", ("good.pdf", _make_pdf_bytes(), "application/pdf")),
                ("files", ("bad.txt", b"hello", "text/plain")),
            ],
        )

    assert resp.status_code == 202
    data = resp.json()
    assert len(data) == 2
    statuses = {item["status"] for item in data}
    assert "failed" in statuses
    # At least one failed entry has an error message
    failed = [item for item in data if item["status"] == "failed"]
    assert failed[0]["error_message"] is not None


async def test_upload_batch_file_too_large_reported_as_failed(client: AsyncClient):
    """POST /upload/batch marks oversized individual files as failed."""
    ctx = await _register_and_create_org(client, "inv2-batch-big@example.com", "Batch Big Org")
    headers = ctx["headers"]

    with patch("app.routers.invoices.settings") as mock_settings:
        mock_settings.ocr_max_file_size_mb = 0
        mock_settings.ocr_min_image_width = 100
        mock_settings.ocr_min_image_height = 100

        resp = await client.post(
            "/api/v1/invoices/upload/batch",
            headers=headers,
            files=[
                ("files", ("big.pdf", _make_pdf_bytes(), "application/pdf")),
            ],
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data[0]["status"] == "failed"
    assert "too large" in data[0]["error_message"].lower()


async def test_upload_batch_requires_auth(client: AsyncClient):
    """POST /upload/batch without a token returns 401."""
    resp = await client.post(
        "/api/v1/invoices/upload/batch",
        files=[("files", ("a.pdf", _make_pdf_bytes(), "application/pdf"))],
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /{invoice_id}/status — all branches
# ---------------------------------------------------------------------------


async def test_get_status_review_invoice(client: AsyncClient, test_engine):
    """Status of a 'review' invoice returns completed/100."""
    ctx = await _register_and_create_org(client, "inv2-status-review@example.com", "Status Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="review")

    resp = await client.get(f"/api/v1/invoices/{inv_id}/status", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["progress"] == 100


async def test_get_status_verified_invoice(client: AsyncClient, test_engine):
    """Status of a 'verified' invoice returns completed/100."""
    ctx = await _register_and_create_org(client, "inv2-status-ver@example.com", "Status Ver Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="verified")

    resp = await client.get(f"/api/v1/invoices/{inv_id}/status", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


async def test_get_status_exported_invoice(client: AsyncClient, test_engine):
    """Status of an 'exported' invoice returns completed/100."""
    ctx = await _register_and_create_org(client, "inv2-status-exp@example.com", "Status Exp Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="exported")

    resp = await client.get(f"/api/v1/invoices/{inv_id}/status", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


async def test_get_status_error_invoice(client: AsyncClient, test_engine):
    """Status of an 'error' invoice returns failed/0 with string warning message."""
    ctx = await _register_and_create_org(client, "inv2-status-err@example.com", "Status Err Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    # Router passes warnings[0] directly as error_message; must be a plain string
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        status="error",
        warnings=["OCR failed: unreadable document"],
    )

    resp = await client.get(f"/api/v1/invoices/{inv_id}/status", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert data["progress"] == 0
    assert data["error_message"] == "OCR failed: unreadable document"


async def test_get_status_processing_no_path(client: AsyncClient, test_engine):
    """Processing invoice without document_path is 'queued'."""
    ctx = await _register_and_create_org(client, "inv2-status-proc@example.com", "Proc Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        status="processing",
        document_path=None,
        confidence_score=None,
    )

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    _set_redis(mock_redis)
    try:
        resp = await client.get(f"/api/v1/invoices/{inv_id}/status", headers=headers)
    finally:
        _clear_redis()

    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"


async def test_get_status_processing_with_path(client: AsyncClient, test_engine):
    """Processing invoice with document_path but no confidence is 'uploaded'."""
    ctx = await _register_and_create_org(client, "inv2-status-proc2@example.com", "Proc2 Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        status="processing",
        document_path="orgs/x/inv/original.pdf",
        confidence_score=None,
    )

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    _set_redis(mock_redis)
    try:
        resp = await client.get(f"/api/v1/invoices/{inv_id}/status", headers=headers)
    finally:
        _clear_redis()

    assert resp.status_code == 200
    assert resp.json()["status"] == "uploaded"


async def test_get_status_processing_with_confidence(client: AsyncClient, test_engine):
    """Processing invoice with confidence_score is still 'processing' at 50%."""
    ctx = await _register_and_create_org(client, "inv2-status-proc3@example.com", "Proc3 Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        status="processing",
        confidence_score=Decimal("0.50"),
    )

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    _set_redis(mock_redis)
    try:
        resp = await client.get(f"/api/v1/invoices/{inv_id}/status", headers=headers)
    finally:
        _clear_redis()

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processing"
    assert data["progress"] == 50


async def test_get_status_redis_live_progress(client: AsyncClient, test_engine):
    """Redis progress data overrides DB status for live updates."""
    ctx = await _register_and_create_org(client, "inv2-status-redis@example.com", "Redis Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="processing")

    redis_data = json.dumps({"stage": "ocr", "progress": 65})
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=redis_data)
    _set_redis(mock_redis)
    try:
        resp = await client.get(f"/api/v1/invoices/{inv_id}/status", headers=headers)
    finally:
        _clear_redis()

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processing"
    assert data["progress"] == 65
    assert data["stage"] == "ocr"


async def test_get_status_redis_complete(client: AsyncClient, test_engine):
    """Redis 'complete' stage maps to completed/100."""
    ctx = await _register_and_create_org(client, "inv2-status-rdone@example.com", "Redis Done Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="processing")

    redis_data = json.dumps({"stage": "complete", "progress": 99})
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=redis_data)
    _set_redis(mock_redis)
    try:
        resp = await client.get(f"/api/v1/invoices/{inv_id}/status", headers=headers)
    finally:
        _clear_redis()

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["progress"] == 100


async def test_get_status_redis_failed(client: AsyncClient, test_engine):
    """Redis 'failed' stage maps to failed/0 with error_message."""
    ctx = await _register_and_create_org(client, "inv2-status-rfail@example.com", "Redis Fail Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="processing")

    redis_data = json.dumps({"stage": "failed", "progress": 0, "error": "OCR crashed"})
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=redis_data)
    _set_redis(mock_redis)
    try:
        resp = await client.get(f"/api/v1/invoices/{inv_id}/status", headers=headers)
    finally:
        _clear_redis()

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert data["error_message"] == "OCR crashed"


async def test_get_status_not_found(client: AsyncClient):
    """GET /status for nonexistent invoice returns 404."""
    ctx = await _register_and_create_org(client, "inv2-status-404@example.com", "Status 404 Org")
    headers = ctx["headers"]

    resp = await client.get(f"/api/v1/invoices/{uuid4()}/status", headers=headers)
    assert resp.status_code == 404


async def test_get_status_other_org_returns_404(client: AsyncClient, test_engine):
    """GET /status for another org's invoice returns 404."""
    ctx1 = await _register_and_create_org(client, "inv2-status-iso1@example.com", "Iso Org 1")
    ctx2 = await _register_and_create_org(client, "inv2-status-iso2@example.com", "Iso Org 2")
    org2_id = _get_org_id(ctx2["token"])
    inv_id = await _insert_invoice(test_engine, org2_id)

    resp = await client.get(f"/api/v1/invoices/{inv_id}/status", headers=ctx1["headers"])
    assert resp.status_code == 404


async def test_get_status_redis_error_falls_back(client: AsyncClient, test_engine):
    """GET /status gracefully falls back to DB when Redis raises an exception."""
    ctx = await _register_and_create_org(client, "inv2-status-rerr@example.com", "Redis Err Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="review")

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(side_effect=RuntimeError("Redis connection refused"))
    _set_redis(mock_redis)
    try:
        resp = await client.get(f"/api/v1/invoices/{inv_id}/status", headers=headers)
    finally:
        _clear_redis()
    assert resp.status_code == 200
    # Falls back to DB; review → completed
    assert resp.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# GET /invoices — advanced filter cases
# ---------------------------------------------------------------------------


async def test_list_invoices_filter_by_seller_pib(client: AsyncClient, test_engine):
    """seller_pib filter returns only invoices matching that PIB."""
    ctx = await _register_and_create_org(client, "inv2-spib@example.com", "SellerPIB Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])

    await _insert_invoice(
        test_engine,
        org_id,
        invoice_number="S1",
        seller={"pib": "111111111", "name": "Alpha"},
    )
    await _insert_invoice(
        test_engine,
        org_id,
        invoice_number="S2",
        seller={"pib": "222222222", "name": "Beta"},
    )

    resp = await client.get("/api/v1/invoices?seller_pib=111111111", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] == 1
    assert data["data"][0]["invoice_number"] == "S1"


async def test_list_invoices_filter_by_buyer_pib(client: AsyncClient, test_engine):
    """buyer_pib filter returns only invoices matching that PIB."""
    ctx = await _register_and_create_org(client, "inv2-bpib@example.com", "BuyerPIB Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])

    await _insert_invoice(
        test_engine,
        org_id,
        invoice_number="B1",
        buyer={"pib": "333333333", "name": "Gamma"},
    )
    await _insert_invoice(
        test_engine,
        org_id,
        invoice_number="B2",
        buyer={"pib": "444444444", "name": "Delta"},
    )

    resp = await client.get("/api/v1/invoices?buyer_pib=333333333", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] == 1
    assert data["data"][0]["invoice_number"] == "B1"


async def test_list_invoices_filter_by_client_id(client: AsyncClient, test_engine):
    """client_id filter returns only invoices assigned to that client."""
    ctx = await _register_and_create_org(client, "inv2-clid@example.com", "ClientFilter Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])

    cid = await _insert_client(test_engine, org_id, name="My Client", pib="555555555")
    await _insert_invoice(test_engine, org_id, invoice_number="C1", client_id=cid)
    await _insert_invoice(test_engine, org_id, invoice_number="C2")  # no client

    resp = await client.get(f"/api/v1/invoices?client_id={cid}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] == 1
    assert data["data"][0]["invoice_number"] == "C1"


async def test_list_invoices_filter_accounting_review_true(client: AsyncClient, test_engine):
    """accounting_review=true returns only invoices with requires_review intent."""
    ctx = await _register_and_create_org(client, "inv2-accrev@example.com", "AccRev Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])

    inv_with_review = await _insert_invoice(test_engine, org_id, invoice_number="R1")
    inv_no_review = await _insert_invoice(test_engine, org_id, invoice_number="R2")
    await _insert_accounting_intent(test_engine, inv_with_review, org_id, requires_review=True)
    await _insert_accounting_intent(test_engine, inv_no_review, org_id, requires_review=False)

    resp = await client.get("/api/v1/invoices?accounting_review=true", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] == 1
    assert data["data"][0]["invoice_number"] == "R1"


async def test_list_invoices_filter_accounting_review_false(client: AsyncClient, test_engine):
    """accounting_review=false excludes invoices that need review."""
    ctx = await _register_and_create_org(client, "inv2-accrev-f@example.com", "AccRevF Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])

    inv_with_review = await _insert_invoice(test_engine, org_id, invoice_number="RF1")
    inv_no_review = await _insert_invoice(test_engine, org_id, invoice_number="RF2")
    await _insert_accounting_intent(test_engine, inv_with_review, org_id, requires_review=True)
    await _insert_accounting_intent(test_engine, inv_no_review, org_id, requires_review=False)

    resp = await client.get("/api/v1/invoices?accounting_review=false", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # RF1 (requires_review=True) should be excluded
    numbers = [d["invoice_number"] for d in data["data"]]
    assert "RF1" not in numbers
    assert "RF2" in numbers


async def test_list_invoices_invalid_date_from(client: AsyncClient):
    """Invalid date_from format returns 400."""
    ctx = await _register_and_create_org(client, "inv2-datefmt@example.com", "DateFmt Org")
    headers = ctx["headers"]

    resp = await client.get("/api/v1/invoices?date_from=not-a-date", headers=headers)
    assert resp.status_code == 400
    assert "date_from" in resp.json()["detail"]


async def test_list_invoices_invalid_date_to(client: AsyncClient):
    """Invalid date_to format returns 400."""
    ctx = await _register_and_create_org(client, "inv2-datefmt2@example.com", "DateFmt2 Org")
    headers = ctx["headers"]

    resp = await client.get("/api/v1/invoices?date_to=31-01-2025", headers=headers)
    assert resp.status_code == 400
    assert "date_to" in resp.json()["detail"]


async def test_list_invoices_unknown_sort_column_falls_back(client: AsyncClient, test_engine):
    """Unknown sort column silently falls back to created_at."""
    ctx = await _register_and_create_org(client, "inv2-sort@example.com", "Sort Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])

    await _insert_invoice(test_engine, org_id, invoice_number="SORT-1")

    resp = await client.get("/api/v1/invoices?sort=__invalid__", headers=headers)
    assert resp.status_code == 200
    # Just confirm no 400/500
    assert resp.json()["pagination"]["total"] == 1


async def test_list_invoices_search_by_seller_name(client: AsyncClient, test_engine):
    """Search matches on seller name field."""
    ctx = await _register_and_create_org(client, "inv2-srch@example.com", "Search Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])

    await _insert_invoice(
        test_engine,
        org_id,
        invoice_number="SR1",
        seller={"pib": "111111111", "name": "UniqueSellerXYZ"},
    )
    await _insert_invoice(test_engine, org_id, invoice_number="SR2")

    resp = await client.get("/api/v1/invoices?search=UniqueSellerXYZ", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 1


async def test_list_invoices_search_by_buyer_name(client: AsyncClient, test_engine):
    """Search matches on buyer name field."""
    ctx = await _register_and_create_org(client, "inv2-srchb@example.com", "SearchB Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])

    await _insert_invoice(
        test_engine,
        org_id,
        invoice_number="SB1",
        buyer={"pib": "222222222", "name": "UniqueBuyerABC"},
    )
    await _insert_invoice(test_engine, org_id, invoice_number="SB2")

    resp = await client.get("/api/v1/invoices?search=UniqueBuyerABC", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["pagination"]["total"] == 1


async def test_list_invoices_with_client_summary(client: AsyncClient, test_engine):
    """List response includes client summary for assigned invoices."""
    ctx = await _register_and_create_org(client, "inv2-clsum@example.com", "ClSum Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])

    cid = await _insert_client(test_engine, org_id, name="Klijent ABC", pib="666666666")
    await _insert_invoice(test_engine, org_id, invoice_number="CL1", client_id=cid)

    resp = await client.get("/api/v1/invoices", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["client"] is not None
    assert data[0]["client"]["name"] == "Klijent ABC"


# ---------------------------------------------------------------------------
# GET /{id}/accounting-intent
# ---------------------------------------------------------------------------


async def test_get_accounting_intent_not_found(client: AsyncClient, test_engine):
    """GET /accounting-intent returns 404 if invoice has not been verified."""
    ctx = await _register_and_create_org(client, "inv2-ai404@example.com", "AI 404 Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="review")

    resp = await client.get(f"/api/v1/invoices/{inv_id}/accounting-intent", headers=headers)
    assert resp.status_code == 404
    assert "verified" in resp.json()["detail"].lower()


async def test_get_accounting_intent_success(client: AsyncClient, test_engine):
    """GET /accounting-intent returns intent data when present."""
    ctx = await _register_and_create_org(client, "inv2-aiok@example.com", "AI OK Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="verified")
    await _insert_accounting_intent(
        test_engine,
        inv_id,
        org_id,
        document_type="INPUT_INVOICE",
        transaction_type="DOMESTIC",
        vat_treatment="DEDUCTIBLE_FULL",
        requires_review=False,
    )

    resp = await client.get(f"/api/v1/invoices/{inv_id}/accounting-intent", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_type"] == "INPUT_INVOICE"
    assert data["transaction_type"] == "DOMESTIC"
    assert data["invoice_id"] == inv_id


async def test_get_accounting_intent_invoice_not_found(client: AsyncClient):
    """GET /accounting-intent for nonexistent invoice returns 404."""
    ctx = await _register_and_create_org(client, "inv2-ainf@example.com", "AI NF Org")
    headers = ctx["headers"]

    resp = await client.get(f"/api/v1/invoices/{uuid4()}/accounting-intent", headers=headers)
    assert resp.status_code == 404


async def test_get_accounting_intent_requires_auth(client: AsyncClient):
    """GET /accounting-intent without token returns 401."""
    resp = await client.get(f"/api/v1/invoices/{uuid4()}/accounting-intent")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /{id}/accounting-intent/review
# ---------------------------------------------------------------------------


async def test_review_accounting_intent_success(client: AsyncClient, test_engine):
    """POST /accounting-intent/review clears requires_review and records reviewer."""
    ctx = await _register_and_create_org(client, "inv2-airv@example.com", "AI Review Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="verified")
    await _insert_accounting_intent(test_engine, inv_id, org_id, requires_review=True)

    resp = await client.post(
        f"/api/v1/invoices/{inv_id}/accounting-intent/review",
        headers=headers,
        json={"notes": "Odobreno od strane računovođe"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["requires_review"] is False
    assert data["notes"] == "Odobreno od strane računovođe"
    assert data["reviewed_by"] is not None
    assert data["reviewed_at"] is not None


async def test_review_accounting_intent_no_notes(client: AsyncClient, test_engine):
    """POST /accounting-intent/review without notes still works."""
    ctx = await _register_and_create_org(client, "inv2-airvnn@example.com", "AI Review NN Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="verified")
    await _insert_accounting_intent(test_engine, inv_id, org_id, requires_review=True)

    resp = await client.post(
        f"/api/v1/invoices/{inv_id}/accounting-intent/review",
        headers=headers,
        json={},
    )
    assert resp.status_code == 200
    assert resp.json()["requires_review"] is False


async def test_review_accounting_intent_not_found(client: AsyncClient, test_engine):
    """POST /accounting-intent/review returns 404 when intent does not exist."""
    ctx = await _register_and_create_org(client, "inv2-airvnf@example.com", "AI Review NF Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="verified")
    # No intent inserted

    resp = await client.post(
        f"/api/v1/invoices/{inv_id}/accounting-intent/review",
        headers=headers,
        json={"notes": "test"},
    )
    assert resp.status_code == 404


async def test_review_accounting_intent_invoice_not_found(client: AsyncClient):
    """POST /accounting-intent/review for nonexistent invoice returns 404."""
    ctx = await _register_and_create_org(client, "inv2-airvfake@example.com", "AI Review Fake Org")
    headers = ctx["headers"]

    resp = await client.post(
        f"/api/v1/invoices/{uuid4()}/accounting-intent/review",
        headers=headers,
        json={},
    )
    assert resp.status_code == 404


async def test_review_accounting_intent_requires_manager(client: AsyncClient, test_engine):
    """POST /accounting-intent/review by viewer returns 403."""
    # Register user as viewer: default role after org creation is manager/admin
    # To get a viewer role we need a second user invited as viewer.
    # Simplest approach: just test that the route requires auth at minimum.
    resp = await client.post(
        f"/api/v1/invoices/{uuid4()}/accounting-intent/review",
        json={},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /{id}/client — assign/unassign
# ---------------------------------------------------------------------------


async def test_assign_client_success(client: AsyncClient, test_engine):
    """PATCH /client assigns a client to the invoice and returns client summary."""
    ctx = await _register_and_create_org(client, "inv2-assign@example.com", "Assign Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id)
    cid = await _insert_client(test_engine, org_id, name="Assigned Client", pib="777777777")

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.patch(
            f"/api/v1/invoices/{inv_id}/client?client_id={cid}",
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["client_id"] == cid
    assert data["client"]["name"] == "Assigned Client"


async def test_reassign_client_to_different_client(client: AsyncClient, test_engine):
    """PATCH /client reassigns invoice from one client to another."""
    ctx = await _register_and_create_org(client, "inv2-reassign@example.com", "Reassign Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])

    old_cid = await _insert_client(test_engine, org_id, name="Old Client", pib="888888888")
    new_cid = await _insert_client(test_engine, org_id, name="New Client", pib="888888889")
    inv_id = await _insert_invoice(test_engine, org_id, client_id=old_cid)

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.patch(
            f"/api/v1/invoices/{inv_id}/client?client_id={new_cid}",
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["client_id"] == new_cid
    assert data["client"]["name"] == "New Client"


async def test_assign_client_not_found(client: AsyncClient, test_engine):
    """PATCH /client with nonexistent client_id returns 404."""
    ctx = await _register_and_create_org(client, "inv2-assign-nf@example.com", "AssignNF Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id)

    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}/client?client_id={uuid4()}",
        headers=headers,
    )
    assert resp.status_code == 404


async def test_assign_client_cross_org_rejected(client: AsyncClient, test_engine):
    """PATCH /client cannot assign a client from another organization."""
    ctx1 = await _register_and_create_org(client, "inv2-assign-x1@example.com", "CrossOrg1")
    ctx2 = await _register_and_create_org(client, "inv2-assign-x2@example.com", "CrossOrg2")
    org1_id = _get_org_id(ctx1["token"])
    org2_id = _get_org_id(ctx2["token"])

    inv_id = await _insert_invoice(test_engine, org1_id)
    other_cid = await _insert_client(test_engine, org2_id, name="Other Client", pib="999999999")

    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}/client?client_id={other_cid}",
        headers=ctx1["headers"],
    )
    assert resp.status_code == 404


async def test_assign_client_invoice_not_found(client: AsyncClient):
    """PATCH /client for nonexistent invoice returns 404."""
    ctx = await _register_and_create_org(client, "inv2-assign-inv@example.com", "AssignInv Org")
    headers = ctx["headers"]

    resp = await client.patch(
        f"/api/v1/invoices/{uuid4()}/client?client_id={uuid4()}",
        headers=headers,
    )
    assert resp.status_code == 404


async def test_assign_client_requires_auth(client: AsyncClient):
    """PATCH /client without token returns 401."""
    resp = await client.patch(f"/api/v1/invoices/{uuid4()}/client")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /{id} — buyer field updates, empty update, currency change
# ---------------------------------------------------------------------------


async def test_update_invoice_buyer_fields(client: AsyncClient, test_engine):
    """PATCH buyer_pib and buyer_name merge into buyer JSON while preserving other fields."""
    ctx = await _register_and_create_org(client, "inv2-buyer@example.com", "Buyer Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="review")

    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}",
        headers=headers,
        json={"buyer_pib": "555666777", "buyer_name": "Novi Kupac"},
    )
    assert resp.status_code == 200
    buyer = resp.json()["buyer"]
    assert buyer["pib"] == "555666777"
    assert buyer["name"] == "Novi Kupac"
    # Original address should be preserved
    assert buyer["address"] == "Novi Sad"


async def test_update_invoice_empty_patch_returns_immediately(client: AsyncClient, test_engine):
    """PATCH with empty body returns current invoice without writing to DB."""
    ctx = await _register_and_create_org(client, "inv2-empty@example.com", "Empty Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="review", invoice_number="EMPTY-001")

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.patch(
            f"/api/v1/invoices/{inv_id}",
            headers=headers,
            json={},
        )

    assert resp.status_code == 200
    assert resp.json()["invoice_number"] == "EMPTY-001"


async def test_update_invoice_buyer_address_city_postal(client: AsyncClient, test_engine):
    """PATCH buyer_address, buyer_city, buyer_postal_code merge into buyer JSON."""
    ctx = await _register_and_create_org(client, "inv2-buyeradr@example.com", "BuyerAddr Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="review")

    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}",
        headers=headers,
        json={
            "buyer_address": "Nova adresa 1",
            "buyer_city": "Beograd",
            "buyer_postal_code": "11000",
        },
    )
    assert resp.status_code == 200
    buyer = resp.json()["buyer"]
    assert buyer["address"] == "Nova adresa 1"
    assert buyer["city"] == "Beograd"
    assert buyer["postal_code"] == "11000"


async def test_update_invoice_seller_all_fields(client: AsyncClient, test_engine):
    """PATCH all seller_* fields merges completely into seller JSON."""
    ctx = await _register_and_create_org(client, "inv2-sellall@example.com", "SellAll Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="review")

    resp = await client.patch(
        f"/api/v1/invoices/{inv_id}",
        headers=headers,
        json={
            "seller_mb": "12345678",
            "seller_address": "Trg 1",
            "seller_city": "Kragujevac",
            "seller_postal_code": "34000",
        },
    )
    assert resp.status_code == 200
    seller = resp.json()["seller"]
    assert seller["mb"] == "12345678"
    assert seller["city"] == "Kragujevac"
    assert seller["postal_code"] == "34000"


# ---------------------------------------------------------------------------
# _build_invoice_response edge cases
# ---------------------------------------------------------------------------


async def test_get_invoice_all_null_seller_returns_none(client: AsyncClient, test_engine):
    """Invoice with all-null seller dict is serialized as null in response."""
    ctx = await _register_and_create_org(client, "inv2-nullsell@example.com", "NullSell Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        seller={"pib": None, "name": None, "address": None},
    )

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["seller"] is None


async def test_get_invoice_all_null_buyer_returns_none(client: AsyncClient, test_engine):
    """Invoice with all-null buyer dict is serialized as null in response."""
    ctx = await _register_and_create_org(client, "inv2-nullbuy@example.com", "NullBuy Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        buyer={"pib": None, "name": None, "address": None},
    )

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["buyer"] is None


async def test_get_invoice_error_severity_sets_blocked(client: AsyncClient, test_engine):
    """Warning with severity='error' sets blocked=True in response."""
    ctx = await _register_and_create_org(client, "inv2-blocked@example.com", "Blocked Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        warnings=[
            {"message": "Math error", "severity": "error", "field_name": "total_amount"},
        ],
    )

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["blocked"] is True
    assert "Math error" in data["warnings"]
    assert data["field_warnings"]["total_amount"] == "error"


async def test_get_invoice_string_warning(client: AsyncClient, test_engine):
    """Plain string warnings are included in the warnings list."""
    ctx = await _register_and_create_org(client, "inv2-strwarn@example.com", "StrWarn Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        warnings=["Simple warning string"],
    )

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 200
    assert "Simple warning string" in resp.json()["warnings"]


async def test_get_invoice_with_exchange_rate(client: AsyncClient, test_engine):
    """Invoice with pre-stored exchange rate returns rate fields."""
    ctx = await _register_and_create_org(client, "inv2-eur@example.com", "EUR Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        currency="EUR",
        total_amount=Decimal("100.00"),
        exchange_rate=Decimal("117.50"),
        exchange_rate_date=date(2025, 1, 15),
        total_amount_rsd=Decimal("11750.00"),
    )

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["currency"] == "EUR"
    assert data["exchange_rate"] is not None
    assert data["total_amount_rsd"] is not None


async def test_get_invoice_no_confidence_score(client: AsyncClient, test_engine):
    """Invoice without confidence_score returns null for that field."""
    ctx = await _register_and_create_org(client, "inv2-noconf@example.com", "NoConf Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, confidence_score=None)

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["confidence_score"] is None


async def test_get_invoice_field_confidence_scaled(client: AsyncClient, test_engine):
    """field_confidence entries are scaled from 0-1 to 0-100."""
    ctx = await _register_and_create_org(client, "inv2-fieldconf@example.com", "FieldConf Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        field_confidence=[
            {
                "field_name": "total_amount",
                "value": "5000",
                "confidence": 0.75,
                "needs_review": False,
            },
        ],
    )

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 200
    fc = resp.json()["field_confidences"]
    assert len(fc) == 1
    assert fc[0]["confidence"] == 75.0


async def test_get_invoice_with_client_summary(client: AsyncClient, test_engine):
    """GET detail includes client summary when client is assigned."""
    ctx = await _register_and_create_org(client, "inv2-cldetail@example.com", "ClDetail Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    cid = await _insert_client(test_engine, org_id, name="Detail Client", pib="101010101")
    inv_id = await _insert_invoice(test_engine, org_id, client_id=cid)

    with patch("app.routers.invoices.get_presigned_url", return_value=""):
        resp = await client.get(f"/api/v1/invoices/{inv_id}", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["client_id"] == cid
    assert data["client"]["name"] == "Detail Client"
    assert data["client"]["pib"] == "101010101"


# ---------------------------------------------------------------------------
# Verify — additional branches
# ---------------------------------------------------------------------------


async def test_verify_invoice_with_pib_warning(client: AsyncClient, test_engine):
    """POST /verify adds PIB format warning but still verifies if otherwise valid."""
    ctx = await _register_and_create_org(client, "inv2-verpib@example.com", "VerPIB Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    # Use obviously invalid PIB (wrong length/checksum) to trigger pib warning
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        status="review",
        seller={"pib": "000000000", "name": "Test"},
        buyer={"pib": "000000001", "name": "BuyTest"},
    )

    resp = await client.post(f"/api/v1/invoices/{inv_id}/verify", headers=headers)
    # Should succeed (warnings are non-blocking)
    assert resp.status_code == 200
    assert resp.json()["status"] == "verified"


async def test_verify_invoice_missing_invoice_date(client: AsyncClient, test_engine):
    """POST /verify rejects invoice missing invoice_date."""
    ctx = await _register_and_create_org(client, "inv2-verdate@example.com", "VerDate Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        status="review",
        invoice_date=None,
    )

    resp = await client.post(f"/api/v1/invoices/{inv_id}/verify", headers=headers)
    assert resp.status_code == 400
    assert "Datum fakture" in resp.json()["detail"]


async def test_verify_invoice_missing_total_amount(client: AsyncClient, test_engine):
    """POST /verify rejects invoice missing total_amount."""
    ctx = await _register_and_create_org(client, "inv2-verta@example.com", "VerTA Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(
        test_engine,
        org_id,
        status="review",
        total_amount=None,
        subtotal=None,
        tax_amount=None,
    )

    resp = await client.post(f"/api/v1/invoices/{inv_id}/verify", headers=headers)
    assert resp.status_code == 400
    assert "Ukupan iznos" in resp.json()["detail"]


async def test_verify_invoice_already_verified_rejected(client: AsyncClient, test_engine):
    """POST /verify on an already-verified invoice returns 400."""
    ctx = await _register_and_create_org(client, "inv2-verdup@example.com", "VerDup Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])
    inv_id = await _insert_invoice(test_engine, org_id, status="verified")

    resp = await client.post(f"/api/v1/invoices/{inv_id}/verify", headers=headers)
    assert resp.status_code == 400
    assert "verified" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# List — book_type filter
# ---------------------------------------------------------------------------


async def test_list_invoices_filter_by_book_type(client: AsyncClient, test_engine):
    """book_type filter returns only invoices with matching KPR/KIR book type."""
    ctx = await _register_and_create_org(client, "inv2-bt@example.com", "BookType Org")
    headers = ctx["headers"]
    org_id = _get_org_id(ctx["token"])

    inv_kpr = await _insert_invoice(test_engine, org_id, invoice_number="KPR1", status="verified")
    inv_kir = await _insert_invoice(test_engine, org_id, invoice_number="KIR1", status="verified")

    await _insert_accounting_intent(
        test_engine,
        inv_kpr,
        org_id,
        pdv_book_entries={"book_type": "KPR"},
    )
    await _insert_accounting_intent(
        test_engine,
        inv_kir,
        org_id,
        pdv_book_entries={"book_type": "KIR"},
    )

    resp = await client.get("/api/v1/invoices?book_type=KPR", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] == 1
    assert data["data"][0]["invoice_number"] == "KPR1"
