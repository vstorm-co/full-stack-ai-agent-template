"""Business logic for user-configured MCP server connections.

Connections are user-scoped rows (Settings → Integrations) pointing at
remote MCP servers (streamable HTTP or SSE, inferred from the URL). The
service owns:
  - SSRF validation of user-supplied URLs (same policy as webhooks),
  - at-rest encryption of bearer tokens (Fernet, see app/core/crypto.py),
  - the connectivity test that discovers the server's tools, and
  - building per-turn agent toolsets from the user's enabled connections.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from mcp.shared.auth import OAuthToken
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import mcp_oauth
from app.agents.mcp import (
    McpServerSpec,
    McpToolInfo,
    build_mcp_toolsets,
    probe_error_message,
    probe_mcp_server,
    static_server_specs,
)
from app.agents.mcp_oauth import McpOAuthPayload, OAuthError
from app.core.config import settings
from app.core.crypto import decrypt_value, encrypt_value
from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.core.sanitize import validate_webhook_url
from app.db.models.mcp_connection import McpConnection
from app.db.session import get_db_context
from app.repositories import mcp_connection_repo
from app.schemas.mcp_connection import McpConnectionCreate, McpConnectionUpdate

logger = logging.getLogger(__name__)


def _oauth_redirect_uri() -> str:
    """Where the provider sends the user back — a Next route that forwards the
    code + state to our (state-authenticated) callback endpoint."""
    return f"{settings.FRONTEND_URL.rstrip('/')}/api/me/mcp-connections/oauth/callback"


def _now_epoch() -> float:
    return datetime.now(UTC).timestamp()


def _apply_token(payload: McpOAuthPayload, token: OAuthToken) -> McpOAuthPayload:
    """Fold a fresh token grant/refresh into the stored payload."""
    return payload.model_copy(
        update={
            "access_token": token.access_token,
            # A refresh response may omit refresh_token — keep the existing one.
            "refresh_token": token.refresh_token or payload.refresh_token,
            "expires_at": (_now_epoch() + token.expires_in) if token.expires_in else None,
            "scope": token.scope or payload.scope,
            "code_verifier": None,
        }
    )


async def _validate_url(url: str) -> str:
    """SSRF-check a user-supplied MCP server URL (same policy as webhooks).

    Runs in a thread because validation resolves DNS (blocking I/O).
    """
    return await asyncio.to_thread(validate_webhook_url, url)


async def _oauth_access_token(db: AsyncSession, connection: McpConnection) -> str | None:
    """A currently-valid access token for an OAuth connection, refreshing and
    persisting if needed. None when the connection isn't authorized yet, its
    token expired with no refresh path, or the payload can't be decrypted."""
    if not connection.oauth_payload:
        return None
    try:
        payload = McpOAuthPayload.model_validate_json(
            decrypt_value(connection.oauth_payload, settings.SECRET_KEY)
        )
    except Exception:
        logger.warning("Cannot decrypt OAuth payload for MCP connection %r", connection.name)
        return None
    if not payload.access_token:
        return None  # awaiting consent
    fresh_enough = (
        payload.expires_at is None
        or _now_epoch() < payload.expires_at - mcp_oauth.TOKEN_EXPIRY_SKEW_SECS
    )
    if fresh_enough:
        return payload.access_token
    if not payload.refresh_token:
        return None  # expired, no refresh token → user must re-authorize
    try:
        token = await mcp_oauth.refresh_tokens(
            token_endpoint=payload.token_endpoint,
            client_id=payload.client_id,
            client_secret=payload.client_secret,
            refresh_token=payload.refresh_token,
            resource=payload.resource,
            scope=payload.scope,
        )
    except OAuthError as exc:
        logger.warning("OAuth token refresh failed for %r: %s", connection.name, exc)
        return None
    payload = _apply_token(payload, token)
    await mcp_connection_repo.update(
        db,
        db_connection=connection,
        update_data={
            "oauth_payload": encrypt_value(payload.model_dump_json(), settings.SECRET_KEY)
        },
    )
    return payload.access_token


async def _resolve_auth_headers(
    db: AsyncSession, connection: McpConnection
) -> dict[str, str] | None:
    """Auth headers to reach *connection*, or None if it can't be used right now
    (OAuth not authorized / expired, or an undecryptable bearer token)."""
    if connection.auth_type == "oauth":
        token = await _oauth_access_token(db, connection)
        return {"Authorization": f"Bearer {token}"} if token else None
    if connection.auth_token is None:
        return {}
    try:
        token = decrypt_value(connection.auth_token, settings.SECRET_KEY)
    except Exception:
        logger.warning("Cannot decrypt auth token for MCP connection %r", connection.name)
        return None
    return {"Authorization": f"Bearer {token}"}


class McpConnectionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_user(self, *, user_id: UUID) -> tuple[list[McpConnection], int]:
        return await mcp_connection_repo.list_for_user(self.db, user_id=user_id)

    async def create(self, *, user_id: UUID, data: McpConnectionCreate) -> McpConnection:
        url = await _validate_url(data.url)
        existing = await mcp_connection_repo.get_by_name(self.db, user_id=user_id, name=data.name)
        if existing is not None:
            raise AlreadyExistsError(
                message="MCP connection with this name already exists",
                details={"name": data.name},
            )
        token = data.auth_token.strip() if data.auth_token else None
        try:
            return await mcp_connection_repo.create(
                self.db,
                user_id=user_id,
                name=data.name,
                url=url,
                auth_token=encrypt_value(token, settings.SECRET_KEY) if token else None,
                allowed_tools=data.allowed_tools,
                is_enabled=data.is_enabled,
            )
        except IntegrityError as exc:
            raise AlreadyExistsError(
                message="MCP connection with this name already exists",
                details={"name": data.name},
            ) from exc

    async def update(
        self, *, user_id: UUID, connection_id: UUID, data: McpConnectionUpdate
    ) -> McpConnection:
        db_connection = await self._get_owned(user_id=user_id, connection_id=connection_id)
        update_data: dict[str, Any] = data.model_dump(
            exclude_unset=True, exclude={"clear_allowed_tools"}
        )

        if "url" in update_data:
            update_data["url"] = await _validate_url(update_data["url"])

        if "name" in update_data and update_data["name"] != db_connection.name:
            collision = await mcp_connection_repo.get_by_name(
                self.db, user_id=user_id, name=update_data["name"]
            )
            if collision is not None and collision.id != db_connection.id:
                raise AlreadyExistsError(
                    message="MCP connection with this name already exists",
                    details={"name": update_data["name"]},
                )

        if "auth_token" in update_data:
            token = (update_data["auth_token"] or "").strip()
            # "" clears the stored token; a non-empty value replaces it.
            update_data["auth_token"] = encrypt_value(token, settings.SECRET_KEY) if token else None

        if data.clear_allowed_tools:
            update_data["allowed_tools"] = None

        # URL or credentials changed → the previous check result is stale.
        if "url" in update_data or "auth_token" in update_data:
            update_data.setdefault("last_status", None)
            update_data.setdefault("last_error", None)
            update_data.setdefault("last_checked_at", None)

        if not update_data:
            return db_connection
        return await mcp_connection_repo.update(
            self.db, db_connection=db_connection, update_data=update_data
        )

    async def delete(self, *, user_id: UUID, connection_id: UUID) -> None:
        db_connection = await self._get_owned(user_id=user_id, connection_id=connection_id)
        await mcp_connection_repo.delete(self.db, db_connection=db_connection)

    async def test(
        self, *, user_id: UUID, connection_id: UUID
    ) -> tuple[McpConnection, list[McpToolInfo], str | None]:
        """Probe the server, persist the result, and return discovered tools."""
        db_connection = await self._get_owned(user_id=user_id, connection_id=connection_id)
        tools: list[McpToolInfo] = []
        error: str | None = None
        headers = await _resolve_auth_headers(self.db, db_connection)
        if headers is None:
            error = "This plugin needs to be authorized before it can connect."
        else:
            try:
                tools = await probe_mcp_server(db_connection.url, headers)
            except Exception as exc:
                error = probe_error_message(exc)
        db_connection = await mcp_connection_repo.update(
            self.db,
            db_connection=db_connection,
            update_data={
                "last_status": "error" if error else "ok",
                "last_error": error,
                "last_checked_at": datetime.now(UTC),
            },
        )
        return db_connection, tools, error

    async def oauth_start(self, *, user_id: UUID, name: str, url: str) -> str:
        """Begin the OAuth authorization-code flow for a server.

        Discovers the authorization server, dynamically registers this app,
        stores the flow state (endpoints, client creds, PKCE verifier) on a
        pending connection row, and returns the provider consent URL. Creating
        again with the same name re-authorizes the existing OAuth connection.
        """
        url = await _validate_url(url)
        server = await mcp_oauth.discover(url)  # raises OAuthError if unsupported
        redirect_uri = _oauth_redirect_uri()
        client_id, client_secret = await mcp_oauth.register_client(server, redirect_uri)
        pkce = mcp_oauth.new_pkce()
        state = secrets.token_urlsafe(32)
        payload = McpOAuthPayload(
            authorization_endpoint=server.authorization_endpoint,
            token_endpoint=server.token_endpoint,
            registration_endpoint=server.registration_endpoint,
            client_id=client_id,
            client_secret=client_secret,
            scope=server.scope,
            resource=server.resource,
            redirect_uri=redirect_uri,
            code_verifier=pkce.code_verifier,
        )
        enc = encrypt_value(payload.model_dump_json(), settings.SECRET_KEY)

        existing = await mcp_connection_repo.get_by_name(self.db, user_id=user_id, name=name)
        if existing is not None:
            if existing.auth_type != "oauth":
                raise AlreadyExistsError(
                    message="A connection with this name already exists",
                    details={"name": name},
                )
            await mcp_connection_repo.update(
                self.db,
                db_connection=existing,
                update_data={
                    "url": url,
                    "auth_type": "oauth",
                    "is_enabled": True,
                    "oauth_state": state,
                    "oauth_payload": enc,
                    "last_status": None,
                    "last_error": None,
                    "last_checked_at": None,
                },
            )
        else:
            await mcp_connection_repo.create(
                self.db,
                user_id=user_id,
                name=name,
                url=url,
                auth_token=None,
                allowed_tools=None,
                is_enabled=True,
                auth_type="oauth",
                oauth_state=state,
                oauth_payload=enc,
            )
        return mcp_oauth.authorization_url(
            server,
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=pkce.code_challenge,
        )

    async def oauth_callback(self, *, state: str, code: str) -> McpConnection:
        """Complete the flow: exchange the code for tokens and store them.

        Authenticated by *state* (an unguessable CSRF token we issued), so this
        needs no user session — the provider redirect lands here without our
        cookies. Clears ``oauth_state`` so the connection reads as authorized.
        """
        connection = await mcp_connection_repo.get_by_oauth_state(self.db, state)
        if connection is None or not connection.oauth_payload:
            raise NotFoundError(message="OAuth session not found or already completed")
        payload = McpOAuthPayload.model_validate_json(
            decrypt_value(connection.oauth_payload, settings.SECRET_KEY)
        )
        if not payload.code_verifier:
            raise OAuthError("This authorization session has expired — start again.")
        token = await mcp_oauth.exchange_code(
            token_endpoint=payload.token_endpoint,
            client_id=payload.client_id,
            client_secret=payload.client_secret,
            code=code,
            code_verifier=payload.code_verifier,
            redirect_uri=payload.redirect_uri,
            resource=payload.resource,
        )
        payload = _apply_token(payload, token)
        return await mcp_connection_repo.update(
            self.db,
            db_connection=connection,
            update_data={
                "oauth_payload": encrypt_value(payload.model_dump_json(), settings.SECRET_KEY),
                "oauth_state": None,
                "last_status": "ok",
                "last_error": None,
                "last_checked_at": datetime.now(UTC),
            },
        )

    async def _get_owned(self, *, user_id: UUID, connection_id: UUID) -> McpConnection:
        db_connection = await mcp_connection_repo.get_by_id(self.db, connection_id)
        if db_connection is None or db_connection.user_id != user_id:
            raise NotFoundError(
                message="MCP connection not found",
                details={"connection_id": str(connection_id)},
            )
        return db_connection


async def build_toolsets_for_user(user_id: UUID) -> list[Any]:
    """Agent toolsets for one chat turn: static MCP_SERVERS + the user's
    enabled connections. Unreachable servers are skipped, never fatal."""
    specs = static_server_specs()
    async with get_db_context() as db:
        connections, _ = await mcp_connection_repo.list_for_user(
            db, user_id=user_id, enabled_only=True
        )
        for connection in connections:
            headers = await _resolve_auth_headers(db, connection)
            if headers is None:
                # OAuth not authorized / expired, or an undecryptable bearer token
                # (e.g. SECRET_KEY rotated) — skip, never crash the chat turn.
                logger.info("Skipping MCP connection %r: no usable credentials", connection.name)
                continue
            specs.append(
                McpServerSpec(
                    name=connection.name,
                    url=connection.url,
                    headers=headers,
                    allowed_tools=connection.allowed_tools,
                )
            )
    return await build_mcp_toolsets(specs)
