"""Celery application configuration for OCR workers."""

import os

from celery import Celery
from celery.schedules import crontab

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
    worker_prefetch_multiplier=1,  # One task at a time per worker process
    worker_concurrency=4,  # 4 concurrent tasks (vLLM batching)
    # Task time limits (5/6 min to handle Cloud Run cold starts)
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=360,  # 6 minutes hard limit
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
    # Beat schedule for periodic tasks
    beat_schedule={
        "fetch-nbs-exchange-rates": {
            "task": "ocr_worker.tasks.fetch_nbs_exchange_rates",
            "schedule": crontab(
                hour=8, minute=30, day_of_week="1-5"
            ),  # Business days at 08:30
        },
        "aggregate-daily-usage": {
            "task": "ocr_worker.tasks.aggregate_daily_usage",
            "schedule": crontab(hour=2, minute=0),  # Daily at 02:00
        },
        "monthly-archive-exports": {
            "task": "ocr_worker.tasks.run_monthly_archive_exports",
            "schedule": crontab(
                hour=6, minute=0, day_of_month=1
            ),  # 1st of every month at 06:00
        },
        "enforce-data-retention": {
            "task": "ocr_worker.tasks.enforce_data_retention",
            "schedule": crontab(hour=3, minute=0),  # Daily at 03:00
        },
    },
)

# Optional: Configure task priorities
app.conf.broker_transport_options = {
    "priority_steps": list(range(10)),
    "queue_order_strategy": "priority",
}

if __name__ == "__main__":
    app.start()
