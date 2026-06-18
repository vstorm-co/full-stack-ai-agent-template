"""Date and time utilities for agents."""

from datetime import UTC, datetime


def get_current_datetime() -> dict[str, str]:
    """Get the current date and time (UTC)."""
    now = datetime.now(UTC)
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
    }
