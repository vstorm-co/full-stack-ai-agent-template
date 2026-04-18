{%- if cookiecutter.use_slack %}
"""Slack channel adapter using slack-sdk.

Supports:
- Events API (webhook mode) — production
- Socket Mode (polling equivalent) — development
- Thread-aware sessions: messages in a Slack thread get their own
  ChannelSession / Conversation (thread_ts folded into platform_chat_id)
- @mention detection in channels
"""

import asyncio
import hashlib
import hmac
import logging
import time
from typing import Any

from app.channels.base import ChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class SlackAdapter(ChannelAdapter):
    """Concrete Slack adapter using slack-sdk."""

    platform: str = "slack"

    def __init__(self) -> None:
        self._socket_tasks: dict[str, asyncio.Task[None]] = {}

    # Send

    async def send_message(self, bot_token: str, msg: OutgoingMessage) -> None:
        """Send a reply back to Slack via the Web API."""
        from slack_sdk.web.async_client import AsyncWebClient

        client = AsyncWebClient(token=bot_token)

        # If platform_chat_id contains ":" it includes a thread_ts
        channel, _, thread_ts = msg.platform_chat_id.partition(":")

        kwargs: dict[str, Any] = {
            "channel": channel,
            "text": msg.text,
        }
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        if "thread_ts" not in kwargs and msg.reply_to_message_id:
            kwargs["thread_ts"] = msg.reply_to_message_id

        await client.chat_postMessage(**kwargs)

    # Polling — Socket Mode (development)

    async def start_polling(self, bot_id: str, bot_token: str) -> None:
        """Start Slack Socket Mode (equivalent to polling for dev)."""
        if bot_id in self._socket_tasks and not self._socket_tasks[bot_id].done():
            logger.info("Socket Mode already running for bot %s", bot_id)
            return

        task = asyncio.create_task(
            self._socket_supervisor(bot_id, bot_token),
            name=f"slack_socket_{bot_id}",
        )
        self._socket_tasks[bot_id] = task
        logger.info("Started Slack Socket Mode for bot %s", bot_id)

    async def stop_polling(self, bot_id: str) -> None:
        """Stop Socket Mode for this bot."""
        task = self._socket_tasks.pop(bot_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped Slack Socket Mode for bot %s", bot_id)

    async def _socket_supervisor(self, bot_id: str, bot_token: str) -> None:
        """Supervised loop: restart Socket Mode on crash."""
        while True:
            try:
                await self._run_socket_mode(bot_id, bot_token)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception(
                    "Slack Socket Mode crashed for bot %s, restarting in 5s", bot_id
                )
                await asyncio.sleep(5)

    async def _run_socket_mode(self, bot_id: str, bot_token: str) -> None:
        """Run one Socket Mode session."""
        from app.core.config import settings

        try:
            from slack_sdk.socket_mode.aiohttp import SocketModeClient
            from slack_sdk.socket_mode.request import SocketModeRequest
            from slack_sdk.socket_mode.response import SocketModeResponse
        except ImportError:
            logger.error(
                "Slack Socket Mode requires 'slack-sdk[socket-mode]'. "
                "Install with: pip install 'slack-sdk[socket-mode]'"
            )
            return

        client = SocketModeClient(
            app_token=settings.SLACK_APP_TOKEN,
            web_client=__import__("slack_sdk.web.async_client", fromlist=["AsyncWebClient"]).AsyncWebClient(
                token=bot_token
            ),
        )

        async def handler(client_: Any, req: SocketModeRequest) -> None:
            await client_.send_socket_mode_response(
                SocketModeResponse(envelope_id=req.envelope_id)
            )
            if req.type == "events_api":
                event = req.payload.get("event", {})
                await self._handle_event(event, bot_id)

        client.socket_mode_request_listeners.append(handler)  # type: ignore[arg-type]
        await client.connect()
        # Keep running until cancelled
        while True:
            await asyncio.sleep(1)

    # Webhook

    async def register_webhook(
        self, bot_token: str, url: str, secret: str | None
    ) -> bool:
        """Slack doesn't have a register webhook API — configuration is done
        in the Slack app dashboard. This is a no-op that returns True."""
        logger.info("Slack: webhook URL should be configured in Slack app settings: %s", url)
        return True

    async def delete_webhook(self, bot_token: str) -> bool:
        """Slack doesn't have a delete webhook API. No-op."""
        return True

    def verify_webhook_signature(
        self, headers: dict[str, str], secret: str, body: str | None = None
    ) -> bool:
        """Verify Slack request signature (HMAC-SHA256).

        Slack signs requests with: v0=HMAC-SHA256(signing_secret, "v0:{timestamp}:{body}")
        The raw request body must be passed via the ``body`` parameter.
        """
        timestamp = headers.get("x-slack-request-timestamp", "")
        signature = headers.get("x-slack-signature", "")
        raw_body = body or ""

        # Reject missing timestamp (required for replay protection)
        if not timestamp or not signature:
            return False

        # Reject requests older than 5 minutes (replay protection)
        try:
            ts = int(timestamp)
        except ValueError:
            return False
        if abs(time.time() - ts) > 300:
            return False

        base_string = f"v0:{timestamp}:{raw_body}"
        computed = "v0=" + hmac.new(
            secret.encode(), base_string.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed, signature)

    # Parsing

    def parse_incoming(
        self, raw_payload: dict[str, Any], bot_id: str
    ) -> IncomingMessage | None:
        """Parse a Slack event payload into IncomingMessage.

        Handles ``message`` events (direct messages and channel messages).
        Ignores bot messages, message_changed, and other subtypes.
        Thread replies get thread_ts folded into platform_chat_id.
        """
        event: dict[str, Any] = raw_payload.get("event", raw_payload)

        event_type: str = event.get("type", "")
        if event_type != "message" and event_type != "app_mention":
            return None

        # Ignore bot messages and edits
        if event.get("bot_id") or event.get("subtype"):
            return None

        text: str | None = event.get("text")
        if not text:
            return None

        user_id: str = event.get("user", "")
        channel: str = event.get("channel", "")
        channel_type: str = event.get("channel_type", "channel")
        thread_ts: str | None = event.get("thread_ts")
        message_ts: str | None = event.get("ts")

        # Map Slack channel types
        chat_type = "private" if channel_type in ("im", "mpim") else "group"

        # For threads: fold thread_ts into platform_chat_id so each thread
        # gets its own ChannelSession and Conversation
        platform_chat_id = f"{channel}:{thread_ts}" if thread_ts else channel

        return IncomingMessage(
            platform="slack",
            bot_id=bot_id,
            platform_user_id=user_id,
            platform_chat_id=platform_chat_id,
            chat_type=chat_type,
            text=text,
            raw=raw_payload,
            platform_username=None,  # resolved later if needed
            platform_display_name=None,
            message_id=message_ts,
        )

    # Internal event handler

    async def _handle_event(self, event: dict[str, Any], bot_id: str) -> None:
        """Handle a Slack event from Socket Mode or webhook."""
        incoming = self.parse_incoming({"event": event}, bot_id)
        if incoming is None:
            return

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
        await router.route(incoming, None)
{%- endif %}
{%- endif %}
