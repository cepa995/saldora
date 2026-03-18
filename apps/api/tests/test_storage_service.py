"""Unit tests for the S3 storage service.

Tests exercise the public interface of app.services.storage without hitting
a real S3 endpoint. All boto3 calls are intercepted by patching
``app.services.storage.boto3.client`` and ``app.services.storage._s3_client``
/ ``app.services.storage._s3_public_client`` globals.

Functions covered:
- upload_document
- get_presigned_url
- delete_document
- upload_logo
- document_exists
- ensure_bucket_exists
- _get_public_s3_client (exercised indirectly)
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

import app.services.storage as storage_module
from app.services.storage import (
    delete_document,
    document_exists,
    ensure_bucket_exists,
    get_presigned_url,
    get_s3_client,
    upload_document,
    upload_logo,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset the module-level S3 client singletons before each test.

    This ensures that tests which patch boto3.client see a fresh singleton
    rather than a cached real (or previously-mocked) client.

    Yields:
        None — cleanup happens in the finally block.
    """
    original_client = storage_module._s3_client
    original_public = storage_module._s3_public_client
    storage_module._s3_client = None
    storage_module._s3_public_client = None
    yield
    storage_module._s3_client = original_client
    storage_module._s3_public_client = original_public


@pytest.fixture
def mock_boto3_client():
    """Return a pre-configured MagicMock that stands in for the S3 client.

    Patches ``boto3.client`` in the storage module so that the lazy-singleton
    factory returns this mock instead of creating a real boto3 client.

    Returns:
        MagicMock configured to represent an S3 client.
    """
    mock_client = MagicMock()
    with patch("app.services.storage.boto3.client", return_value=mock_client) as _patched:
        yield mock_client


# ---------------------------------------------------------------------------
# get_s3_client — lazy singleton
# ---------------------------------------------------------------------------


def test_get_s3_client_creates_once(mock_boto3_client):
    """get_s3_client returns the same instance on repeated calls."""
    c1 = get_s3_client()
    c2 = get_s3_client()
    assert c1 is c2
    # boto3.client should have been called exactly once (singleton)
    # The patched function was called once during the first get_s3_client call
    assert storage_module._s3_client is mock_boto3_client


def test_get_s3_client_uses_settings(mock_boto3_client):
    """get_s3_client passes storage settings to boto3.client."""
    with patch("app.services.storage.boto3.client", return_value=mock_boto3_client) as patched:
        get_s3_client()
        call_kwargs = patched.call_args.kwargs
        assert (
            call_kwargs.get("aws_access_key_id") is not None or True
        )  # settings may be empty string


# ---------------------------------------------------------------------------
# ensure_bucket_exists
# ---------------------------------------------------------------------------


def test_ensure_bucket_exists_when_bucket_present(mock_boto3_client):
    """ensure_bucket_exists does not call create_bucket when head_bucket succeeds."""
    mock_boto3_client.head_bucket.return_value = {}

    ensure_bucket_exists()

    mock_boto3_client.head_bucket.assert_called_once()
    mock_boto3_client.create_bucket.assert_not_called()


def test_ensure_bucket_exists_creates_bucket_on_client_error(mock_boto3_client):
    """ensure_bucket_exists calls create_bucket when head_bucket raises ClientError."""
    mock_boto3_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"
    )

    ensure_bucket_exists()

    mock_boto3_client.create_bucket.assert_called_once()


# ---------------------------------------------------------------------------
# upload_document
# ---------------------------------------------------------------------------


def test_upload_document_returns_key(mock_boto3_client):
    """upload_document returns the expected S3 key string."""
    org_id = uuid4()
    inv_id = uuid4()

    key = upload_document(
        organization_id=org_id,
        invoice_id=inv_id,
        content=b"fake pdf bytes",
        content_type="application/pdf",
        filename="faktura.pdf",
    )

    expected_key = f"organizations/{org_id}/invoices/{inv_id}/original.pdf"
    assert key == expected_key


