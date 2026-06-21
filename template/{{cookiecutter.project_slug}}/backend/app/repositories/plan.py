{%- if cookiecutter.enable_billing %}
"""Plan and Price repository."""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.plan import Plan, Price


async def get_plan_by_code(db: AsyncSession, code: str) -> Plan | None:
    result = await db.execute(select(Plan).where(Plan.code == code, Plan.is_active))
    return result.scalar_one_or_none()


async def get_plan_by_id(db: AsyncSession, plan_id: uuid.UUID) -> Plan | None:
    return await db.get(Plan, plan_id)


async def list_active_plans(db: AsyncSession) -> list[Plan]:
    result = await db.execute(select(Plan).where(Plan.is_active).order_by(Plan.sort_order))
    return list(result.scalars().all())


async def get_price_by_id(db: AsyncSession, price_id: uuid.UUID) -> Price | None:
    return await db.get(Price, price_id)


async def get_price_by_stripe_id(db: AsyncSession, stripe_price_id: str) -> Price | None:
    result = await db.execute(select(Price).where(Price.stripe_price_id == stripe_price_id))
    return result.scalar_one_or_none()


async def upsert_plan(db: AsyncSession, *, code: str, display_name: str, **kwargs) -> Plan:
    existing = await get_plan_by_code(db, code)
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        existing.display_name = display_name
        await db.flush()
        await db.refresh(existing)
        return existing
    plan = Plan(code=code, display_name=display_name, **kwargs)
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return plan


async def upsert_price(db: AsyncSession, *, stripe_price_id: str, plan_id: uuid.UUID, **kwargs) -> Price:
    existing = await get_price_by_stripe_id(db, stripe_price_id)
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        await db.flush()
        await db.refresh(existing)
        return existing
    price = Price(stripe_price_id=stripe_price_id, plan_id=plan_id, **kwargs)
    db.add(price)
    await db.flush()
    await db.refresh(price)
    return price

{%- else %}
"""Plan repository — not enabled (enable_billing=false)."""
{%- endif %}
