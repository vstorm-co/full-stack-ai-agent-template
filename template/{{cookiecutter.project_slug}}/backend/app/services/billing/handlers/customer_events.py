{%- if cookiecutter.enable_billing %}
import logging
import stripe
from sqlalchemy.ext.asyncio import AsyncSession

import app.repositories.organization as org_repo

logger = logging.getLogger(__name__)


async def handle_customer_created(db: AsyncSession, event: stripe.Event) -> None:
    customer = event.data.object
    org_id = customer.metadata.get("org_id")
    if org_id:
        logger.info(
            "stripe_customer_created",
            extra={"customer_id": customer.id, "org_id": org_id},
        )


async def handle_customer_updated(db: AsyncSession, event: stripe.Event) -> None:
    customer = event.data.object
    logger.debug("stripe_customer_updated", extra={"customer_id": customer.id})


async def handle_customer_deleted(db: AsyncSession, event: stripe.Event) -> None:
    customer = event.data.object
    logger.warning("stripe_customer_deleted", extra={"customer_id": customer.id})
    org = await org_repo.get_by_stripe_customer(db, customer.id)
    if org:
        org.stripe_customer_id = None
        await db.flush()

{%- else %}
"""customer_events — not enabled (enable_billing=false)."""
{%- endif %}
