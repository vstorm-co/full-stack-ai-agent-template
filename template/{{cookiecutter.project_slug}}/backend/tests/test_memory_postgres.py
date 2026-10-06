{%- if cookiecutter.enable_memory %}
"""Agent memory against a real PostgreSQL - skipped when none is reachable.

The other memory tests run on the harness ``InMemoryStore``; these cover what
only the database exercises: the asyncpg pool and its DSN, the store's own
tables, the file cap, forgetting a user, and Alembic leaving those tables alone.
"""

import uuid

import asyncpg
import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from pydantic_ai_harness.memory import PostgresMemoryStore
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.db import memory_pool
{%- if cookiecutter.use_sqlmodel %}
from sqlmodel import SQLModel
{%- else %}
from app.db.base import Base
{%- endif %}
from app.db.memory_pool import CappedMemoryStore, MemoryQuotaExceededError
from app.db.migration_filters import EXTERNALLY_MANAGED_TABLES, include_name
from app.services.user_memory import forget_user_memory

pytestmark = pytest.mark.anyio


def _dsn() -> str:
    return make_url(settings.DATABASE_URL_SYNC).set(drivername="postgresql").render_as_string(
        hide_password=False
    )


async def _postgres_reachable() -> bool:
    try:
        connection = await asyncpg.connect(_dsn(), timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    await connection.close()
    return True


@pytest.fixture
async def store(monkeypatch: pytest.MonkeyPatch):
    if not await _postgres_reachable():
        pytest.skip("No live PostgreSQL for the memory store")
    monkeypatch.setattr(settings, "ENABLE_MEMORY", True)
    await memory_pool.close_memory_pool()
    await memory_pool.init_memory_pool()
    store = await memory_pool.get_memory_store()
    assert store is not None, "the pool could not connect - check the DSN"
    yield store
    await memory_pool.close_memory_pool()


async def test_the_pool_connects_with_the_sync_url(store) -> None:
    """``DATABASE_URL_SYNC`` names a SQLAlchemy driver that asyncpg rejects."""
    assert "+" in make_url(settings.DATABASE_URL_SYNC).drivername
    path = f"user-{uuid.uuid4()}/main/MEMORY.md"

    written = await store.write(path, "likes tea", expected_version=None)
    read = await store.read(path, max_chars=100)

    assert read is not None and read.content == "likes tea"
    await store.delete(path, expected_version=written.version)


async def test_a_full_notebook_refuses_another_file(store) -> None:
    pool = await asyncpg.create_pool(_dsn(), min_size=1, max_size=2)
    try:
        capped = CappedMemoryStore(PostgresMemoryStore(pool), max_files=2)
        scope = f"user-{uuid.uuid4()}/main/"
        await capped.write(f"{scope}a.md", "a", expected_version=None)
        b = await capped.write(f"{scope}b.md", "b", expected_version=None)

        with pytest.raises(MemoryQuotaExceededError):
            await capped.write(f"{scope}c.md", "c", expected_version=None)
        # Updating a file that exists is not a new file.
        await capped.write(f"{scope}b.md", "b2", expected_version=b.version)

        for name in ("a.md", "b.md"):
            file = await capped.read(f"{scope}{name}", max_chars=10)
            assert file is not None
            await capped.delete(f"{scope}{name}", expected_version=file.version)
    finally:
        await pool.close()


async def test_forgetting_a_user_removes_every_scope_and_nothing_else(store) -> None:
    user, other = uuid.uuid4(), uuid.uuid4()
    mine = [f"user-{user}/main/MEMORY.md", f"user-{user}/org-{uuid.uuid4()}/main/notes.md"]
    theirs = f"user-{other}/main/MEMORY.md"
    for path in [*mine, theirs]:
        await store.write(path, "x", expected_version=None)

    removed = await forget_user_memory(user)

    assert removed == 2
    assert await store.list_paths(f"user-{user}/", limit=10) == []
    kept = await store.read(theirs, max_chars=10)
    assert kept is not None
    await store.delete(theirs, expected_version=kept.version)


async def test_autogenerate_leaves_the_memory_tables_alone(store) -> None:
    """The store creates its tables itself; no migration may drop them."""
    await store.list_paths("", limit=1)  # makes sure the tables exist
    engine = create_engine(settings.DATABASE_URL_SYNC)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection, opts={"include_name": include_name}
            )
            diff = compare_metadata(context, {% if cookiecutter.use_sqlmodel %}SQLModel{% else %}Base{% endif %}.metadata)
    finally:
        engine.dispose()

    dropped = {op[1].name for op in diff if op[0] == "remove_table"}
    assert dropped.isdisjoint(EXTERNALLY_MANAGED_TABLES)
{%- else %}
"""Agent memory PostgreSQL tests - not configured (enable_memory=false)."""
{%- endif %}
