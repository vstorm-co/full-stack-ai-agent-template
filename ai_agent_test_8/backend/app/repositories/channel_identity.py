"""ChannelIdentity repository (PostgreSQL async)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.channel_identity import ChannelIdentity


async def get_by_id(db: AsyncSession, identity_id: UUID) -> ChannelIdentity | None:
    """Get a channel identity by ID."""
    return await db.get(ChannelIdentity, identity_id)


async def get_by_platform_user(
    db: AsyncSession,
    platform: str,
    platform_user_id: str,
) -> ChannelIdentity | None:
    """Get identity by platform + platform_user_id."""
    result = await db.execute(
        select(ChannelIdentity).where(
            ChannelIdentity.platform == platform,
            ChannelIdentity.platform_user_id == platform_user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_by_link_code(db: AsyncSession, link_code: str) -> ChannelIdentity | None:
    """Get identity by link code (only if not expired)."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(ChannelIdentity).where(
            ChannelIdentity.link_code == link_code,
            ChannelIdentity.link_code_expires_at > now,
        )
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    platform: str,
    platform_user_id: str,
    platform_username: str | None = None,
    platform_display_name: str | None = None,
    user_id: UUID | None = None,
) -> ChannelIdentity:
    """Create a new channel identity."""
    identity = ChannelIdentity(
        platform=platform,
        platform_user_id=platform_user_id,
        platform_username=platform_username,
        platform_display_name=platform_display_name,
        user_id=user_id,
    )
    db.add(identity)
    await db.flush()
    await db.refresh(identity)
    return identity


async def update(
    db: AsyncSession,
    *,
    db_identity: ChannelIdentity,
    update_data: dict,
) -> ChannelIdentity:
    """Update a channel identity."""
    for field, value in update_data.items():
        setattr(db_identity, field, value)
    db.add(db_identity)
    await db.flush()
    await db.refresh(db_identity)
    return db_identity


async def link_to_user(
    db: AsyncSession,
    *,
    db_identity: ChannelIdentity,
    user_id: UUID,
) -> ChannelIdentity:
    """Link a platform identity to an app user and clear the link code."""
    db_identity.user_id = user_id
    db_identity.link_code = None
    db_identity.link_code_expires_at = None
    db.add(db_identity)
    await db.flush()
    await db.refresh(db_identity)
    return db_identity
