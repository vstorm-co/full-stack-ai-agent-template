"""Admin endpoints for message ratings.

Provides endpoints for administrators to view and analyze user ratings
on AI assistant messages.

The endpoints are:
- GET /admin/ratings - List all ratings with filtering
- GET /admin/ratings/summary - Get aggregated rating statistics
- GET /admin/ratings/export - Export ratings as JSON or CSV
"""

{%- if cookiecutter.use_jwt %}
from typing import Any

from fastapi import APIRouter, Query

from app.api.deps import CurrentAdmin, MessageRatingSvc
from app.schemas.message_rating import MessageRatingList, RatingSummary

router = APIRouter()

{%- if cookiecutter.use_postgresql %}


@router.get("", response_model=MessageRatingList)
async def list_ratings_admin(
    rating_service: MessageRatingSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    rating_filter: int | None = Query(None, ge=-1, le=1, description="Filter by rating value"),
    with_comments_only: bool = Query(False, description="Only show ratings with comments"),
) -> Any:
    """List all ratings with filtering (admin only).

    Returns paginated list of ratings with optional filters:
    - rating_filter: Filter by rating value (1 for likes, -1 for dislikes)
    - with_comments_only: Only return ratings that have comments

    Results are ordered by creation date (newest first).
    """
    items, total = await rating_service.list_ratings(
        skip=skip,
        limit=limit,
        rating_filter=rating_filter,
        with_comments_only=with_comments_only,
    )
    return MessageRatingList(items=items, total=total)


@router.get("/summary", response_model=RatingSummary)
async def get_rating_summary(
    rating_service: MessageRatingSvc,
    _: CurrentAdmin,
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
) -> Any:
    """Get aggregated rating statistics (admin only).

    Returns summary statistics including:
    - Total ratings count
    - Like/dislike counts
    - Average rating (-1.0 to 1.0)
    - Count of ratings with comments
    - Daily breakdown of ratings

    The `days` parameter controls the time window (default: 30 days).
    """
    return await rating_service.get_summary(days=days)


@router.get("/export")
async def export_ratings(
    rating_service: MessageRatingSvc,
    _: CurrentAdmin,
    export_format: str = Query("json", description="Export format: 'json' or 'csv'"),
    rating_filter: int | None = Query(None, ge=-1, le=1, description="Filter by rating value"),
    with_comments_only: bool = Query(False, description="Only show ratings with comments"),
) -> Any:
    """Export all ratings as JSON or CSV (admin only).

    CSV is streamed row-by-row; JSON collects into a single document.
    """
    return await rating_service.export_ratings(
        export_format=export_format,
        rating_filter=rating_filter,
        with_comments_only=with_comments_only,
    )


{%- elif cookiecutter.use_sqlite %}


@router.get("", response_model=MessageRatingList)
def list_ratings_admin(
    rating_service: MessageRatingSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    rating_filter: int | None = Query(None, ge=-1, le=1, description="Filter by rating value"),
    with_comments_only: bool = Query(False, description="Only show ratings with comments"),
) -> Any:
    """List all ratings with filtering (admin only).

    Returns paginated list of ratings with optional filters:
    - rating_filter: Filter by rating value (1 for likes, -1 for dislikes)
    - with_comments_only: Only return ratings that have comments

    Results are ordered by creation date (newest first).
    """
    items, total = rating_service.list_ratings(
        skip=skip,
        limit=limit,
        rating_filter=rating_filter,
        with_comments_only=with_comments_only,
    )
    return MessageRatingList(items=items, total=total)


@router.get("/summary", response_model=RatingSummary)
def get_rating_summary(
    rating_service: MessageRatingSvc,
    _: CurrentAdmin,
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
) -> Any:
    """Get aggregated rating statistics (admin only).

    Returns summary statistics including:
    - Total ratings count
    - Like/dislike counts
    - Average rating (-1.0 to 1.0)
    - Count of ratings with comments
    - Daily breakdown of ratings

    The `days` parameter controls the time window (default: 30 days).
    """
    return rating_service.get_summary(days=days)


@router.get("/export")
def export_ratings(
    rating_service: MessageRatingSvc,
    _: CurrentAdmin,
    export_format: str = Query("json", description="Export format: 'json' or 'csv'"),
    rating_filter: int | None = Query(None, ge=-1, le=1, description="Filter by rating value"),
    with_comments_only: bool = Query(False, description="Only show ratings with comments"),
) -> Any:
    """Export all ratings as JSON or CSV (admin only).

    CSV is streamed row-by-row; JSON collects into a single document.
    """
    return rating_service.export_ratings(
        export_format=export_format,
        rating_filter=rating_filter,
        with_comments_only=with_comments_only,
    )


{%- elif cookiecutter.use_mongodb %}


@router.get("", response_model=MessageRatingList)
async def list_ratings_admin(
    rating_service: MessageRatingSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    rating_filter: int | None = Query(None, ge=-1, le=1, description="Filter by rating value"),
    with_comments_only: bool = Query(False, description="Only show ratings with comments"),
) -> Any:
    """List all ratings with filtering (admin only).

    Returns paginated list of ratings with optional filters:
    - rating_filter: Filter by rating value (1 for likes, -1 for dislikes)
    - with_comments_only: Only return ratings that have comments

    Results are ordered by creation date (newest first).
    """
    items, total = await rating_service.list_ratings(
        skip=skip,
        limit=limit,
        rating_filter=rating_filter,
        with_comments_only=with_comments_only,
    )
    return MessageRatingList(items=items, total=total)


@router.get("/summary", response_model=RatingSummary)
async def get_rating_summary(
    rating_service: MessageRatingSvc,
    _: CurrentAdmin,
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
) -> Any:
    """Get aggregated rating statistics (admin only).

    Returns summary statistics including:
    - Total ratings count
    - Like/dislike counts
    - Average rating (-1.0 to 1.0)
    - Count of ratings with comments
    - Daily breakdown of ratings

    The `days` parameter controls the time window (default: 30 days).
    """
    return await rating_service.get_summary(days=days)


@router.get("/export")
async def export_ratings(
    rating_service: MessageRatingSvc,
    _: CurrentAdmin,
    export_format: str = Query("json", description="Export format: 'json' or 'csv'"),
    rating_filter: int | None = Query(None, ge=-1, le=1, description="Filter by rating value"),
    with_comments_only: bool = Query(False, description="Only show ratings with comments"),
) -> Any:
    """Export all ratings as JSON or CSV (admin only).

    CSV is streamed row-by-row; JSON collects into a single document.
    """
    return await rating_service.export_ratings(
        export_format=export_format,
        rating_filter=rating_filter,
        with_comments_only=with_comments_only,
    )


{%- endif %}
{%- else %}
# Admin ratings router - JWT not enabled
router = APIRouter()  # type: ignore
{%- endif %}
