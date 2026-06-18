"""Celery application configuration."""

from celery import Celery

from app.core.config import settings
from app.core.logfire_setup import instrument_celery

celery_app = Celery(
    "ai_agent_test",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

celery_app.autodiscover_tasks(["app.worker.tasks"])

celery_app.conf.beat_schedule = {
    "rag-sync-check": {
        "task": "app.worker.tasks.rag_tasks.check_scheduled_syncs",
        "schedule": 60.0,
    },
}


instrument_celery()
