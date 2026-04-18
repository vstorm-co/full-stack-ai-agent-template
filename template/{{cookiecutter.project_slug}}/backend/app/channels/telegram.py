{%- if cookiecutter.use_telegram %}
"""Telegram channel adapter using aiogram v3."""

import asyncio
import hmac
import logging
from typing import Any

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message as AiogramMessage

from app.channels.base import ChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)

_telegram_router = Router()


class TelegramAdapter(ChannelAdapter):
    """Concrete Telegram adapter using aiogram v3."""

    platform: str = "telegram"

    def __init__(self) -> None:
        self._polling_tasks: dict[str, asyncio.Task[None]] = {}

    # Send

    async def send_message(self, bot_token: str, msg: OutgoingMessage) -> None:
        """Send a reply back to Telegram.

        Tries Markdown parse mode first; falls back to plain text if
        Telegram rejects the formatting (common with LLM-generated markdown).
        """
        from aiogram.exceptions import TelegramBadRequest

        bot = Bot(
            token=bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
        )
        reply_to = int(msg.reply_to_message_id) if msg.reply_to_message_id else None
        try:
            try:
                await bot.send_message(
                    chat_id=msg.platform_chat_id,
                    text=msg.text,
                    parse_mode=msg.parse_mode,  # type: ignore[arg-type]
                    reply_to_message_id=reply_to,
                )
            except TelegramBadRequest:
                # Markdown parsing failed — send as plain text
                await bot.send_message(
                    chat_id=msg.platform_chat_id,
                    text=msg.text,
                    parse_mode=None,
                    reply_to_message_id=reply_to,
                )
        finally:
            await bot.session.close()

    # Polling

    async def start_polling(self, bot_id: str, bot_token: str) -> None:
        """Start a supervised polling loop for this bot."""
        if bot_id in self._polling_tasks and not self._polling_tasks[bot_id].done():
            logger.info("Polling already running for bot %s", bot_id)
            return

        task = asyncio.create_task(
            self._polling_supervisor(bot_id, bot_token),
            name=f"telegram_polling_{bot_id}",
        )
        self._polling_tasks[bot_id] = task
        logger.info("Started Telegram polling for bot %s", bot_id)

    async def stop_polling(self, bot_id: str) -> None:
        """Cancel the polling task for this bot."""
        task = self._polling_tasks.pop(bot_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped Telegram polling for bot %s", bot_id)

    async def _polling_supervisor(self, bot_id: str, bot_token: str) -> None:
        """Supervised loop: restart polling on crash, stop on CancelledError."""
        while True:
            try:
                await self._run_polling_once(bot_id, bot_token)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception(
                    "Telegram polling crashed for bot %s, restarting in 5s", bot_id
                )
                await asyncio.sleep(5)

    async def _run_polling_once(self, bot_id: str, bot_token: str) -> None:
        """Run one polling session using aiogram Dispatcher."""
        bot = Bot(
            token=bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
        )
        dp = Dispatcher()

        # Register the message handler bound to this bot_id
        @dp.message()
        async def on_message(message: AiogramMessage) -> None:
            await self._handle_update(message, bot_id)

        try:
            await dp.start_polling(bot, handle_signals=False)
        finally:
            await bot.session.close()

    # Webhook

    async def register_webhook(
        self, bot_token: str, url: str, secret: str | None
    ) -> bool:
        """Register a webhook URL with Telegram."""
        bot = Bot(token=bot_token)
        try:
            await bot.set_webhook(url=url, secret_token=secret)
            return True
        except Exception:
            logger.exception("Failed to register Telegram webhook")
            return False
        finally:
            await bot.session.close()

    async def delete_webhook(self, bot_token: str) -> bool:
        """Remove the webhook from Telegram."""
        bot = Bot(token=bot_token)
        try:
            await bot.delete_webhook()
            return True
        except Exception:
            logger.exception("Failed to delete Telegram webhook")
            return False
        finally:
            await bot.session.close()

    def verify_webhook_signature(
        self, headers: dict[str, str], secret: str, body: str | None = None
    ) -> bool:
        """Verify that the request came from Telegram via the secret token header.

        The ``body`` parameter is unused for Telegram (signature is header-only)
        but accepted for interface compatibility with ChannelAdapter.
        """
        received = headers.get("x-telegram-bot-api-secret-token", "")
        # Use hmac.compare_digest for constant-time comparison
        return hmac.compare_digest(received.encode(), secret.encode())

    # Parsing

    def parse_incoming(
        self, raw_payload: dict[str, Any], bot_id: str
    ) -> IncomingMessage | None:
        """Parse a Telegram update payload into IncomingMessage.

        Handles `message` and `edited_message` update types; text only (V1).
        Returns None for non-text updates.
        """
        msg_data: dict[str, Any] | None = raw_payload.get(
            "message"
        ) or raw_payload.get("edited_message")

        if not msg_data:
            return None

        text: str | None = msg_data.get("text")
        if not text:
            return None

        chat = msg_data.get("chat", {})
        from_user = msg_data.get("from", {})

        chat_type: str = chat.get("type", "private")
        platform_chat_id: str = str(chat.get("id", ""))
        platform_user_id: str = str(from_user.get("id", ""))

        username: str | None = from_user.get("username")
        first_name: str = from_user.get("first_name", "")
        last_name: str = from_user.get("last_name", "")
        display_name: str = f"{first_name} {last_name}".strip() or username or platform_user_id

        message_id: str | None = str(msg_data["message_id"]) if "message_id" in msg_data else None

        return IncomingMessage(
            platform="telegram",
            bot_id=bot_id,
            platform_user_id=platform_user_id,
            platform_chat_id=platform_chat_id,
            chat_type=chat_type,
            text=text,
            raw=raw_payload,
            platform_username=username,
            platform_display_name=display_name,
            message_id=message_id,
        )

    # Internal update handler

    async def _handle_update(
        self, message: AiogramMessage, bot_id: str
    ) -> None:
        """Handle an incoming aiogram Message inside the polling loop."""
        if not message.text:
            return

        chat = message.chat
        from_user = message.from_user

        if from_user is None:
            return

        chat_type: str = chat.type.value if hasattr(chat.type, "value") else str(chat.type)

        incoming = IncomingMessage(
            platform="telegram",
            bot_id=bot_id,
            platform_user_id=str(from_user.id),
            platform_chat_id=str(chat.id),
            chat_type=chat_type,
            text=message.text,
            raw={},
            platform_username=from_user.username,
            platform_display_name=from_user.full_name,
            message_id=str(message.message_id),
        )

        from app.channels.router import ChannelMessageRouter
        router = ChannelMessageRouter()

{%- if cookiecutter.use_postgresql %}
        from app.db.session import get_db_context
        async with get_db_context() as db:
            await router.route(incoming, db)
{%- elif cookiecutter.use_sqlite %}
        from contextlib import contextmanager
        from app.db.session import get_db_session
        # NOTE: Holding a sync SQLite session across an `await` boundary is not
        # ideal — the session stays open while the coroutine is suspended. For
        # production SQLite usage the router should adopt a more careful session
        # management strategy (e.g. open/close around each synchronous DB call,
        # or use asyncio.to_thread for the sync work).
        with contextmanager(get_db_session)() as db:
            await router.route(incoming, db)
{%- elif cookiecutter.use_mongodb %}
        await router.route(incoming, None)  # MongoDB repos don't need db session
{%- endif %}

{%- endif %}
