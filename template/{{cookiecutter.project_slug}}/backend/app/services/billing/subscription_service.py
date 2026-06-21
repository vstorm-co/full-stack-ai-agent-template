{%- if cookiecutter.enable_billing %}
import uuid
from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.billing.exceptions import BillingError
from app.services.billing.stripe_client import StripeClient
from app.core.exceptions import NotFoundError, BadRequestError
from app.db.models.subscription import Subscription, SubscriptionStatus
import app.repositories.subscription as sub_repo
import app.repositories.plan as plan_repo


class SubscriptionService:
    def __init__(self, db: AsyncSession, stripe: type[StripeClient] = StripeClient) -> None:
        self.db = db
        self.stripe = stripe

    async def get_for_org(self, org_id: uuid.UUID) -> Subscription | None:
        return await sub_repo.get_by_org(self.db, org_id)

    async def cancel(self, *, org_id: uuid.UUID, at_period_end: bool = True) -> Subscription:
        sub = await sub_repo.get_by_org(self.db, org_id)
        if not sub:
            raise NotFoundError(message="No subscription found", details={"org_id": str(org_id)})
        if sub.status in (SubscriptionStatus.CANCELED, SubscriptionStatus.INCOMPLETE_EXPIRED):
            raise BillingError(message="Subscription already canceled")

        await self.stripe.cancel_subscription(
            subscription_id=sub.stripe_subscription_id,
            at_period_end=at_period_end,
        )

        # Optimistic local update; webhook will reconcile authoritative state
        sub.cancel_at_period_end = at_period_end
        if not at_period_end:
            sub.status = SubscriptionStatus.CANCELED
            sub.canceled_at = datetime.now(UTC)
        await self.db.flush()
        return sub

    async def reactivate(self, *, org_id: uuid.UUID) -> Subscription:
        sub = await sub_repo.get_by_org(self.db, org_id)
        if not sub:
            raise NotFoundError(message="No subscription found", details={"org_id": str(org_id)})
        if not sub.cancel_at_period_end:
            raise BadRequestError(message="Subscription is not scheduled for cancellation")

        await self.stripe.reactivate_subscription(subscription_id=sub.stripe_subscription_id)
        sub.cancel_at_period_end = False
        sub.canceled_at = None
        await self.db.flush()
        return sub

    async def change_plan(self, *, org_id: uuid.UUID, new_price_id: uuid.UUID) -> Subscription:
        sub = await sub_repo.get_by_org(self.db, org_id)
        if not sub:
            raise NotFoundError(message="No subscription found", details={"org_id": str(org_id)})

        new_price = await plan_repo.get_price_by_id(self.db, new_price_id)
        if not new_price or not new_price.is_active:
            raise NotFoundError(message="Price not found", details={"price_id": str(new_price_id)})
        if new_price.interval == "one_time":
            raise BadRequestError(message="Cannot change subscription to a one-time price")

        await self.stripe.update_subscription(
            subscription_id=sub.stripe_subscription_id,
            new_stripe_price_id=new_price.stripe_price_id,
        )

        # Optimistic local update; webhook will reconcile authoritative state
        sub.stripe_price_id = new_price.stripe_price_id
        sub.plan_id = new_price.plan_id
        await self.db.flush()
        return sub

{%- else %}
"""subscription_service — not enabled (enable_billing=false)."""
{%- endif %}
