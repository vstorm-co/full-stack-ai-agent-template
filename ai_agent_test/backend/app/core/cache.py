"""Caching configuration using fastapi-cache2."""

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

from app.clients.redis import RedisClient


def setup_cache(redis: RedisClient) -> None:
    """Initialize FastAPI cache with Redis backend.

    Uses the shared Redis client from lifespan state.
    """
    FastAPICache.init(RedisBackend(redis.raw), prefix="ai_agent_test:cache:")
