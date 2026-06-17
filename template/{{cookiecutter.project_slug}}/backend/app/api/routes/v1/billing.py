{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
"""Billing routes — Plans, Checkout, Portal, Subscription management, Credits.

Routes are pure HTTP plumbing. All business logic — repositories, Stripe calls,
credit accounting — lives in :class:`app.services.billing.BillingService`.
"""

from typing import Any

from fastapi import APIRouter, Header, Query, Request, status
{%- if cookiecutter.use_postgresql and cookiecutter.enable_rag %}
from sqlalchemy import func, select
{%- endif %}

{%- if cookiecutter.use_postgresql and cookiecutter.enable_rag %}
from app.api.deps import ActiveOrg, BillingSvc, CurrentUser, DBSession
{%- else %}
from app.api.deps import ActiveOrg, BillingSvc, CurrentUser
{%- endif %}
from app.core.config import settings
{%- if cookiecutter.use_postgresql and cookiecutter.enable_rag %}
from app.db.models.chat_file import ChatFile
from app.db.models.rag_document import RAGDocument
{%- endif %}
from app.schemas.billing import (
    CheckoutSessionCreate,
    CheckoutSessionRead,
    PlanList,
    PlanRead,
    PortalSessionRead,
    SubscriptionChangePlan,
    SubscriptionRead,
{%- if cookiecutter.enable_credits_system %}
    CreditBalanceRead,
    CreditTransactionList,
    UsageAggregateRead,
    UsageTimelineRead,
{%- endif %}
)

router = APIRouter()


@router.get("/plans", response_model=PlanList)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def list_plans(billing_service: BillingSvc) -> Any:
    """Return all active plans with their prices. Suitable for the pricing page."""
    plans = await billing_service.list_active_plans()
    return PlanList(plans=plans)  # ty: ignore[invalid-argument-type]
{%- else %}
def list_plans(billing_service: BillingSvc) -> Any:
    """Return all active plans with their prices."""
    plans = billing_service.list_active_plans()
    return PlanList(plans=plans)  # ty: ignore[invalid-argument-type]
{%- endif %}


@router.get("/plans/{code}", response_model=PlanRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def get_plan(code: str, billing_service: BillingSvc) -> Any:
    """Return a single active plan by code."""
    return await billing_service.get_plan(code)
{%- else %}
def get_plan(code: str, billing_service: BillingSvc) -> Any:
    """Return a single active plan by code."""
    return billing_service.get_plan(code)
{%- endif %}


@router.post("/checkout", response_model=CheckoutSessionRead, status_code=status.HTTP_201_CREATED)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
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
{%- else %}
def create_checkout_session(
    data: CheckoutSessionCreate,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Create a Stripe Checkout session and return the redirect URL."""
    url = billing_service.create_checkout_session(
        str(active_org.id),
        user=current_user,
        seats=data.seats,
        price_id=str(data.price_id),
        success_url=data.success_url,
        cancel_url=data.cancel_url,
    )
    return CheckoutSessionRead(url=url)
{%- endif %}


@router.post("/portal", response_model=PortalSessionRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def create_portal_session(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Open the Stripe Customer Portal for managing the active org's subscription."""
    url = await billing_service.create_portal_session(active_org.id)
    return PortalSessionRead(url=url)
{%- else %}
def create_portal_session(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Open the Stripe Customer Portal for managing the active org's subscription."""
    url = billing_service.create_portal_session(str(active_org.id))
    return PortalSessionRead(url=url)
{%- endif %}


@router.get("/me/subscription", response_model=SubscriptionRead | None)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def get_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Get the active subscription for the current organization."""
    return await billing_service.get_subscription(active_org.id)
{%- else %}
def get_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Get the active subscription for the current organization."""
    return billing_service.get_subscription(str(active_org.id))
{%- endif %}


@router.patch("/me/subscription", response_model=SubscriptionRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def change_plan(
    data: SubscriptionChangePlan,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Upgrade or downgrade the current organization's subscription plan."""
    return await billing_service.change_plan(active_org.id, data.new_price_id)
{%- else %}
def change_plan(
    data: SubscriptionChangePlan,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Upgrade or downgrade the current organization's subscription plan."""
    return billing_service.change_plan(str(active_org.id), str(data.new_price_id))
{%- endif %}


@router.delete("/me/subscription", response_model=SubscriptionRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def cancel_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
    at_period_end: bool = Query(True, description="Cancel at period end (recommended)"),
) -> Any:
    """Cancel the active subscription. Defaults to end-of-period cancellation."""
    return await billing_service.cancel_subscription(active_org.id, at_period_end=at_period_end)
{%- else %}
def cancel_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
    at_period_end: bool = Query(True),
) -> Any:
    """Cancel the active subscription. Defaults to end-of-period cancellation."""
    return billing_service.cancel_subscription(str(active_org.id), at_period_end=at_period_end)
{%- endif %}


@router.post("/me/subscription/reactivate", response_model=SubscriptionRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def reactivate_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Undo a scheduled cancellation if the period hasn't ended yet."""
    return await billing_service.reactivate_subscription(active_org.id)
{%- else %}
def reactivate_subscription(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Undo a scheduled cancellation if the period hasn't ended yet."""
    return billing_service.reactivate_subscription(str(active_org.id))
{%- endif %}

{%- if cookiecutter.use_postgresql and cookiecutter.enable_rag %}


@router.get("/me/storage")
async def get_storage_usage(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    db: DBSession,
) -> dict[str, Any]:
    """Sum bytes used by chat-attached files (per-user) and RAG docs (per-org)."""
    chat_bytes = (
        await db.execute(
            select(func.coalesce(func.sum(ChatFile.size), 0)).where(
                ChatFile.user_id == current_user.id
            )
        )
    ).scalar_one()
    rag_bytes = (
        await db.execute(
            select(func.coalesce(func.sum(RAGDocument.filesize), 0)).where(
                RAGDocument.organization_id == active_org.id
            )
        )
    ).scalar_one()
    return {
        "chat_bytes": int(chat_bytes),
        "rag_bytes": int(rag_bytes),
        "total_bytes": int(chat_bytes) + int(rag_bytes),
        # Soft cap surfaced by the gauge — not enforced server-side yet.
        "limit_bytes": settings.STORAGE_SOFT_LIMIT_BYTES,
    }
{%- endif %}

{%- if cookiecutter.enable_credits_system %}


@router.get("/me/credits", response_model=CreditBalanceRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def get_credits_balance(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Return current credits balance for the active organization."""
    balance = await billing_service.get_credit_balance(active_org.id)
    return CreditBalanceRead(balance=balance, low_threshold=settings.CREDITS_LOW_THRESHOLD)
{%- else %}
def get_credits_balance(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
) -> Any:
    """Return current credits balance for the active organization."""
    balance = billing_service.get_credit_balance(str(active_org.id))
    return CreditBalanceRead(balance=balance, low_threshold=settings.CREDITS_LOW_THRESHOLD)
{%- endif %}


@router.get("/me/credits/transactions", response_model=CreditTransactionList)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
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
    return CreditTransactionList(items=items, total=total)  # ty: ignore[invalid-argument-type]
{%- else %}
def list_credit_transactions(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List the active organization's credit ledger entries."""
    items, total = billing_service.list_credit_transactions(
        str(active_org.id), skip=skip, limit=limit
    )
    return CreditTransactionList(items=items, total=total)  # ty: ignore[invalid-argument-type]
{%- endif %}


@router.get("/me/credits/usage", response_model=UsageAggregateRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
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
{%- else %}
def get_usage_aggregate(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
    days: int | None = Query(
        None, ge=1, le=365, description="Restrict aggregation to the last N days (default: all-time)"
    ),
) -> Any:
    """Return aggregated usage stats for the active organization."""
    return billing_service.get_usage_aggregate(str(active_org.id), days=days)
{%- endif %}


@router.get("/me/credits/usage/timeline", response_model=UsageTimelineRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def get_usage_timeline(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
    days: int = Query(30, ge=7, le=365, description="Days of history to return"),
) -> Any:
    """Return per-day usage buckets for the active organization."""
    buckets = await billing_service.get_usage_timeline(active_org.id, days=days)
    return UsageTimelineRead(buckets=buckets, days=days)
{%- else %}
def get_usage_timeline(
    current_user: CurrentUser,
    active_org: ActiveOrg,
    billing_service: BillingSvc,
    days: int = Query(30, ge=7, le=365, description="Days of history to return"),
) -> Any:
    """Return per-day usage buckets for the active organization."""
    buckets = billing_service.get_usage_timeline(str(active_org.id), days=days)
    return UsageTimelineRead(buckets=buckets, days=days)
{%- endif %}
{%- endif %}


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    billing_service: BillingSvc,
    stripe_signature: str = Header(..., alias="stripe-signature"),
) -> Any:
    """Receive and process Stripe webhook events.

    Stripe sends a ``stripe-signature`` header for HMAC payload verification.
    This endpoint is intentionally unauthenticated.
    """
    payload = await request.body()
    await billing_service.handle_webhook_event(payload, stripe_signature)
    return {"received": True}
{%- else %}
"""Billing routes — not configured (enable_billing or enable_teams is false)."""
{%- endif %}
