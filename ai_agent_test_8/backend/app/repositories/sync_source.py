"""Sync source repository (PostgreSQL async).

Contains database operations for SyncSource entities.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.sync_source import SyncSource


async def get_by_id(db: AsyncSession, source_id: UUID) -> SyncSource | None:
    """Get a sync source by ID."""
    return await db.get(SyncSource, source_id)


async def get_all(
    db: AsyncSession,
    is_active: bool | None = None,
) -> list[SyncSource]:
    """Get all sync sources, optionally filtered by active status."""
    query = select(SyncSource)
    if is_active is not None:
        query = query.where(SyncSource.is_active == is_active)
    query = query.order_by(SyncSource.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_due_for_sync(db: AsyncSession) -> list[SyncSource]:
    """Get sources that are due for scheduled sync.

    Returns active sources with a schedule where enough time has elapsed
    since the last sync (or that have never been synced).
    """
    now = datetime.now(UTC)
    # Fetch all active scheduled sources, filter in Python (avoids DB-specific interval syntax)
    query = select(SyncSource).where(
        SyncSource.is_active == True,  # noqa: E712
        SyncSource.schedule_minutes.isnot(None),
    )
    result = await db.execute(query)
    sources = list(result.scalars().all())
    return [
        s
        for s in sources
        if s.schedule_minutes is not None
        and (
            s.last_sync_at is None or s.last_sync_at + timedelta(minutes=s.schedule_minutes) <= now
        )
    ]


async def create(
    db: AsyncSession,
    *,
    name: str,
    connector_type: str,
    collection_name: str,
    config: dict[str, object],
    sync_mode: str = "new_only",
    schedule_minutes: int | None = None,
) -> SyncSource:
    """Create a new sync source configuration."""
    source = SyncSource(
        name=name,
        connector_type=connector_type,
        collection_name=collection_name,
        config=config,
        sync_mode=sync_mode,
        schedule_minutes=schedule_minutes,
    )
    db.add(source)
    await db.flush()
    return source


async def update(
    db: AsyncSession,
    source_id: UUID,
    **updates: object,
) -> SyncSource | None:
    """Update a sync source with the given fields."""
    source = await db.get(SyncSource, source_id)
    if not source:
        return None
    for key, value in updates.items():
        if value is not None and hasattr(source, key):
            setattr(source, key, value)
    await db.flush()
    return source


async def delete(db: AsyncSession, source_id: UUID) -> bool:
    """Delete a sync source by ID. Returns True if deleted."""
    source = await db.get(SyncSource, source_id)
    if not source:
        return False
    await db.delete(source)
    await db.flush()
    return True


async def update_sync_status(
    db: AsyncSession,
    source_id: UUID,
    *,
    last_sync_at: datetime,
    last_sync_status: str,
    last_error: str | None = None,
) -> SyncSource | None:
    """Update the sync status fields after a sync operation."""
    source = await db.get(SyncSource, source_id)
    if not source:
        return None
    source.last_sync_at = last_sync_at
    source.last_sync_status = last_sync_status
    source.last_error = last_error
    await db.flush()
    return source
