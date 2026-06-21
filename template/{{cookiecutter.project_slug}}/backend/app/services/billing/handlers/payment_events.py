{%- if cookiecutter.enable_billing %}
import logging
import uuid
import stripe
from sqlalchemy.ext.asyncio import AsyncSession

import app.repositories.plan as plan_repo
{%- if cookiecutter.enable_credits_system %}
from app.services.billing.credit_service import CreditService
{%- endif %}

logger = logging.getLogger(__name__)


async def handle_checkout_completed(db: AsyncSession, event: stripe.Event) -> None:
    session = event.data.object
    if session.mode != "payment":
        # subscription mode — handled by customer.subscription.created
        return

{%- if cookiecutter.enable_credits_system %}
    try:
        org_id = uuid.UUID(session.metadata.get("org_id", ""))
        price_id = uuid.UUID(session.metadata.get("price_id", ""))
    except (ValueError, KeyError):
        logger.error("checkout_completed_invalid_metadata", extra={"session_id": session.id})
        return

    price = await plan_repo.get_price_by_id(db, price_id)
    if not price or not price.credits_grant:
        logger.warning("topup_price_no_credits", extra={"price_id": str(price_id)})
        return

    actor_user_id_str = session.metadata.get("user_id")
    actor_user_id = uuid.UUID(actor_user_id_str) if actor_user_id_str else None

    await CreditService(db).add_topup_credits(
        organization_id=org_id,
        actor_user_id=actor_user_id,
        amount=price.credits_grant,
        stripe_payment_intent_id=session.payment_intent or session.id,
    )
{%- else %}
    logger.info("checkout_completed_payment", extra={"session_id": session.id})
{%- endif %}


async def handle_payment_intent_succeeded(db: AsyncSession, event: stripe.Event) -> None:
    logger.info("payment_intent_succeeded", extra={"pi_id": event.data.object.id})


async def handle_payment_intent_failed(db: AsyncSession, event: stripe.Event) -> None:
    logger.warning("payment_intent_failed", extra={"pi_id": event.data.object.id})

{%- else %}
"""payment_events — not enabled (enable_billing=false)."""
{%- endif %}
