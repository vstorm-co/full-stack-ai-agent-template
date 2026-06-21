"""Cleanup tasks — periodic purge of old usage events."""

import logging

from prefect import flow

from app.db.session import get_worker_db_context
from app.services.usage import UsageService

logger = logging.getLogger(__name__)

USAGE_RETENTION_DAYS = 90


async def _cleanup_usage_events() -> int:
    async with get_worker_db_context() as db:
        return await UsageService(db).cleanup_old_events(retention_days=USAGE_RETENTION_DAYS)


async def _refresh_usage_matview() -> None:
    async with get_worker_db_context() as db:
        await UsageService(db).refresh_daily_matview()


@flow(name="cleanup-usage-events", log_prints=True)
async def cleanup_usage_events_flow() -> dict[str, int]:
    """Cron: purge usage events older than 90 days and refresh the daily matview."""
    count = await _cleanup_usage_events()
    logger.info("cleanup_usage_events_done", extra={"deleted": count})
    return {"deleted": count}


@flow(name="refresh-usage-matview", log_prints=True)
async def refresh_usage_matview_flow() -> None:
    """Cron: refresh ``mv_usage_daily`` so the dashboard timeline stays fresh."""
    await _refresh_usage_matview()
