"""Unit tests for the MiniMax REST API client.

Tests cover OAuth2 authentication, token caching, all public API methods,
and error-handling paths. No database is needed — pure unit tests with
httpx.AsyncClient mocked throughout.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.minimax.client import MiniMaxClient, MiniMaxError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(**kwargs) -> MiniMaxClient:
    """Create a MiniMaxClient with sensible test defaults.

    Args:
        **kwargs: Field overrides for MiniMaxClient constructor.

    Returns:
        MiniMaxClient instance.
    """
    return MiniMaxClient(
        client_id=kwargs.get("client_id", "test_client_id"),
        client_secret=kwargs.get("client_secret", "test_secret"),
        username=kwargs.get("username", "test_user"),
        password=kwargs.get("password", "test_pass"),
        org_id=kwargs.get("org_id", 12345),
        timeout=kwargs.get("timeout", 30),
    )


def _make_httpx_response(payload, status_code: int = 200, text: str = "") -> MagicMock:
    """Build a MagicMock that mimics an httpx.Response.

    Args:
        payload: Dict or list to return from .json().
        status_code: HTTP status code.
        text: Text to return from .text.

    Returns:
        MagicMock mimicking httpx.Response.
    """
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = text or str(payload)
    response.content = b"content"
    return response


def _make_async_http_client(response: MagicMock) -> MagicMock:
    """Wrap a response mock in an async context-manager httpx.AsyncClient mock.

    Args:
        response: Mock response returned by client methods.

    Returns:
        MagicMock usable as ``async with httpx.AsyncClient() as client``.
    """
    inner = AsyncMock()
    inner.post = AsyncMock(return_value=response)
    inner.request = AsyncMock(return_value=response)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=inner)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# A. authenticate()
# ---------------------------------------------------------------------------


async def test_authenticate_returns_token_on_success():
    """authenticate() returns the access token from the token response."""
    token_response = _make_httpx_response({"access_token": "abc123", "expires_in": 3600})
    client = _make_client()

    with patch("httpx.AsyncClient", return_value=_make_async_http_client(token_response)):
        token = await client.authenticate()

    assert token == "abc123"


async def test_authenticate_caches_token():
    """Second call to authenticate() reuses the cached token without an HTTP request."""
    token_response = _make_httpx_response({"access_token": "cached_token", "expires_in": 3600})
    client = _make_client()

    with patch(
        "httpx.AsyncClient", return_value=_make_async_http_client(token_response)
    ) as mock_cls:
        await client.authenticate()
        token = await client.authenticate()

    # httpx.AsyncClient context manager was entered only once
    assert mock_cls.call_count == 1
    assert token == "cached_token"


async def test_authenticate_refreshes_expired_token():
    """authenticate() fetches a new token after the previous one expires."""
    first_response = _make_httpx_response({"access_token": "old_token", "expires_in": 3600})
    second_response = _make_httpx_response({"access_token": "new_token", "expires_in": 3600})
    client = _make_client()

    with patch("httpx.AsyncClient", return_value=_make_async_http_client(first_response)):
        await client.authenticate()

    # Force expiry
    client._token_expires_at = datetime.now(UTC) - timedelta(seconds=10)

    with patch("httpx.AsyncClient", return_value=_make_async_http_client(second_response)):
        token = await client.authenticate()

    assert token == "new_token"


async def test_authenticate_raises_minimax_error_on_non_200():
    """authenticate() raises MiniMaxError when the token endpoint returns a non-200 status."""
    error_response = _make_httpx_response({}, status_code=401, text="Unauthorized")
    client = _make_client()

    with patch("httpx.AsyncClient", return_value=_make_async_http_client(error_response)):
        with pytest.raises(MiniMaxError) as exc_info:
            await client.authenticate()

    assert exc_info.value.status_code == 401
    assert "Authentication failed" in str(exc_info.value)


async def test_authenticate_raises_on_400():
    """authenticate() raises MiniMaxError for a 400 Bad Request."""
    bad_response = _make_httpx_response({}, status_code=400, text="Bad credentials")
    client = _make_client()

    with patch("httpx.AsyncClient", return_value=_make_async_http_client(bad_response)):
        with pytest.raises(MiniMaxError) as exc_info:
            await client.authenticate()

    assert exc_info.value.status_code == 400


async def test_authenticate_stores_token_expires_at():
    """authenticate() sets _token_expires_at approximately 60s before actual expiry."""
    token_response = _make_httpx_response({"access_token": "tok", "expires_in": 3600})
    client = _make_client()

    before = datetime.now(UTC)
    with patch("httpx.AsyncClient", return_value=_make_async_http_client(token_response)):
        await client.authenticate()
    after = datetime.now(UTC)

    # Should expire roughly 3540 seconds from now (3600 - 60)
    expected_low = before + timedelta(seconds=3530)
    expected_high = after + timedelta(seconds=3541)
    assert expected_low <= client._token_expires_at <= expected_high


async def test_authenticate_defaults_expires_in_when_missing():
    """authenticate() uses 3600 as the default expires_in when absent from response."""
    token_response = _make_httpx_response({"access_token": "tok"})
    client = _make_client()

    before = datetime.now(UTC)
    with patch("httpx.AsyncClient", return_value=_make_async_http_client(token_response)):
        await client.authenticate()

    # expires_in defaults to 3600, so expiry window is ~3540s from now
    assert client._token_expires_at > before + timedelta(seconds=3500)


# ---------------------------------------------------------------------------
# B. _request() — generic authenticated request
# ---------------------------------------------------------------------------


async def test_request_adds_bearer_token():
    """_request() sets the Authorization header to the active token."""
    token_resp = _make_httpx_response({"access_token": "mytoken", "expires_in": 3600})
    api_resp = _make_httpx_response({"result": "ok"})

    client = _make_client()
    inner_auth = AsyncMock()
    inner_auth.post = AsyncMock(return_value=token_resp)
    auth_ctx = MagicMock()
    auth_ctx.__aenter__ = AsyncMock(return_value=inner_auth)
    auth_ctx.__aexit__ = AsyncMock(return_value=False)

    inner_api = AsyncMock()
    inner_api.request = AsyncMock(return_value=api_resp)
    api_ctx = MagicMock()
    api_ctx.__aenter__ = AsyncMock(return_value=inner_api)
    api_ctx.__aexit__ = AsyncMock(return_value=False)

    call_count = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return auth_ctx if call_count == 1 else api_ctx

    with patch("httpx.AsyncClient", side_effect=_side_effect):
        await client._request("GET", "customers")

    _, kwargs = inner_api.request.call_args
    assert "Authorization" in kwargs["headers"]
    assert kwargs["headers"]["Authorization"] == "Bearer mytoken"


async def test_request_returns_204_as_empty_dict():
    """_request() returns an empty dict for HTTP 204 No Content."""
    token_resp = _make_httpx_response({"access_token": "tok", "expires_in": 3600})
    no_content_resp = _make_httpx_response({}, status_code=204)
    no_content_resp.content = b""

    client = _make_client()
    inner_auth = AsyncMock()
    inner_auth.post = AsyncMock(return_value=token_resp)
    auth_ctx = MagicMock()
    auth_ctx.__aenter__ = AsyncMock(return_value=inner_auth)
    auth_ctx.__aexit__ = AsyncMock(return_value=False)

    inner_api = AsyncMock()
    inner_api.request = AsyncMock(return_value=no_content_resp)
    api_ctx = MagicMock()
    api_ctx.__aenter__ = AsyncMock(return_value=inner_api)
    api_ctx.__aexit__ = AsyncMock(return_value=False)

    call_count = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return auth_ctx if call_count == 1 else api_ctx

    with patch("httpx.AsyncClient", side_effect=_side_effect):
        result = await client._request("DELETE", "customers/1")

    assert result == {}


async def test_request_raises_on_400():
    """_request() raises MiniMaxError when the API returns 400+."""
    token_resp = _make_httpx_response({"access_token": "tok", "expires_in": 3600})
    error_resp = _make_httpx_response({}, status_code=422, text="Unprocessable")

    client = _make_client()
    inner_auth = AsyncMock()
    inner_auth.post = AsyncMock(return_value=token_resp)
    auth_ctx = MagicMock()
    auth_ctx.__aenter__ = AsyncMock(return_value=inner_auth)
    auth_ctx.__aexit__ = AsyncMock(return_value=False)

    inner_api = AsyncMock()
    inner_api.request = AsyncMock(return_value=error_resp)
    api_ctx = MagicMock()
    api_ctx.__aenter__ = AsyncMock(return_value=inner_api)
    api_ctx.__aexit__ = AsyncMock(return_value=False)

    call_count = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return auth_ctx if call_count == 1 else api_ctx

    with patch("httpx.AsyncClient", side_effect=_side_effect):
        with pytest.raises(MiniMaxError) as exc_info:
            await client._request("POST", "receivedinvoices", json={})

    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Helper: build a pre-authenticated client with _request mocked
# ---------------------------------------------------------------------------


def _patched_client() -> tuple[MiniMaxClient, AsyncMock]:
    """Create a client whose _request method is replaced by an AsyncMock.

    Returns:
        Tuple of (MiniMaxClient, AsyncMock for _request).
    """
    client = _make_client()
    mock_request = AsyncMock()
    client._request = mock_request
    return client, mock_request


# ---------------------------------------------------------------------------
# C. find_customer_by_pib()
# ---------------------------------------------------------------------------


async def test_find_customer_by_pib_returns_first_row():
    """find_customer_by_pib() returns the first matching row."""
    client, mock_req = _patched_client()
    mock_req.return_value = {"Rows": [{"ID": 1, "Name": "Test DOO", "TaxNumber": "123456789"}]}

    result = await client.find_customer_by_pib("123456789")

    mock_req.assert_called_once_with(
        "GET", "customers", params={"filter": "TaxNumber eq '123456789'"}
    )
    assert result["ID"] == 1


async def test_find_customer_by_pib_returns_none_when_empty():
    """find_customer_by_pib() returns None when Rows is empty."""
    client, mock_req = _patched_client()
    mock_req.return_value = {"Rows": []}

    result = await client.find_customer_by_pib("999999999")

    assert result is None


async def test_find_customer_by_pib_handles_list_response():
    """find_customer_by_pib() handles a raw list response (non-dict)."""
    client, mock_req = _patched_client()
    mock_req.return_value = [{"ID": 5, "TaxNumber": "111111111"}]

    result = await client.find_customer_by_pib("111111111")

    assert result["ID"] == 5


async def test_find_customer_by_pib_returns_none_for_empty_list():
    """find_customer_by_pib() returns None when the response is an empty list."""
    client, mock_req = _patched_client()
    mock_req.return_value = []

    result = await client.find_customer_by_pib("000000000")

    assert result is None


# ---------------------------------------------------------------------------
# D. create_customer()
# ---------------------------------------------------------------------------


async def test_create_customer_posts_correct_payload():
    """create_customer() sends the correct JSON payload to the customers endpoint."""
    client, mock_req = _patched_client()
    mock_req.return_value = {"ID": 42, "Name": "Novo Preduzeće DOO"}

    result = await client.create_customer(
        name="Novo Preduzeće DOO",
        pib="123456789",
        address="Nemanjina 1",
        city="Beograd",
    )

    call_args = mock_req.call_args
    assert call_args[0] == ("POST", "customers")
    payload = call_args[1]["json"]
    assert payload["Name"] == "Novo Preduzeće DOO"
    assert payload["TaxNumber"] == "123456789"
    assert payload["Address"] == "Nemanjina 1"
    assert payload["City"] == "Beograd"
    assert payload["Country"] == {"ID": 3}
    assert payload["SubjectToVAT"] == "D"
    assert payload["Currency"] == {"ID": 2}
    assert result["ID"] == 42


async def test_create_customer_defaults_address_and_city():
    """create_customer() uses empty strings for address/city when omitted."""
    client, mock_req = _patched_client()
    mock_req.return_value = {"ID": 7}

    await client.create_customer(name="Min DOO", pib="100000001")

    _, kwargs = mock_req.call_args
    assert kwargs["json"]["Address"] == ""
    assert kwargs["json"]["City"] == ""


# ---------------------------------------------------------------------------
# E. find_or_create_customer()
# ---------------------------------------------------------------------------


async def test_find_or_create_returns_existing_customer():
    """find_or_create_customer() returns the existing customer when PIB is found."""
    client = _make_client()
    existing = {"ID": 99, "Name": "Staro Preduzeće", "TaxNumber": "123456789"}
    client.find_customer_by_pib = AsyncMock(return_value=existing)
    client.create_customer = AsyncMock()

    result = await client.find_or_create_customer(pib="123456789", name="Staro Preduzeće")

    assert result == existing
    client.create_customer.assert_not_called()


async def test_find_or_create_creates_when_not_found():
    """find_or_create_customer() calls create_customer when PIB is not found."""
    client = _make_client()
    created = {"ID": 50, "Name": "Novo Preduzeće"}
    client.find_customer_by_pib = AsyncMock(return_value=None)
    client.create_customer = AsyncMock(return_value=created)

    result = await client.find_or_create_customer(
        pib="987654321",
        name="Novo Preduzeće",
        address="Bulevar 5",
        city="Novi Sad",
    )

    client.create_customer.assert_called_once_with(
        "Novo Preduzeće", "987654321", "Bulevar 5", "Novi Sad", ""
    )
    assert result == created


# ---------------------------------------------------------------------------
# F. push_received_invoice()
# ---------------------------------------------------------------------------


async def test_push_received_invoice_posts_to_correct_path():
    """push_received_invoice() calls POST receivedinvoices with the given data."""
    client, mock_req = _patched_client()
    payload = {"DocumentReference": "INV-001", "Customer": {"ID": 1}}
    mock_req.return_value = {"ID": 500, "DocumentReference": "INV-001"}

    result = await client.push_received_invoice(payload)

    mock_req.assert_called_once_with("POST", "receivedinvoices", json=payload)
    assert result["ID"] == 500


async def test_push_received_invoice_propagates_error():
    """push_received_invoice() raises MiniMaxError when _request fails."""
    client, mock_req = _patched_client()
    mock_req.side_effect = MiniMaxError("API error", status_code=500)

    with pytest.raises(MiniMaxError) as exc_info:
        await client.push_received_invoice({"DocumentReference": "BAD"})

    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# G. attach_document()
# ---------------------------------------------------------------------------


async def test_attach_document_posts_multipart():
    """attach_document() posts a multipart file to the attachments endpoint."""
    token_resp = _make_httpx_response({"access_token": "tok", "expires_in": 3600})
    attach_resp = _make_httpx_response({"ID": 77, "FileName": "invoice.pdf"})
    attach_resp.content = b'{"ID": 77}'

    client = _make_client()
    inner_auth = AsyncMock()
    inner_auth.post = AsyncMock(return_value=token_resp)
    auth_ctx = MagicMock()
    auth_ctx.__aenter__ = AsyncMock(return_value=inner_auth)
    auth_ctx.__aexit__ = AsyncMock(return_value=False)

    inner_attach = AsyncMock()
    inner_attach.post = AsyncMock(return_value=attach_resp)
    attach_ctx = MagicMock()
    attach_ctx.__aenter__ = AsyncMock(return_value=inner_attach)
    attach_ctx.__aexit__ = AsyncMock(return_value=False)

    call_count = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return auth_ctx if call_count == 1 else attach_ctx

    with patch("httpx.AsyncClient", side_effect=_side_effect):
        result = await client.attach_document(
            invoice_id=123,
            pdf_bytes=b"%PDF-1.4 content",
            filename="invoice.pdf",
        )

    # Verify the URL includes the invoice ID
    _, kwargs = inner_attach.post.call_args
    assert "123" in inner_attach.post.call_args[0][0]
    assert result["ID"] == 77


async def test_attach_document_returns_empty_dict_when_no_content():
    """attach_document() returns {} when the response body is empty."""
    token_resp = _make_httpx_response({"access_token": "tok", "expires_in": 3600})
    empty_resp = _make_httpx_response({}, status_code=200)
    empty_resp.content = b""

    client = _make_client()
    inner_auth = AsyncMock()
    inner_auth.post = AsyncMock(return_value=token_resp)
    auth_ctx = MagicMock()
    auth_ctx.__aenter__ = AsyncMock(return_value=inner_auth)
    auth_ctx.__aexit__ = AsyncMock(return_value=False)

    inner_attach = AsyncMock()
    inner_attach.post = AsyncMock(return_value=empty_resp)
    attach_ctx = MagicMock()
    attach_ctx.__aenter__ = AsyncMock(return_value=inner_attach)
    attach_ctx.__aexit__ = AsyncMock(return_value=False)

    call_count = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return auth_ctx if call_count == 1 else attach_ctx

    with patch("httpx.AsyncClient", side_effect=_side_effect):
        result = await client.attach_document(1, b"bytes", "file.pdf")

    assert result == {}


async def test_attach_document_raises_on_error_status():
    """attach_document() raises MiniMaxError when the attachment endpoint returns 400+."""
    token_resp = _make_httpx_response({"access_token": "tok", "expires_in": 3600})
    error_resp = _make_httpx_response({}, status_code=413, text="Payload Too Large")

    client = _make_client()
    inner_auth = AsyncMock()
    inner_auth.post = AsyncMock(return_value=token_resp)
    auth_ctx = MagicMock()
    auth_ctx.__aenter__ = AsyncMock(return_value=inner_auth)
    auth_ctx.__aexit__ = AsyncMock(return_value=False)

    inner_attach = AsyncMock()
    inner_attach.post = AsyncMock(return_value=error_resp)
    attach_ctx = MagicMock()
    attach_ctx.__aenter__ = AsyncMock(return_value=inner_attach)
    attach_ctx.__aexit__ = AsyncMock(return_value=False)

    call_count = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return auth_ctx if call_count == 1 else attach_ctx

    with patch("httpx.AsyncClient", side_effect=_side_effect):
        with pytest.raises(MiniMaxError) as exc_info:
            await client.attach_document(1, b"big file", "big.pdf")

    assert exc_info.value.status_code == 413
    assert "Document attachment failed" in str(exc_info.value)


# ---------------------------------------------------------------------------
# H. get_currency()
# ---------------------------------------------------------------------------


async def test_get_currency_returns_first_match():
    """get_currency() returns the first currency row matching the code."""
    client, mock_req = _patched_client()
    mock_req.return_value = {"Rows": [{"ID": 3, "Code": "EUR"}]}

    result = await client.get_currency("EUR")

    mock_req.assert_called_once_with("GET", "currencies", params={"filter": "Code eq 'EUR'"})
    assert result["Code"] == "EUR"
    assert result["ID"] == 3


async def test_get_currency_returns_none_when_not_found():
    """get_currency() returns None when no matching currency exists."""
    client, mock_req = _patched_client()
    mock_req.return_value = {"Rows": []}

    result = await client.get_currency("XYZ")

    assert result is None


async def test_get_currency_handles_list_response():
    """get_currency() works when API returns a plain list instead of Rows dict."""
    client, mock_req = _patched_client()
    mock_req.return_value = [{"ID": 1, "Code": "RSD"}]

    result = await client.get_currency("RSD")

    assert result["Code"] == "RSD"


async def test_get_currency_returns_none_for_empty_list():
    """get_currency() returns None when API returns an empty list."""
    client, mock_req = _patched_client()
    mock_req.return_value = []

    result = await client.get_currency("EUR")

    assert result is None


# ---------------------------------------------------------------------------
# I. MiniMaxError — exception attributes
# ---------------------------------------------------------------------------


def test_minimax_error_stores_status_code():
    """MiniMaxError preserves status_code and response_body attributes."""
    err = MiniMaxError("Something went wrong", status_code=503, response_body="Service Unavailable")
    assert err.status_code == 503
    assert err.response_body == "Service Unavailable"
    assert str(err) == "Something went wrong"


def test_minimax_error_default_attributes():
    """MiniMaxError defaults status_code to None and response_body to empty string."""
    err = MiniMaxError("Minimal error")
    assert err.status_code is None
    assert err.response_body == ""


# ---------------------------------------------------------------------------
# J. _request() — 401 auto-retry
# ---------------------------------------------------------------------------


async def test_request_retries_once_on_401():
    """_request() clears the cached token and retries once when a 401 is received."""
    token_resp = _make_httpx_response({"access_token": "initial_tok", "expires_in": 3600})
    token_resp2 = _make_httpx_response({"access_token": "fresh_tok", "expires_in": 3600})
    unauthorized_resp = _make_httpx_response({}, status_code=401, text="Unauthorized")
    ok_resp = _make_httpx_response({"ID": 1})

    client = _make_client()
    responses = [token_resp, unauthorized_resp, token_resp2, ok_resp]
    call_idx = 0

    def _make_ctx(resp):
        inner = AsyncMock()
        inner.post = AsyncMock(return_value=resp)
        inner.request = AsyncMock(return_value=resp)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=inner)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx

    def _side_effect(*args, **kwargs):
        nonlocal call_idx
        ctx = _make_ctx(responses[call_idx])
        call_idx += 1
        return ctx

    with patch("httpx.AsyncClient", side_effect=_side_effect):
        result = await client._request("GET", "customers")

    assert result == {"ID": 1}
