"""Shared asyncpg pool for the deep-research TODO planner.

The ``pydantic-ai-todo`` async storage backend speaks raw asyncpg (DSN or pool),
not SQLAlchemy, and only its async backends emit the lifecycle events that drive
the live research checklist. One process-wide pool is created in the app lifespan
against the same Postgres as the ORM and handed to a per-conversation
``AsyncPostgresStorage`` keyed by ``session_id``. ``None`` when the pool could not
be created, in which case callers fall back to in-memory storage.
"""

import logging

import asyncpg

from app.core.config import settings

logger = logging.getLogger(__name__)

_todo_pool: asyncpg.Pool | None = None


async def init_todo_pool() -> asyncpg.Pool | None:
    """Create the shared asyncpg pool, returning ``None`` on failure.

    asyncpg rejects the ``+asyncpg`` driver suffix, so ``DATABASE_URL_SYNC``
    (plain ``postgresql://``) is used, which it parses directly.
    """
    global _todo_pool
    if _todo_pool is not None:
        return _todo_pool
    try:
        _todo_pool = await asyncpg.create_pool(
            settings.DATABASE_URL_SYNC, min_size=1, max_size=settings.DB_POOL_SIZE
        )
        logger.info("Deep-research TODO pool connected")
    except Exception as e:
        _todo_pool = None
        logger.warning("TODO pool unavailable, deep research will use memory storage: %s", e)
    return _todo_pool


async def close_todo_pool() -> None:
    """Close the shared asyncpg pool on shutdown."""
    global _todo_pool
    if _todo_pool is not None:
        await _todo_pool.close()
        _todo_pool = None


def get_todo_pool() -> asyncpg.Pool | None:
    """Return the shared asyncpg pool, or ``None`` when it could not be created."""
    return _todo_pool
