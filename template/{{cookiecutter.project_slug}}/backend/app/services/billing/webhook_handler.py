{%- if cookiecutter.enable_billing %}
import logging

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

import app.repositories.stripe_event as stripe_event_repo
from app.services.billing.handlers import customer_events
from app.services.billing.handlers import invoice_events
from app.services.billing.handlers import payment_events
from app.services.billing.handlers import subscription_events

logger = logging.getLogger(__name__)

EVENT_HANDLERS = {
    "customer.subscription.created": subscription_events.handle_created,
    "customer.subscription.updated": subscription_events.handle_updated,
    "customer.subscription.deleted": subscription_events.handle_deleted,
    "customer.subscription.trial_will_end": subscription_events.handle_trial_ending,
    "invoice.payment_succeeded": invoice_events.handle_payment_succeeded,
    "invoice.payment_failed": invoice_events.handle_payment_failed,
    "invoice.upcoming": invoice_events.handle_upcoming,
    "checkout.session.completed": payment_events.handle_checkout_completed,
    "payment_intent.succeeded": payment_events.handle_payment_intent_succeeded,
    "payment_intent.payment_failed": payment_events.handle_payment_intent_failed,
    "customer.created": customer_events.handle_customer_created,
    "customer.updated": customer_events.handle_customer_updated,
    "customer.deleted": customer_events.handle_customer_deleted,
}


class WebhookHandler:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def dispatch(self, event: stripe.Event) -> None:
        existing = await stripe_event_repo.get_by_stripe_id(self.db, event.id)
        if existing and existing.status in ("processed", "skipped"):
            logger.info(
                "stripe_event_already_processed",
                extra={"event_id": event.id, "type": event.type},
            )
            return

        # Reuse the row on retry (status=failed/pending). Only insert when new.
        if existing is not None:
            db_event = existing
            db_event.status = "pending"
            db_event.payload = dict(event)  # ty: ignore[no-matching-overload]
            await self.db.flush()
        else:
            db_event = await stripe_event_repo.create(
                self.db,
                stripe_event_id=event.id,
                event_type=event.type,
                payload=dict(event),  # ty: ignore[no-matching-overload]
            )

        handler = EVENT_HANDLERS.get(event.type)
        if not handler:
            db_event.status = "skipped"
            await self.db.flush()
            return

        try:
            await handler(self.db, event)
            await stripe_event_repo.mark_processed(self.db, db_event=db_event)
        except Exception as exc:
            logger.exception(
                "webhook_handler_failed",
                extra={"event_id": event.id, "type": event.type},
            )
            try:
                await stripe_event_repo.mark_failed(self.db, db_event=db_event, error=str(exc))
            except Exception:
                logger.exception("webhook_mark_failed_error", extra={"event_id": event.id})

{%- else %}
"""webhook_handler — not enabled (enable_billing=false)."""
{%- endif %}
