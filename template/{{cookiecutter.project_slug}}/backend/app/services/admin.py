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

{%- if cookiecutter.use_ai %}
from app.db.models.conversation import Conversation, Message
{%- endif %}
from app.db.models.user import User
{%- if cookiecutter.enable_session_management %}
from app.db.models.session import Session as UserSession
{%- endif %}
{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
from app.db.models.credit_transaction import CreditTransaction
{%- endif %}
{%- if cookiecutter.enable_billing %}
from app.db.models.plan import Price
from app.db.models.stripe_event import StripeEvent
from app.db.models.subscription import Subscription
{%- endif %}

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
        total_users = (await self.db.execute(select(func.count(User.id)))).scalar_one()

        # Active in last 24h via session.last_used_at — best-effort, returns 0
        # when session_management isn't enabled in this deployment.
        active_24h: int = 0
{%- if cookiecutter.enable_session_management %}
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        try:
            active_24h = int(
                (
                    await self.db.execute(
                        select(func.count(func.distinct(UserSession.user_id))).where(
                            UserSession.last_used_at >= cutoff
                        )
                    )
                ).scalar_one()
            )
        except Exception:  # noqa: BLE001
            logger.exception("admin_stats_active_users_query_failed")
{%- endif %}

        # Conversations + messages totals — 0 when AI/chat is disabled
{%- if cookiecutter.use_ai %}
        total_conversations = (
            await self.db.execute(select(func.count(Conversation.id)))
        ).scalar_one()
        total_messages = (
            await self.db.execute(select(func.count(Message.id)))
        ).scalar_one()
{%- else %}
        total_conversations = 0
        total_messages = 0
{%- endif %}

        # Billing — best-effort, only if tables exist + billing on
        credits_30d = 0
        mrr_cents = 0
{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
        try:
            since = datetime.now(UTC) - timedelta(days=30)
            credits_30d_raw = (
                await self.db.execute(
                    select(func.coalesce(func.sum(-CreditTransaction.delta), 0)).where(
                        CreditTransaction.created_at >= since,
                        CreditTransaction.delta < 0,
                    )
                )
            ).scalar_one()
            credits_30d = int(credits_30d_raw)
        except Exception:  # noqa: BLE001
            logger.exception("admin_stats_credits_query_failed")
{%- endif %}
{%- if cookiecutter.enable_billing %}
        try:
            # Sum active subscription unit_amount * quantity, monthly equiv.
            stmt = (
                select(
                    func.coalesce(
                        func.sum(Price.amount_cents * Subscription.seats_quantity), 0
                    )
                )
                .select_from(Subscription)
                .join(Price, Price.id == Subscription.price_id)
                .where(Subscription.status.in_(("active", "trialing")))
                .where(Price.interval == "month")
            )
            mrr_cents = int((await self.db.execute(stmt)).scalar_one() or 0)
        except Exception:  # noqa: BLE001
            logger.exception("admin_stats_mrr_query_failed")
{%- endif %}

        return {
            "total_users": int(total_users),
            "active_users_24h": int(active_24h),
            "total_conversations": int(total_conversations),
            "total_messages": int(total_messages),
            "credits_charged_30d": credits_30d,
            "mrr_cents": mrr_cents,
        }

    async def list_stripe_events(
        self, *, skip: int = 0, limit: int = 50
    ) -> tuple[list[Any], int]:
        """Page through the Stripe webhook idempotency log.

        Returns ([], 0) when billing is disabled in this deployment.
        """
{%- if cookiecutter.enable_billing %}
        try:
            total = (await self.db.execute(select(func.count(StripeEvent.id)))).scalar_one()
            rows = (
                await self.db.execute(
                    select(StripeEvent)
                    .order_by(StripeEvent.created_at.desc())
                    .offset(skip)
                    .limit(limit)
                )
            ).scalars().all()
            return list(rows), int(total)
        except Exception:  # noqa: BLE001
            logger.exception("admin_stats_stripe_event_query_failed")
            return [], 0
{%- else %}
        return [], 0
{%- endif %}
