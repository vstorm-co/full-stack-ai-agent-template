{%- if cookiecutter.enable_email and (cookiecutter.enable_billing or cookiecutter.enable_credits_system) and (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq or cookiecutter.use_prefect) %}
"""Lifecycle email tasks — trial reminders and low-credits alerts."""

import asyncio
import logging
from typing import Any

{%- if cookiecutter.use_celery %}
from celery import shared_task
{%- elif cookiecutter.use_taskiq %}
from app.worker.taskiq_app import broker
{%- elif cookiecutter.use_prefect %}
from prefect import flow
{%- endif %}

from app.db.session import get_worker_db_context
from app.services.billing import BillingService

logger = logging.getLogger(__name__)

{%- if cookiecutter.enable_billing %}


async def _send_trial_reminders() -> int:
    async with get_worker_db_context() as db:
        return await BillingService(db).send_trial_ending_reminders()
{%- endif %}
{%- if cookiecutter.enable_credits_system %}


async def _send_low_credits_alerts() -> int:
    async with get_worker_db_context() as db:
        return await BillingService(db).send_low_credits_alerts()
{%- endif %}

{%- if cookiecutter.use_celery %}

{%- if cookiecutter.enable_billing %}


@shared_task(bind=True, max_retries=1, ignore_result=True)
def send_trial_reminders_task(self: Any) -> None:
    """Cron: send trial-ending reminder emails for trials expiring within 3 days."""
    try:
        count = asyncio.run(_send_trial_reminders())
        logger.info("trial_reminders_sent", extra={"count": count})
    except Exception as exc:
        logger.exception("send_trial_reminders_task_failed")
        raise self.retry(exc=exc, countdown=300) from exc
{%- endif %}
{%- if cookiecutter.enable_credits_system %}


@shared_task(bind=True, max_retries=1, ignore_result=True)
def send_low_credits_alerts_task(self: Any) -> None:
    """Cron: send low-credits alert emails to orgs below threshold."""
    try:
        count = asyncio.run(_send_low_credits_alerts())
        logger.info("low_credits_alerts_sent", extra={"count": count})
    except Exception as exc:
        logger.exception("send_low_credits_alerts_task_failed")
        raise self.retry(exc=exc, countdown=300) from exc
{%- endif %}

{%- elif cookiecutter.use_taskiq %}

{%- if cookiecutter.enable_billing %}


@broker.task
async def send_trial_reminders_task() -> dict[str, int]:
    """Cron: send trial-ending reminder emails."""
    count = await _send_trial_reminders()
    logger.info("trial_reminders_sent", extra={"count": count})
    return {"sent": count}
{%- endif %}
{%- if cookiecutter.enable_credits_system %}


@broker.task
async def send_low_credits_alerts_task() -> dict[str, int]:
    """Cron: send low-credits alert emails to orgs below threshold."""
    count = await _send_low_credits_alerts()
    logger.info("low_credits_alerts_sent", extra={"count": count})
    return {"sent": count}
{%- endif %}

{%- elif cookiecutter.use_arq %}

{%- if cookiecutter.enable_billing %}


async def send_trial_reminders_task(ctx: dict[str, Any]) -> dict[str, int]:
    """Cron: send trial-ending reminder emails."""
    count = await _send_trial_reminders()
    logger.info("trial_reminders_sent", extra={"count": count})
    return {"sent": count}
{%- endif %}
{%- if cookiecutter.enable_credits_system %}


async def send_low_credits_alerts_task(ctx: dict[str, Any]) -> dict[str, int]:
    """Cron: send low-credits alert emails to orgs below threshold."""
    count = await _send_low_credits_alerts()
    logger.info("low_credits_alerts_sent", extra={"count": count})
    return {"sent": count}
{%- endif %}

{%- elif cookiecutter.use_prefect %}

{%- if cookiecutter.enable_billing %}


@flow(name="send-trial-reminders", log_prints=True)
async def send_trial_reminders_flow() -> dict[str, int]:
    """Cron: send trial-ending reminder emails."""
    count = await _send_trial_reminders()
    logger.info("trial_reminders_sent", extra={"count": count})
    return {"sent": count}
{%- endif %}
{%- if cookiecutter.enable_credits_system %}


@flow(name="send-low-credits-alerts", log_prints=True)
async def send_low_credits_alerts_flow() -> dict[str, int]:
    """Cron: send low-credits alert emails to orgs below threshold."""
    count = await _send_low_credits_alerts()
    logger.info("low_credits_alerts_sent", extra={"count": count})
    return {"sent": count}
{%- endif %}
{%- endif %}
{%- endif %}
