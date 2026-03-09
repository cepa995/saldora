"""S3-compatible storage service for document management."""

import logging
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_s3_client = None
_s3_public_client = None

_MIME_TO_EXT: dict[str, str] = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/tiff": ".tiff",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
}


def get_s3_client():
    """Get or create the S3 client (lazy singleton).

    Uses storage settings from app config (endpoint, access key, secret key,
    region). The client is created once and reused for all subsequent calls.

    Returns:
        boto3 S3 client configured for the storage backend.
    """
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name=settings.storage_region,
        )
    return _s3_client


def ensure_bucket_exists() -> None:
    """Create the storage bucket if it doesn't already exist.

    Called once during application startup (lifespan) to guarantee the
    bucket is available before any upload operations.
    """
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.storage_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.storage_bucket)
        logger.info("Created bucket: %s", settings.storage_bucket)


def document_exists(key: str) -> bool:
    """Check whether an object exists in S3.

    Args:
        key: S3 object key to check.

    Returns:
        True if the object exists, False otherwise.
    """
    client = get_s3_client()
    try:
        client.head_object(Bucket=settings.storage_bucket, Key=key)
        return True
    except ClientError:
        return False


def upload_document(
    organization_id: UUID,
    invoice_id: UUID,
    content: bytes,
    content_type: str,
    filename: str,
) -> str:
    """Upload a document to S3 and return the object key.

    Files are stored under
    ``organizations/{organization_id}/invoices/{invoice_id}/original{ext}``
    with the original filename preserved in S3 object metadata.

    Args:
        organization_id: UUID of the owning organization (tenant prefix).
        invoice_id: UUID of the invoice this document belongs to.
        content: Raw file bytes.
        content_type: MIME type (e.g. ``application/pdf``, ``image/png``).
        filename: Original filename from the upload.

    Returns:
        The S3 object key where the document was stored.
    """
    ext = _get_extension(content_type)
    key = f"organizations/{organization_id}/invoices/{invoice_id}/original{ext}"

    client = get_s3_client()
    client.put_object(
        Bucket=settings.storage_bucket,
        Key=key,
        Body=content,
        ContentType=content_type,
        Metadata={"original-filename": filename},
    )

    logger.info("Uploaded %d bytes to %s", len(content), key)
    return key


def _get_public_s3_client():
    """Get or create an S3 client for browser-facing presigned URLs.

    When ``STORAGE_PUBLIC_ENDPOINT`` is configured, this returns a client
    pointing at the public URL so the signature matches the host the browser
    uses.  Falls back to the internal client when no public endpoint is set.

    Returns:
        boto3 S3 client configured with the public endpoint.
    """
    if not settings.storage_public_endpoint:
        return get_s3_client()
    global _s3_public_client
    if _s3_public_client is None:
        _s3_public_client = boto3.client(
            "s3",
            endpoint_url=settings.storage_public_endpoint,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name=settings.storage_region,
        )
    return _s3_public_client


def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for downloading a document.

    Uses ``STORAGE_PUBLIC_ENDPOINT`` (when set) so the signature is valid
    when the browser accesses the URL from outside Docker.

    Args:
        key: S3 object key returned by :func:`upload_document`.
        expires_in: URL validity in seconds (default 3600 = 1 hour).

    Returns:
        A temporary URL that grants unauthenticated download access.
    """
    client = _get_public_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.storage_bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def delete_document(key: str) -> None:
    """Delete a document from S3.

    Args:
        key: S3 object key to delete
            (e.g. ``organizations/{org_id}/invoices/{id}/original.pdf``).
    """
    client = get_s3_client()
    client.delete_object(Bucket=settings.storage_bucket, Key=key)
    logger.info("Deleted %s", key)


def upload_logo(
    organization_id: UUID,
    content: bytes,
    content_type: str,
) -> str:
    """Upload an organization logo to S3.

    Args:
        organization_id: UUID of the organization.
        content: Raw image bytes.
        content_type: MIME type (image/png, image/jpeg).

    Returns:
        The S3 object key where the logo was stored.
    """
    ext = _get_extension(content_type)
    key = f"organizations/{organization_id}/logo{ext}"

    client = get_s3_client()
    client.put_object(
        Bucket=settings.storage_bucket,
        Key=key,
        Body=content,
        ContentType=content_type,
    )

    logger.info("Uploaded logo for org %s (%d bytes)", organization_id, len(content))
    return key


def _get_extension(content_type: str) -> str:
    """Map MIME type to file extension, falling back to ``.bin``."""
    return _MIME_TO_EXT.get(content_type, ".bin")
