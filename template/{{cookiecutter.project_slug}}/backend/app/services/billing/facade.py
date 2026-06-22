{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
"""Billing facade — single entry point for the API layer; routes never import sub-services directly."""
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

import app.repositories.plan as plan_repo
{%- if cookiecutter.enable_rag %}
import app.repositories.chat_file as chat_file_repo
import app.repositories.rag_document as rag_document_repo
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
import app.repositories.usage_event as usage_event_repo
{%- endif %}
from app.core.config import settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.plan import Plan
{%- if cookiecutter.enable_credits_system %}
from app.db.models.credit_transaction import CreditTransaction
{%- endif %}
from app.db.models.subscription import Subscription
from app.db.models.user import User
from app.repositories import organization_repo
from app.services.billing.checkout_service import CheckoutService
{%- if cookiecutter.enable_credits_system %}
from app.services.billing.credit_service import CreditService
{%- endif %}
from app.services.billing.exceptions import InvalidWebhookError
from app.services.billing.stripe_client import StripeClient
from app.services.billing.subscription_service import SubscriptionService
from app.services.billing.webhook_handler import WebhookHandler
{%- if cookiecutter.enable_email %}
# subscription_repo and get_email_service are only needed for lifecycle-email batch methods
import app.repositories.subscription as subscription_repo
from app.services.email.service import get_email_service
{%- endif %}

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

    async def list_active_plans(self) -> list[Plan]:
        return await plan_repo.list_active_plans(self.db)

    async def get_plan(self, code: str) -> Plan:
        plan = await plan_repo.get_plan_by_code(self.db, code)
        if not plan:
            raise NotFoundError(message="Plan not found", details={"code": code})
        return plan

    async def create_checkout_session(
        self,
        org_id: uuid.UUID,
        *,
        seats: int = 1,
        price_id: str | None = None,
        success_url: str,
        cancel_url: str,
        user: User,
    ) -> str:
        """Create a Stripe Checkout session URL."""
        if not price_id:
            raise BadRequestError(message="price_id is required")

        org = await organization_repo.get_by_id(self.db, org_id)
        if org is None:
            raise NotFoundError(
                message="Organization not found", details={"org_id": str(org_id)}
            )

        try:
            price_uuid = uuid.UUID(price_id)
        except ValueError:
            raise BadRequestError(
                message="Invalid price_id format", details={"price_id": price_id}
            ) from None
        result = await self._checkout.create_checkout(
            user=user,
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

    async def handle_webhook_event(self, payload: bytes, sig_header: str) -> None:
        """Verify and dispatch a Stripe webhook event."""
        try:
            event = StripeClient.construct_event(payload=payload, signature=sig_header)
        except InvalidWebhookError as exc:
            raise BadRequestError(message=str(exc)) from exc

        handler = WebhookHandler(self.db)
        await handler.dispatch(event)

    async def get_subscription(self, org_id: uuid.UUID) -> Subscription:
        sub = await self._subscription.get_for_org(org_id)
        if sub is None:
            raise NotFoundError(message="No active subscription", details={"org_id": str(org_id)})
        return sub

{%- if cookiecutter.enable_rag %}

    async def get_storage_usage(self, user_id: uuid.UUID, org_id: uuid.UUID) -> dict[str, Any]:
        chat_bytes = await chat_file_repo.sum_size_for_user(self.db, user_id)
        rag_bytes = await rag_document_repo.sum_filesize_for_org(self.db, org_id)
        return {"chat_files_bytes": chat_bytes, "rag_documents_bytes": rag_bytes, "total_bytes": chat_bytes + rag_bytes}
{%- endif %}

    async def cancel_subscription(
        self, org_id: uuid.UUID, *, at_period_end: bool = True
    ) -> Subscription:
        return await self._subscription.cancel(org_id=org_id, at_period_end=at_period_end)

    async def reactivate_subscription(self, org_id: uuid.UUID) -> Subscription:
        return await self._subscription.reactivate(org_id=org_id)

    async def change_plan(self, org_id: uuid.UUID, new_price_id: uuid.UUID) -> Subscription:
        return await self._subscription.change_plan(org_id=org_id, new_price_id=new_price_id)

{%- if cookiecutter.enable_credits_system %}

    async def get_credit_balance(self, org_id: uuid.UUID) -> int:
        return await self._credits.get_balance(org_id)

    async def list_credit_transactions(
        self, org_id: uuid.UUID, *, skip: int, limit: int
    ) -> tuple[list[CreditTransaction], int]:
        return await self._credits.get_history(org_id, skip=skip, limit=limit)

    async def get_usage_aggregate(self, org_id: uuid.UUID, *, days: int | None = None) -> Any:
        since = (
            datetime.now(UTC) - timedelta(days=days)
            if days is not None and days > 0
            else None
        )
        return await usage_event_repo.aggregate_for_org(self.db, org_id, since=since)

    async def get_usage_timeline(self, org_id: uuid.UUID, *, days: int) -> Any:
        return await usage_event_repo.daily_timeline(self.db, org_id, days=days)
{%- endif %}

    async def get_invoices(self, org_id: uuid.UUID) -> list[dict[str, Any]]:
        """Return mock invoices built from subscription-grant and top-up credit transactions."""
        from sqlalchemy import select

        from app.db.models.credit_transaction import CreditTransaction

        result = await self.db.execute(
            select(CreditTransaction)
            .where(
                CreditTransaction.organization_id == org_id,
                CreditTransaction.type.in_(["grant_subscription", "purchase_topup"]),
            )
            .order_by(CreditTransaction.created_at.desc())
            .limit(24)
        )
        txs = result.scalars().all()

        invoices: list[dict[str, Any]] = []
        for i, tx in enumerate(txs, start=1):
            amount_cents = max(990, tx.delta * 10)
            period_start = tx.created_at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)

            invoices.append(
                {
                    "id": str(tx.id),
                    "number": f"INV-{tx.created_at.strftime('%Y%m')}-{i:03d}",
                    "status": "paid",
                    "amount_due": amount_cents,
                    "amount_paid": amount_cents,
                    "currency": "usd",
                    "period_start": period_start,
                    "period_end": period_end,
                    "invoice_pdf": None,
                    "hosted_invoice_url": None,
                    "created_at": tx.created_at,
                }
            )
        return invoices

{%- if cookiecutter.enable_email %}

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
            except stripe.StripeError:
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
            except stripe.StripeError:
                logger.exception("low_credits_alert_failed", extra={"org_id": str(org.id)})
        return sent
{%- endif %}


{%- else %}
"""Billing service — not configured (enable_billing or enable_teams is false)."""
{%- endif %}
