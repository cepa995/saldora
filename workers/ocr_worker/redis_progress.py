"""Redis-based progress publishing for OCR tasks."""

import json
import logging
import os

import redis

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    """Get or create a sync Redis client for progress updates."""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(redis_url)
    return _redis_client


def publish_progress(
    invoice_id: str,
    stage: str,
    progress: int,
    error: str | None = None,
) -> None:
    """Publish processing progress to Redis.

    Writes a JSON payload to ``invoice:{invoice_id}:progress`` with a
    5-minute TTL.  The API status endpoint reads this key to serve
    real-time progress to the frontend.

    Args:
        invoice_id: UUID of the invoice being processed.
        stage: Current processing stage name.
        progress: Percentage complete (0-100).
        error: Optional error message when stage is 'failed'.
    """
    try:
        r = _get_redis()
        key = f"invoice:{invoice_id}:progress"
        value = json.dumps(
            {
                "stage": stage,
                "progress": progress,
                "error": error,
            }
        )
        r.set(key, value, ex=300)  # 5-minute TTL
    except Exception as e:
        logger.warning("Failed to publish progress for %s: %s", invoice_id, e)
