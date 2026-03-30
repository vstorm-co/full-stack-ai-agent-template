"""Admin endpoints for message ratings.

Provides endpoints for administrators to view and analyze user ratings
on AI assistant messages.

The endpoints are:
- GET /admin/ratings - List all ratings with filtering
- GET /admin/ratings/summary - Get aggregated rating statistics
- GET /admin/ratings/export - Export ratings as JSON or CSV
"""

{%- if cookiecutter.use_jwt %}
{%- if cookiecutter.use_postgresql %}
from typing import Any
from uuid import UUID
{%- elif cookiecutter.use_mongodb %}
from typing import Any
{%- else %}
from typing import Any
{%- endif %}

import csv
from datetime import datetime
from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.deps import CurrentAdmin, MessageRatingSvc
from app.schemas.message_rating import (
    MessageRatingList,
    RatingSummary,
)

router = APIRouter()


{%- if cookiecutter.use_postgresql %}


@router.get("", response_model=MessageRatingList)
async def list_ratings_admin(
    rating_service: MessageRatingSvc,
    admin_user: CurrentAdmin,
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
    admin_user: CurrentAdmin,
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
    admin_user: CurrentAdmin,
    format: str = Query("json", description="Export format: 'json' or 'csv'"),
    rating_filter: int | None = Query(None, ge=-1, le=1, description="Filter by rating value"),
    with_comments_only: bool = Query(False, description="Only show ratings with comments"),
) -> Any:
    """Export all ratings as JSON or CSV (admin only).

    Returns all matching ratings (not paginated) in the requested format.
    """
    # Fetch all ratings without pagination
    items, _ = await rating_service.list_ratings(
        skip=0,
        limit=10000,  # Large limit for export
        rating_filter=rating_filter,
        with_comments_only=with_comments_only,
    )

    if format.lower() == "csv":
        # Generate CSV
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)
        # Header row
        writer.writerow([
            "ID", "Message ID", "Conversation ID", "User ID",
            "Rating", "Comment", "Message Content", "Message Role",
            "User Email", "User Name", "Created At", "Updated At"
        ])
        # Data rows
        for item in items:
            writer.writerow([
                str(item.id),
                str(item.message_id),
                str(item.conversation_id) if item.conversation_id else "",
                str(item.user_id),
                "Like" if item.rating == 1 else "Dislike",
                item.comment or "",
                item.message_content or "",
                item.message_role or "",
                item.user_email or "",
                item.user_name or "",
                item.created_at.isoformat() if item.created_at else "",
                item.updated_at.isoformat() if item.updated_at else "",
            ])

        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="ratings_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            }
        )
    else:
        # Return JSON
        return JSONResponse(
            content={
                "ratings": [item.model_dump(mode="json") for item in items],
                "total": len(items),
                "exported_at": datetime.now().isoformat()
            },
            headers={
                "Content-Disposition": f'attachment; filename="ratings_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
            }
        )


{%- elif cookiecutter.use_sqlite %}


@router.get("", response_model=MessageRatingList)
def list_ratings_admin(
    rating_service: MessageRatingSvc,
    admin_user: CurrentAdmin,
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
    admin_user: CurrentAdmin,
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
    admin_user: CurrentAdmin,
    format: str = Query("json", description="Export format: 'json' or 'csv'"),
    rating_filter: int | None = Query(None, ge=-1, le=1, description="Filter by rating value"),
    with_comments_only: bool = Query(False, description="Only show ratings with comments"),
) -> Any:
    """Export all ratings as JSON or CSV (admin only).

    Returns all matching ratings (not paginated) in the requested format.
    """
    # Fetch all ratings without pagination
    items, _ = rating_service.list_ratings(
        skip=0,
        limit=10000,  # Large limit for export
        rating_filter=rating_filter,
        with_comments_only=with_comments_only,
    )

    if format.lower() == "csv":
        # Generate CSV
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)
        # Header row
        writer.writerow([
            "ID", "Message ID", "Conversation ID", "User ID",
            "Rating", "Comment", "Message Content", "Message Role",
            "User Email", "User Name", "Created At", "Updated At"
        ])
        # Data rows
        for item in items:
            writer.writerow([
                str(item.id),
                str(item.message_id),
                str(item.conversation_id) if item.conversation_id else "",
                str(item.user_id),
                "Like" if item.rating == 1 else "Dislike",
                item.comment or "",
                item.message_content or "",
                item.message_role or "",
                item.user_email or "",
                item.user_name or "",
                item.created_at.isoformat() if item.created_at else "",
                item.updated_at.isoformat() if item.updated_at else "",
            ])

        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="ratings_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            }
        )
    else:
        # Return JSON
        return JSONResponse(
            content={
                "ratings": [item.model_dump(mode="json") for item in items],
                "total": len(items),
                "exported_at": datetime.now().isoformat()
            },
            headers={
                "Content-Disposition": f'attachment; filename="ratings_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
            }
        )


{%- elif cookiecutter.use_mongodb %}


@router.get("", response_model=MessageRatingList)
async def list_ratings_admin(
    rating_service: MessageRatingSvc,
    admin_user: CurrentAdmin,
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
    admin_user: CurrentAdmin,
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
    admin_user: CurrentAdmin,
    format: str = Query("json", description="Export format: 'json' or 'csv'"),
    rating_filter: int | None = Query(None, ge=-1, le=1, description="Filter by rating value"),
    with_comments_only: bool = Query(False, description="Only show ratings with comments"),
) -> Any:
    """Export all ratings as JSON or CSV (admin only).

    Returns all matching ratings (not paginated) in the requested format.
    """
    # Fetch all ratings without pagination
    items, _ = await rating_service.list_ratings(
        skip=0,
        limit=10000,  # Large limit for export
        rating_filter=rating_filter,
        with_comments_only=with_comments_only,
    )

    if format.lower() == "csv":
        # Generate CSV
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)
        # Header row
        writer.writerow([
            "ID", "Message ID", "Conversation ID", "User ID",
            "Rating", "Comment", "Message Content", "Message Role",
            "User Email", "User Name", "Created At", "Updated At"
        ])
        # Data rows
        for item in items:
            writer.writerow([
                str(item.id),
                str(item.message_id),
                str(item.conversation_id) if item.conversation_id else "",
                str(item.user_id),
                "Like" if item.rating == 1 else "Dislike",
                item.comment or "",
                item.message_content or "",
                item.message_role or "",
                item.user_email or "",
                item.user_name or "",
                item.created_at.isoformat() if item.created_at else "",
                item.updated_at.isoformat() if item.updated_at else "",
            ])

        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="ratings_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            }
        )
    else:
        # Return JSON
        return JSONResponse(
            content={
                "ratings": [item.model_dump(mode="json") for item in items],
                "total": len(items),
                "exported_at": datetime.now().isoformat()
            },
            headers={
                "Content-Disposition": f'attachment; filename="ratings_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
            }
        )


{%- endif %}
{%- else %}
# Admin ratings router - JWT not enabled
router = None  # type: ignore
{%- endif %}
