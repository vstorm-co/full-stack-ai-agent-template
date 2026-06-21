"""Health check utilities."""

from datetime import UTC, datetime
from typing import Any

from app.core.config import settings


def build_health_response(
    status: str,
    checks: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        "service": settings.PROJECT_NAME,
    }
    if checks is not None:
        response["checks"] = checks
    if details is not None:
        response["details"] = details
    return response
