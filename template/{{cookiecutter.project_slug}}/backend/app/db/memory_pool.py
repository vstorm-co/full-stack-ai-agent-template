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
from pydantic_ai import ModelRetry
from pydantic_ai_harness.memory import (
    MemoryFile,
    MemoryMutation,
    MemoryOperation,
    MemoryStore,
    PostgresMemoryStore,
)
from sqlalchemy.engine import make_url

from app.core.config import settings

logger = logging.getLogger(__name__)

_RETRY_COOLDOWN_SECS = 10.0
# asyncpg waits 60s for a connection by default; a database that drops packets
# would hold every request waiting on the lock below for that long.
_CONNECT_TIMEOUT_SECS = 5.0

# Most files one notebook may hold. Each is capped in size by the harness, but
# nothing else bounds how many the agent - or the API - can create.
MAX_MEMORY_FILES = 100


class MemoryQuotaExceededError(ModelRetry):
    """A new file would take a notebook past ``MAX_MEMORY_FILES``.

    A ``ModelRetry`` so the agent's write tool hands the model a message it can
    act on - consolidate or delete notes - instead of failing the run.
    """


class CappedMemoryStore:
    """A ``MemoryStore`` that refuses to create a file past ``max_files`` per notebook.

    A notebook is the directory a file lives in - one user's scope. The count
    and the write are not atomic, so concurrent creates may overshoot by a few;
    it bounds growth rather than enforcing an exact quota.
    """

    def __init__(self, inner: MemoryStore, *, max_files: int) -> None:
        self._inner = inner
        self._max_files = max_files

    async def read(self, path: str, *, max_chars: int) -> MemoryFile | None:
        return await self._inner.read(path, max_chars=max_chars)

    async def get_operation(self, operation: MemoryOperation) -> MemoryMutation | None:
        return await self._inner.get_operation(operation)

    async def write(
        self,
        path: str,
        content: str,
        *,
        expected_version: str | None,
        operation: MemoryOperation | None = None,
    ) -> MemoryMutation:
        if expected_version is None:
            notebook = path.rsplit("/", 1)[0] + "/"
            existing = await self._inner.list_paths(notebook, limit=self._max_files + 1)
            if path not in existing and len(existing) >= self._max_files:
                raise MemoryQuotaExceededError(
                    f"This notebook already holds {self._max_files} files, the most it "
                    "may. Merge related notes into an existing file, or delete ones that "
                    "are no longer needed, before creating another."
                )
        return await self._inner.write(
            path, content, expected_version=expected_version, operation=operation
        )

    async def delete(
        self,
        path: str,
        *,
        expected_version: str | None,
        operation: MemoryOperation | None = None,
    ) -> MemoryMutation:
        return await self._inner.delete(path, expected_version=expected_version, operation=operation)

    async def list_paths(self, prefix: str = "", *, limit: int) -> list[str]:
        return await self._inner.list_paths(prefix, limit=limit)


_memory_pool: asyncpg.Pool | None = None
_memory_store: MemoryStore | None = None
_init_lock = asyncio.Lock()
_last_attempt_at: float | None = None


async def _connect() -> None:
    """Create the pool and store; on failure leave both ``None``. Call under the lock."""
    global _memory_pool, _memory_store, _last_attempt_at
    # asyncpg accepts no SQLAlchemy driver suffix, so strip it from the sync URL.
    dsn = make_url(settings.DATABASE_URL_SYNC).set(drivername="postgresql")
    pool: asyncpg.Pool | None = None
    try:
        pool = await asyncpg.create_pool(
            dsn.render_as_string(hide_password=False),
            min_size=1,
            max_size=settings.DB_POOL_SIZE,
            timeout=_CONNECT_TIMEOUT_SECS,
        )
        _memory_store = CappedMemoryStore(PostgresMemoryStore(pool), max_files=MAX_MEMORY_FILES)
        _memory_pool = pool
        logger.info("Agent memory pool connected")
    except Exception as e:
        if pool is not None:
            await pool.close()
        _memory_pool = None
        _memory_store = None
        logger.warning("Memory pool unavailable, agent memory is disabled: %s", e)
    finally:
        # Stamped when the attempt ends: a connect that hangs longer than the
        # cooldown must not let the next caller start another straight away.
        _last_attempt_at = time.monotonic()


async def init_memory_pool() -> asyncpg.Pool | None:
    """Create the shared asyncpg pool and store at startup; the pool or ``None``."""
    async with _init_lock:
        if _memory_pool is None:
            await _connect()
    return _memory_pool


async def close_memory_pool() -> None:
    """Close the shared asyncpg pool on shutdown."""
    global _memory_pool, _memory_store, _last_attempt_at
    if _memory_pool is not None:
        await _memory_pool.close()
        _memory_pool = None
    _memory_store = None
    _last_attempt_at = None


def _cooling_down() -> bool:
    return (
        _last_attempt_at is not None
        and time.monotonic() - _last_attempt_at < _RETRY_COOLDOWN_SECS
    )


async def get_memory_store() -> MemoryStore | None:
    """Return the shared memory store, or ``None`` when unavailable.

    Requests that queue on the lock while one attempt fails do not each try
    again: the cooldown is checked under the lock too.
    """
    if not settings.ENABLE_MEMORY:
        return None
    if _memory_store is not None:
        return _memory_store
    if _cooling_down():
        return None
    async with _init_lock:
        if _memory_store is None and not _cooling_down():
            await _connect()
    return _memory_store
