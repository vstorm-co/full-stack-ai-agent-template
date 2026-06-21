"""CreditTransaction repository."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.credit_transaction import CreditTransaction, CreditTransactionType


async def create(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    delta: int,
    balance_after: int,
    type: CreditTransactionType,
    description: str,
    actor_user_id: uuid.UUID | None = None,
    stripe_reference: str | None = None,
    usage_event_id: uuid.UUID | None = None,
) -> CreditTransaction:
    tx = CreditTransaction(
        organization_id=organization_id,
        delta=delta,
        balance_after=balance_after,
        type=type,
        description=description,
        actor_user_id=actor_user_id,
        stripe_reference=stripe_reference,
        usage_event_id=usage_event_id,
    )
    db.add(tx)
    await db.flush()
    await db.refresh(tx)
    return tx


async def list_for_org(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[CreditTransaction], int]:
    count_q = select(func.count()).where(CreditTransaction.organization_id == organization_id)
    total = (await db.execute(count_q)).scalar_one()
    rows_q = (
        select(CreditTransaction)
        .where(CreditTransaction.organization_id == organization_id)
        .order_by(CreditTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(rows_q)
    return list(result.scalars().all()), total
