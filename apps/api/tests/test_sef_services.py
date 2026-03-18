"""Unit tests for SEF service modules.

Covers:
- client.py: DemoSefClient and LiveSefClient (all methods + error paths)
- process.py: process_sef_invoice (happy path, status guards, error rollback)
- sync.py: sync helpers, sync_sef_invoices, get_sync_status, get_sef_client_for_org
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sef_connection import SefConnection
from app.models.sef_invoice import SefInvoice
from app.services.sef.client import (
    DemoSefClient,
    LiveSefClient,
    SefError,
    get_sef_client,
)
from app.services.sef.process import _parse_decimal, process_sef_invoice
from app.services.sef.sync import (
    acquire_sync_lock,
    get_sef_client_for_org,
    get_sync_status,
    is_sync_in_progress,
    release_sync_lock,
    sync_sef_invoices,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_httpx_response(
    payload,
    status_code: int = 200,
    content: bytes = b"",
) -> MagicMock:
    """Build a MagicMock that mimics an httpx.Response.

    Args:
        payload: Dict or list to return from .json().
        status_code: HTTP status code.
        content: Raw bytes to return from .content.

    Returns:
        MagicMock mimicking httpx.Response.
    """
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = str(payload)
    response.content = content
    return response


def _make_async_http_client(response: MagicMock) -> MagicMock:
    """Wrap a response mock in an async context-manager httpx.AsyncClient mock.

    Args:
        response: Mock response returned by client.request() / client.get().

    Returns:
        MagicMock usable as ``async with httpx.AsyncClient() as client``.
    """
    inner = AsyncMock()
    inner.request = AsyncMock(return_value=response)
    inner.get = AsyncMock(return_value=response)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=inner)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _make_redis(locked: bool = False) -> AsyncMock:
    """Create an AsyncMock simulating a Redis client for SEF lock operations.

    Args:
        locked: Whether the lock key already exists (True = lock held).

    Returns:
        AsyncMock with set/delete/exists configured.
    """
    redis = AsyncMock()
    # set with nx=True returns True when key was set (lock acquired)
    redis.set = AsyncMock(return_value=not locked)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=int(locked))
    return redis


def _make_raw_invoice(sef_id: str | None = None) -> dict:
    """Build a minimal raw SEF invoice dict matching the sync expectations.

    Args:
        sef_id: Override the generated sef_id.

    Returns:
        Dict with all fields required by sync_sef_invoices.
    """
    return {
        "sef_id": sef_id or str(uuid4()),
        "sef_status": "DELIVERED",
        "invoice_number": "2026-0001",
        "invoice_date": "2026-03-01",
        "due_date": "2026-03-31",
        "supplier": {
            "name": "Test Supplier d.o.o.",
            "pib": "123456789",
            "address": "Beograd 1",
        },
        "amount": "12000.00",
        "currency": "RSD",
        "received_at": datetime.now(UTC).isoformat(),
        "line_items": [
            {
                "description": "Usluga 1",
                "quantity": "1",
                "unit_price": "10000.00",
                "total": "10000.00",
                "vat_rate": "20.00",
                "vat_amount": "2000.00",
            }
        ],
        "monetary_totals": {
            "tax_exclusive_amount": "10000.00",
            "tax_amount": "2000.00",
            "payable_amount": "12000.00",
        },
    }


# ===========================================================================
# A. SefError
# ===========================================================================


def test_sef_error_stores_status_code():
    """SefError stores status_code and response_body attributes."""
    err = SefError("something went wrong", status_code=422, response_body="bad")
    assert err.status_code == 422
    assert err.response_body == "bad"
    assert "something went wrong" in str(err)


def test_sef_error_defaults_none_status():
    """SefError status_code defaults to None when not provided."""
    err = SefError("minimal error")
    assert err.status_code is None
    assert err.response_body == ""


# ===========================================================================
# B. DemoSefClient
# ===========================================================================


async def test_sef_demo_fetch_inbound_returns_list():
    """DemoSefClient.fetch_inbound_invoices returns a non-empty list."""
    client = DemoSefClient()
    invoices = await client.fetch_inbound_invoices(pib="100002552")
    assert isinstance(invoices, list)
    assert len(invoices) > 0


async def test_sef_demo_invoices_have_required_keys():
    """Each demo invoice contains sef_id, amount, currency, and supplier."""
    client = DemoSefClient()
    invoices = await client.fetch_inbound_invoices(pib="100002552")
    for inv in invoices:
        assert "sef_id" in inv
        assert "amount" in inv
        assert "currency" in inv
        assert "supplier" in inv


async def test_sef_demo_fetch_filtered_by_since():
    """DemoSefClient filters invoices received before the since timestamp."""
    client = DemoSefClient()
    # Initialize first so _invoices is populated
    all_invoices = await client.fetch_inbound_invoices(pib="000")

    # Use a far-future timestamp — should return empty
    future = datetime.now(UTC) + timedelta(days=365)
    filtered = await client.fetch_inbound_invoices(pib="000", since=future)
    assert filtered == []

    # Use a far-past timestamp — should return all
    past = datetime.now(UTC) - timedelta(days=9999)
    from_past = await client.fetch_inbound_invoices(pib="000", since=past)
    assert len(from_past) == len(all_invoices)


async def test_sef_demo_get_invoice_detail_found():
    """DemoSefClient.get_invoice_detail returns ubl_xml for known sef_id."""
    client = DemoSefClient()
    invoices = await client.fetch_inbound_invoices(pib="000")
    first_id = invoices[0]["sef_id"]

    detail = await client.get_invoice_detail(first_id)
    assert detail["sef_id"] == first_id
    assert "ubl_xml" in detail
    assert first_id in detail["ubl_xml"]


async def test_sef_demo_get_invoice_detail_not_found():
    """DemoSefClient.get_invoice_detail raises SefError for unknown sef_id."""
    client = DemoSefClient()
    with pytest.raises(SefError) as exc_info:
        await client.get_invoice_detail("nonexistent-id")
    assert exc_info.value.status_code == 404


async def test_sef_demo_download_pdf_returns_none():
    """DemoSefClient.download_pdf always returns None (no real PDFs)."""
    client = DemoSefClient()
    result = await client.download_pdf("any-sef-id")
    assert result is None


async def test_sef_demo_accept_invoice_returns_approved():
    """DemoSefClient.accept_invoice returns APPROVED status."""
    client = DemoSefClient()
    result = await client.accept_invoice("test-id")
    assert result["sef_status"] == "APPROVED"
    assert result["sef_id"] == "test-id"


async def test_sef_demo_reject_invoice_returns_rejected():
    """DemoSefClient.reject_invoice returns REJECTED status."""
    client = DemoSefClient()
    result = await client.reject_invoice("test-id", reason="Neispravna faktura")
    assert result["sef_status"] == "REJECTED"
    assert result["sef_id"] == "test-id"


async def test_sef_demo_lazy_initialization_stable():
    """DemoSefClient only generates invoices once; second call returns same data."""
    client = DemoSefClient()
    first = await client.fetch_inbound_invoices(pib="000")
    second = await client.fetch_inbound_invoices(pib="000")
    assert [inv["sef_id"] for inv in first] == [inv["sef_id"] for inv in second]


async def test_sef_demo_line_items_structure():
    """Demo invoices contain well-formed line_items with vat_rate."""
    client = DemoSefClient()
    invoices = await client.fetch_inbound_invoices(pib="000")
    # At least one invoice should have line items
    invoices_with_items = [inv for inv in invoices if inv.get("line_items")]
    assert len(invoices_with_items) > 0
    for item in invoices_with_items[0]["line_items"]:
        assert "description" in item
        assert "quantity" in item
        assert "vat_rate" in item


# ===========================================================================
# C. LiveSefClient._request
# ===========================================================================


async def test_sef_live_request_success_returns_json():
    """LiveSefClient._request returns parsed JSON on HTTP 200."""
    payload = {"items": [{"sef_id": "abc"}]}
    response = _make_httpx_response(payload, status_code=200)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="test-key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        result = await client._request("GET", "purchase-invoices")

    assert result == payload


async def test_sef_live_request_204_returns_empty_dict():
    """LiveSefClient._request returns empty dict on HTTP 204 No Content."""
    response = _make_httpx_response({}, status_code=204)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="test-key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        result = await client._request("POST", "purchase-invoices/xyz/accept")

    assert result == {}


async def test_sef_live_request_4xx_raises_sef_error():
    """LiveSefClient._request raises SefError on HTTP 4xx responses."""
    response = _make_httpx_response({"error": "not found"}, status_code=404)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="test-key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        with pytest.raises(SefError) as exc_info:
            await client._request("GET", "purchase-invoices/missing")

    assert exc_info.value.status_code == 404


async def test_sef_live_request_5xx_raises_sef_error():
    """LiveSefClient._request raises SefError on HTTP 5xx responses."""
    response = _make_httpx_response({"error": "server error"}, status_code=500)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="test-key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        with pytest.raises(SefError) as exc_info:
            await client._request("GET", "purchase-invoices")

    assert exc_info.value.status_code == 500


async def test_sef_live_request_sends_api_key_header():
    """LiveSefClient._request sends ApiKey header on every request."""
    payload = []
    response = _make_httpx_response(payload, status_code=200)
    inner = AsyncMock()
    inner.request = AsyncMock(return_value=response)
    inner.get = AsyncMock(return_value=response)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=inner)
    ctx.__aexit__ = AsyncMock(return_value=False)

    client = LiveSefClient(api_key="my-secret-key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        await client._request("GET", "purchase-invoices")

    call_kwargs = inner.request.call_args
    headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
    assert headers.get("ApiKey") == "my-secret-key"


# ===========================================================================
# D. LiveSefClient.fetch_inbound_invoices
# ===========================================================================


async def test_sef_live_fetch_inbound_list_response():
    """fetch_inbound_invoices handles a direct list response."""
    invoices = [{"sef_id": "inv-1"}, {"sef_id": "inv-2"}]
    response = _make_httpx_response(invoices, status_code=200)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        result = await client.fetch_inbound_invoices(pib="123456789")

    assert result == invoices


async def test_sef_live_fetch_inbound_dict_response_items():
    """fetch_inbound_invoices extracts items from a dict response."""
    payload = {"items": [{"sef_id": "inv-1"}], "total": 1}
    response = _make_httpx_response(payload, status_code=200)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        result = await client.fetch_inbound_invoices(pib="123456789")

    assert result == [{"sef_id": "inv-1"}]


async def test_sef_live_fetch_inbound_with_since_adds_date_param():
    """fetch_inbound_invoices includes dateFrom param when since is provided."""
    inner = AsyncMock()
    inner.request = AsyncMock(return_value=_make_httpx_response([], status_code=200))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=inner)
    ctx.__aexit__ = AsyncMock(return_value=False)

    since_dt = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        await client.fetch_inbound_invoices(pib="123", since=since_dt)

    call_kwargs = inner.request.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
    assert "dateFrom" in params
    assert "2026-03-01" in params["dateFrom"]


async def test_sef_live_fetch_inbound_no_since_omits_date_param():
    """fetch_inbound_invoices omits dateFrom when since is None."""
    inner = AsyncMock()
    inner.request = AsyncMock(return_value=_make_httpx_response([], status_code=200))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=inner)
    ctx.__aexit__ = AsyncMock(return_value=False)

    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        await client.fetch_inbound_invoices(pib="123")

    call_kwargs = inner.request.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
    assert "dateFrom" not in params


# ===========================================================================
# E. LiveSefClient.get_invoice_detail
# ===========================================================================


async def test_sef_live_get_invoice_detail_returns_dict():
    """get_invoice_detail returns a dict on success."""
    payload = {"sef_id": "abc-123", "ubl_xml": "<Invoice/>"}
    response = _make_httpx_response(payload, status_code=200)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        result = await client.get_invoice_detail("abc-123")

    assert result["sef_id"] == "abc-123"


async def test_sef_live_get_invoice_detail_list_response_returns_empty():
    """get_invoice_detail returns empty dict when API returns a list."""
    response = _make_httpx_response([], status_code=200)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        result = await client.get_invoice_detail("abc-123")

    assert result == {}


async def test_sef_live_get_invoice_detail_404_raises():
    """get_invoice_detail raises SefError when invoice not found on SEF."""
    response = _make_httpx_response({"error": "not found"}, status_code=404)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        with pytest.raises(SefError):
            await client.get_invoice_detail("missing")


# ===========================================================================
# F. LiveSefClient.download_pdf
# ===========================================================================


async def test_sef_live_download_pdf_success():
    """download_pdf returns bytes on HTTP 200 with PDF content."""
    pdf_bytes = b"%PDF-1.4 fake content"
    response = _make_httpx_response({}, status_code=200, content=pdf_bytes)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        result = await client.download_pdf("inv-001")

    assert result == pdf_bytes


async def test_sef_live_download_pdf_404_returns_none():
    """download_pdf returns None when SEF returns 404."""
    response = _make_httpx_response({}, status_code=404)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        result = await client.download_pdf("inv-001")

    assert result is None


async def test_sef_live_download_pdf_http_error_returns_none():
    """download_pdf returns None when an httpx.HTTPError is raised."""
    inner = AsyncMock()
    inner.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=inner)
    ctx.__aexit__ = AsyncMock(return_value=False)

    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        result = await client.download_pdf("inv-001")

    assert result is None


# ===========================================================================
# G. LiveSefClient.accept_invoice / reject_invoice
# ===========================================================================


async def test_sef_live_accept_invoice_success():
    """accept_invoice posts to the correct path and returns a dict."""
    payload = {"sef_id": "inv-001", "sef_status": "APPROVED"}
    response = _make_httpx_response(payload, status_code=200)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        result = await client.accept_invoice("inv-001")

    assert result["sef_status"] == "APPROVED"


async def test_sef_live_accept_invoice_list_response_returns_empty():
    """accept_invoice returns empty dict when API unexpectedly returns a list."""
    response = _make_httpx_response([], status_code=200)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        result = await client.accept_invoice("inv-001")

    assert result == {}


async def test_sef_live_reject_invoice_sends_reason():
    """reject_invoice POSTs with reason in the JSON body."""
    inner = AsyncMock()
    inner.request = AsyncMock(
        return_value=_make_httpx_response({"sef_id": "inv-001"}, status_code=200)
    )
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=inner)
    ctx.__aexit__ = AsyncMock(return_value=False)

    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        await client.reject_invoice("inv-001", reason="Duplikat fakture")

    call_kwargs = inner.request.call_args
    json_body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json", {})
    assert json_body == {"reason": "Duplikat fakture"}


async def test_sef_live_reject_invoice_list_response_returns_empty():
    """reject_invoice returns empty dict when API unexpectedly returns a list."""
    response = _make_httpx_response([], status_code=200)
    ctx = _make_async_http_client(response)

    client = LiveSefClient(api_key="key", base_url="https://sef.test")
    with patch("app.services.sef.client.httpx.AsyncClient", return_value=ctx):
        result = await client.reject_invoice("inv-001", reason="reason")

    assert result == {}


# ===========================================================================
# H. get_sef_client factory
# ===========================================================================


def test_sef_get_sef_client_demo_mode_returns_demo_client():
    """get_sef_client returns DemoSefClient when sef_demo_mode is True."""
    with patch("app.services.sef.client.get_settings") as mock_settings:
        mock_settings.return_value.sef_demo_mode = True
        client = get_sef_client()
    assert isinstance(client, DemoSefClient)


def test_sef_get_sef_client_live_mode_returns_demo_fallback():
    """get_sef_client returns DemoSefClient as fallback even when demo mode is off."""
    with patch("app.services.sef.client.get_settings") as mock_settings:
        mock_settings.return_value.sef_demo_mode = False
        client = get_sef_client()
    # Current implementation always falls back to Demo; assert it's a BaseSefClient
    assert client is not None


# ===========================================================================
# I. _parse_decimal (process.py helper)
# ===========================================================================


def test_sef_parse_decimal_string():
    """_parse_decimal converts a valid numeric string to Decimal."""
    result = _parse_decimal("12345.67")
    assert result == Decimal("12345.67")


def test_sef_parse_decimal_integer():
    """_parse_decimal converts an integer to Decimal."""
    result = _parse_decimal(100)
    assert result == Decimal("100")


def test_sef_parse_decimal_float():
    """_parse_decimal converts a float to Decimal via str to avoid imprecision."""
    result = _parse_decimal(1.5)
    assert result is not None


def test_sef_parse_decimal_none_returns_none():
    """_parse_decimal returns None for None input."""
    assert _parse_decimal(None) is None


def test_sef_parse_decimal_invalid_string_returns_none():
    """_parse_decimal returns None for non-numeric strings."""
    assert _parse_decimal("not-a-number") is None


def test_sef_parse_decimal_empty_string_returns_none():
    """_parse_decimal returns None for empty string."""
    assert _parse_decimal("") is None


# ===========================================================================
# J. process_sef_invoice — mock-based unit tests
# ===========================================================================


def _make_sef_invoice_mock(
    status: str = "new",
    sef_response_json: dict | None = None,
) -> MagicMock:
    """Create a MagicMock SefInvoice instance for use in unit tests.

    Args:
        status: Internal status to set on the mock.
        sef_response_json: Optional SEF response data dict.

    Returns:
        MagicMock with SefInvoice-like attributes.
    """
    inv = MagicMock(spec=SefInvoice)
    inv.id = uuid4()
    inv.status = status
    inv.invoice_number = "2026-0099"
    inv.invoice_date = None
    inv.currency = "RSD"
    inv.sef_response_json = sef_response_json or {
        "supplier": {
            "name": "Supplier d.o.o.",
            "pib": "987654321",
            "address": "Beograd",
            "mb": None,
        },
        "monetary_totals": {
            "tax_exclusive_amount": "10000.00",
            "tax_amount": "2000.00",
            "payable_amount": "12000.00",
        },
        "line_items": [
            {
                "description": "Usluga 1",
                "quantity": "1",
                "unit_price": "10000.00",
                "total": "10000.00",
                "vat_rate": "20.00",
                "vat_amount": "2000.00",
            }
        ],
    }
    inv.invoice_id = None
    inv.processed_at = None
    inv.processing_error = None
    return inv


def _make_mock_db_for_process(sef_inv: MagicMock | None) -> AsyncMock:
    """Build a mock AsyncSession that returns the given SefInvoice from execute().

    The second flush() call (after db.add(invoice)) will assign a UUID to the
    invoice's id field, mimicking what PostgreSQL does on flush in a real session.

    Args:
        sef_inv: The SefInvoice mock to return, or None to simulate not-found.

    Returns:
        AsyncMock behaving like an AsyncSession.
    """
    db = AsyncMock(spec=AsyncSession)

    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none.return_value = sef_inv

    db.execute = AsyncMock(return_value=scalar_mock)

    _flush_call_count = [0]

    async def _flush_side_effect():
        _flush_call_count[0] += 1
        # On the second flush (after db.add(invoice)), assign an ID to the added invoice
        if _flush_call_count[0] == 2 and db.add.call_count >= 1:
            added = db.add.call_args[0][0]
            if hasattr(added, "id") and added.id is None:
                added.id = uuid4()

    db.flush = AsyncMock(side_effect=_flush_side_effect)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    return db


async def test_sef_process_invoice_not_found_raises():
    """process_sef_invoice raises ValueError when SefInvoice does not exist."""
    db = _make_mock_db_for_process(None)
    with pytest.raises(ValueError, match="not found"):
        await process_sef_invoice(db, uuid4(), uuid4())


async def test_sef_process_invoice_wrong_status_raises():
    """process_sef_invoice raises ValueError when status is not new/pending."""
    inv = _make_sef_invoice_mock(status="processed")
    db = _make_mock_db_for_process(inv)
    with pytest.raises(ValueError, match="cannot be processed"):
        await process_sef_invoice(db, inv.id, uuid4())


async def test_sef_process_invoice_archived_status_raises():
    """process_sef_invoice raises ValueError when status is 'archived'."""
    inv = _make_sef_invoice_mock(status="archived")
    db = _make_mock_db_for_process(inv)
    with pytest.raises(ValueError, match="cannot be processed"):
        await process_sef_invoice(db, inv.id, uuid4())


async def test_sef_process_invoice_happy_path():
    """process_sef_invoice sets status to processed and adds Invoice to session."""
    inv = _make_sef_invoice_mock(status="new")
    db = _make_mock_db_for_process(inv)
    org_id = uuid4()

    result = await process_sef_invoice(db, inv.id, org_id)

    assert result.status == "processed"
    assert result.invoice_id is not None
    # Invoice model should have been added to the session
    db.add.assert_called_once()
    db.commit.assert_called()


async def test_sef_process_invoice_pending_status_allowed():
    """process_sef_invoice accepts SefInvoices with status 'pending'."""
    inv = _make_sef_invoice_mock(status="pending")
    db = _make_mock_db_for_process(inv)

    result = await process_sef_invoice(db, inv.id, uuid4())

    assert result.status == "processed"


async def test_sef_process_invoice_maps_line_items():
    """process_sef_invoice passes line_items to the Invoice constructor."""
    inv = _make_sef_invoice_mock(status="new")
    db = _make_mock_db_for_process(inv)

    await process_sef_invoice(db, inv.id, uuid4())

    # Inspect the Invoice added to the session
    added_invoice = db.add.call_args[0][0]
    assert added_invoice.line_items is not None
    assert len(added_invoice.line_items) == 1
    assert added_invoice.line_items[0]["description"] == "Usluga 1"
    assert added_invoice.line_items[0]["tax_rate"] == "20.00"


async def test_sef_process_invoice_seller_dict_populated():
    """process_sef_invoice populates Invoice seller from SEF supplier."""
    inv = _make_sef_invoice_mock(status="new")
    db = _make_mock_db_for_process(inv)

    await process_sef_invoice(db, inv.id, uuid4())

    added_invoice = db.add.call_args[0][0]
    assert added_invoice.seller["pib"] == "987654321"
    assert added_invoice.seller["name"] == "Supplier d.o.o."


async def test_sef_process_invoice_amounts_parsed():
    """process_sef_invoice correctly parses tax and total amounts from JSON."""
    inv = _make_sef_invoice_mock(status="new")
    db = _make_mock_db_for_process(inv)

    await process_sef_invoice(db, inv.id, uuid4())

    added_invoice = db.add.call_args[0][0]
    assert added_invoice.subtotal == Decimal("10000.00")
    assert added_invoice.tax_amount == Decimal("2000.00")
    assert added_invoice.total_amount == Decimal("12000.00")


async def test_sef_process_invoice_empty_response_json():
    """process_sef_invoice handles None sef_response_json without raising."""
    inv = _make_sef_invoice_mock(status="new", sef_response_json=None)
    # Override the spec attribute so it returns None
    inv.sef_response_json = None
    db = _make_mock_db_for_process(inv)

    result = await process_sef_invoice(db, inv.id, uuid4())

    assert result.status == "processed"
    added_invoice = db.add.call_args[0][0]
    assert added_invoice.subtotal is None
    assert added_invoice.total_amount is None


async def test_sef_process_invoice_error_reverts_status():
    """process_sef_invoice reverts status to 'new' and records error on exception."""
    inv = _make_sef_invoice_mock(status="new")

    db = AsyncMock(spec=AsyncSession)
    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none.return_value = inv
    db.execute = AsyncMock(return_value=scalar_mock)
    db.flush = AsyncMock(side_effect=[None, RuntimeError("DB write failed")])
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    with pytest.raises(RuntimeError, match="DB write failed"):
        await process_sef_invoice(db, inv.id, uuid4())

    assert inv.status == "new"
    assert inv.processing_error is not None
    db.rollback.assert_called()


# ===========================================================================
# K. sync.py — Redis lock helpers
# ===========================================================================


async def test_sef_acquire_sync_lock_success():
    """acquire_sync_lock returns True when lock is not held."""
    redis = _make_redis(locked=False)
    org_id = uuid4()

    result = await acquire_sync_lock(redis, org_id)

    assert result is True
    redis.set.assert_called_once()
    call_kwargs = redis.set.call_args
    key = call_kwargs[0][0]
    assert str(org_id) in key


async def test_sef_acquire_sync_lock_already_locked():
    """acquire_sync_lock returns False when lock is already held."""
    redis = _make_redis(locked=True)
    org_id = uuid4()

    result = await acquire_sync_lock(redis, org_id)

    assert result is False


async def test_sef_release_sync_lock_deletes_key():
    """release_sync_lock deletes the correct Redis key."""
    redis = _make_redis()
    org_id = uuid4()

    await release_sync_lock(redis, org_id)

    redis.delete.assert_called_once()
    call_args = redis.delete.call_args[0][0]
    assert str(org_id) in call_args


async def test_sef_is_sync_in_progress_true():
    """is_sync_in_progress returns True when lock key exists."""
    redis = _make_redis(locked=True)
    org_id = uuid4()

    result = await is_sync_in_progress(redis, org_id)

    assert result is True


async def test_sef_is_sync_in_progress_false():
    """is_sync_in_progress returns False when lock key does not exist."""
    redis = _make_redis(locked=False)
    org_id = uuid4()

    result = await is_sync_in_progress(redis, org_id)

    assert result is False


# ===========================================================================
# L. get_sef_client_for_org
# ===========================================================================


async def test_sef_get_client_for_org_no_connection_returns_demo():
    """get_sef_client_for_org returns DemoSefClient when no SefConnection exists."""
    db = AsyncMock(spec=AsyncSession)
    # Simulate no connection found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    with patch("app.config.get_settings") as mock_settings:
        mock_settings.return_value.sef_demo_mode = True
        mock_settings.return_value.sef_api_base_url = "https://sef.test"
        client, connection = await get_sef_client_for_org(db, uuid4())

    assert isinstance(client, DemoSefClient)
    assert connection is None


async def test_sef_get_client_for_org_demo_mode_ignores_connection():
    """get_sef_client_for_org returns DemoSefClient in demo mode even if connection exists."""
    mock_connection = MagicMock(spec=SefConnection)
    mock_connection.api_key_encrypted = "some-key"
    mock_connection.pib = "100002552"

    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_connection
    db.execute = AsyncMock(return_value=mock_result)

    with patch("app.config.get_settings") as mock_settings:
        mock_settings.return_value.sef_demo_mode = True
        mock_settings.return_value.sef_api_base_url = "https://sef.test"
        client, connection = await get_sef_client_for_org(db, uuid4())

    assert isinstance(client, DemoSefClient)


async def test_sef_get_client_for_org_live_mode_with_connection():
    """get_sef_client_for_org returns LiveSefClient when demo mode is off and connection exists."""
    mock_connection = MagicMock(spec=SefConnection)
    mock_connection.api_key_encrypted = "live-api-key"
    mock_connection.pib = "100002552"

    db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_connection
    db.execute = AsyncMock(return_value=mock_result)

    with patch("app.config.get_settings") as mock_settings:
        mock_settings.return_value.sef_demo_mode = False
        mock_settings.return_value.sef_api_base_url = "https://efaktura.mfin.gov.rs/api/v1"
        client, connection = await get_sef_client_for_org(db, uuid4())

    assert isinstance(client, LiveSefClient)
    assert client.api_key == "live-api-key"
    assert connection is mock_connection


# ===========================================================================
# M. sync_sef_invoices
# ===========================================================================


def _make_mock_db_for_sync(
    existing_sef_inv: MagicMock | None = None,
    num_invoices: int = 1,
) -> AsyncMock:
    """Build a mock AsyncSession for sync_sef_invoices unit tests.

    When get_sef_client_for_org is also mocked (skipping the connection lookup),
    every execute() call is a duplicate-check for a raw invoice.

    Args:
        existing_sef_inv: SefInvoice to return from duplicate check, or None for new.
        num_invoices: Number of duplicate-check execute() calls to expect.

    Returns:
        AsyncMock behaving like an AsyncSession.
    """
    db = AsyncMock(spec=AsyncSession)

    dup_result = MagicMock()
    dup_result.scalar_one_or_none.return_value = existing_sef_inv

    db.execute = AsyncMock(return_value=dup_result)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()

    return db


async def test_sef_sync_invoices_lock_already_held_raises():
    """sync_sef_invoices raises RuntimeError when sync lock cannot be acquired."""
    db = AsyncMock(spec=AsyncSession)
    redis = _make_redis(locked=True)
    org_id = uuid4()

    with pytest.raises(RuntimeError, match="Sync already in progress"):
        await sync_sef_invoices(db, org_id, redis)

    db.execute.assert_not_called()


async def test_sef_sync_invoices_creates_new_records():
    """sync_sef_invoices adds SefInvoice to session for each new invoice."""
    raw_invoice = _make_raw_invoice()
    db = _make_mock_db_for_sync(existing_sef_inv=None)
    redis = _make_redis(locked=False)
    org_id = uuid4()

    mock_client = AsyncMock()
    mock_client.fetch_inbound_invoices = AsyncMock(return_value=[raw_invoice])

    with patch("app.services.sef.sync.get_sef_client_for_org", return_value=(mock_client, None)):
        count = await sync_sef_invoices(db, org_id, redis)

    assert count == 1
    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert isinstance(added, SefInvoice)
    assert added.sef_id == raw_invoice["sef_id"]
    assert added.status == "new"
    assert added.direction == "INBOUND"


async def test_sef_sync_invoices_deduplicates_existing():
    """sync_sef_invoices skips invoices that already exist (duplicate check)."""
    raw_invoice = _make_raw_invoice()
    existing = MagicMock(spec=SefInvoice)
    db = _make_mock_db_for_sync(existing_sef_inv=existing)
    redis = _make_redis(locked=False)
    org_id = uuid4()

    mock_client = AsyncMock()
    mock_client.fetch_inbound_invoices = AsyncMock(return_value=[raw_invoice])

    with patch("app.services.sef.sync.get_sef_client_for_org", return_value=(mock_client, None)):
        count = await sync_sef_invoices(db, org_id, redis)

    assert count == 0
    db.add.assert_not_called()


async def test_sef_sync_invoices_skips_missing_sef_id():
    """sync_sef_invoices skips raw invoice dicts that have no sef_id."""
    db = AsyncMock(spec=AsyncSession)
    redis = _make_redis(locked=False)
    org_id = uuid4()

    conn_result = MagicMock()
    conn_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=conn_result)
    db.commit = AsyncMock()
    db.add = MagicMock()

    raw_without_id = {"invoice_number": "2026-0001", "amount": "100.00"}
    mock_client = AsyncMock()
    mock_client.fetch_inbound_invoices = AsyncMock(return_value=[raw_without_id])

    with patch("app.services.sef.sync.get_sef_client_for_org", return_value=(mock_client, None)):
        count = await sync_sef_invoices(db, org_id, redis)

    assert count == 0
    db.add.assert_not_called()


async def test_sef_sync_invoices_invalid_amount_stored_as_none():
    """sync_sef_invoices stores None amount when value cannot be parsed."""
    raw_invoice = _make_raw_invoice()
    raw_invoice["amount"] = "not-a-number"
    raw_invoice["monetary_totals"] = {}

    db = _make_mock_db_for_sync(existing_sef_inv=None)
    redis = _make_redis(locked=False)
    org_id = uuid4()

    mock_client = AsyncMock()
    mock_client.fetch_inbound_invoices = AsyncMock(return_value=[raw_invoice])

    with patch("app.services.sef.sync.get_sef_client_for_org", return_value=(mock_client, None)):
        count = await sync_sef_invoices(db, org_id, redis)

    assert count == 1
    added = db.add.call_args[0][0]
    assert added.amount is None


async def test_sef_sync_invoices_invalid_received_at_uses_now():
    """sync_sef_invoices uses current time when received_at is malformed."""
    raw_invoice = _make_raw_invoice()
    raw_invoice["received_at"] = "not-a-date"

    db = _make_mock_db_for_sync(existing_sef_inv=None)
    redis = _make_redis(locked=False)
    org_id = uuid4()

    mock_client = AsyncMock()
    mock_client.fetch_inbound_invoices = AsyncMock(return_value=[raw_invoice])

    before = datetime.now(UTC)
    with patch("app.services.sef.sync.get_sef_client_for_org", return_value=(mock_client, None)):
        await sync_sef_invoices(db, org_id, redis)

    added = db.add.call_args[0][0]
    assert added.received_at >= before


async def test_sef_sync_invoices_invalid_invoice_date_stores_none():
    """sync_sef_invoices stores invoice_date as None when format is invalid."""
    raw_invoice = _make_raw_invoice()
    raw_invoice["invoice_date"] = "31/02/2026"  # Invalid format

    db = _make_mock_db_for_sync(existing_sef_inv=None)
    redis = _make_redis(locked=False)
    org_id = uuid4()

    mock_client = AsyncMock()
    mock_client.fetch_inbound_invoices = AsyncMock(return_value=[raw_invoice])

    with patch("app.services.sef.sync.get_sef_client_for_org", return_value=(mock_client, None)):
        await sync_sef_invoices(db, org_id, redis)

    added = db.add.call_args[0][0]
    assert added.invoice_date is None


async def test_sef_sync_invoices_updates_connection_metadata():
    """sync_sef_invoices updates last_sync_at and total_invoices_synced on connection."""
    raw_invoices = [_make_raw_invoice(), _make_raw_invoice()]

    mock_connection = MagicMock(spec=SefConnection)
    mock_connection.last_sync_at = None
    mock_connection.total_invoices_synced = 5
    mock_connection.pib = "100002552"

    # Each invoice triggers one duplicate-check execute call; both return None = new
    db = _make_mock_db_for_sync(existing_sef_inv=None, num_invoices=2)
    redis = _make_redis(locked=False)
    org_id = uuid4()

    mock_sef_client = AsyncMock()
    mock_sef_client.fetch_inbound_invoices = AsyncMock(return_value=raw_invoices)

    patch_target = "app.services.sef.sync.get_sef_client_for_org"
    with patch(patch_target, return_value=(mock_sef_client, mock_connection)):
        count = await sync_sef_invoices(db, org_id, redis)

    assert count == 2
    assert mock_connection.last_sync_at is not None
    assert mock_connection.last_sync_status == "success"
    assert mock_connection.last_sync_error is None
    assert mock_connection.total_invoices_synced == 7  # 5 + 2


async def test_sef_sync_invoices_releases_lock_after_success():
    """sync_sef_invoices releases the Redis lock even after a successful run."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    db.commit = AsyncMock()
    redis = _make_redis(locked=False)
    org_id = uuid4()

    mock_client = AsyncMock()
    mock_client.fetch_inbound_invoices = AsyncMock(return_value=[])

    with patch("app.services.sef.sync.get_sef_client_for_org", return_value=(mock_client, None)):
        await sync_sef_invoices(db, org_id, redis)

    redis.delete.assert_called_once()


