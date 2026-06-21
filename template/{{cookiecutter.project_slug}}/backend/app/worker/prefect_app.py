{%- if cookiecutter.use_prefect %}
"""Prefect runner — starts a long-running server that hosts all flow deployments.

Run with:
    python -m app.worker.prefect_app

The process registers scheduled deployments with the Prefect server and polls for
work.  Set PREFECT_API_URL to http://prefect-server:4200/api (self-hosted Docker)
or to your Prefect Cloud workspace URL + PREFECT_API_KEY for Cloud mode.
"""

import asyncio
import logging

from prefect import aserve
from prefect.client.schemas.schedules import CronSchedule, IntervalSchedule
{%- if cookiecutter.enable_rag %}
from app.worker.tasks.rag_tasks import (
    check_scheduled_syncs_flow,
    ingest_document_flow,
    sync_single_source_flow,
{%- if not cookiecutter.use_celery and not cookiecutter.use_taskiq and not cookiecutter.use_arq %}
    sync_collection_flow,
{%- endif %}
)
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}
from app.worker.tasks.email_tasks import send_trial_reminders_flow
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}
from app.worker.tasks.email_tasks import send_low_credits_alerts_flow
{%- endif %}
{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
from app.worker.tasks.cleanup_tasks import (
    cleanup_usage_events_flow,
    refresh_usage_matview_flow,
)
{%- endif %}

logger = logging.getLogger(__name__)


async def main() -> None:
    """Register all deployments and serve them."""
    deployments = []
{%- if cookiecutter.enable_rag %}
    # On-demand: triggered from API on file upload
    deployments.append(await ingest_document_flow.ato_deployment(name="ingest-document"))
    deployments.append(await sync_single_source_flow.ato_deployment(name="sync-single-source"))
{%- if not cookiecutter.use_celery and not cookiecutter.use_taskiq and not cookiecutter.use_arq %}
    deployments.append(await sync_collection_flow.ato_deployment(name="sync-collection"))
{%- endif %}
    # Scheduled: check connector sources every minute
    deployments.append(await check_scheduled_syncs_flow.ato_deployment(
        name="rag-sync-check",
        schedules=[IntervalSchedule(interval=60)],
    ))
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}
    deployments.append(await send_trial_reminders_flow.ato_deployment(
        name="trial-reminders",
        schedules=[CronSchedule(cron="0 9 * * *", timezone="{{ cookiecutter.timezone }}")],
    ))
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}
    deployments.append(await send_low_credits_alerts_flow.ato_deployment(
        name="low-credits-alerts",
        schedules=[CronSchedule(cron="0 */4 * * *", timezone="{{ cookiecutter.timezone }}")],
    ))
{%- endif %}
{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
    deployments.append(await cleanup_usage_events_flow.ato_deployment(
        name="cleanup-usage-events",
        schedules=[CronSchedule(cron="0 3 * * 0", timezone="{{ cookiecutter.timezone }}")],
    ))
    deployments.append(await refresh_usage_matview_flow.ato_deployment(
        name="refresh-usage-matview",
        schedules=[IntervalSchedule(interval=300)],
    ))
{%- endif %}
    logger.info("Starting Prefect runner with %d deployments", len(deployments))
    await aserve(*deployments)


if __name__ == "__main__":
    asyncio.run(main())
{%- endif %}
