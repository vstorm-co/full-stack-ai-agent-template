{%- if cookiecutter.enable_billing %}
import logging
import datetime as _dt
from datetime import UTC, datetime
import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.subscription import Subscription, SubscriptionStatus
import app.repositories.subscription as sub_repo
import app.repositories.plan as plan_repo
import app.repositories.organization as org_repo
{%- if cookiecutter.enable_credits_system %}
from app.services.billing.credit_service import CreditService
{%- endif %}
{%- if cookiecutter.enable_email %}
from app.services.email.service import get_email_service
{%- endif %}

logger = logging.getLogger(__name__)


async def _sync_from_stripe(
    db: AsyncSession, stripe_sub: stripe.Subscription
) -> Subscription:
    price_obj = stripe_sub["items"]["data"][0]["price"]
    price = await plan_repo.get_price_by_stripe_id(db, price_obj["id"])
    org = await org_repo.get_by_stripe_customer(db, stripe_sub.customer)  # ty: ignore[invalid-argument-type]

    if not org:
        logger.error(
            "subscription_org_not_found",
            extra={"customer_id": stripe_sub.customer},
        )
        raise ValueError(f"No org found for customer {stripe_sub.customer}")

    fields = {
        "stripe_subscription_id": stripe_sub.id,
        "stripe_customer_id": stripe_sub.customer,
        "stripe_item_id": stripe_sub["items"]["data"][0]["id"],
        "price_id": price.id if price else None,
        "organization_id": org.id,
        "seats_quantity": stripe_sub["items"]["data"][0].get("quantity", 1),
        "status": SubscriptionStatus(stripe_sub.status),
        "current_period_start": datetime.fromtimestamp(stripe_sub.current_period_start, UTC),  # ty: ignore[unresolved-attribute]
        "current_period_end": datetime.fromtimestamp(stripe_sub.current_period_end, UTC),  # ty: ignore[unresolved-attribute]
        "cancel_at_period_end": stripe_sub.cancel_at_period_end,
        "canceled_at": datetime.fromtimestamp(stripe_sub.canceled_at, UTC) if stripe_sub.canceled_at else None,
        "trial_start": datetime.fromtimestamp(stripe_sub.trial_start, UTC) if stripe_sub.trial_start else None,
        "trial_end": datetime.fromtimestamp(stripe_sub.trial_end, UTC) if stripe_sub.trial_end else None,
    }

    existing = await sub_repo.get_by_stripe_id(db, stripe_sub.id)
    if existing:
        return await sub_repo.update(db, db_sub=existing, **fields)

    return await sub_repo.create(db, **fields)


{%- if cookiecutter.enable_credits_system %}
async def _grant_subscription_credits_if_needed(db: AsyncSession, sub: Subscription) -> None:
    """Grant the plan's monthly credit budget to the org. Idempotent within a billing period."""
    if not sub.price_id:
        return
    price = await plan_repo.get_price_by_id(db, sub.price_id)
    if not price:
        return
    plan = await plan_repo.get_plan_by_id(db, price.plan_id)
    if not plan:
        return
    seats = sub.seats_quantity or 1
    amount = (plan.monthly_credits_base or 0) + (plan.monthly_credits_per_seat or 0) * seats
    if amount <= 0:
        return
    try:
        await CreditService(db).grant_subscription_credits(
            organization_id=sub.organization_id,
            amount=amount,
            description=f"{plan.display_name} — {seats} seat(s) — monthly grant",
            stripe_reference=sub.stripe_subscription_id,
        )
    except Exception:
        logger.exception(
            "subscription_credit_grant_failed",
            extra={"org_id": str(sub.organization_id)},
        )
{%- endif %}


async def handle_created(db: AsyncSession, event: stripe.Event) -> None:
{%- if cookiecutter.enable_credits_system %}
    sub = await _sync_from_stripe(db, event.data.object)  # ty: ignore[invalid-argument-type]
    if sub.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
        await _grant_subscription_credits_if_needed(db, sub)
{%- else %}
    await _sync_from_stripe(db, event.data.object)
{%- endif %}


