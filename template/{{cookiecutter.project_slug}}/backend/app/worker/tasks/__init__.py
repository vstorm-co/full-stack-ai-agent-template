{%- if cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq or cookiecutter.use_prefect %}
"""Background tasks."""

{%- if cookiecutter.enable_credits_system and cookiecutter.enable_usage_anomaly_detection %}
from app.worker.tasks.anomaly_tasks import detect_usage_spikes_task
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
from app.worker.tasks.cleanup_tasks import (
    cleanup_usage_events_task,
    refresh_usage_matview_task,
)
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}
from app.worker.tasks.email_tasks import send_trial_reminders_task
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}
from app.worker.tasks.email_tasks import send_low_credits_alerts_task
{%- endif %}
{%- if cookiecutter.enable_rag %}
{%- if cookiecutter.use_prefect %}
from app.worker.tasks.rag_tasks import (
    check_scheduled_syncs_flow,
    ingest_document_flow,
    sync_collection_flow,
    sync_single_source_flow,
)
{%- else %}
from app.worker.tasks.rag_tasks import (
    check_scheduled_syncs,
    ingest_document_task,
{%- if cookiecutter.use_celery %}
    sync_collection_task,
{%- endif %}
    sync_single_source_task,
)
{%- endif %}
{%- endif %}

__all__ = [
{%- if cookiecutter.enable_rag %}
{%- if cookiecutter.use_prefect %}
    "check_scheduled_syncs_flow",
    "ingest_document_flow",
    "sync_collection_flow",
    "sync_single_source_flow",
{%- else %}
    "check_scheduled_syncs",
    "ingest_document_task",
{%- if cookiecutter.use_celery %}
    "sync_collection_task",
{%- endif %}
    "sync_single_source_task",
{%- endif %}
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
    "cleanup_usage_events_task",
{%- if cookiecutter.enable_usage_anomaly_detection %}
    "detect_usage_spikes_task",
{%- endif %}
    "refresh_usage_matview_task",
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}
    "send_trial_reminders_task",
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}
    "send_low_credits_alerts_task",
{%- endif %}
]
{%- endif %}
