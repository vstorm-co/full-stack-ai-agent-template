"""Lifecycle email tasks — trial reminders and low-credits alerts."""

import logging

from prefect import flow

from app.db.session import get_worker_db_context
from app.services.billing import BillingService

logger = logging.getLogger(__name__)


async def _send_trial_reminders() -> int:
    async with get_worker_db_context() as db:
        return await BillingService(db).send_trial_ending_reminders()


async def _send_low_credits_alerts() -> int:
    async with get_worker_db_context() as db:
        return await BillingService(db).send_low_credits_alerts()


@flow(name="send-trial-reminders", log_prints=True)
async def send_trial_reminders_flow() -> dict[str, int]:
    """Cron: send trial-ending reminder emails."""
    count = await _send_trial_reminders()
    logger.info("trial_reminders_sent", extra={"count": count})
    return {"sent": count}


@flow(name="send-low-credits-alerts", log_prints=True)
async def send_low_credits_alerts_flow() -> dict[str, int]:
    """Cron: send low-credits alert emails to orgs below threshold."""
    count = await _send_low_credits_alerts()
    logger.info("low_credits_alerts_sent", extra={"count": count})
    return {"sent": count}
