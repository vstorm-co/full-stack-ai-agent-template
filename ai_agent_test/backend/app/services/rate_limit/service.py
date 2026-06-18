"""RateLimitService — per-category, per-plan, sliding-window rate limiter."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status

from app.services.rate_limit.rules import DEFAULT_RATE_LIMITS, RateLimitRule
from app.services.rate_limit.storage import RateLimitResult, RateLimitStorage, get_storage

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_storage: RateLimitStorage | None = None


def _get_storage() -> RateLimitStorage:
    global _storage
    if _storage is None:
        _storage = get_storage()
    return _storage


async def _check_one(
    storage: RateLimitStorage,
    key: str,
    limit: int,
    period: int,
) -> RateLimitResult:
    return await storage.increment_and_check(key, limit, period)


async def check_rate_limit(
    *,
    category: str,
    request: Request,
    user_id: str | None = None,
    org_id: str | None = None,
    is_admin: bool = False,
    plan_features: dict | None = None,
) -> None:
    """Check rate limit; raise HTTP 429 if exceeded.

    Args:
        category: One of RateLimitCategory constants.
        request: The incoming FastAPI request (for IP extraction).
        user_id: Authenticated user ID (None for anonymous).
        org_id: Active organization ID (None for no-org context).
        is_admin: If True, all limits are bypassed.
        plan_features: org.subscription.price.plan.features dict (or None for free-tier defaults).
    """
    if is_admin:
        return

    storage = _get_storage()
    ip = request.client.host if request.client else "unknown"

    # Resolve rule: plan features > defaults
    rule: RateLimitRule | None = None
    if plan_features:
        rl = plan_features.get("rate_limits", {})
        if category in rl:
            rule = RateLimitRule.from_dict(rl[category])

    if rule is None:
        rule = DEFAULT_RATE_LIMITS.get(category)

    if rule is None or rule.is_unlimited():
        return

    # Check IP limit
    if rule.per_ip is not None:
        result = await _check_one(
            storage, f"rl:{category}:ip:{ip}", rule.per_ip, rule.ip_period_seconds
        )
        if not result.allowed:
            _raise_429(result, category, "ip")

    # Check per-user limit
    if rule.per_user is not None and user_id:
        result = await _check_one(
            storage, f"rl:{category}:user:{user_id}", rule.per_user, rule.period_seconds
        )
        if not result.allowed:
            _raise_429(result, category, "user")

    # Check per-org limit
    if rule.per_org is not None and org_id:
        result = await _check_one(
            storage, f"rl:{category}:org:{org_id}", rule.per_org, rule.org_period_seconds
        )
        if not result.allowed:
            _raise_429(result, category, "org")


def _raise_429(result: RateLimitResult, category: str, scope: str) -> None:
    retry_after = result.retry_after_seconds or 60
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Rate limit exceeded for category '{category}' (scope: {scope}). "
                f"Retry after {retry_after} seconds.",
                "details": {
                    "category": category,
                    "scope": scope,
                    "limit": result.limit,
                    "current": result.current_count,
                    "retry_after_seconds": retry_after,
                },
            }
        },
        headers={"Retry-After": str(retry_after)},
    )


def make_rate_limit_dep(category: str):
    """FastAPI dependency factory for a given category.

    Usage::

        AgentRateLimit = make_rate_limit_dep(RateLimitCategory.AGENT_INVOCATION)

        @router.post("/invoke")
        async def invoke(user: CurrentUser, _: None = Depends(AgentRateLimit)):
            ...
    """
    from fastapi import Depends

    from app.api.deps import ActiveOrg, CurrentUser

    async def _dep(request: Request, user: CurrentUser, active_org: ActiveOrg) -> None:
        plan_features: dict | None = None
        # Try to load plan features from org subscription (best-effort)
        try:
            if hasattr(active_org, "subscription") and active_org.subscription:
                sub = active_org.subscription
                if hasattr(sub, "price") and sub.price and hasattr(sub.price, "plan"):
                    plan_features = sub.price.plan.features or {}
        except Exception:
            pass

        await check_rate_limit(
            category=category,
            request=request,
            user_id=str(user.id),
            org_id=str(active_org.id) if active_org else None,
            is_admin=getattr(user, "is_app_admin", False),
            plan_features=plan_features,
        )

    return Depends(_dep)
