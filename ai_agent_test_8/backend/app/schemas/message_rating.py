"""Message rating schemas for feedback API."""

import re
from enum import IntEnum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema, TimestampSchema


class RatingValue(IntEnum):
    """Rating values for message feedback."""

    LIKE = 1
    DISLIKE = -1


def _sanitize_comment(comment: str | None) -> str | None:
    """Normalize user comment for storage.

    Strips whitespace and removes dangerous control characters. HTML escaping
    is intentionally NOT done here — the comment is stored raw and escaped
    at render time (React does this automatically; CSV export escapes
    separately against formula injection).
    """
    if not comment:
        return None

    comment = comment.strip()
    if not comment:
        return None

    # Strip null bytes and control chars (keep \t, \n, \r)
    comment = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", comment)

    return comment[:2000]


class MessageRatingBase(BaseSchema):
    """Base rating schema."""

    rating: RatingValue = Field(..., description="1 for like, -1 for dislike")
    comment: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional feedback comment",
    )

    @field_validator("comment", mode="before")
    @classmethod
    def sanitize_comment(cls, v: str | None) -> str | None:
        """Sanitize comment input."""
        return _sanitize_comment(v)


class MessageRatingCreate(MessageRatingBase):
    """Schema for creating/updating a rating."""

    pass


class MessageRatingRead(MessageRatingBase, TimestampSchema):
    """Schema for reading a rating."""

    id: UUID
    message_id: UUID
    user_id: UUID


class MessageRatingWithDetails(MessageRatingRead):
    """Rating with related message and user info."""

    message_content: str | None = None
    message_role: str | None = None
    conversation_id: UUID | None = None
    user_email: str | None = None
    user_name: str | None = None


class MessageRatingList(BaseSchema):
    """Schema for listing ratings."""

    items: list[MessageRatingWithDetails]
    total: int


class RatingSummary(BaseSchema):
    """Aggregated rating statistics."""

    total_ratings: int
    like_count: int
    dislike_count: int
    average_rating: float  # -1.0 to 1.0
    with_comments: int
    ratings_by_day: list[dict[str, Any]]  # [{date: "2026-03-25", likes: 10, dislikes: 2}]
