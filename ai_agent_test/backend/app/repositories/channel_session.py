"""ChannelSession repository (PostgreSQL async)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.channel_identity import ChannelIdentity
from app.db.models.channel_session import ChannelSession


async def get_by_id(db: AsyncSession, session_id: UUID) -> ChannelSession | None:
    """Get a channel session by ID."""
    return await db.get(ChannelSession, session_id)


async def get_by_bot_and_chat(
    db: AsyncSession,
    bot_id: UUID,
    platform_chat_id: str,
) -> ChannelSession | None:
    """Get an active session by bot + chat ID."""
    result = await db.execute(
        select(ChannelSession).where(
            ChannelSession.bot_id == bot_id,
            ChannelSession.platform_chat_id == platform_chat_id,
        )
    )
    return result.scalar_one_or_none()


async def get_sessions_for_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[ChannelSession]:
    """Get all sessions for a user (via their linked channel identities)."""
    result = await db.execute(
        select(ChannelSession)
        .join(ChannelIdentity, ChannelSession.identity_id == ChannelIdentity.id)
        .where(ChannelIdentity.user_id == user_id)
        .order_by(ChannelSession.last_message_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    bot_id: UUID,
    identity_id: UUID,
    platform_chat_id: str,
    chat_type: str = "private",
    conversation_id: UUID | None = None,
    project_id: UUID | None = None,
) -> ChannelSession:
    """Create a new channel session."""
    session = ChannelSession(
        bot_id=bot_id,
        identity_id=identity_id,
        platform_chat_id=platform_chat_id,
        chat_type=chat_type,
        conversation_id=conversation_id,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def update(
    db: AsyncSession,
    *,
    db_session: ChannelSession,
    update_data: dict,
) -> ChannelSession:
    """Update a channel session."""
    for field, value in update_data.items():
        setattr(db_session, field, value)
    db.add(db_session)
    await db.flush()
    await db.refresh(db_session)
    return db_session


async def list_by_bot(
    db: AsyncSession,
    bot_id: UUID,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[ChannelSession]:
    """List sessions for a specific bot with pagination."""
    result = await db.execute(
        select(ChannelSession)
        .where(ChannelSession.bot_id == bot_id)
        .order_by(ChannelSession.last_message_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_by_bot(db: AsyncSession, bot_id: UUID) -> int:
    """Count sessions for a specific bot."""
    from sqlalchemy import func

    result = await db.scalar(
        select(func.count()).select_from(ChannelSession).where(ChannelSession.bot_id == bot_id)
    )
    return result or 0


async def touch(db: AsyncSession, db_session: ChannelSession) -> ChannelSession:
    """Update last_message_at to now (UTC)."""
    db_session.last_message_at = datetime.now(UTC)
    db.add(db_session)
    await db.flush()
    await db.refresh(db_session)
    return db_session
