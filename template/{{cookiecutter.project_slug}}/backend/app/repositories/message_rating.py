"""Message rating repository for database operations."""

from datetime import datetime, timedelta, UTC
from typing import Any

from uuid import UUID

from sqlalchemy import Select, and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.message_rating import MessageRating
from app.db.models.user import User


async def get_rating_by_message_and_user(
    db: AsyncSession,
    message_id: UUID,
    user_id: UUID,
) -> MessageRating | None:
    """Get a user's rating for a specific message."""
    query = select(MessageRating).where(
        MessageRating.message_id == message_id,
        MessageRating.user_id == user_id,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_rating(
    db: AsyncSession,
    *,
    message_id: UUID,
    user_id: UUID,
    rating: int,
    comment: str | None = None,
) -> MessageRating:
    """Create a new rating.

    Note: The unique constraint on (message_id, user_id) prevents duplicates
    at the database level. Callers should handle IntegrityError.
    """
    rating_obj = MessageRating(
        message_id=message_id,
        user_id=user_id,
        rating=rating,
        comment=comment,
    )
    db.add(rating_obj)
    await db.flush()
    await db.refresh(rating_obj)
    return rating_obj


async def update_rating(
    db: AsyncSession,
    rating: MessageRating,
    *,
    new_rating: int,
    comment: str | None = None,
) -> MessageRating:
    """Update an existing rating."""
    rating.rating = new_rating
    rating.comment = comment
    await db.flush()
    await db.refresh(rating)
    return rating


async def delete_rating(db: AsyncSession, rating: MessageRating) -> None:
    """Delete a rating."""
    await db.delete(rating)
    await db.flush()


async def get_ratings_for_message(
    db: AsyncSession,
    message_id: UUID,
) -> list[MessageRating]:
    """Get all ratings for a message."""
    query = select(MessageRating).where(
        MessageRating.message_id == message_id
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_user_ratings_for_messages(
    db: AsyncSession,
    *,
    message_ids: list[UUID],
    user_id: UUID,
) -> dict[UUID, int]:
    """Return mapping of message_id → rating value for a single user."""
    if not message_ids:
        return {}
    query = select(MessageRating).where(
        MessageRating.message_id.in_(message_ids),
        MessageRating.user_id == user_id,
    )
    result = await db.execute(query)
    return {rating.message_id: rating.rating for rating in result.scalars().all()}


async def get_rating_counts_for_messages(
    db: AsyncSession,
    *,
    message_ids: list[UUID],
) -> dict[UUID, dict[str, int]]:
    """Return mapping of message_id → {likes, dislikes} counts."""
    if not message_ids:
        return {}
    query = (
        select(
            MessageRating.message_id,
            func.sum(case((MessageRating.rating == 1, 1), else_=0)).label("likes"),
            func.sum(case((MessageRating.rating == -1, 1), else_=0)).label("dislikes"),
        )
        .where(MessageRating.message_id.in_(message_ids))
        .group_by(MessageRating.message_id)
    )
    result = await db.execute(query)
    return {
        row.message_id: {"likes": row.likes or 0, "dislikes": row.dislikes or 0}
        for row in result.all()
    }


async def get_ratings_with_users_for_messages(
    db: AsyncSession,
    *,
    message_ids: list[UUID],
) -> list[tuple[MessageRating, Any]]:
    """Return ratings joined with users for the given message IDs (admin export)."""
    if not message_ids:
        return []
    query = (
        select(MessageRating, User)
        .join(User, MessageRating.user_id == User.id)
        .where(MessageRating.message_id.in_(message_ids))
    )
    result = await db.execute(query)
    return [(rating, user) for rating, user in result.all()]


async def list_ratings(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    rating_filter: int | None = None,  # 1 or -1 to filter
    with_comments_only: bool = False,
) -> tuple[list[MessageRating], int]:
    """List ratings with optional filters."""
    query = select(MessageRating)

    if rating_filter is not None:
        query = query.where(MessageRating.rating == rating_filter)

    if with_comments_only:
        query = query.where(MessageRating.comment.isnot(None), MessageRating.comment != "")

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    query = query.order_by(MessageRating.created_at.desc()).offset(skip).limit(limit)

    query = query.options(
        selectinload(MessageRating.message),
{%- if cookiecutter.use_jwt %}
        selectinload(MessageRating.user),
{%- endif %}
    )

    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def get_rating_summary(
    db: AsyncSession,
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Get aggregated rating statistics."""
    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    counts_query = select(
        func.count().label("total"),
        func.sum(case((MessageRating.rating == 1, 1), else_=0)).label("likes"),
        func.sum(case((MessageRating.rating == -1, 1), else_=0)).label("dislikes"),
        func.avg(MessageRating.rating).label("avg_rating"),
        func.sum(case((and_(MessageRating.comment.isnot(None), MessageRating.comment != ""), 1), else_=0)).label("with_comments"),
    ).where(MessageRating.created_at >= cutoff_date)

    result = await db.execute(counts_query)
    row = result.one()

    daily_query = select(
        func.date(MessageRating.created_at).label("date"),
        func.sum(case((MessageRating.rating == 1, 1), else_=0)).label("likes"),
        func.sum(case((MessageRating.rating == -1, 1), else_=0)).label("dislikes"),
    ).where(
        MessageRating.created_at >= cutoff_date
    ).group_by(
        func.date(MessageRating.created_at)
    ).order_by(
        func.date(MessageRating.created_at)
    )

    daily_result = await db.execute(daily_query)
    ratings_by_day = [
        {"date": str(row.date), "likes": row.likes or 0, "dislikes": row.dislikes or 0}
        for row in daily_result
    ]

    return {
        "total_ratings": row.total or 0,
        "like_count": row.likes or 0,
        "dislike_count": row.dislikes or 0,
        "average_rating": float(row.avg_rating) if row.avg_rating else 0.0,
        "with_comments": row.with_comments or 0,
        "ratings_by_day": ratings_by_day,
    }


