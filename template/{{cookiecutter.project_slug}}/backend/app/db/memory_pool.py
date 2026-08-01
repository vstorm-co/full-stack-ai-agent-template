"""Shared asyncpg pool and store for persistent agent memory.

The pydantic-ai-harness ``PostgresMemoryStore`` speaks a raw asyncpg-compatible
pool, not SQLAlchemy. One process-wide pool is created in the app lifespan
against the same Postgres as the ORM; the store lazily creates and migrates its
own ``agent_memory*`` tables on first use (advisory-lock guarded), so they have
no Alembic migration. ``None`` when the pool could not be created — there is
deliberately no in-memory fallback, which would fake persistence: without the
store the memory capability and the ``/me/memory`` API are simply unavailable.

Startup is not the only chance to connect. A database that is unreachable while
the process boots must not leave memory dead until the next restart, so
``get_memory_store`` retries the connection, at most once every
``_RETRY_COOLDOWN_SECS`` so a down database can't be hammered per request.
"""

import asyncio
import logging
import time

import asyncpg
from pydantic_ai_harness.memory import PostgresMemoryStore

from app.core.config import settings

logger = logging.getLogger(__name__)

_RETRY_COOLDOWN_SECS = 10.0

_memory_pool: asyncpg.Pool | None = None
_memory_store: PostgresMemoryStore | None = None
_init_lock = asyncio.Lock()
_last_attempt_at: float | None = None


async def init_memory_pool() -> asyncpg.Pool | None:
    """Create the shared asyncpg pool and store, returning the pool or ``None``.

    asyncpg rejects the ``+asyncpg`` driver suffix, so ``DATABASE_URL_SYNC``
    (plain ``postgresql://``) is used, which it parses directly.
    """
    global _memory_pool, _memory_store, _last_attempt_at
    if _memory_pool is not None:
        return _memory_pool
    async with _init_lock:
        if _memory_pool is not None:
            return _memory_pool
        _last_attempt_at = time.monotonic()
        pool: asyncpg.Pool | None = None
        try:
            pool = await asyncpg.create_pool(
                settings.DATABASE_URL_SYNC, min_size=1, max_size=settings.DB_POOL_SIZE
            )
            _memory_store = PostgresMemoryStore(pool)
            _memory_pool = pool
            logger.info("Agent memory pool connected")
        except Exception as e:
            if pool is not None:
                await pool.close()
            _memory_pool = None
            _memory_store = None
            logger.warning("Memory pool unavailable, agent memory is disabled: %s", e)
        return _memory_pool


async def close_memory_pool() -> None:
    """Close the shared asyncpg pool on shutdown."""
    global _memory_pool, _memory_store, _last_attempt_at
    if _memory_pool is not None:
        await _memory_pool.close()
        _memory_pool = None
    _memory_store = None
    _last_attempt_at = None


async def get_memory_store() -> PostgresMemoryStore | None:
    """Return the shared memory store, or ``None`` when unavailable."""
    if not settings.ENABLE_MEMORY:
        return None
    if _memory_store is not None:
        return _memory_store
    if _last_attempt_at is not None and time.monotonic() - _last_attempt_at < _RETRY_COOLDOWN_SECS:
        return None
    await init_memory_pool()
    return _memory_store
