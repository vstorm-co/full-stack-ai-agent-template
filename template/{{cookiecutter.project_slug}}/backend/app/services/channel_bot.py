{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
"""ChannelBotService — business logic for bot management (PostgreSQL async)."""

from __future__ import annotations

import logging
import secrets
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.channels import get_adapter
from app.core.channel_crypto import decrypt_token, encrypt_token
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.db.models.channel_bot import ChannelBot
from app.repositories import channel_bot_repo, channel_session_repo
from app.schemas.channel_bot import ChannelBotCreate, ChannelBotUpdate

logger = logging.getLogger(__name__)


class ChannelBotService:
    """Service for channel bot management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: ChannelBotCreate) -> ChannelBot:
        """Create a new channel bot with an encrypted token."""
        token_encrypted = encrypt_token(data.token)
        webhook_secret = secrets.token_urlsafe(32) if data.webhook_mode else None
        return await channel_bot_repo.create(
            self.db,
            platform=data.platform,
            name=data.name,
            token_encrypted=token_encrypted,
            webhook_mode=data.webhook_mode,
            webhook_url=data.webhook_url,
            webhook_secret=webhook_secret,
            access_policy=data.access_policy.model_dump(),
            ai_model_override=data.ai_model_override,
            system_prompt_override=data.system_prompt_override,
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
            project_id=data.project_id,
{%- else %}
            project_id=None,
{%- endif %}
        )

    async def get(self, bot_id: UUID) -> ChannelBot:
        """Get a bot by ID; raises NotFoundError if not found."""
        bot = await channel_bot_repo.get_by_id(self.db, bot_id)
        if not bot:
            raise NotFoundError(
                message="Channel bot not found",
                details={"bot_id": str(bot_id)},
            )
        return bot

    async def find_active(self, bot_id: UUID) -> ChannelBot | None:
        """Return an active bot by ID, or None (used by webhook handlers)."""
        bot = await channel_bot_repo.get_by_id(self.db, bot_id)
        if not bot or not bot.is_active:
            return None
        return bot

    async def list_all(self, *, skip: int = 0, limit: int = 50) -> tuple[list[ChannelBot], int]:
        """List all bots with total count."""
        bots = await channel_bot_repo.list_all(self.db, skip=skip, limit=limit)
        total = await channel_bot_repo.count(self.db)
        return bots, total

    async def list_by_platform(self, platform: str | None = None) -> list[ChannelBot]:
        """Return bots, optionally filtered by platform."""
        if platform:
            return await channel_bot_repo.get_by_platform(self.db, platform)
        return await channel_bot_repo.list_all(self.db)

    async def update(self, bot_id: UUID, data: ChannelBotUpdate) -> ChannelBot:
        """Update a channel bot."""
        bot = await self.get(bot_id)
        update_data = data.model_dump(exclude_unset=True)
        if "token" in update_data:
            update_data["token_encrypted"] = encrypt_token(update_data.pop("token"))
        if "access_policy" in update_data and update_data["access_policy"] is not None:
            policy = update_data["access_policy"]
            update_data["access_policy"] = (
                policy.model_dump() if hasattr(policy, "model_dump") else policy
            )
        return await channel_bot_repo.update(self.db, db_bot=bot, update_data=update_data)

    async def delete(self, bot_id: UUID) -> None:
        """Delete a channel bot."""
        await self.get(bot_id)
        await channel_bot_repo.delete(self.db, bot_id)

    async def activate(self, bot_id: UUID) -> ChannelBot:
        """Set is_active = True."""
        bot = await self.get(bot_id)
        return await channel_bot_repo.update(self.db, db_bot=bot, update_data={"is_active": True})

    async def deactivate(self, bot_id: UUID) -> ChannelBot:
        """Set is_active = False."""
        bot = await self.get(bot_id)
        return await channel_bot_repo.update(self.db, db_bot=bot, update_data={"is_active": False})

    def get_decrypted_token(self, bot: ChannelBot) -> str:
        """Return the decrypted bot token."""
        return decrypt_token(bot.token_encrypted)

    async def get_active_polling_bots(self, platform: str) -> list[ChannelBot]:
        """Return active polling (non-webhook) bots for the given platform."""
        return await channel_bot_repo.get_active_polling_bots(self.db, platform)

    async def list_sessions(
        self, bot_id: UUID, *, skip: int = 0, limit: int = 50
    ) -> tuple[list, int]:
        """List channel sessions for this bot."""
        items = await channel_session_repo.list_by_bot(self.db, bot_id, skip=skip, limit=limit)
        total = await channel_session_repo.count_by_bot(self.db, bot_id)
        return items, total

    async def register_webhook(self, bot_id: UUID) -> dict[str, Any]:
        """Register a webhook URL with the bot's platform.

        Looks up the bot, picks the adapter for its platform, builds the platform-specific
        webhook URL from settings, and asks the adapter to register it.
        """
        bot = await self.get(bot_id)
        adapter = get_adapter(bot.platform)
        token = self.get_decrypted_token(bot)
        webhook_url = (
            f"{settings.TELEGRAM_WEBHOOK_BASE_URL}/api/v1/channels/{bot.platform}/{bot_id}/webhook"
        )
        success = await adapter.register_webhook(
            token, url=webhook_url, secret=bot.webhook_secret
        )
        return {"success": success, "webhook_url": webhook_url}

    async def delete_webhook(self, bot_id: UUID) -> dict[str, Any]:
        """Remove the webhook from the bot's platform (switches to polling mode)."""
        bot = await self.get(bot_id)
        adapter = get_adapter(bot.platform)
        token = self.get_decrypted_token(bot)
        success = await adapter.delete_webhook(token)
        return {"success": success}


{%- else %}
"""ChannelBotService — not configured (use_telegram is disabled)."""
{%- endif %}
