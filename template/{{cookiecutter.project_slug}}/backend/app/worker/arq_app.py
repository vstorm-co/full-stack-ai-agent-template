{%- if cookiecutter.use_arq %}
"""ARQ (Async Redis Queue) application configuration."""

import asyncio
import logging
from typing import Any

from arq import create_pool, cron
from arq.connections import ArqRedis, RedisSettings

from app.core.config import settings
{%- if cookiecutter.enable_rag %}
from app.worker.tasks.rag_tasks import check_scheduled_syncs, sync_single_source_task
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}
from app.worker.tasks.email_tasks import send_trial_reminders_task
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}
from app.worker.tasks.email_tasks import send_low_credits_alerts_task
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
from app.worker.tasks.cleanup_tasks import cleanup_usage_events_task
{%- endif %}

logger = logging.getLogger(__name__)

# Single source of truth for ARQ Redis connection settings - shared by the worker
# (WorkerSettings.redis_settings below) and the FastAPI-side enqueueing pool
# (get_arq_pool below) so the two can never drift apart.
ARQ_REDIS_SETTINGS = RedisSettings(
    host=settings.ARQ_REDIS_HOST,
    port=settings.ARQ_REDIS_PORT,
    password=settings.ARQ_REDIS_PASSWORD or None,
    database=settings.ARQ_REDIS_DB,
)

_arq_pool: ArqRedis | None = None
_arq_pool_lock = asyncio.Lock()


async def get_arq_pool() -> ArqRedis:
    """Return the shared ARQ Redis pool, creating it on first use.

    The FastAPI process is long-lived, so a single pool is created lazily and
    reused across requests/enqueues rather than opened per call. Guarded with
    a lock + double-check so concurrent first-callers don't each create one.
    """
    global _arq_pool

    if _arq_pool is not None:
        return _arq_pool

    async with _arq_pool_lock:
        if _arq_pool is None:
            _arq_pool = await create_pool(ARQ_REDIS_SETTINGS)

    return _arq_pool


async def close_arq_pool() -> None:
    """Close the shared ARQ Redis pool, if one was created."""
    global _arq_pool

    if _arq_pool is not None:
        await _arq_pool.close()
        _arq_pool = None


async def startup(ctx: dict[str, Any]) -> None:
    """Initialize resources on worker startup."""
    logger.info("ARQ worker starting up...")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Cleanup resources on worker shutdown."""
    logger.info("ARQ worker shutting down...")


class WorkerSettings:
    """ARQ Worker configuration. Used by the ARQ CLI: arq app.worker.arq_app.WorkerSettings."""

    redis_settings = ARQ_REDIS_SETTINGS

    functions = [
{%- if cookiecutter.enable_rag %}
        sync_single_source_task,
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}
        send_trial_reminders_task,
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}
        send_low_credits_alerts_task,
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
        cleanup_usage_events_task,
{%- endif %}
    ]

    cron_jobs = [
{%- if cookiecutter.enable_rag %}
        cron(check_scheduled_syncs),
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}
        cron(send_trial_reminders_task, hour=9, minute=0),
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}
        cron(send_low_credits_alerts_task, minute=0),
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
        cron(cleanup_usage_events_task, weekday=0, hour=3, minute=0),
{%- endif %}
    ]

    on_startup = startup
    on_shutdown = shutdown

    max_jobs = 10
    job_timeout = 300
    keep_result = 3600
    poll_delay = 0.5
    queue_read_limit = 100
{%- endif %}
