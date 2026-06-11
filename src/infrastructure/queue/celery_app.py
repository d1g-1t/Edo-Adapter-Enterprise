from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from src.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "edo_adapter",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "src.infrastructure.queue.tasks.send_document_task.*": {"queue": "edo.send"},
        "edo.poll_incoming": {"queue": "edo.sync"},
        "edo.sync_statuses": {"queue": "edo.sync"},
        "edo.process_webhook": {"queue": "edo.webhooks"},
        "edo.process_dlq": {"queue": "edo.dlq"},
        "edo.provider_health": {"queue": "edo.health"},
        "edo.cleanup_idempotency": {"queue": "edo.health"},
    },
    beat_schedule={
        "sync-statuses-every-2min": {
            "task": "edo.sync_statuses",
            "schedule": 120.0,
        },
        "poll-incoming-every-5min": {
            "task": "edo.poll_incoming",
            "schedule": 300.0,
        },
        "provider-health-every-1min": {
            "task": "edo.provider_health",
            "schedule": 60.0,
        },
        "cleanup-idempotency-daily": {
            "task": "edo.cleanup_idempotency",
            "schedule": crontab(hour=2, minute=0),
        },
        "process-dlq-every-10min": {
            "task": "edo.process_dlq",
            "schedule": 600.0,
        },
    },
)

celery_app.autodiscover_tasks(
    [
        "src.infrastructure.queue.tasks.send_document_task",
        "src.infrastructure.queue.tasks.poll_incoming_task",
        "src.infrastructure.queue.tasks.sync_statuses_task",
        "src.infrastructure.queue.tasks.process_webhook_task",
        "src.infrastructure.queue.tasks.process_dlq_task",
        "src.infrastructure.queue.tasks.provider_health_task",
        "src.infrastructure.queue.tasks.cleanup_idempotency_task",
    ]
)
