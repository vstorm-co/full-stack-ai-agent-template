"""ChannelBot repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.channel_bot import ChannelBot
from app.services.channels.base import DEFAULT_ACCESS_POLICY


async def get_by_id(db: AsyncSession, bot_id: UUID) -> ChannelBot | None:
    """Get a channel bot by ID."""
    return await db.get(ChannelBot, bot_id)


async def get_by_platform(
    db: AsyncSession,
    platform: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[ChannelBot]:
    """Get all bots for a given platform with pagination."""
    result = await db.execute(
        select(ChannelBot)
        .where(ChannelBot.platform == platform)
        .order_by(ChannelBot.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_active_polling_bots(db: AsyncSession, platform: str) -> list[ChannelBot]:
    """Get all active polling bots for a given platform."""
    result = await db.execute(
        select(ChannelBot).where(
            ChannelBot.platform == platform,
            ChannelBot.is_active.is_(True),
            ChannelBot.webhook_mode.is_(False),
        )
    )
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    platform: str,
    name: str,
    token_encrypted: str,
    webhook_mode: bool = False,
    webhook_url: str | None = None,
    webhook_secret: str | None = None,
    access_policy: dict | None = None,
    ai_model_override: str | None = None,
    system_prompt_override: str | None = None,
) -> ChannelBot:
    """Create a new channel bot."""
    bot = ChannelBot(
        platform=platform,
        name=name,
        token_encrypted=token_encrypted,
        webhook_mode=webhook_mode,
        webhook_url=webhook_url,
        webhook_secret=webhook_secret,
        access_policy=access_policy or dict(DEFAULT_ACCESS_POLICY),
        ai_model_override=ai_model_override,
        system_prompt_override=system_prompt_override,
    )
    db.add(bot)
    await db.flush()
    await db.refresh(bot)
    return bot


async def update(
    db: AsyncSession,
    *,
    db_bot: ChannelBot,
    update_data: dict,
) -> ChannelBot:
    """Update a channel bot."""
    for field, value in update_data.items():
        setattr(db_bot, field, value)
    db.add(db_bot)
    await db.flush()
    await db.refresh(db_bot)
    return db_bot


async def delete(db: AsyncSession, bot_id: UUID) -> bool:
    """Delete a channel bot by ID. Returns True if deleted, False if not found."""
    bot = await get_by_id(db, bot_id)
    if not bot:
        return False
    await db.delete(bot)
    await db.flush()
    return True


async def count(db: AsyncSession) -> int:
    """Count total number of channel bots."""
    result = await db.scalar(select(func.count()).select_from(ChannelBot))
    return result or 0


async def list_all(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[ChannelBot]:
    """List all channel bots with pagination."""
    result = await db.execute(
        select(ChannelBot).order_by(ChannelBot.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())
