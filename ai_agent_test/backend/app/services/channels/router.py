"""Channel message router — processes incoming messages end-to-end."""

import asyncio
import logging
import time
from typing import Any

from app.agents.tools.chart_render import chart_to_markdown, render_chart_png
from app.agents.tools.chart_tool import parse_chart_spec
from app.core.channel_crypto import decrypt_token
from app.core.exceptions import AuthorizationError, BadRequestError
from app.repositories import (
    channel_bot_repo,
    channel_identity_repo,
    channel_session_repo,
    conversation_repo,
)
from app.services.agent_invocation import AgentInvocationService
from app.services.channels import get_adapter
from app.services.channels.base import IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory rate limiter state
# key = "{bot_id}:{identity_id}", value = (count, window_start_ts)
# ---------------------------------------------------------------------------
_rate_buckets: dict[str, tuple[int, float]] = {}

_DEFAULT_RPM = 10  # requests per minute

# ---------------------------------------------------------------------------
# Per-chat lock — serialises concurrent messages in group channels.
#
# In group chats (Telegram groups, Slack channels) multiple users can send
# messages at the same time.  Without a lock the router would process them
# concurrently, causing:
#   • Duplicate ChannelSession creation (DB constraint violation)
#   • Interleaved agent invocations sharing the same Conversation
#   • Rate-limit counter races
#
# The lock is keyed on (bot_id, platform_chat_id).  Private 1-on-1 chats
# also acquire the lock but contention there is negligible.
# ---------------------------------------------------------------------------
_chat_locks: dict[str, asyncio.Lock] = {}


def _get_chat_lock(bot_id: str, chat_id: str) -> asyncio.Lock:
    """Return (or create) the asyncio.Lock for a bot + chat pair."""
    key = f"{bot_id}:{chat_id}"
    if key not in _chat_locks:
        _chat_locks[key] = asyncio.Lock()
    return _chat_locks[key]


