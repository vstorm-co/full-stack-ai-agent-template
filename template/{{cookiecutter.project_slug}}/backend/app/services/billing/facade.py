{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
{%- if cookiecutter.use_postgresql %}
"""Billing service — delegates to app.services.billing.* module (PostgreSQL async).

Single facade exposed to the API layer for everything billing-related: plans, checkout,
portal, subscription management, credits, and usage. Routes never touch repositories or
the ``app.services.billing.*`` services directly.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

{%- if cookiecutter.enable_email %}
import stripe
{%- endif %}
from sqlalchemy.ext.asyncio import AsyncSession

import app.repositories.plan as plan_repo
{%- if cookiecutter.enable_email %}
import app.repositories.subscription as subscription_repo
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
import app.repositories.usage_event as usage_event_repo
{%- endif %}
from app.services.billing.checkout_service import CheckoutService
{%- if cookiecutter.enable_credits_system %}
from app.services.billing.credit_service import CreditService
{%- endif %}
from app.services.billing.exceptions import InvalidWebhookError
from app.services.billing.stripe_client import StripeClient
from app.services.billing.subscription_service import SubscriptionService
from app.services.billing.webhook_handler import WebhookHandler
{%- if cookiecutter.enable_email %}
from app.core.config import settings
{%- endif %}
from app.core.exceptions import BadRequestError, NotFoundError
{%- if cookiecutter.enable_credits_system %}
from app.db.models.credit_transaction import CreditTransaction
{%- endif %}
from app.db.models.plan import Plan
from app.db.models.subscription import Subscription
from app.db.models.user import User
{%- if cookiecutter.enable_email %}
from app.services.email.service import get_email_service
{%- endif %}
from app.repositories import organization_repo

logger = logging.getLogger(__name__)


class BillingService:
    """Facade over CheckoutService, SubscriptionService, WebhookHandler, CreditService."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._checkout = CheckoutService(db)
        self._subscription = SubscriptionService(db)
{%- if cookiecutter.enable_credits_system %}
        self._credits = CreditService(db)
{%- endif %}

    # -- Plans --

    async def list_active_plans(self) -> list[Plan]:
        return await plan_repo.list_active_plans(self.db)

    async def get_plan(self, code: str) -> Plan:
        plan = await plan_repo.get_plan_by_code(self.db, code)
        if not plan:
            raise NotFoundError(message="Plan not found", details={"code": code})
        return plan

    # -- Checkout / Portal --

    async def create_checkout_session(
        self,
        org_id: uuid.UUID,
        *,
        seats: int = 1,
        price_id: str | None = None,
        success_url: str,
        cancel_url: str,
        user: User | None = None,
    ) -> str:
        """Create a Stripe Checkout session URL."""
        if not price_id:
            raise BadRequestError(message="price_id is required")

        org = await organization_repo.get_by_id(self.db, org_id)
        if org is None:
            raise NotFoundError(
                message="Organization not found", details={"org_id": str(org_id)}
            )

        price_uuid = uuid.UUID(price_id) if isinstance(price_id, str) else price_id
        result = await self._checkout.create_checkout(
            user=user,  # ty: ignore[invalid-argument-type]
            org_id=org.id,
            price_id=price_uuid,
            seats=seats,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return result["url"]

    async def create_portal_session(self, org_id: uuid.UUID) -> str:
        """Create a Stripe Customer Portal URL."""
        org = await organization_repo.get_by_id(self.db, org_id)
        if org is None:
            raise NotFoundError(
                message="Organization not found", details={"org_id": str(org_id)}
            )
        return await self._checkout.create_portal_session(org_id=org.id)

    # -- Webhook --

    async def handle_webhook_event(self, payload: bytes, sig_header: str) -> None:
        """Verify and dispatch a Stripe webhook event."""
        try:
            event = StripeClient.construct_event(payload=payload, signature=sig_header)
        except InvalidWebhookError as exc:
            raise BadRequestError(message=str(exc)) from exc

        handler = WebhookHandler(self.db)
        await handler.dispatch(event)

    # -- Subscription management --

    async def get_subscription(self, org_id: uuid.UUID) -> Subscription | None:
        return await self._subscription.get_for_org(org_id)

    async def cancel_subscription(
        self, org_id: uuid.UUID, *, at_period_end: bool = True
    ) -> Subscription:
        return await self._subscription.cancel(org_id=org_id, at_period_end=at_period_end)

    async def reactivate_subscription(self, org_id: uuid.UUID) -> Subscription:
        return await self._subscription.reactivate(org_id=org_id)

    async def change_plan(self, org_id: uuid.UUID, new_price_id: uuid.UUID) -> Subscription:
        return await self._subscription.change_plan(org_id=org_id, new_price_id=new_price_id)

{%- if cookiecutter.enable_credits_system %}

    # -- Credits --

    async def get_credit_balance(self, org_id: uuid.UUID) -> int:
        return await self._credits.get_balance(org_id)

    async def list_credit_transactions(
        self, org_id: uuid.UUID, *, skip: int, limit: int
    ) -> tuple[list[CreditTransaction], int]:
        return await self._credits.get_history(org_id, skip=skip, limit=limit)

    # -- Usage --

    async def get_usage_aggregate(self, org_id: uuid.UUID, *, days: int | None = None):
        since = (
            datetime.now(UTC) - timedelta(days=days)
            if days is not None and days > 0
            else None
        )
        return await usage_event_repo.aggregate_for_org(self.db, org_id, since=since)

    async def get_usage_timeline(self, org_id: uuid.UUID, *, days: int):
        return await usage_event_repo.daily_timeline(self.db, org_id, days=days)
{%- endif %}

{%- if cookiecutter.enable_email %}

    # -- Lifecycle emails (driven by scheduled worker tasks) --

    async def send_trial_ending_reminders(self, *, within_days: int = 3) -> int:
        """Send a reminder email to every org whose Stripe trial ends within ``within_days``.

        Returns the count of successfully sent reminders. Per-customer failures are logged
        and skipped — one bad row should not block the rest of the batch.
        """
        subs = await subscription_repo.get_trialing_ending_soon(self.db, within_days=within_days)
        email_svc = get_email_service()
        sent = 0
        for sub in subs:
            try:
                customer = stripe.Customer.retrieve(sub.stripe_customer_id)
                now = datetime.now(UTC)
                days_left = (
                    max(1, int((sub.trial_end.timestamp() - now.timestamp()) / 86400))
                    if sub.trial_end
                    else within_days
                )
                await email_svc.send_trial_ending(
                    to=customer.email or "",
                    name=customer.name or customer.email or "there",
                    days_left=days_left,
                    upgrade_url=settings.BILLING_SUCCESS_URL,
                )
                sent += 1
            except Exception:
                logger.exception("trial_reminder_email_failed", extra={"sub_id": str(sub.id)})
        return sent

    async def send_low_credits_alerts(self) -> int:
        """Send a low-credits alert email to every org below ``CREDITS_LOW_THRESHOLD``.

        Returns the count of successfully sent alerts.
        """
        rows = await organization_repo.get_with_low_credits(
            self.db, threshold=settings.CREDITS_LOW_THRESHOLD
        )
        email_svc = get_email_service()
        sent = 0
        for org, owner_email, owner_name in rows:
            try:
                await email_svc.send_low_credits(
                    to=owner_email,
                    name=owner_name,
                    balance=org.credits_balance,
                    topup_url=settings.BILLING_SUCCESS_URL,
                )
                sent += 1
            except Exception:
                logger.exception("low_credits_alert_failed", extra={"org_id": str(org.id)})
        return sent
{%- endif %}


{%- elif cookiecutter.use_sqlite %}
"""Billing service — delegates to app.services.billing.* module (SQLite sync).

Single facade exposed to the API layer for everything billing-related. Routes never
touch repositories or the ``app.services.billing.*`` services directly.
"""

import logging
from sqlalchemy.orm import Session

import app.repositories.plan as plan_repo
{%- if cookiecutter.enable_credits_system %}
import app.repositories.usage_event as usage_event_repo
{%- endif %}
from app.services.billing.checkout_service import CheckoutService
{%- if cookiecutter.enable_credits_system %}
from app.services.billing.credit_service import CreditService
{%- endif %}
from app.services.billing.exceptions import InvalidWebhookError
from app.services.billing.stripe_client import StripeClient
from app.services.billing.subscription_service import SubscriptionService
from app.services.billing.webhook_handler import WebhookHandler
from app.core.exceptions import BadRequestError, NotFoundError
{%- if cookiecutter.enable_credits_system %}
from app.db.models.credit_transaction import CreditTransaction
{%- endif %}
from app.db.models.plan import Plan
from app.db.models.subscription import Subscription
from app.repositories import organization_repo

logger = logging.getLogger(__name__)


class BillingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._checkout = CheckoutService(db)
        self._subscription = SubscriptionService(db)
{%- if cookiecutter.enable_credits_system %}
        self._credits = CreditService(db)
{%- endif %}

    # -- Plans --

    def list_active_plans(self) -> list[Plan]:
        return plan_repo.list_active_plans(self.db)

    def get_plan(self, code: str) -> Plan:
        plan = plan_repo.get_plan_by_code(self.db, code)
        if not plan:
            raise NotFoundError(message="Plan not found", details={"code": code})
        return plan

    # -- Checkout / Portal --

    def create_checkout_session(
        self,
        org_id: str,
        *,
        seats: int = 1,
        price_id: str | None = None,
        success_url: str,
        cancel_url: str,
        user=None,
    ) -> str:
        if not price_id:
            raise BadRequestError(message="price_id is required")
        org = organization_repo.get_by_id(self.db, org_id)
        if org is None:
            raise NotFoundError(
                message="Organization not found", details={"org_id": str(org_id)}
            )
        result = self._checkout.create_checkout(
            user=user,  # ty: ignore[invalid-argument-type]
            org_id=str(org.id),
            price_id=price_id,
            seats=seats,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return result["url"]

    def create_portal_session(self, org_id: str) -> str:
        org = organization_repo.get_by_id(self.db, org_id)
        if org is None:
            raise NotFoundError(
                message="Organization not found", details={"org_id": str(org_id)}
            )
        return self._checkout.create_portal_session(org_id=str(org.id))

    # -- Webhook --

    async def handle_webhook_event(self, payload: bytes, sig_header: str) -> None:
        try:
            event = StripeClient.construct_event(payload=payload, signature=sig_header)
        except InvalidWebhookError as exc:
            raise BadRequestError(message=str(exc)) from exc

        handler = WebhookHandler(self.db)
        await handler.dispatch(event)

    # -- Subscription management --

    def get_subscription(self, org_id: str) -> Subscription | None:
        return self._subscription.get_for_org(org_id)

    def cancel_subscription(self, org_id: str, *, at_period_end: bool = True) -> Subscription:
        return self._subscription.cancel(org_id=org_id, at_period_end=at_period_end)

    def reactivate_subscription(self, org_id: str) -> Subscription:
        return self._subscription.reactivate(org_id=org_id)

    def change_plan(self, org_id: str, new_price_id: str) -> Subscription:
        return self._subscription.change_plan(org_id=org_id, new_price_id=new_price_id)

{%- if cookiecutter.enable_credits_system %}

    # -- Credits --

    def get_credit_balance(self, org_id: str) -> int:
        return self._credits.get_balance(org_id)

    def list_credit_transactions(
        self, org_id: str, *, skip: int, limit: int
    ) -> tuple[list[CreditTransaction], int]:
        return self._credits.get_history(org_id, skip=skip, limit=limit)

    # -- Usage --

    def get_usage_aggregate(self, org_id: str, *, days: int | None = None):
        since = (
            datetime.now(UTC) - timedelta(days=days)
            if days is not None and days > 0
            else None
        )
        return usage_event_repo.aggregate_for_org(self.db, org_id, since=since)

    def get_usage_timeline(self, org_id: str, *, days: int):
        return usage_event_repo.daily_timeline(self.db, org_id, days=days)
{%- endif %}


{%- else %}
"""Billing service — not applicable (no SQL database)."""
{%- endif %}
{%- else %}
"""Billing service — not configured (enable_billing or enable_teams is false)."""
{%- endif %}
