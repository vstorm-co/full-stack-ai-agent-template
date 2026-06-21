"""Prefect runner — starts a long-running server that hosts all flow deployments.

Run with:
    python -m app.worker.prefect_app

The process registers scheduled deployments with the Prefect server and polls for
work.  Set PREFECT_API_URL to http://prefect-server:4200/api (self-hosted Docker)
or to your Prefect Cloud workspace URL + PREFECT_API_KEY for Cloud mode.
"""

import asyncio
import logging

from prefect import serve
from prefect.client.schemas.schedules import CronSchedule, IntervalSchedule

from app.worker.tasks.cleanup_tasks import (
    cleanup_usage_events_flow,
    refresh_usage_matview_flow,
)
from app.worker.tasks.email_tasks import send_low_credits_alerts_flow, send_trial_reminders_flow
from app.worker.tasks.rag_tasks import (
    check_scheduled_syncs_flow,
    ingest_document_flow,
    sync_collection_flow,
    sync_single_source_flow,
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Register all deployments and serve them."""
    deployments = [
        # On-demand: triggered from API on file upload
        ingest_document_flow.to_deployment(name="ingest-document"),
        sync_single_source_flow.to_deployment(name="sync-single-source"),
        sync_collection_flow.to_deployment(name="sync-collection"),
        # Scheduled: check connector sources every minute
        check_scheduled_syncs_flow.to_deployment(
            name="rag-sync-check",
            schedules=[IntervalSchedule(interval=60)],
        ),
        send_trial_reminders_flow.to_deployment(
            name="trial-reminders",
            schedules=[CronSchedule(cron="0 9 * * *", timezone="UTC")],
        ),
        send_low_credits_alerts_flow.to_deployment(
            name="low-credits-alerts",
            schedules=[CronSchedule(cron="0 */4 * * *", timezone="UTC")],
        ),
        cleanup_usage_events_flow.to_deployment(
            name="cleanup-usage-events",
            schedules=[CronSchedule(cron="0 3 * * 0", timezone="UTC")],
        ),
        refresh_usage_matview_flow.to_deployment(
            name="refresh-usage-matview",
            schedules=[IntervalSchedule(interval=300)],
        ),
    ]
    logger.info("Starting Prefect runner with %d deployments", len(deployments))
    await serve(*deployments)


if __name__ == "__main__":
    asyncio.run(main())
