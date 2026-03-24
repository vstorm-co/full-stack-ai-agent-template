{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
{%- if cookiecutter.use_postgresql %}
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
        update(Session)
        .where(Session.id == session_id)
        .values(last_used_at=datetime.now(UTC))
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


{%- elif cookiecutter.use_sqlite %}
"""Session repository (SQLite sync)."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session as DBSession

from app.db.models.session import Session


def get_by_id(db: DBSession, session_id: str) -> Session | None:
    """Get session by ID."""
    return db.get(Session, session_id)


def get_by_refresh_token_hash(db: DBSession, token_hash: str) -> Session | None:
    """Get session by refresh token hash."""
    result = db.execute(
        select(Session).where(
            Session.refresh_token_hash == token_hash,
            Session.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


def get_user_sessions(
    db: DBSession,
    user_id: str,
    *,
    active_only: bool = True,
) -> list[Session]:
    """Get all sessions for a user."""
    query = select(Session).where(Session.user_id == user_id)
    if active_only:
        query = query.where(Session.is_active.is_(True))
    query = query.order_by(Session.last_used_at.desc())
    result = db.execute(query)
    return list(result.scalars().all())


def create(
    db: DBSession,
    *,
    user_id: str,
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
    db.flush()
    db.refresh(session)
    return session


def update_last_used(db: DBSession, session_id: str) -> None:
    """Update session last used timestamp."""
    db.execute(
        update(Session)
        .where(Session.id == session_id)
        .values(last_used_at=datetime.now(UTC))
    )
    db.flush()


def deactivate(db: DBSession, session_id: str) -> Session | None:
    """Deactivate a session (logout)."""
    session = get_by_id(db, session_id)
    if session:
        session.is_active = False
        db.add(session)
        db.flush()
    return session


def deactivate_all_user_sessions(db: DBSession, user_id: str) -> int:
    """Deactivate all sessions for a user. Returns count of deactivated sessions."""
    result = db.execute(
        update(Session)
        .where(Session.user_id == user_id, Session.is_active.is_(True))
        .values(is_active=False)
    )
    db.flush()
    return getattr(result, "rowcount", 0) or 0


def deactivate_by_refresh_token_hash(db: DBSession, token_hash: str) -> Session | None:
    """Deactivate session by refresh token hash."""
    session = get_by_refresh_token_hash(db, token_hash)
    if session:
        session.is_active = False
        db.add(session)
        db.flush()
    return session


{%- elif cookiecutter.use_mongodb %}
"""Session repository (MongoDB)."""

from datetime import UTC, datetime

from app.db.models.session import Session


async def get_by_id(session_id: str) -> Session | None:
    """Get session by ID."""
    return await Session.get(session_id)


async def get_by_refresh_token_hash(token_hash: str) -> Session | None:
    """Get session by refresh token hash."""
    return await Session.find_one(
        Session.refresh_token_hash == token_hash,
        Session.is_active == True,
    )


async def get_user_sessions(
    user_id: str,
    *,
    active_only: bool = True,
) -> list[Session]:
    """Get all sessions for a user."""
    query = Session.find(Session.user_id == user_id)
    if active_only:
        query = query.find(Session.is_active == True)
    return await query.sort(-Session.last_used_at).to_list()


async def create(
    *,
    user_id: str,
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
    await session.insert()
    return session


async def update_last_used(session_id: str) -> None:
    """Update session last used timestamp."""
    session = await get_by_id(session_id)
    if session:
        session.last_used_at = datetime.now(UTC)
        await session.save()


async def deactivate(session_id: str) -> Session | None:
    """Deactivate a session (logout)."""
    session = await get_by_id(session_id)
    if session:
        session.is_active = False
        await session.save()
    return session


async def deactivate_all_user_sessions(user_id: str) -> int:
    """Deactivate all sessions for a user. Returns count of deactivated sessions."""
    result = await Session.find(
        Session.user_id == user_id,
        Session.is_active == True,
    ).update({"$set": {"is_active": False}})
    return result.modified_count if result else 0


async def deactivate_by_refresh_token_hash(token_hash: str) -> Session | None:
    """Deactivate session by refresh token hash."""
    session = await get_by_refresh_token_hash(token_hash)
    if session:
        session.is_active = False
        await session.save()
    return session


{%- endif %}
{%- else %}
"""Session repository - not configured."""
{%- endif %}
