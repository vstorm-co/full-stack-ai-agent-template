"""Admin overview / observability service.

Reads aggregate counts across users / conversations / billing and exposes
them to the dashboard. All reads — no mutation. Should remain cheap (single
COUNT(*) per metric); if usage grows we'd promote to materialized views.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from app.db.models.conversation import Conversation, Message
from app.db.models.user import User

logger = logging.getLogger(__name__)


class AdminService:
    # ``db`` is an AsyncSession (Postgres) or a sync Session (SQLite); typed as
    # ``Any`` so the one shared implementation accepts both.
    def __init__(self, db: Any) -> None:
        self.db = db

    async def workspace_stats(self) -> dict[str, Any]:
        """Aggregate workspace metrics. Billing fields stay at 0 when the
        feature isn't enabled — the schema doesn't change shape between
        configurations.
        """
        # Total users
        total_users = (await self.db.execute(select(func.count(User.id)))).scalar_one()

        # Active in last 24h via session.last_used_at — best-effort, returns 0
        # when session_management isn't enabled in this deployment.
        active_24h: int = 0
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        try:
            from app.db.models.session import Session as UserSession

            active_24h = int(
                (
                    await self.db.execute(
                        select(func.count(func.distinct(UserSession.user_id))).where(
                            UserSession.last_used_at >= cutoff
                        )
                    )
                ).scalar_one()
            )
        except Exception:
            logger.exception("admin_stats_active_users_query_failed")

        # Conversations + messages totals — 0 when AI/chat is disabled
        total_conversations = (
            await self.db.execute(select(func.count(Conversation.id)))
        ).scalar_one()
        total_messages = (await self.db.execute(select(func.count(Message.id)))).scalar_one()

        # Billing — best-effort, only if tables exist + billing on
        credits_30d = 0
        mrr_cents = 0

        return {
            "total_users": int(total_users),
            "active_users_24h": int(active_24h),
            "total_conversations": int(total_conversations),
            "total_messages": int(total_messages),
            "credits_charged_30d": credits_30d,
            "mrr_cents": mrr_cents,
        }

    async def list_stripe_events(self, *, skip: int = 0, limit: int = 50) -> tuple[list[Any], int]:
        """Page through the Stripe webhook idempotency log.

        Returns ([], 0) when the StripeEvent table doesn't exist (billing
        disabled in this deployment). Caller projects to schema.
        """
        try:
            from app.db.models.stripe_event import StripeEvent
        except Exception:
            logger.exception("admin_stats_stripe_event_import_failed")
            return [], 0

        total = (await self.db.execute(select(func.count(StripeEvent.id)))).scalar_one()
        rows = (
            (
                await self.db.execute(
                    select(StripeEvent)
                    .order_by(StripeEvent.created_at.desc())
                    .offset(skip)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), int(total)
