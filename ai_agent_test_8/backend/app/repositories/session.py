"""Session repository (PostgreSQL async)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.session import Session


async def get_by_id(db: AsyncSession, session_id: UUID) -> Session | None:
    """Get session by ID."""
    return await db.get(Session, session_id)


async def get_by_refresh_token_hash(db: AsyncSession, token_hash: str) -> Session | None:
    """Get session by refresh token hash."""
    result = await db.execute(
        select(Session).where(
            Session.refresh_token_hash == token_hash,
            Session.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def get_user_sessions(
    db: AsyncSession,
    user_id: UUID,
    *,
    active_only: bool = True,
) -> list[Session]:
    """Get all sessions for a user."""
    query = select(Session).where(Session.user_id == user_id)
    if active_only:
        query = query.where(Session.is_active.is_(True))
    query = query.order_by(Session.last_used_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    user_id: UUID,
    refresh_token_hash: str,
    expires_at: datetime,
    device_name: str | None = None,
    device_type: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Session:
    """Create a new session."""
    session = Session(
        user_id=user_id,
        refresh_token_hash=refresh_token_hash,
        expires_at=expires_at,
        device_name=device_name,
        device_type=device_type,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def update_last_used(db: AsyncSession, session_id: UUID) -> None:
    """Update session last used timestamp."""
    await db.execute(
        update(Session).where(Session.id == session_id).values(last_used_at=datetime.now(UTC))
    )
    await db.flush()


async def deactivate(db: AsyncSession, session_id: UUID) -> Session | None:
    """Deactivate a session (logout)."""
    session = await get_by_id(db, session_id)
    if session:
        session.is_active = False
        db.add(session)
        await db.flush()
    return session


async def deactivate_all_user_sessions(db: AsyncSession, user_id: UUID) -> int:
    """Deactivate all sessions for a user. Returns count of deactivated sessions."""
    result = await db.execute(
        update(Session)
        .where(Session.user_id == user_id, Session.is_active.is_(True))
        .values(is_active=False)
    )
    await db.flush()
    return getattr(result, "rowcount", 0) or 0


async def deactivate_by_refresh_token_hash(db: AsyncSession, token_hash: str) -> Session | None:
    """Deactivate session by refresh token hash."""
    session = await get_by_refresh_token_hash(db, token_hash)
    if session:
        session.is_active = False
        db.add(session)
        await db.flush()
    return session
