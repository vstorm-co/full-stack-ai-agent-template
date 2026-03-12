{%- if cookiecutter.use_taskiq and cookiecutter.enable_rag and cookiecutter.use_milvus %}
"""Taskiq scheduled tasks (cron-like)."""

from app.worker.taskiq_app import broker
from app.worker.tasks.taskiq_examples import example_task


# Define scheduled tasks using labels
# These are picked up by the scheduler

@broker.task(schedule=[{"cron": "* * * * *"}])  # Every minute
async def scheduled_example() -> dict:
    """Example scheduled task that runs every minute."""
    result = await example_task.kiq("scheduled")
    return {"scheduled": True, "task_id": str(result.task_id)}


{%- if cookiecutter.enable_rag and cookiecutter.use_milvus %}
# RAG scheduled tasks
from app.rag.config import RAGSettings


@broker.task  # Schedule defined via scheduler sources in taskiq_app.py
async def scheduled_rag_reindex(collection_name: str | None = None) -> dict:
    """Daily RAG collection reindex at 2 AM."""
    from app.worker.tasks.rag_ingestion import reindex_collection_taskiq

    settings = RAGSettings()
    if collection_name is None:
        collection_name = settings.collection_name

    result = await reindex_collection_taskiq.kiq(collection_name)
    return {"scheduled": True, "task_id": str(result.task_id), "collection": collection_name}


# Define schedules via SCHEDULES list (picked up by TaskiqScheduler with sources=)
SCHEDULES = [
    {
        "task": "app.worker.tasks.schedules:scheduled_rag_reindex",
        "cron": "0 2 * * *",  # Daily at 2 AM
    },
]
{%- endif %}
{%- else %}
# Taskiq not enabled for this project
{%- endif %}
