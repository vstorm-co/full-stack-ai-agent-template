"""RateLimitRule dataclass and category definitions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitRule:
    """Defines limits per user, per org, and per IP for a given category."""

    per_user: int | None = None
    period_seconds: int = 60
    per_org: int | None = None
    org_period_seconds: int = 60
    per_ip: int | None = None
    ip_period_seconds: int = 60

    @classmethod
    def unlimited(cls) -> "RateLimitRule":
        return cls()

    def is_unlimited(self) -> bool:
        return self.per_user is None and self.per_org is None and self.per_ip is None

    @classmethod
    def from_dict(cls, data: dict) -> "RateLimitRule":
        return cls(
            per_user=data.get("per_user"),
            period_seconds=data.get("period_seconds", 60),
            per_org=data.get("per_org"),
            org_period_seconds=data.get("org_period_seconds", 60),
            per_ip=data.get("per_ip"),
            ip_period_seconds=data.get("ip_period_seconds", 60),
        )


# Category constants
class RateLimitCategory:
    AGENT_INVOCATION = "agent_invocation"
    RAG_UPLOAD = "rag_upload"
    AUTH = "auth"
    READ_API = "read_api"
    WEBHOOK = "webhook"


# Default fallback limits (used when plan features don't define limits)
DEFAULT_RATE_LIMITS: dict[str, RateLimitRule] = {
    RateLimitCategory.AGENT_INVOCATION: RateLimitRule(per_user=10, period_seconds=86400),
    RateLimitCategory.RAG_UPLOAD: RateLimitRule(per_user=5, period_seconds=86400),
    RateLimitCategory.AUTH: RateLimitRule(per_ip=5, ip_period_seconds=900),
    RateLimitCategory.READ_API: RateLimitRule(per_user=300, period_seconds=60),
}
