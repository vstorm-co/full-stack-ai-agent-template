{%- if cookiecutter.use_arq %}
"""ARQ (Async Redis Queue) application configuration."""

import asyncio
import logging
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings

logger = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    """Initialize resources on worker startup."""
    logger.info("ARQ worker starting up...")
    # Add any startup initialization here
    # e.g., database connections, external clients


async def shutdown(ctx: dict[str, Any]) -> None:
    """Cleanup resources on worker shutdown."""
    logger.info("ARQ worker shutting down...")
    # Add any cleanup here


# === Example Tasks ===
# Tasks are defined as regular async functions

{%- if cookiecutter.enable_rag and cookiecutter.use_milvus %}
from app.worker.tasks.rag_ingestion import reindex_collection_arq
{%- endif %}


async def example_task(ctx: dict[str, Any], message: str) -> dict[str, Any]:
    """
    Example task that processes a message.

    Args:
        ctx: ARQ context dictionary (contains redis connection, job info, etc.)
        message: Message to process

    Returns:
        Result dictionary with processed message
    """
    logger.info(f"Processing message: {message}")

    # Simulate async work
    await asyncio.sleep(1)

    result = {
        "status": "completed",
        "message": f"Processed: {message}",
        "job_id": ctx.get("job_id"),
    }
    logger.info(f"Task completed: {result}")
    return result


async def long_running_task(ctx: dict[str, Any], duration: int = 10) -> dict[str, Any]:
    """
    Example long-running async task.

    Args:
        ctx: ARQ context dictionary
        duration: Duration in seconds

    Returns:
        Result dictionary
    """
    logger.info(f"Starting long-running task for {duration} seconds")

    for i in range(duration):
        await asyncio.sleep(1)
        logger.info(f"Progress: {i + 1}/{duration}")

    return {
        "status": "completed",
        "duration": duration,
        "job_id": ctx.get("job_id"),
    }


async def send_email_task(
    ctx: dict[str, Any], to: str, subject: str, body: str
) -> dict[str, Any]:
    """
    Example email sending task.

    Replace with actual email sending logic (e.g., using aiosmtplib, sendgrid, etc.)

    Args:
        ctx: ARQ context dictionary
        to: Recipient email
        subject: Email subject
        body: Email body

    Returns:
        Result dictionary
    """
    logger.info(f"Sending email to {to}: {subject}")

    # TODO: Implement actual email sending
    # Example with aiosmtplib:
    # import aiosmtplib
    # ...

    # Simulate sending
    await asyncio.sleep(0.5)

    return {
        "status": "sent",
        "to": to,
        "subject": subject,
    }


# === Scheduled Task (runs periodically) ===


async def scheduled_example(ctx: dict[str, Any]) -> dict[str, Any]:
    """Example scheduled task that runs every minute."""
    logger.info("Running scheduled example task")
    return await example_task(ctx, "scheduled")


# === Worker Settings ===
# This class is used by the ARQ CLI: arq app.worker.arq_app.WorkerSettings


class WorkerSettings:
    """ARQ Worker configuration."""

    # Redis connection settings
    redis_settings = RedisSettings(
        host=settings.ARQ_REDIS_HOST,
        port=settings.ARQ_REDIS_PORT,
        password=settings.ARQ_REDIS_PASSWORD or None,
        database=settings.ARQ_REDIS_DB,
    )

    # Register task functions
    functions = [
        example_task,
        long_running_task,
        send_email_task,
        {%- if cookiecutter.enable_rag and cookiecutter.use_milvus %}
        reindex_collection_arq,
        {%- endif %}
    ]

    # Scheduled/cron jobs
    cron_jobs = [
        cron(scheduled_example, minute={0, 15, 30, 45}),  # Every 15 minutes
        # cron(scheduled_example, minute=0, hour=0),  # Daily at midnight
        {%- if cookiecutter.enable_rag and cookiecutter.use_milvus %}
        cron(reindex_collection_arq, hour=2, minute=0),  # Daily at 2 AM
        {%- endif %}
    ]

    # Worker lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown

    # Worker settings
    max_jobs = 10  # Maximum concurrent jobs
    job_timeout = 300  # Job timeout in seconds (5 minutes)
    keep_result = 3600  # Keep results for 1 hour
    poll_delay = 0.5  # Polling delay in seconds
    queue_read_limit = 100  # Number of jobs to read at once
{%- else %}
# ARQ not enabled for this project
{%- endif %}