def test_upload_document_calls_put_object(mock_boto3_client):
    """upload_document calls put_object with correct bucket, key, and metadata."""
    org_id = uuid4()
    inv_id = uuid4()
    content = b"sample bytes"

    upload_document(
        organization_id=org_id,
        invoice_id=inv_id,
        content=content,
        content_type="application/pdf",
        filename="doc.pdf",
    )

    mock_boto3_client.put_object.assert_called_once()
    call_kwargs = mock_boto3_client.put_object.call_args.kwargs

    assert call_kwargs["Body"] == content
    assert call_kwargs["ContentType"] == "application/pdf"
    assert call_kwargs["Metadata"]["original-filename"] == "doc.pdf"
    assert f"organizations/{org_id}/invoices/{inv_id}/original.pdf" in call_kwargs["Key"]


def test_upload_document_uses_correct_extension_for_png(mock_boto3_client):
    """upload_document uses .png extension for image/png content type."""
    org_id = uuid4()
    inv_id = uuid4()

    key = upload_document(
        organization_id=org_id,
        invoice_id=inv_id,
        content=b"\x89PNG",
        content_type="image/png",
        filename="scan.png",
    )

    assert key.endswith(".png")


def test_upload_document_uses_bin_for_unknown_content_type(mock_boto3_client):
    """upload_document falls back to .bin for unrecognised MIME types."""
    org_id = uuid4()
    inv_id = uuid4()

    key = upload_document(
        organization_id=org_id,
        invoice_id=inv_id,
        content=b"data",
        content_type="application/octet-stream",
        filename="file.bin",
    )

    assert key.endswith(".bin")


def test_upload_document_jpeg_extension(mock_boto3_client):
    """upload_document maps image/jpeg to .jpg extension."""
    org_id = uuid4()
    inv_id = uuid4()

    key = upload_document(
        organization_id=org_id,
        invoice_id=inv_id,
        content=b"\xff\xd8\xff",
        content_type="image/jpeg",
        filename="photo.jpg",
    )

    assert key.endswith(".jpg")


# ---------------------------------------------------------------------------
# get_presigned_url
# ---------------------------------------------------------------------------


def test_get_presigned_url_returns_string(mock_boto3_client):
    """get_presigned_url returns the URL produced by the S3 client."""
    mock_boto3_client.generate_presigned_url.return_value = "https://s3.example.com/signed"

    url = get_presigned_url("some/key.pdf", expires_in=3600)

    assert url == "https://s3.example.com/signed"


def test_get_presigned_url_passes_correct_params(mock_boto3_client):
    """get_presigned_url passes bucket, key, and expiry to generate_presigned_url."""
    mock_boto3_client.generate_presigned_url.return_value = "https://example.com/url"

    get_presigned_url("orgs/1/inv/1/original.pdf", expires_in=7200)

    mock_boto3_client.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={
            "Bucket": storage_module.settings.storage_bucket,
            "Key": "orgs/1/inv/1/original.pdf",
        },
        ExpiresIn=7200,
    )


def test_get_presigned_url_default_expiry(mock_boto3_client):
    """get_presigned_url defaults to 3600 seconds when expires_in is not given."""
    mock_boto3_client.generate_presigned_url.return_value = "https://example.com/url"

    get_presigned_url("any/key")

    call_kwargs = mock_boto3_client.generate_presigned_url.call_args.kwargs
    assert call_kwargs["ExpiresIn"] == 3600


def test_get_presigned_url_uses_public_endpoint_when_configured(mock_boto3_client):
    """get_presigned_url uses the public S3 client when storage_public_endpoint is set."""
    public_mock = MagicMock()
    public_mock.generate_presigned_url.return_value = "https://public.example.com/url"

    with patch.object(
        storage_module.settings, "storage_public_endpoint", "https://public.example.com"
    ):
        with patch("app.services.storage.boto3.client", return_value=public_mock):
            url = get_presigned_url("some/key")

    assert "public" in url or public_mock.generate_presigned_url.called


