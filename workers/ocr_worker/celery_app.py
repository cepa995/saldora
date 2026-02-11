"""Celery application configuration for OCR workers."""

import os

from celery import Celery

# Redis configuration
REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

app = Celery(
    "ocr_worker",
    broker=REDIS_URL,
    backend=RESULT_BACKEND,
    include=["ocr_worker.tasks"],
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Belgrade",
    enable_utc=True,
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time for GPU workers
    worker_concurrency=1,  # Single task per worker (GPU bound)
    # Task time limits
    task_soft_time_limit=120,  # 2 minutes soft limit
    task_time_limit=180,  # 3 minutes hard limit
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    # Task routing
    task_routes={
        "ocr_worker.tasks.process_invoice": {"queue": "ocr"},
        "ocr_worker.tasks.process_batch": {"queue": "ocr"},
    },
    # Retry settings
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,  # Requeue if worker crashes
)

# Optional: Configure task priorities
app.conf.broker_transport_options = {
    "priority_steps": list(range(10)),
    "queue_order_strategy": "priority",
}

if __name__ == "__main__":
    app.start()
