{%- if cookiecutter.use_celery %}
"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings
{%- if cookiecutter.enable_logfire and cookiecutter.logfire_celery %}
from app.core.logfire_setup import instrument_celery
{%- endif %}

# Create Celery app
celery_app = Celery(
    "{{ cookiecutter.project_slug }}",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result settings
    result_expires=3600,  # 1 hour
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

# Autodiscover tasks from app.worker.tasks module
celery_app.autodiscover_tasks(["app.worker.tasks"])


# === Beat Schedule ===
# Add periodic tasks here
celery_app.conf.beat_schedule = {
    "example-every-minute": {
        "task": "app.worker.tasks.examples.example_task",
        "schedule": 60.0,  # Every 60 seconds
        "args": ("periodic",),
    },
    # Example with crontab (runs at 00:00 every day)
    # "daily-cleanup": {
    #     "task": "app.worker.tasks.examples.cleanup_task",
    #     "schedule": crontab(hour=0, minute=0),
    # },
    {%- if cookiecutter.enable_rag and cookiecutter.use_milvus %}
    # RAG scheduled tasks
    "rag-reindex-daily": {
        "task": "app.worker.tasks.rag_ingestion.reindex_collection",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
        # collection_name defaults to RAGSettings.collection_name
    },
    {%- endif %}
}

{%- if cookiecutter.enable_logfire and cookiecutter.logfire_celery %}


# Instrument Celery with Logfire
instrument_celery()
{%- endif %}
{%- else %}
# Celery not enabled for this project
{%- endif %}
