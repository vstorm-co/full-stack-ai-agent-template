{%- if cookiecutter.enable_rate_limiting %}
"""Rate limiting configuration using slowapi.

Default rate limit: {{ cookiecutter.rate_limit_requests }} requests per {{ cookiecutter.rate_limit_period }} seconds.
Override with RATE_LIMIT_REQUESTS and RATE_LIMIT_PERIOD environment variables.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def get_default_rate_limit() -> str:
    """Get default rate limit string from settings.

    Returns a rate limit string like "100/minute" or "60/second".
    """
    requests = settings.RATE_LIMIT_REQUESTS
    period = settings.RATE_LIMIT_PERIOD

    period_map = {
        60: "minute",
        3600: "hour",
        86400: "day",
    }

    if period in period_map:
        return f"{requests}/{period_map[period]}"
    return f"{requests}/{period} seconds"


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[get_default_rate_limit()],
)

def rate_limit_low(limit: str = "10/minute"):
    """Low rate limit for expensive operations."""
    return limiter.limit(limit)


def rate_limit_medium(limit: str = "30/minute"):
    """Medium rate limit for standard operations."""
    return limiter.limit(limit)


def rate_limit_high(limit: str = "100/minute"):
    """High rate limit for lightweight operations."""
    return limiter.limit(limit)
{%- else %}
"""Rate limiting - not configured."""
{%- endif %}
