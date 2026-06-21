{%- if cookiecutter.enable_billing %}
"""Subscription repository."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.subscription import Subscription, SubscriptionStatus


async def get_by_org(db: AsyncSession, organization_id: uuid.UUID) -> Subscription | None:
    result = await db.execute(select(Subscription).where(Subscription.organization_id == organization_id))
    return result.scalar_one_or_none()


async def get_by_stripe_id(db: AsyncSession, stripe_subscription_id: str) -> Subscription | None:
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
    )
    return result.scalar_one_or_none()


async def get_by_customer_id(db: AsyncSession, stripe_customer_id: str) -> Subscription | None:
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
    )
    return result.scalar_one_or_none()


async def create(db: AsyncSession, **kwargs) -> Subscription:
    sub = Subscription(**kwargs)
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return sub


async def update(db: AsyncSession, *, db_sub: Subscription, **kwargs) -> Subscription:
    for k, v in kwargs.items():
        setattr(db_sub, k, v)
    await db.flush()
    await db.refresh(db_sub)
    return db_sub


async def delete(db: AsyncSession, *, db_sub: Subscription) -> None:
    await db.delete(db_sub)
    await db.flush()


async def get_trialing_ending_soon(
    db: AsyncSession, *, within_days: int = 3
) -> list[Subscription]:
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=within_days)
    result = await db.execute(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.TRIALING,
            Subscription.trial_end.isnot(None),
            Subscription.trial_end > now,
            Subscription.trial_end <= cutoff,
        )
    )
    return list(result.scalars().all())

{%- else %}
"""Subscription repository — not enabled (enable_billing=false)."""
{%- endif %}
