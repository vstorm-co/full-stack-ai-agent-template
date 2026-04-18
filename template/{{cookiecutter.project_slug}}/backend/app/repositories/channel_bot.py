{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
{%- if cookiecutter.use_postgresql %}
"""ChannelBot repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import DEFAULT_ACCESS_POLICY
from app.db.models.channel_bot import ChannelBot


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
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: UUID | None = None,
{%- endif %}
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
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
        project_id=project_id,
{%- endif %}
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
        select(ChannelBot)
        .order_by(ChannelBot.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


{%- elif cookiecutter.use_sqlite %}
"""ChannelBot repository (SQLite sync)."""

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.channels.base import DEFAULT_ACCESS_POLICY
from app.db.models.channel_bot import ChannelBot


def get_by_id(db: DBSession, bot_id: str) -> ChannelBot | None:
    """Get a channel bot by ID."""
    return db.get(ChannelBot, bot_id)


def get_by_platform(
    db: DBSession,
    platform: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[ChannelBot]:
    """Get all bots for a given platform with pagination."""
    result = db.execute(
        select(ChannelBot)
        .where(ChannelBot.platform == platform)
        .order_by(ChannelBot.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


def get_active_polling_bots(db: DBSession, platform: str) -> list[ChannelBot]:
    """Get all active polling bots for a given platform."""
    result = db.execute(
        select(ChannelBot).where(
            ChannelBot.platform == platform,
            ChannelBot.is_active.is_(True),
            ChannelBot.webhook_mode.is_(False),
        )
    )
    return list(result.scalars().all())


def create(
    db: DBSession,
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
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: str | None = None,
{%- endif %}
) -> ChannelBot:
    """Create a new channel bot."""
    bot = ChannelBot(
        platform=platform,
        name=name,
        token_encrypted=token_encrypted,
        webhook_mode=webhook_mode,
        webhook_url=webhook_url,
        webhook_secret=webhook_secret,
        access_policy=json.dumps(access_policy or DEFAULT_ACCESS_POLICY),
        ai_model_override=ai_model_override,
        system_prompt_override=system_prompt_override,
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
        project_id=project_id,
{%- endif %}
    )
    db.add(bot)
    db.flush()
    db.refresh(bot)
    return bot


def update(
    db: DBSession,
    *,
    db_bot: ChannelBot,
    update_data: dict,
) -> ChannelBot:
    """Update a channel bot."""
    for field, value in update_data.items():
        if field == "access_policy" and isinstance(value, dict):
            setattr(db_bot, field, json.dumps(value))
        else:
            setattr(db_bot, field, value)
    db.add(db_bot)
    db.flush()
    db.refresh(db_bot)
    return db_bot


def delete(db: DBSession, bot_id: str) -> bool:
    """Delete a channel bot by ID. Returns True if deleted, False if not found."""
    bot = get_by_id(db, bot_id)
    if not bot:
        return False
    db.delete(bot)
    db.flush()
    return True


def count(db: DBSession) -> int:
    """Count total number of channel bots."""
    result = db.scalar(select(func.count()).select_from(ChannelBot))
    return result or 0


def list_all(
    db: DBSession,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[ChannelBot]:
    """List all channel bots with pagination."""
    result = db.execute(
        select(ChannelBot)
        .order_by(ChannelBot.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


{%- elif cookiecutter.use_mongodb %}
"""ChannelBot repository (MongoDB)."""

from datetime import UTC, datetime

from app.channels.base import DEFAULT_ACCESS_POLICY
from app.db.models.channel_bot import ChannelBot


async def get_by_id(bot_id: str) -> ChannelBot | None:
    """Get a channel bot by ID."""
    return await ChannelBot.get(bot_id)


async def get_by_platform(
    platform: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[ChannelBot]:
    """Get all bots for a given platform with pagination."""
    return (
        await ChannelBot.find(ChannelBot.platform == platform)
        .sort(-ChannelBot.created_at)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


async def get_active_polling_bots(platform: str) -> list[ChannelBot]:
    """Get all active polling bots for a given platform."""
    return await ChannelBot.find(
        ChannelBot.platform == platform,
        ChannelBot.is_active == True,
        ChannelBot.webhook_mode == False,
    ).to_list()


async def create(
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
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: str | None = None,
{%- endif %}
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
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
        project_id=project_id,
{%- endif %}
    )
    await bot.insert()
    return bot


async def update(
    *,
    db_bot: ChannelBot,
    update_data: dict,
) -> ChannelBot:
    """Update a channel bot."""
    for field, value in update_data.items():
        setattr(db_bot, field, value)
    db_bot.updated_at = datetime.now(UTC)
    await db_bot.save()
    return db_bot


async def delete(bot_id: str) -> bool:
    """Delete a channel bot by ID. Returns True if deleted, False if not found."""
    bot = await get_by_id(bot_id)
    if not bot:
        return False
    await bot.delete()
    return True


async def count() -> int:
    """Count total number of channel bots."""
    return await ChannelBot.count()


async def list_all(
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[ChannelBot]:
    """List all channel bots with pagination."""
    return (
        await ChannelBot.find()
        .sort(-ChannelBot.created_at)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


{%- else %}
"""ChannelBot repository — no supported database configured."""
{%- endif %}
{%- else %}
"""ChannelBot repository — not configured (use_telegram is disabled)."""
{%- endif %}
