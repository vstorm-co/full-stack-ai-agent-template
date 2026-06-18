"""External service clients.

This module contains thin wrappers around external services like Redis.
"""

from app.clients.redis import RedisClient

__all__ = [
    "RedisClient",
]
