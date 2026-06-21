{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
"""UsageService — record AI usage events and debit credits."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import app.repositories.usage_event as usage_repo
from app.core.config import settings
from app.db.models.credit_transaction import CreditTransactionType
from app.services.billing.credit_service import CreditService
from app.services.billing.pricing import usage_to_credits

logger = logging.getLogger(__name__)


class UsageService:
    """Record a usage event, debit the corresponding credits, and prune old data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._credit_svc = CreditService(db)

    async def cleanup_old_events(self, *, retention_days: int) -> int:
        """Delete usage events older than ``retention_days`` and refresh the daily matview.

        The matview is refreshed concurrently so reads are not blocked. Returns the
        number of usage-event rows deleted.
        """
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        deleted = await usage_repo.delete_older_than(self.db, cutoff)
        await self.refresh_daily_matview()
        return deleted

    async def refresh_daily_matview(self) -> None:
        """Refresh ``mv_usage_daily`` so the dashboard shows recent activity.

        Falls back to a non-concurrent refresh if the view has never been populated
        (CONCURRENTLY requires the view to have data + a unique index).
        """
        try:
            await self.db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_usage_daily"))
        except Exception:
            await self.db.execute(text("REFRESH MATERIALIZED VIEW mv_usage_daily"))

    async def record(
        self,
        *,
        organization_id: uuid.UUID,
        model: str,
        provider: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        ai_framework: str = "",
        actor_user_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
    ) -> int:
        """Persist usage event, compute credits, debit org, return credits charged."""
        credits = usage_to_credits(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            credits_per_usd=settings.CREDITS_PER_USD,
        )

        event = await usage_repo.create(
            self.db,
            organization_id=organization_id,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            credits_charged=credits,
            ai_framework=ai_framework,
            actor_user_id=actor_user_id,
            conversation_id=conversation_id,
        )

        if credits > 0:
            try:
                await self._credit_svc.debit(
                    organization_id=organization_id,
                    actor_user_id=actor_user_id,
                    amount=credits,
                    type=CreditTransactionType.DEBIT_AGENT,
                    description=f"{model} — {input_tokens + output_tokens} tokens",
                    usage_event_id=event.id,
                )
            except Exception:
                logger.exception("usage_credit_debit_failed", extra={"org_id": str(organization_id)})

        return credits

{%- else %}
"""UsageService — not enabled (enable_credits_system=false)."""
{%- endif %}
