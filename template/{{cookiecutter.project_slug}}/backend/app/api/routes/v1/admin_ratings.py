{%- if cookiecutter.use_jwt %}
from typing import Any, Literal

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.deps import CurrentAdmin, MessageRatingSvc
from app.schemas.message_rating import MessageRatingList, RatingSummary

router = APIRouter()


@router.get("", response_model=MessageRatingList)
async def list_ratings_admin(
    rating_service: MessageRatingSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    rating_filter: int | None = Query(None, ge=-1, le=1, description="Filter by rating value"),
    with_comments_only: bool = Query(False, description="Only show ratings with comments"),
) -> Any:
    """List all ratings with filtering (admin only)."""
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
    """Get aggregated rating statistics (admin only)."""
    return await rating_service.get_summary(days=days)


@router.get("/export", response_model=None)
async def export_ratings(
    rating_service: MessageRatingSvc,
    _: CurrentAdmin,
    export_format: Literal["json", "csv"] = Query("json", description="Export format"),
    rating_filter: int | None = Query(None, ge=-1, le=1, description="Filter by rating value"),
    with_comments_only: bool = Query(False, description="Only show ratings with comments"),
) -> Any:
    """Export all ratings as JSON or CSV (admin only).

    CSV is streamed row-by-row; JSON collects into a single document.
    """
    result = await rating_service.export_ratings(
        export_format=export_format,
        rating_filter=rating_filter,
        with_comments_only=with_comments_only,
    )
    if result.media_type == "text/csv":
        return StreamingResponse(
            result.payload,
            media_type="text/csv",
            headers={"Content-Disposition": result.content_disposition},
        )
    return JSONResponse(
        content=result.payload,
        headers={"Content-Disposition": result.content_disposition},
    )


{%- else %}
# Admin ratings router - JWT not enabled
router = APIRouter()
{%- endif %}
