"""Unit tests for the storage service utilities."""

import pytest

from app.services.storage import _get_extension


@pytest.mark.parametrize(
    ("mime_type", "expected"),
    [
        ("application/pdf", ".pdf"),
        ("image/png", ".png"),
        ("image/jpeg", ".jpg"),
        ("image/tiff", ".tiff"),
        ("image/bmp", ".bmp"),
        ("image/webp", ".webp"),
    ],
)
def test_get_extension_known_types(mime_type: str, expected: str):
    """Known MIME types map to the correct file extension."""
    assert _get_extension(mime_type) == expected


def test_get_extension_unknown_falls_back_to_bin():
    """Unknown MIME types fall back to .bin."""
    assert _get_extension("text/plain") == ".bin"
    assert _get_extension("application/octet-stream") == ".bin"
    assert _get_extension("") == ".bin"
