{%- if cookiecutter.enable_rate_limiting %}
"""Rate limit storage implementations — Redis sliding window and in-memory fallback."""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    allowed: bool
    current_count: int
    limit: int
    reset_at: datetime
    retry_after_seconds: int | None = None


class RateLimitStorage(Protocol):
    async def increment_and_check(
        self, key: str, limit: int, period_seconds: int
    ) -> RateLimitResult: ...


{%- if cookiecutter.enable_redis %}
from redis import asyncio as aioredis

from app.core.config import settings


class RedisSlidingWindowStorage:
    """Sliding window log algorithm backed by Redis sorted sets."""

    def __init__(self, redis) -> None:
        self.redis = redis

    async def increment_and_check(self, key: str, limit: int, period_seconds: int) -> RateLimitResult:
        now_ms = int(time.time() * 1000)
        window_start_ms = now_ms - (period_seconds * 1000)
        member = f"{now_ms}:{secrets.token_hex(4)}"

        try:
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start_ms)
            pipe.zadd(key, {member: now_ms})
            pipe.zcard(key)
            pipe.expire(key, period_seconds + 1)
            results = await pipe.execute()
            current_count: int = results[2]
        except Exception:
            # Fail open: a Redis outage must not take the whole API down with
            # it. The exception is logged in full because the alternative —
            # silently unlimited traffic — is worth paging about.
            logger.exception("rate_limit_redis_error")
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=limit,
                reset_at=datetime.now(UTC),
                retry_after_seconds=None,
            )

        if current_count > limit:
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_ts_ms = oldest[0][1]
                retry_after = max(1, int((oldest_ts_ms + period_seconds * 1000 - now_ms) / 1000))
            else:
                retry_after = period_seconds
            return RateLimitResult(
                allowed=False,
                current_count=current_count,
                limit=limit,
                reset_at=datetime.fromtimestamp((now_ms / 1000) + retry_after, UTC),
                retry_after_seconds=retry_after,
            )

        return RateLimitResult(
            allowed=True,
            current_count=current_count,
            limit=limit,
            reset_at=datetime.fromtimestamp((now_ms / 1000) + period_seconds, UTC),
            retry_after_seconds=None,
        )
{%- endif %}


class InMemoryStorage:
    """Single-instance in-memory sliding window. Safe only for dev / single-process deployments."""

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def increment_and_check(self, key: str, limit: int, period_seconds: int) -> RateLimitResult:
        async with self._lock:
            now = time.time()
            window_start = now - period_seconds
            self._windows[key] = [t for t in self._windows[key] if t > window_start]
            self._windows[key].append(now)
            current_count = len(self._windows[key])

            if current_count > limit:
                oldest = self._windows[key][0]
                retry_after = max(1, int(oldest + period_seconds - now))
                return RateLimitResult(
                    allowed=False,
                    current_count=current_count,
                    limit=limit,
                    reset_at=datetime.fromtimestamp(now + retry_after, UTC),
                    retry_after_seconds=retry_after,
                )

            return RateLimitResult(
                allowed=True,
                current_count=current_count,
                limit=limit,
                reset_at=datetime.fromtimestamp(now + period_seconds, UTC),
                retry_after_seconds=None,
            )


def get_storage() -> RateLimitStorage:
    """Pick the backing store once, at first use.

    Storage is resolved outside any request, so it cannot borrow the Redis
    client from lifespan state — it opens its own connection from
    ``REDIS_URL``. Connecting is lazy inside redis-py, so this does no I/O and
    cannot fail here; a Redis that is actually unreachable surfaces per-call in
    ``RedisSlidingWindowStorage.increment_and_check``, which fails open.
    """
{%- if cookiecutter.enable_redis %}
    return RedisSlidingWindowStorage(
        aioredis.from_url(  # type: ignore[no-untyped-call]
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
    )
{%- else %}
    # Counters live in this process only, so with N workers the effective limit
    # is N times the configured one. Enable Redis for a shared window.
    logger.warning("rate_limit_using_in_memory_storage")
    return InMemoryStorage()
{%- endif %}

{%- else %}
"""Rate limit storage — not enabled."""
{%- endif %}
