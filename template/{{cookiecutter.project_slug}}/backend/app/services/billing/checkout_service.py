{%- if cookiecutter.enable_billing %}
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.billing.exceptions import BillingError
from app.services.billing.stripe_client import StripeClient
from app.core.config import settings
from app.core.exceptions import NotFoundError, BadRequestError
from app.db.models.user import User
import app.repositories.plan as plan_repo
import app.repositories.organization as org_repo


class CheckoutService:
    def __init__(self, db: AsyncSession, stripe: type[StripeClient] = StripeClient) -> None:
        self.db = db
        self.stripe = stripe

    async def create_checkout(
        self,
        *,
        user: User,
        org_id: uuid.UUID,
        price_id: uuid.UUID,
        seats: int = 1,
        success_url: str,
        cancel_url: str,
    ) -> dict:
        price = await plan_repo.get_price_by_id(self.db, price_id)
        if not price or not price.is_active:
            raise NotFoundError(message="Price not found", details={"price_id": str(price_id)})

        org = await org_repo.get_by_id(self.db, org_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": str(org_id)})

        if not org.stripe_customer_id:
            customer = await self.stripe.create_customer(
                email=user.email, name=org.name, org_id=org_id
            )
            org.stripe_customer_id = customer.id
            await self.db.flush()

        mode = "subscription" if price.interval in ("month", "year") else "payment"

        params: dict = {
            "customer": org.stripe_customer_id,
            "mode": mode,
            "line_items": [{"price": price.stripe_price_id, "quantity": seats}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "org_id": str(org_id),
                "user_id": str(user.id),
                "price_id": str(price_id),
            },
            "allow_promotion_codes": True,
            "client_reference_id": str(org_id),
        }

        if mode == "subscription":
            trial_days = price.trial_period_days or settings.STRIPE_TRIAL_DAYS_DEFAULT or None
            sub_data: dict = {"metadata": {"org_id": str(org_id)}}
            if trial_days:
                sub_data["trial_period_days"] = trial_days
                sub_data["trial_settings"] = {
                    "end_behavior": {
                        "missing_payment_method": (
                            "cancel" if not settings.STRIPE_TRIAL_REQUIRES_PAYMENT_METHOD else "pause"
                        )
                    }
                }
            params["subscription_data"] = sub_data
            if not settings.STRIPE_TRIAL_REQUIRES_PAYMENT_METHOD:
                params["payment_method_collection"] = "if_required"

        session = await self.stripe.create_checkout_session(**params)
        return {"url": session.url, "session_id": session.id}

    async def create_portal_session(self, *, org_id: uuid.UUID) -> str:
        org = await org_repo.get_by_id(self.db, org_id)
        if not org or not org.stripe_customer_id:
            raise BadRequestError(
                message="Organization has no Stripe customer. Subscribe first.",
                details={"org_id": str(org_id)},
            )
        session = await self.stripe.create_portal_session(
            customer_id=org.stripe_customer_id,
            return_url=settings.BILLING_PORTAL_RETURN_URL,
        )
        return session.url

{%- else %}
"""checkout_service — not enabled (enable_billing=false)."""
{%- endif %}
