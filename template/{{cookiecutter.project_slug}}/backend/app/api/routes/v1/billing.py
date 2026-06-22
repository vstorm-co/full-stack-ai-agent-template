{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
"""Billing routes — Plans, Checkout, Portal, Subscription management, Credits.

Routes are pure HTTP plumbing. All business logic — repositories, Stripe calls,
credit accounting — lives in :class:`app.services.billing.BillingService`.
"""

from typing import Any

from fastapi import APIRouter, Header, Query, Request, status

from app.api.deps import ActiveOrg, BillingSvc, CurrentUser
from app.core.config import settings
from app.schemas.billing import (
    CheckoutSessionCreate,
    CheckoutSessionRead,
    InvoiceList,
    InvoiceRead,
    PlanList,
    PlanRead,
    PortalSessionRead,
    StorageUsageRead,
    SubscriptionChangePlan,
    SubscriptionRead,
{%- if cookiecutter.enable_credits_system %}
    CreditBalanceRead,
    CreditTransactionList,
    CreditTransactionRead,
    UsageAggregateRead,
    UsageTimelineRead,
{%- endif %}
)

router = APIRouter()


@router.get("/plans", response_model=PlanList)
async def list_plans(billing_service: BillingSvc) -> Any:
    """Return all active plans with their prices. Suitable for the pricing page."""
    plans = await billing_service.list_active_plans()
    return PlanList(plans=[PlanRead.model_validate(p) for p in plans])


@router.get("/plans/{code}", response_model=PlanRead)
async def get_plan(code: str, billing_service: BillingSvc) -> Any:
    """Return a single active plan by code."""
    return await billing_service.get_plan(code)


@router.post("/checkout", response_model=CheckoutSessionRead, status_code=status.HTTP_201_CREATED)
async def create_checkout_session(
    data: CheckoutSessionCreate,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Create a Stripe Checkout session and return the redirect URL."""
    url = await billing_service.create_checkout_session(
        active_org.id,
        user=current_user,
        seats=data.seats,
        price_id=str(data.price_id),
        success_url=data.success_url,
        cancel_url=data.cancel_url,
    )
    return CheckoutSessionRead(url=url)


@router.post("/portal", response_model=PortalSessionRead)
async def create_portal_session(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Open the Stripe Customer Portal for managing the active org's subscription."""
    url = await billing_service.create_portal_session(active_org.id)
    return PortalSessionRead(url=url)


@router.get("/me/subscription", response_model=SubscriptionRead)
async def get_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Get the active subscription for the current organization."""
    return await billing_service.get_subscription(active_org.id)


@router.patch("/me/subscription", response_model=SubscriptionRead)
async def change_plan(
    data: SubscriptionChangePlan,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Upgrade or downgrade the current organization's subscription plan."""
    return await billing_service.change_plan(active_org.id, data.new_price_id)


@router.delete("/me/subscription", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def cancel_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
    at_period_end: bool = Query(True, description="Cancel at period end (recommended)"),
) -> None:
    """Cancel the active subscription. Defaults to end-of-period cancellation."""
    await billing_service.cancel_subscription(active_org.id, at_period_end=at_period_end)


@router.post("/me/subscription/reactivate", response_model=SubscriptionRead)
async def reactivate_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Undo a scheduled cancellation if the period hasn't ended yet."""
    return await billing_service.reactivate_subscription(active_org.id)

{%- if cookiecutter.enable_rag %}


@router.get("/me/storage", response_model=StorageUsageRead)
async def get_storage_usage(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> dict[str, Any]:
    """Sum bytes used by chat-attached files (per-user) and RAG docs (per-org)."""
    return await billing_service.get_storage_usage(current_user.id, active_org.id)
{%- endif %}

@router.get("/me/invoices", response_model=InvoiceList)
async def list_invoices(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Return invoices for the active organization (built from subscription/topup transactions)."""
    items = await billing_service.get_invoices(active_org.id)
    return InvoiceList(items=[InvoiceRead(**i) for i in items], total=len(items))


{%- if cookiecutter.enable_credits_system %}


@router.get("/me/credits", response_model=CreditBalanceRead)
async def get_credits_balance(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Return current credits balance for the active organization."""
    balance = await billing_service.get_credit_balance(active_org.id)
    return CreditBalanceRead(balance=balance, low_threshold=settings.CREDITS_LOW_THRESHOLD)


@router.get("/me/credits/transactions", response_model=CreditTransactionList)
async def list_credit_transactions(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List the active organization's credit ledger entries."""
    items, total = await billing_service.list_credit_transactions(
        active_org.id, skip=skip, limit=limit
    )
    return CreditTransactionList(items=[CreditTransactionRead.model_validate(i) for i in items], total=total)


@router.get("/me/credits/usage", response_model=UsageAggregateRead)
async def get_usage_aggregate(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
    days: int | None = Query(
        None, ge=1, le=365, description="Restrict aggregation to the last N days (default: all-time)"
    ),
) -> Any:
    """Return aggregated usage stats for the active organization."""
    return await billing_service.get_usage_aggregate(active_org.id, days=days)


@router.get("/me/credits/usage/timeline", response_model=UsageTimelineRead)
async def get_usage_timeline(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
    days: int = Query(30, ge=7, le=365, description="Days of history to return"),
) -> Any:
    """Return per-day usage buckets for the active organization."""
    buckets = await billing_service.get_usage_timeline(active_org.id, days=days)
    return UsageTimelineRead(buckets=buckets, days=days)
{%- endif %}


@router.post("/webhook", status_code=status.HTTP_200_OK, response_model=None)
async def stripe_webhook(
    request: Request,
    billing_service: BillingSvc,
    stripe_signature: str = Header(..., alias="stripe-signature"),
) -> Any:
    """Receive and process Stripe webhook events. Intentionally unauthenticated."""
    payload = await request.body()
    await billing_service.handle_webhook_event(payload, stripe_signature)
    return {"received": True}
{%- else %}
"""Billing routes — not configured (enable_billing or enable_teams is false)."""
{%- endif %}
