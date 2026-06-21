{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
"""Channel management CLI commands.

Commands:
    channel-list-bots         — List all registered channel bots
    channel-add-bot           — Register a new channel bot
    channel-webhook-register  — Register webhook URL for a bot with Telegram
    channel-webhook-delete    — Remove webhook for a bot (switches to polling)
    channel-test-message      — Send a test message through a bot
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import click

from app.commands import command, error, info, success
from app.core.config import settings
from app.db.session import get_db_context
from app.schemas.channel_bot import AccessPolicy, ChannelBotCreate
from app.services.channel_bot import ChannelBotService
from app.services.channels import get_adapter
from app.services.channels.base import OutgoingMessage

@asynccontextmanager
async def _channel_service():
    """Open a DB session and yield a ChannelBotService bound to it."""
    async with get_db_context() as db:
        yield ChannelBotService(db)

def _coerce_bot_id(bot_id: str) -> Any:
    return UUID(bot_id)

@command("channel-list-bots", help="List all registered channel bots")
@click.option("--platform", "-p", default=None, help="Filter by platform (e.g. telegram)")
def channel_list_bots(platform: str | None) -> None:
    """List all channel bots stored in the database."""

    async def _run() -> None:
        async with _channel_service() as svc:
            bots = await svc.list_by_platform(platform)

        if not bots:
            info("No channel bots registered.")
            return

        info(f"{'ID':<38}  {'Platform':<12}  {'Name':<30}  {'Active'}")
        info("-" * 90)
        for bot in bots:
            active_flag = "yes" if bot.is_active else "no"
            info(f"{str(bot.id):<38}  {bot.platform:<12}  {bot.name:<30}  {active_flag}")

    asyncio.run(_run())

@command("channel-add-bot", help="Register a new channel bot")
@click.option("--platform", required=True, type=click.Choice(["telegram"]), help="Platform name")
@click.option("--name", "-n", required=True, help="Bot display name")
@click.option("--token", "-t", required=True, help="Bot token (e.g. from BotFather)")
@click.option(
    "--mode",
    default="open",
    type=click.Choice(["open", "whitelist", "jwt_linked", "group_only"]),
    help="Access policy mode",
)
def channel_add_bot(platform: str, name: str, token: str, mode: str) -> None:
    """Encrypt the bot token and register the bot in the database."""
    async def _run() -> None:
        data = ChannelBotCreate(
            platform=platform,
            name=name,
            token=token,
            access_policy=AccessPolicy(mode=mode),
        )
        async with _channel_service() as svc:
            bot = await svc.create(data)

        success(f"Bot registered successfully! ID: {bot.id}")
        info(f"  Platform : {platform}")
        info(f"  Name     : {name}")
        info(f"  Mode     : {mode}")

    asyncio.run(_run())

@command("channel-webhook-register", help="Register webhook URL for a Telegram bot")
@click.option("--bot-id", required=True, help="Bot UUID")
def channel_webhook_register(bot_id: str) -> None:
    """Register the webhook URL for a bot with Telegram."""
    async def _run() -> None:
        async with _channel_service() as svc:
            try:
                bot = await svc.get(_coerce_bot_id(bot_id))
            except Exception:
                error(f"Bot not found: {bot_id}")
                return
            token = svc.get_decrypted_token(bot)

        adapter = get_adapter("telegram")
        webhook_url = (
            f"{settings.TELEGRAM_WEBHOOK_BASE_URL}/api/v1/channels/telegram/{bot_id}/webhook"
        )

        info(f"Registering webhook: {webhook_url}")
        ok = await adapter.register_webhook(token, url=webhook_url, secret=bot.webhook_secret)
        if ok:
            success("Webhook registered successfully.")
        else:
            error("Failed to register webhook. Check logs for details.")

    asyncio.run(_run())

@command("channel-webhook-delete", help="Remove webhook for a bot (switch to polling)")
@click.option("--bot-id", required=True, help="Bot UUID")
def channel_webhook_delete(bot_id: str) -> None:
    """Remove the webhook for a bot from Telegram."""

    async def _run() -> None:
        async with _channel_service() as svc:
            try:
                bot = await svc.get(_coerce_bot_id(bot_id))
            except Exception:
                error(f"Bot not found: {bot_id}")
                return
            token = svc.get_decrypted_token(bot)

        adapter = get_adapter("telegram")
        ok = await adapter.delete_webhook(token)
        if ok:
            success("Webhook removed. Bot is now in polling mode.")
        else:
            error("Failed to remove webhook. Check logs for details.")

    asyncio.run(_run())

@command("channel-test-message", help="Send a test message through a bot")
@click.option("--bot-id", required=True, help="Bot UUID")
@click.option("--chat-id", required=True, help="Telegram chat ID to send the message to")
@click.option("--text", default="Hello from your bot!", help="Message text")
def channel_test_message(bot_id: str, chat_id: str, text: str) -> None:
    """Send a test message to a chat via a registered bot."""

    async def _run() -> None:
        async with _channel_service() as svc:
            try:
                bot = await svc.get(_coerce_bot_id(bot_id))
            except Exception:
                error(f"Bot not found: {bot_id}")
                return
            token = svc.get_decrypted_token(bot)

        adapter = get_adapter("telegram")
        msg = OutgoingMessage(platform_chat_id=chat_id, text=text)
        info(f"Sending test message to chat {chat_id} via bot {bot.name}...")

        try:
            await adapter.send_message(token, msg)
            success("Message sent successfully.")
        except Exception as exc:
            error(f"Failed to send message: {exc}")

    asyncio.run(_run())
{%- endif %}
