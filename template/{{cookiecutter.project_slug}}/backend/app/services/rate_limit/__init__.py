{%- if cookiecutter.enable_rate_limiting %}
"""Per-plan, per-category sliding window rate limiting."""

from app.services.rate_limit.rules import DEFAULT_RATE_LIMITS, RateLimitCategory, RateLimitRule
from app.services.rate_limit.service import (
    check_rate_limit,
    client_ip,
    make_anonymous_rate_limit_dep,
    make_rate_limit_dep,
)

__all__ = [
    "DEFAULT_RATE_LIMITS",
    "RateLimitCategory",
    "RateLimitRule",
    "check_rate_limit",
    "client_ip",
    "make_anonymous_rate_limit_dep",
    "make_rate_limit_dep",
]
{%- else %}
"""Rate limiting — not enabled."""
{%- endif %}