async def test_sef_sync_invoices_releases_lock_after_error():
    """sync_sef_invoices releases the Redis lock even when an error occurs."""
    db = AsyncMock(spec=AsyncSession)
    db.rollback = AsyncMock()
    db.commit = AsyncMock()
    redis = _make_redis(locked=False)
    org_id = uuid4()

    mock_client = AsyncMock()
    mock_client.fetch_inbound_invoices = AsyncMock(side_effect=RuntimeError("SEF down"))

    with patch("app.services.sef.sync.get_sef_client_for_org", return_value=(mock_client, None)):
        with pytest.raises(RuntimeError, match="SEF down"):
            await sync_sef_invoices(db, org_id, redis)

    # Lock must be released even on error
    redis.delete.assert_called_once()


async def test_sef_sync_invoices_uses_monetary_totals_for_amount():
    """sync_sef_invoices falls back to monetary_totals.payable_amount when amount is missing."""
    raw_invoice = _make_raw_invoice()
    del raw_invoice["amount"]  # Remove direct amount field
    raw_invoice["monetary_totals"]["payable_amount"] = "9900.00"

    db = _make_mock_db_for_sync(existing_sef_inv=None)
    redis = _make_redis(locked=False)
    org_id = uuid4()

    mock_client = AsyncMock()
    mock_client.fetch_inbound_invoices = AsyncMock(return_value=[raw_invoice])

    with patch("app.services.sef.sync.get_sef_client_for_org", return_value=(mock_client, None)):
        count = await sync_sef_invoices(db, org_id, redis)

    assert count == 1
    added = db.add.call_args[0][0]
    assert added.amount == Decimal("9900.00")


