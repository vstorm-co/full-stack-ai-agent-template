{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
"""UsageEvent repository."""

{%- if cookiecutter.use_postgresql %}
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

{%- elif cookiecutter.use_sqlite %}
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import delete as sql_delete, select, func
from app.db.models.credit_transaction import UsageEvent


def create(
    db: Session,
    *,
    organization_id: str,
    model: str,
    provider: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    credits_charged: int = 0,
    ai_framework: str = "",
    actor_user_id: str | None = None,
    conversation_id: str | None = None,
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
    db.flush()
    db.refresh(event)
    return event


def list_for_org(
    db: Session,
    organization_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[UsageEvent], int]:
    total = db.execute(
        select(func.count()).where(UsageEvent.organization_id == organization_id)
    ).scalar_one()
    rows = list(
        db.execute(
            select(UsageEvent)
            .where(UsageEvent.organization_id == organization_id)
            .order_by(UsageEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).scalars().all()
    )
    return rows, total


def aggregate_for_org(
    db: Session,
    organization_id: str,
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
    row = db.execute(total_q).one()

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
    by_model_rows = db.execute(by_model_q).all()

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


def daily_timeline(
    db: Session,
    organization_id: str,
    *,
    days: int = 30,
) -> list[dict]:
    """Return daily usage buckets using a live GROUP BY query."""
    from datetime import timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        select(
            func.date(UsageEvent.created_at).label("day"),
            func.sum(UsageEvent.input_tokens).label("input_tokens"),
            func.sum(UsageEvent.output_tokens).label("output_tokens"),
            func.sum(UsageEvent.cached_tokens).label("cached_tokens"),
            func.sum(UsageEvent.credits_charged).label("credits_charged"),
            func.count().label("total_calls"),
        )
        .where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.created_at >= cutoff,
        )
        .group_by(func.date(UsageEvent.created_at))
        .order_by(func.date(UsageEvent.created_at).asc())
    )
    rows = db.execute(q).all()
    return [
        {
            "day": str(r.day),
            "input_tokens": r.input_tokens or 0,
            "output_tokens": r.output_tokens or 0,
            "cached_tokens": r.cached_tokens or 0,
            "credits_charged": r.credits_charged or 0,
            "total_calls": r.total_calls or 0,
        }
        for r in rows
    ]


def delete_older_than(
    db: Session,
    cutoff: datetime,
) -> int:
    """Delete usage events older than cutoff. Returns number of deleted rows."""
    result = db.execute(sql_delete(UsageEvent).where(UsageEvent.created_at < cutoff))
    db.flush()
    return result.rowcount  # ty: ignore[unresolved-attribute]

{%- elif cookiecutter.use_mongodb %}
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.models.credit_transaction import UsageEvent


async def create(
    db: AsyncIOMotorDatabase,
    *,
    organization_id: str,
    model: str,
    provider: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    credits_charged: int = 0,
    ai_framework: str = "",
    actor_user_id: str | None = None,
    conversation_id: str | None = None,
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
    await event.insert()
    return event


async def list_for_org(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[UsageEvent], int]:
    query = UsageEvent.find(UsageEvent.organization_id == organization_id)
    total = await query.count()
    rows = await query.sort("-created_at").skip(skip).limit(limit).to_list()
    return rows, total


async def aggregate_for_org(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    *,
    since: datetime | None = None,
) -> dict:
    """Return total tokens, credits, and per-model breakdown.

    When ``since`` is provided, restricts the aggregation to events at or after
    that timestamp; otherwise aggregates over the full retention window.
    """
    match: dict = {"organization_id": organization_id}
    if since is not None:
        match["created_at"] = {"$gte": since}

    totals_pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": None,
                "total_input": {"$sum": "$input_tokens"},
                "total_output": {"$sum": "$output_tokens"},
                "total_cached": {"$sum": "$cached_tokens"},
                "total_credits": {"$sum": "$credits_charged"},
                "total_calls": {"$sum": 1},
            }
        },
    ]
    totals_result = await UsageEvent.aggregate(totals_pipeline).to_list()
    totals = totals_result[0] if totals_result else {}

    by_model_pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": {"model": "$model", "provider": "$provider"},
                "input_tokens": {"$sum": "$input_tokens"},
                "output_tokens": {"$sum": "$output_tokens"},
                "cached_tokens": {"$sum": "$cached_tokens"},
                "credits_charged": {"$sum": "$credits_charged"},
                "total_calls": {"$sum": 1},
            }
        },
        {"$sort": {"credits_charged": -1}},
    ]
    by_model_rows = await UsageEvent.aggregate(by_model_pipeline).to_list()

    return {
        "total_input_tokens": totals.get("total_input", 0),
        "total_output_tokens": totals.get("total_output", 0),
        "total_cached_tokens": totals.get("total_cached", 0),
        "total_credits_charged": totals.get("total_credits", 0),
        "total_calls": totals.get("total_calls", 0),
        "by_model": [
            {
                "model": r["_id"]["model"],
                "provider": r["_id"]["provider"],
                "input_tokens": r.get("input_tokens", 0),
                "output_tokens": r.get("output_tokens", 0),
                "cached_tokens": r.get("cached_tokens", 0),
                "credits_charged": r.get("credits_charged", 0),
                "total_calls": r.get("total_calls", 0),
            }
            for r in by_model_rows
        ],
    }


async def daily_timeline(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    *,
    days: int = 30,
) -> list[dict]:
    """Return daily usage buckets via MongoDB aggregation pipeline."""
    from datetime import timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {
            "organization_id": organization_id,
            "created_at": {"$gte": cutoff},
        }},
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$created_at",
                        "timezone": "UTC",
                    }
                },
                "input_tokens": {"$sum": "$input_tokens"},
                "output_tokens": {"$sum": "$output_tokens"},
                "cached_tokens": {"$sum": "$cached_tokens"},
                "credits_charged": {"$sum": "$credits_charged"},
                "total_calls": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = await UsageEvent.aggregate(pipeline).to_list()
    return [
        {
            "day": r["_id"],
            "input_tokens": r.get("input_tokens", 0),
            "output_tokens": r.get("output_tokens", 0),
            "cached_tokens": r.get("cached_tokens", 0),
            "credits_charged": r.get("credits_charged", 0),
            "total_calls": r.get("total_calls", 0),
        }
        for r in rows
    ]


async def delete_older_than(
    db: AsyncIOMotorDatabase,
    cutoff: datetime,
) -> int:
    """Delete usage events older than cutoff. Returns number of deleted documents."""
    result = await UsageEvent.find(UsageEvent.created_at < cutoff).delete()
    return result.deleted_count if result else 0

{%- endif %}
{%- else %}
"""UsageEvent repository — not enabled."""
{%- endif %}
