"""Admin observability — workspace stats + Stripe event log."""

from typing import Any

from fastapi import APIRouter, Query

from app.api.deps import AdminSvc, CurrentAdmin
from app.schemas.admin import AdminStats, StripeEventList, StripeEventRead

router = APIRouter()


@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(
    service: AdminSvc,
    _user: CurrentAdmin,
) -> Any:
    """Aggregate workspace metrics. Billing fields are 0 when billing is
    disabled in the deployment."""
    return await service.workspace_stats()


@router.get("/stripe-events", response_model=StripeEventList)
async def list_stripe_events(
    service: AdminSvc,
    _user: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Any:
    """List recent Stripe webhook events from the idempotency log.

    Best-effort: returns empty list when the StripeEvent table doesn't exist
    (billing disabled in this deployment).
    """
    rows, total = await service.list_stripe_events(skip=skip, limit=limit)
    items = [StripeEventRead.model_validate(row) for row in rows]
    return StripeEventList(items=items, total=total)