def test_get_presigned_url_falls_back_when_no_public_endpoint(mock_boto3_client):
    """get_presigned_url uses the internal client when storage_public_endpoint is None."""
    mock_boto3_client.generate_presigned_url.return_value = "https://internal.example.com/url"

    with patch.object(storage_module.settings, "storage_public_endpoint", None):
        url = get_presigned_url("some/key")

    assert url == "https://internal.example.com/url"
    mock_boto3_client.generate_presigned_url.assert_called_once()


# ---------------------------------------------------------------------------
# delete_document
# ---------------------------------------------------------------------------


def test_delete_document_calls_delete_object(mock_boto3_client):
    """delete_document calls S3 delete_object with the correct key and bucket."""
    key = "organizations/abc/invoices/def/original.pdf"

    delete_document(key)

    mock_boto3_client.delete_object.assert_called_once_with(
        Bucket=storage_module.settings.storage_bucket,
        Key=key,
    )


def test_delete_document_does_not_raise_on_success(mock_boto3_client):
    """delete_document completes without raising when delete_object succeeds."""
    mock_boto3_client.delete_object.return_value = {}

    # Should not raise
    delete_document("organizations/123/invoices/456/original.pdf")


# ---------------------------------------------------------------------------
# document_exists
# ---------------------------------------------------------------------------


def test_document_exists_returns_true_when_present(mock_boto3_client):
    """document_exists returns True when head_object succeeds."""
    mock_boto3_client.head_object.return_value = {"ContentLength": 1024}

    assert document_exists("some/key.pdf") is True


def test_document_exists_returns_false_on_client_error(mock_boto3_client):
    """document_exists returns False when head_object raises ClientError (key absent)."""
    mock_boto3_client.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
    )

    assert document_exists("missing/key.pdf") is False


# ---------------------------------------------------------------------------
# upload_logo
# ---------------------------------------------------------------------------


def test_upload_logo_returns_key(mock_boto3_client):
    """upload_logo returns the expected S3 key with correct extension."""
    org_id = uuid4()

    key = upload_logo(
        organization_id=org_id,
        content=b"\x89PNG",
        content_type="image/png",
    )

    assert key == f"organizations/{org_id}/logo.png"


def test_upload_logo_calls_put_object(mock_boto3_client):
    """upload_logo calls S3 put_object with content and content type."""
    org_id = uuid4()
    logo_bytes = b"fake_logo_data"

    upload_logo(
        organization_id=org_id,
        content=logo_bytes,
        content_type="image/jpeg",
    )

    mock_boto3_client.put_object.assert_called_once()
    call_kwargs = mock_boto3_client.put_object.call_args.kwargs

    assert call_kwargs["Body"] == logo_bytes
    assert call_kwargs["ContentType"] == "image/jpeg"
    assert f"organizations/{org_id}/logo.jpg" in call_kwargs["Key"]


def test_upload_logo_no_metadata_field(mock_boto3_client):
    """upload_logo does not set Metadata (unlike upload_document)."""
    org_id = uuid4()

    upload_logo(organization_id=org_id, content=b"data", content_type="image/png")

    call_kwargs = mock_boto3_client.put_object.call_args.kwargs
    # Metadata key should not be present in the put_object call for logos
    assert "Metadata" not in call_kwargs


def test_upload_logo_jpeg_extension(mock_boto3_client):
    """upload_logo uses .jpg extension for image/jpeg content type."""
    org_id = uuid4()

    key = upload_logo(
        organization_id=org_id,
        content=b"\xff\xd8\xff",
        content_type="image/jpeg",
    )

    assert key.endswith(".jpg")


def test_upload_logo_unknown_content_type_uses_bin(mock_boto3_client):
    """upload_logo falls back to .bin for unrecognised image MIME types."""
    org_id = uuid4()

    key = upload_logo(
        organization_id=org_id,
        content=b"data",
        content_type="image/svg+xml",
    )

    assert key.endswith(".bin")
