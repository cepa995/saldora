"""Tests for Redis progress publishing."""

import json
from unittest.mock import MagicMock, patch

from ocr_worker.redis_progress import publish_progress


@patch("ocr_worker.redis_progress._get_redis")
def test_publish_progress_writes_to_redis(mock_get_redis):
    """publish_progress writes correct JSON to Redis with TTL."""
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis

    publish_progress("invoice-123", "ocr_running", 40)

    mock_redis.set.assert_called_once()
    key, value = mock_redis.set.call_args[0]
    assert key == "invoice:invoice-123:progress"
    data = json.loads(value)
    assert data["stage"] == "ocr_running"
    assert data["progress"] == 40
    assert data["error"] is None
    assert mock_redis.set.call_args[1]["ex"] == 300


@patch("ocr_worker.redis_progress._get_redis")
def test_publish_progress_includes_error(mock_get_redis):
    """publish_progress includes error message when provided."""
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis

    publish_progress("invoice-123", "failed", 0, error="Model crashed")

    key, value = mock_redis.set.call_args[0]
    data = json.loads(value)
    assert data["stage"] == "failed"
    assert data["progress"] == 0
    assert data["error"] == "Model crashed"


@patch("ocr_worker.redis_progress._get_redis")
def test_publish_progress_does_not_raise_on_redis_failure(mock_get_redis):
    """publish_progress fails silently if Redis is unavailable."""
    mock_redis = MagicMock()
    mock_redis.set.side_effect = ConnectionError("Redis refused")
    mock_get_redis.return_value = mock_redis

    # Should not raise
    publish_progress("invoice-123", "processing", 50)
