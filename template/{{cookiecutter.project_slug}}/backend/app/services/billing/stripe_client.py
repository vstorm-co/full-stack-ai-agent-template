{%- if cookiecutter.enable_billing %}
"""Stripe SDK wrapper — centralised init, retries, error mapping."""

import uuid
import logging
from typing import NoReturn

import stripe

from app.core.config import settings
from app.services.billing.exceptions import StripeCardError, StripeError, InvalidWebhookError

logger = logging.getLogger(__name__)


def _init_stripe() -> None:
    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe.api_version = settings.STRIPE_API_VERSION


class StripeClient:
    """Thin wrapper around the Stripe SDK.

    All Stripe I/O goes through here so we can mock a single class in tests
    and centralise error mapping.
    """

    @staticmethod
    def _handle_error(exc: Exception, context: dict | None = None) -> NoReturn:
        logger.exception("stripe_error", extra=context or {})
        if isinstance(exc, stripe.CardError):
            raise StripeCardError(message=str(exc), details={"stripe_code": exc.code}) from exc
        raise StripeError(message=str(exc)) from exc

    @staticmethod
    async def create_customer(*, email: str, name: str | None, org_id: uuid.UUID) -> stripe.Customer:
        try:
            return await stripe.Customer.create_async(
                email=email,
                name=name,  # ty: ignore[invalid-argument-type]
                metadata={"org_id": str(org_id)},
                idempotency_key=f"customer_create_{org_id}",
            )
        except Exception as exc:
            StripeClient._handle_error(exc, {"org_id": str(org_id)})

    @staticmethod
    async def create_checkout_session(**params) -> stripe.checkout.Session:
        try:
            return await stripe.checkout.Session.create_async(**params)
        except Exception as exc:
            StripeClient._handle_error(exc)

    @staticmethod
    async def create_portal_session(*, customer_id: str, return_url: str) -> stripe.billing_portal.Session:
        try:
            return await stripe.billing_portal.Session.create_async(
                customer=customer_id,
                return_url=return_url,
            )
        except Exception as exc:
            StripeClient._handle_error(exc, {"customer_id": customer_id})

    @staticmethod
    async def cancel_subscription(*, subscription_id: str, at_period_end: bool = True) -> stripe.Subscription:
        try:
            if at_period_end:
                return await stripe.Subscription.modify_async(
                    subscription_id, cancel_at_period_end=True
                )
            return await stripe.Subscription.cancel_async(subscription_id)
        except Exception as exc:
            StripeClient._handle_error(exc, {"subscription_id": subscription_id})

    @staticmethod
    async def update_subscription(
        *, subscription_id: str, new_stripe_price_id: str, proration_behavior: str = "create_prorations"
    ) -> stripe.Subscription:
        try:
            sub = await stripe.Subscription.retrieve_async(subscription_id)
            item_id = sub["items"]["data"][0]["id"]
            return await stripe.Subscription.modify_async(
                subscription_id,
                items=[{"id": item_id, "price": new_stripe_price_id}],
                proration_behavior=proration_behavior,  # ty: ignore[invalid-argument-type]
            )
        except Exception as exc:
            StripeClient._handle_error(exc, {"subscription_id": subscription_id})

    @staticmethod
    async def reactivate_subscription(*, subscription_id: str) -> stripe.Subscription:
        try:
            return await stripe.Subscription.modify_async(
                subscription_id, cancel_at_period_end=False
            )
        except Exception as exc:
            StripeClient._handle_error(exc, {"subscription_id": subscription_id})

    @staticmethod
    def construct_event(*, payload: bytes, signature: str) -> stripe.Event:
        try:
            return stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.SignatureVerificationError as exc:
            raise InvalidWebhookError(message="Invalid webhook signature") from exc


_init_stripe()

{%- else %}
"""stripe_client — not enabled (enable_billing=false)."""
{%- endif %}
