"""Admin-only schemas — workspace stats + Stripe event log views."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class AdminStats(BaseSchema):
    """Workspace-wide aggregate metrics shown on /admin overview."""

    total_users: int
    active_users_24h: int
    total_conversations: int
    total_messages: int
    credits_charged_30d: int = Field(
        default=0,
        description="Total credits debited in the last 30 days. 0 when billing disabled.",
    )
    mrr_cents: int = Field(
        default=0,
        description="Monthly recurring revenue in cents. 0 when billing disabled.",
    )


class StripeEventRead(BaseSchema, TimestampSchema):
    id: UUID
    stripe_event_id: str
    event_type: str
    status: str
    error: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class StripeEventList(BaseSchema):
    items: list[StripeEventRead]
    total: int
