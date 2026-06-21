{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
"""UsageEvent repository."""

import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete as sql_delete, select, func, text
from app.db.models.credit_transaction import UsageEvent


async def create(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    model: str,
    provider: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    credits_charged: int = 0,
    ai_framework: str = "",
    actor_user_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
) -> UsageEvent:
    event = UsageEvent(
        organization_id=organization_id,
        model=model,
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        credits_charged=credits_charged,
        ai_framework=ai_framework,
        actor_user_id=actor_user_id,
        conversation_id=conversation_id,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def list_for_org(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[UsageEvent], int]:
    count_q = select(func.count()).where(UsageEvent.organization_id == organization_id)
    total = (await db.execute(count_q)).scalar_one()
    rows_q = (
        select(UsageEvent)
        .where(UsageEvent.organization_id == organization_id)
        .order_by(UsageEvent.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(rows_q)
    return list(result.scalars().all()), total


async def aggregate_for_org(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    since: datetime | None = None,
) -> dict:
    """Return total tokens, credits, and per-model breakdown.

    When ``since`` is provided, restricts the aggregation to events at or after
    that timestamp; otherwise aggregates over the full retention window.
    """
    filters = [UsageEvent.organization_id == organization_id]
    if since is not None:
        filters.append(UsageEvent.created_at >= since)

    total_q = select(
        func.sum(UsageEvent.input_tokens).label("total_input"),
        func.sum(UsageEvent.output_tokens).label("total_output"),
        func.sum(UsageEvent.cached_tokens).label("total_cached"),
        func.sum(UsageEvent.credits_charged).label("total_credits"),
        func.count().label("total_calls"),
    ).where(*filters)
    row = (await db.execute(total_q)).one()

    by_model_q = (
        select(
            UsageEvent.model,
            UsageEvent.provider,
            func.sum(UsageEvent.input_tokens).label("input_tokens"),
            func.sum(UsageEvent.output_tokens).label("output_tokens"),
            func.sum(UsageEvent.cached_tokens).label("cached_tokens"),
            func.sum(UsageEvent.credits_charged).label("credits_charged"),
            func.count().label("total_calls"),
        )
        .where(*filters)
        .group_by(UsageEvent.model, UsageEvent.provider)
        .order_by(func.sum(UsageEvent.credits_charged).desc())
    )
    by_model_rows = (await db.execute(by_model_q)).all()

    return {
        "total_input_tokens": row.total_input or 0,
        "total_output_tokens": row.total_output or 0,
        "total_cached_tokens": row.total_cached or 0,
        "total_credits_charged": row.total_credits or 0,
        "total_calls": row.total_calls or 0,
        "by_model": [
            {
                "model": r.model,
                "provider": r.provider,
                "input_tokens": r.input_tokens or 0,
                "output_tokens": r.output_tokens or 0,
                "cached_tokens": r.cached_tokens or 0,
                "credits_charged": r.credits_charged or 0,
                "total_calls": r.total_calls or 0,
            }
            for r in by_model_rows
        ],
    }


async def daily_timeline(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    days: int = 30,
) -> list[dict]:
    """Return daily usage buckets from the mv_usage_daily materialized view."""
    q = text("""
        SELECT day::text, input_tokens, output_tokens, cached_tokens, credits_charged, total_calls
        FROM mv_usage_daily
        WHERE organization_id = :org_id
          AND day >= CURRENT_DATE - INTERVAL '1 day' * :days
        ORDER BY day ASC
    """)
    rows = (await db.execute(q, {"org_id": str(organization_id), "days": days})).all()
    return [
        {
            "day": row.day,
            "input_tokens": row.input_tokens or 0,
            "output_tokens": row.output_tokens or 0,
            "cached_tokens": row.cached_tokens or 0,
            "credits_charged": row.credits_charged or 0,
            "total_calls": row.total_calls or 0,
        }
        for row in rows
    ]


async def delete_older_than(
    db: AsyncSession,
    cutoff: datetime,
) -> int:
    """Delete usage events older than cutoff. Returns number of deleted rows."""
    result = await db.execute(
        sql_delete(UsageEvent).where(UsageEvent.created_at < cutoff)
    )
    await db.flush()
    return result.rowcount  # ty: ignore[unresolved-attribute]

{%- else %}
"""UsageEvent repository — not enabled."""
{%- endif %}
