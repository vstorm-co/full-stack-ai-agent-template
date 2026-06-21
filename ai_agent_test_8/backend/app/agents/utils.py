"""Shared agent utilities."""

from datetime import UTC, datetime


def get_current_datetime() -> dict[str, str]:
    """Return the current UTC date and time."""
    now = datetime.now(UTC)
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
    }