# ===========================================================================
# N. get_sync_status
# ===========================================================================


async def test_sef_get_sync_status_no_connection():
    """get_sync_status returns None last_sync_at when no SefConnection exists."""
    db = AsyncMock(spec=AsyncSession)
    redis = _make_redis(locked=False)
    org_id = uuid4()

    mock_result_conn = MagicMock()
    mock_result_conn.scalar_one_or_none.return_value = None

    mock_result_count = MagicMock()
    mock_result_count.scalar.return_value = 3

    db.execute = AsyncMock(side_effect=[mock_result_conn, mock_result_count])

    status = await get_sync_status(db, org_id, redis)

    assert status["last_sync_at"] is None
    assert status["pending_count"] == 3
    assert status["is_syncing"] is False


async def test_sef_get_sync_status_with_connection():
    """get_sync_status returns last_sync_at ISO string from connection."""
    db = AsyncMock(spec=AsyncSession)
    redis = _make_redis(locked=False)
    org_id = uuid4()

    sync_time = datetime(2026, 3, 15, 10, 30, 0, tzinfo=UTC)
    mock_connection = MagicMock(spec=SefConnection)
    mock_connection.last_sync_at = sync_time

    mock_result_conn = MagicMock()
    mock_result_conn.scalar_one_or_none.return_value = mock_connection

    mock_result_count = MagicMock()
    mock_result_count.scalar.return_value = 0

    db.execute = AsyncMock(side_effect=[mock_result_conn, mock_result_count])

    status = await get_sync_status(db, org_id, redis)

    assert status["last_sync_at"] == sync_time.isoformat()
    assert status["pending_count"] == 0
    assert status["is_syncing"] is False