class ChannelMessageRouter:
    """Process an incoming channel message end-to-end."""

    async def route(self, incoming: IncomingMessage, db: Any) -> None:
        """Acquire per-chat lock, then process the message.

        The lock ensures that concurrent messages in the same group chat
        are processed sequentially — no duplicate sessions, no interleaved
        agent calls.
        """
        lock = _get_chat_lock(incoming.bot_id, incoming.platform_chat_id)
        async with lock:
            await self._route_inner(incoming, db)

    async def _route_inner(self, incoming: IncomingMessage, db: Any) -> None:
        """Process an incoming channel message end-to-end.

        Steps:
            1. Load bot config from DB.
            2. Check access policy.
            3. Handle commands (/start, /new, /help, /link, /project, /unlink).
            4. Resolve or create ChannelIdentity.
            5. Resolve or create ChannelSession (+ Conversation).
            6. Rate-limit check.
            7. Invoke agent via AgentInvocationService.
            8. Send reply via adapter.
        """
        # 1. Load bot
        bot = await channel_bot_repo.get_by_id(db, incoming.bot_id)
        if not bot or not bot.is_active:
            logger.debug("Bot %s not found or inactive — ignoring", incoming.bot_id)
            return

        # 2. Check access policy
        try:
            self._check_access(incoming, bot)
        except AuthorizationError as exc:
            await self._send_reply(bot, incoming, exc.message)
            return

        # 3. Handle commands
        command_reply = await self._handle_command(incoming.text, incoming, bot, db)
        if command_reply is not None:
            await self._send_reply(bot, incoming, command_reply)
            return

        # 4. Resolve identity
        try:
            identity = await self._resolve_identity(incoming, bot, db)
        except AuthorizationError as exc:
            await self._send_reply(bot, incoming, exc.message)
            return

        # 5. Resolve session
        session = await self._resolve_session(incoming, bot, identity, db)

        # 6. Rate limit
        try:
            self._check_rate_limit(bot, str(identity.id))
        except BadRequestError as exc:
            await self._send_reply(bot, incoming, exc.message)
            return

        # 7. Invoke agent
        tool_events = []
        try:
            svc = AgentInvocationService(db)
            response_text, tool_events = await svc.invoke(
                user_message=incoming.text,
                conversation_id=session.conversation_id,
                user_id=identity.user_id,
                project_id=getattr(session, "project_id", None),
                system_prompt_override=getattr(bot, "system_prompt_override", None),
                model_override=getattr(bot, "ai_model_override", None),
            )
        except Exception:
            logger.exception("Agent invocation failed for bot %s", incoming.bot_id)
            response_text = "Sorry, something went wrong. Please try again."

        # 8. Send tool event summaries (if any)
        for te in tool_events:
            if te.tool_name == "create_chart_tool":
                spec = parse_chart_spec(te.result)
                if spec is not None:
                    try:
                        await self._send_chart(bot, incoming, spec)
                    except Exception:
                        logger.debug("Failed to send chart for %s", te.tool_name)
                    continue
            args_str = ", ".join(f"{k}={v!r}" for k, v in te.args.items()) if te.args else ""
            result_preview = (te.result[:200] + "...") if len(te.result) > 200 else te.result
            tool_msg = f"🔧 {te.tool_name}({args_str})\n→ {result_preview}"
            try:
                await self._send_reply(bot, incoming, tool_msg)
            except Exception:
                logger.debug("Failed to send tool event for %s", te.tool_name)

        # 9. Send reply
        await self._send_reply(bot, incoming, response_text)

    # Access policy helpers

    @staticmethod
    def _parse_policy(bot: Any) -> dict[str, Any]:
        """Return bot.access_policy as a dict regardless of storage format.

        SQLite stores access_policy as a JSON string; PostgreSQL/MongoDB store
        it natively as a dict. This helper normalises both cases.
        """
        raw = bot.access_policy or {}
        if isinstance(raw, str):
            import json

            return json.loads(raw) if raw else {}
        return raw

    def _check_access(self, incoming: IncomingMessage, bot: Any) -> None:
        """Enforce access policy. Raises AuthorizationError if denied."""
        policy: dict[str, Any] = self._parse_policy(bot)
        mode: str = policy.get("mode", "open")

        if mode == "whitelist":
            whitelist: list[str] = [str(x) for x in policy.get("whitelist", [])]
            if str(incoming.platform_user_id) not in whitelist:
                raise AuthorizationError(
                    message=policy.get("denied_message", "You are not authorised to use this bot.")
                )
        elif mode == "group_only":
            allowed: list[str] = [str(x) for x in policy.get("allowed_groups", [])]
            if str(incoming.platform_chat_id) not in allowed:
                raise AuthorizationError(
                    message=policy.get(
                        "denied_message", "This bot is only available in specific groups."
                    )
                )
        # "open" and "jwt_linked" pass through here; jwt_linked is enforced at identity resolution

    # Command handling

    async def _handle_command(
        self, text: str, incoming: IncomingMessage, bot: Any, db: Any
    ) -> str | None:
        """Handle bot commands. Returns reply text or None if not a command."""
        if not text.startswith("/"):
            return None

        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().split("@")[0]  # strip @botname suffix
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/start":
            return (
                bot.welcome_message
                if hasattr(bot, "welcome_message") and bot.welcome_message
                else (
                    f"Welcome! I'm {bot.name}. How can I help you today?\n\n"
                    "Use /help to see available commands."
                )
            )

        if cmd == "/help":
            return (
                "Available commands:\n"
                "/start — Show welcome message\n"
                "/new — Start a new conversation\n"
                "/help — Show this help\n"
                "/link <code> — Link your account\n"
                "/unlink — Unlink your account"
            )

        if cmd == "/new":
            session = await channel_session_repo.get_by_bot_and_chat(
                db, bot_id=bot.id, platform_chat_id=incoming.platform_chat_id
            )
            if session:
                new_conv = await conversation_repo.create_conversation(
                    db, title=f"{incoming.platform.capitalize()} Chat"
                )
                await channel_session_repo.update(
                    db, db_session=session, update_data={"conversation_id": new_conv.id}
                )
            return "New conversation started! How can I help you?"

        if cmd == "/link":
            if not arg:
                return "Usage: /link <code>"
            try:
                linked = await channel_identity_repo.get_by_link_code(db, arg)
                if not linked or not linked.user_id:
                    return (
                        "Invalid or expired link code. Please generate a new one from the web app."
                    )
                identity = await channel_identity_repo.get_by_platform_user(
                    db,
                    platform=incoming.platform,
                    platform_user_id=incoming.platform_user_id,
                )
                if identity:
                    await channel_identity_repo.update(
                        db, db_identity=identity, update_data={"user_id": linked.user_id}
                    )
                else:
                    await channel_identity_repo.create(
                        db,
                        platform=incoming.platform,
                        platform_user_id=incoming.platform_user_id,
                        platform_username=incoming.platform_username,
                        platform_display_name=incoming.platform_display_name,
                        user_id=linked.user_id,
                    )
                await channel_identity_repo.update(
                    db,
                    db_identity=linked,
                    update_data={"link_code": None, "link_code_expires_at": None},
                )
                return "Successfully linked your account."
            except Exception:
                logger.exception("Unexpected error processing /link command")
                return "A system error occurred. Please try again later."

        if cmd == "/unlink":
            identity = await channel_identity_repo.get_by_platform_user(
                db,
                platform=incoming.platform,
                platform_user_id=incoming.platform_user_id,
            )
            if identity:
                await channel_identity_repo.update(
                    db, db_identity=identity, update_data={"user_id": None}
                )
            return "Your account has been unlinked."

        return None

    # Identity resolution

    async def _resolve_identity(self, incoming: IncomingMessage, bot: Any, db: Any) -> Any:
        """Get or create ChannelIdentity for this platform user."""
        policy: dict[str, Any] = self._parse_policy(bot)
        mode: str = policy.get("mode", "open")
        identity = await channel_identity_repo.get_by_platform_user(
            db,
            platform=incoming.platform,
            platform_user_id=incoming.platform_user_id,
        )
        if not identity:
            identity = await channel_identity_repo.create(
                db,
                platform=incoming.platform,
                platform_user_id=incoming.platform_user_id,
                platform_username=incoming.platform_username,
                platform_display_name=incoming.platform_display_name,
                user_id=None,
            )

        if mode == "jwt_linked" and policy.get("require_link", False) and not identity.user_id:
            raise AuthorizationError(
                message="Please /link your account first before using this bot."
            )

        return identity

    # Session resolution

    async def _resolve_session(
        self, incoming: IncomingMessage, bot: Any, identity: Any, db: Any
    ) -> Any:
        """Get or create ChannelSession (+ backing Conversation) for this bot+chat."""
        session = await channel_session_repo.get_by_bot_and_chat(
            db, bot_id=bot.id, platform_chat_id=incoming.platform_chat_id
        )
        if not session:
            conv = await conversation_repo.create_conversation(
                db,
                title=f"{incoming.platform.capitalize()} Chat",
                user_id=identity.user_id,
            )
            session = await channel_session_repo.create(
                db,
                bot_id=bot.id,
                identity_id=identity.id,
                platform_chat_id=incoming.platform_chat_id,
                conversation_id=conv.id,
            )
        return session

    # Rate limiting

    def _check_rate_limit(self, bot: Any, identity_id: str) -> None:
        """In-memory token-bucket rate limiter.

        Uses a module-level dict. Default: 10 req/minute from
        ``bot.access_policy.rate_limit_rpm``.

        Raises:
            BadRequestError: If the rate limit is exceeded.
        """
        policy: dict[str, Any] = self._parse_policy(bot)
        rpm: int = int(policy.get("rate_limit_rpm", _DEFAULT_RPM))
        window: float = 60.0

        key = f"{bot.id}:{identity_id}"
        now = time.monotonic()

        if key in _rate_buckets:
            count, window_start = _rate_buckets[key]
            if now - window_start < window:
                if count >= rpm:
                    raise BadRequestError(message="Rate limit exceeded. Please slow down.")
                _rate_buckets[key] = (count + 1, window_start)
            else:
                # Window expired — reset
                _rate_buckets[key] = (1, now)
        else:
            _rate_buckets[key] = (1, now)

    # Send helper

    async def _send_reply(self, bot: Any, incoming: IncomingMessage, text: str) -> None:
        """Decrypt the bot token and send a reply via the appropriate adapter."""
        try:
            adapter = get_adapter(incoming.platform)
            decrypted_token = decrypt_token(bot.token_encrypted)
            out = OutgoingMessage(
                platform_chat_id=incoming.platform_chat_id,
                text=text,
                parse_mode="Markdown",
                reply_to_message_id=incoming.message_id,
            )
            await adapter.send_message(decrypted_token, out)
        except Exception:
            logger.exception(
                "Failed to send reply for bot %s to chat %s",
                incoming.bot_id,
                incoming.platform_chat_id,
            )

    async def _send_chart(self, bot: Any, incoming: IncomingMessage, spec: Any) -> None:
        """Render a chart spec to PNG and send it; fall back to a text table."""
        try:
            png = render_chart_png(spec)
        except Exception:
            logger.debug("Chart PNG render failed; sending text fallback")
            await self._send_reply(bot, incoming, chart_to_markdown(spec))
            return

        adapter = get_adapter(incoming.platform)
        decrypted_token = decrypt_token(bot.token_encrypted)
        out = OutgoingMessage(
            platform_chat_id=incoming.platform_chat_id,
            text=spec.title,
            reply_to_message_id=incoming.message_id,
            image_png=png,
            image_filename="chart.png",
        )
        await adapter.send_message(decrypted_token, out)