async def handle_updated(db: AsyncSession, event: stripe.Event) -> None:
    stripe_sub = event.data.object
{%- if cookiecutter.enable_credits_system %}
    sub = await _sync_from_stripe(db, stripe_sub)  # ty: ignore[invalid-argument-type]
{%- else %}
    await _sync_from_stripe(db, stripe_sub)
{%- endif %}
    prev = event.data.previous_attributes
    if prev is None:
        return
{%- if cookiecutter.enable_credits_system or cookiecutter.enable_email %}
    prev_status = prev.get("status") if hasattr(prev, "get") else None
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
    # New billing period started → grant fresh credits.
    if prev.get("current_period_end") and sub.status == SubscriptionStatus.ACTIVE:
        await _grant_subscription_credits_if_needed(db, sub)
    # Trial converted to active → first paid period.
    if prev_status == "trialing" and stripe_sub.status == "active":
        await _grant_subscription_credits_if_needed(db, sub)
{%- endif %}
{%- if cookiecutter.enable_email %}
    if prev_status == "trialing" and stripe_sub.status not in ("active", "trialing"):
        try:
            customer = stripe.Customer.retrieve(stripe_sub.customer)
            await get_email_service().send_trial_expired(
                to=customer.email or "",
                name=customer.name or customer.email or "there",
                upgrade_url=settings.BILLING_SUCCESS_URL,
            )
        except Exception:
            logger.exception("email_trial_expired_failed")
    elif prev.get("items") and stripe_sub.status == "active":
        try:
            customer = stripe.Customer.retrieve(stripe_sub.customer)
            email_svc = get_email_service()
            try:
                new_price = stripe_sub["items"]["data"][0]["price"]
                new_plan = new_price.get("nickname") or new_price["id"]
            except (KeyError, IndexError):
                new_plan = "updated plan"
            try:
                old_items_data = (prev.get("items") or {}).get("data") or []
                old_price = old_items_data[0]["price"] if old_items_data else {}
                old_plan = old_price.get("nickname") or old_price.get("id") or "previous plan"
            except (KeyError, IndexError, TypeError):
                old_plan = "previous plan"
            await email_svc.send_subscription_changed(
                to=customer.email or "",
                name=customer.name or customer.email or "there",
                old_plan=old_plan,
                new_plan=new_plan,
                effective_date=_dt.datetime.now(_dt.timezone.utc).strftime("%B %d, %Y"),
            )
        except Exception:
            logger.exception("email_subscription_changed_failed")
{%- endif %}


async def handle_deleted(db: AsyncSession, event: stripe.Event) -> None:
    stripe_sub = event.data.object
    sub = await sub_repo.get_by_stripe_id(db, stripe_sub.id)
    if sub:
        sub.status = SubscriptionStatus.CANCELED
        sub.canceled_at = (
            datetime.fromtimestamp(stripe_sub.canceled_at, UTC)
            if stripe_sub.canceled_at
            else datetime.now(UTC)
        )
        await db.flush()
{%- if cookiecutter.enable_email %}
    try:
        customer = stripe.Customer.retrieve(stripe_sub.customer)
        period_end = stripe_sub.current_period_end
        access_until = (
            _dt.datetime.fromtimestamp(period_end, _dt.UTC).strftime("%B %d, %Y")
            if period_end
            else "end of billing period"
        )
        plan_name = (
            stripe_sub.get("plan", {}).get("nickname", "subscription")
            if hasattr(stripe_sub, "get")
            else "subscription"
        )
        await get_email_service().send_subscription_canceled(
            to=customer.email or "",
            name=customer.name or customer.email or "there",
            plan_name=plan_name,
            access_until=access_until,
            resubscribe_url=settings.BILLING_SUCCESS_URL,
        )
    except Exception:
        logger.exception("email_subscription_canceled_failed")
{%- endif %}


async def handle_trial_ending(db: AsyncSession, event: stripe.Event) -> None:
    stripe_sub = event.data.object
    logger.info("subscription_trial_ending", extra={"stripe_sub_id": stripe_sub.id})
{%- if cookiecutter.enable_email %}
    try:
        customer = stripe.Customer.retrieve(stripe_sub.customer)
        trial_end_ts = stripe_sub.trial_end or 0
        now_ts = _dt.datetime.now(_dt.UTC).timestamp()
        days_left = max(1, int((trial_end_ts - now_ts) / 86400))
        await get_email_service().send_trial_ending(
            to=customer.email or "",
            name=customer.name or customer.email or "there",
            days_left=days_left,
            upgrade_url=settings.BILLING_SUCCESS_URL,
        )
    except Exception:
        logger.exception("email_trial_ending_failed")
{%- endif %}

{%- else %}
"""subscription_events — not enabled (enable_billing=false)."""
{%- endif %}
