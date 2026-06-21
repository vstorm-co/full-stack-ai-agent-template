{%- if cookiecutter.enable_teams %}
"""Audit log helpers for recording privileged actions."""

import logging
from typing import Any
from uuid import UUID

from app.db.models.audit_log import AppAdminAuditLog

logger = logging.getLogger(__name__)



async def record_audit(
    db,
    *,
    actor_user_id: UUID,
    action: str,
    organization_id: UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Persist an audit log entry. Failures are logged but do not raise."""
    try:
        entry = AppAdminAuditLog(
            actor_user_id=actor_user_id,
            action=action,
            organization_id=organization_id,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            details=details,
            ip_address=ip_address,
        )
        db.add(entry)
        await db.flush()
    except Exception:
        logger.exception("Failed to write audit log for action=%s actor=%s", action, actor_user_id)

{%- else %}
"""Audit log — not configured (enable_teams=false)."""
{%- endif %}