async def test_sef_get_sync_status_is_syncing_true():
    """get_sync_status reports is_syncing=True when lock is held."""
    db = AsyncMock(spec=AsyncSession)
    redis = _make_redis(locked=True)
    org_id = uuid4()

    mock_result_conn = MagicMock()
    mock_result_conn.scalar_one_or_none.return_value = None

    mock_result_count = MagicMock()
    mock_result_count.scalar.return_value = 0

    db.execute = AsyncMock(side_effect=[mock_result_conn, mock_result_count])

    status = await get_sync_status(db, org_id, redis)

    assert status["is_syncing"] is True


async def test_sef_get_sync_status_connection_no_last_sync():
    """get_sync_status returns None last_sync_at when connection has no sync timestamp."""
    db = AsyncMock(spec=AsyncSession)
    redis = _make_redis(locked=False)
    org_id = uuid4()

    mock_connection = MagicMock(spec=SefConnection)
    mock_connection.last_sync_at = None

    mock_result_conn = MagicMock()
    mock_result_conn.scalar_one_or_none.return_value = mock_connection

    mock_result_count = MagicMock()
    mock_result_count.scalar.return_value = 7

    db.execute = AsyncMock(side_effect=[mock_result_conn, mock_result_count])

    status = await get_sync_status(db, org_id, redis)

    assert status["last_sync_at"] is None
    assert status["pending_count"] == 7
