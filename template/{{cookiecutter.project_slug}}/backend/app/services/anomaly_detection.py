{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system and cookiecutter.enable_usage_anomaly_detection %}
"""Usage anomaly detection — spike detection against rolling average."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

{%- if cookiecutter.enable_slack_alerts %}
import httpx

from app.core.config import settings
{%- endif %}
from app.db.models.credit_transaction import UsageEvent

logger = logging.getLogger(__name__)

# Credits-per-hour spike multiplier before alerting
_SPIKE_MULTIPLIER = 3.0
_ROLLING_HOURS = 24
_MIN_BASELINE = 10  # ignore orgs with < 10 credits/h baseline


async def detect_spike(db: AsyncSession, organization_id: uuid.UUID) -> dict | None:
    """Return spike info dict if current-hour usage > _SPIKE_MULTIPLIER * rolling avg, else None."""
    now = datetime.now(UTC)
    one_hour_ago = now - timedelta(hours=1)
    rolling_start = now - timedelta(hours=_ROLLING_HOURS)

    result = await db.execute(
        select(func.sum(UsageEvent.credits_charged)).where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.created_at >= one_hour_ago,
        )
    )
    current_hour = float(result.scalar() or 0)

    # Rolling hourly average (exclude current hour)
    result = await db.execute(
        select(func.sum(UsageEvent.credits_charged)).where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.created_at >= rolling_start,
            UsageEvent.created_at < one_hour_ago,
        )
    )
    rolling_total = float(result.scalar() or 0)
    rolling_avg = rolling_total / (_ROLLING_HOURS - 1) if _ROLLING_HOURS > 1 else rolling_total

    if rolling_avg < _MIN_BASELINE:
        return None

    if current_hour > rolling_avg * _SPIKE_MULTIPLIER:
        return {
            "organization_id": str(organization_id),
            "current_hour_credits": current_hour,
            "rolling_avg_credits": rolling_avg,
            "spike_ratio": round(current_hour / rolling_avg, 2),
            "detected_at": now.isoformat(),
        }

    return None


async def send_slack_alert(spike: dict) -> None:
{%- if cookiecutter.enable_slack_alerts %}
    webhook_url = getattr(settings, "SLACK_ANOMALY_WEBHOOK_URL", None)
    if not webhook_url:
        return
    msg = (
        f":warning: *Usage spike detected* for org `{spike['organization_id']}`\n"
        f"Current hour: *{spike['current_hour_credits']:.0f} credits*  "
        f"(rolling avg: {spike['rolling_avg_credits']:.0f}, "
        f"ratio: *{spike['spike_ratio']}x*)\n"
        f"Detected at: {spike['detected_at']}"
    )
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(webhook_url, json={"text": msg})
    except Exception:
        logger.exception("slack_anomaly_alert_failed")
{%- else %}
    logger.warning("usage_spike_detected", extra=spike)
{%- endif %}

{%- else %}
"""Anomaly detection — not enabled."""
{%- endif %}
