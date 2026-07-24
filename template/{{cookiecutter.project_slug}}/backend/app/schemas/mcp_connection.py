"""Schemas for user-configured MCP server connections."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.db.models.mcp_connection import McpConnection
from app.schemas.base import BaseSchema, TimestampSchema

# Slug-style names: lowercase letters, digits, hyphens. The name doubles as
# the tool prefix in the agent (sanitized to snake_case), so keep it tight.
NAME_PATTERN = r"^[a-z0-9][a-z0-9-]{0,31}$"

MAX_ALLOWED_TOOLS = 100


class McpConnectionCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=32, pattern=NAME_PATTERN)
    url: str = Field(..., min_length=1, max_length=2048)
    # Sent as "Authorization: Bearer <token>" to the MCP server.
    auth_token: str | None = Field(default=None, max_length=4096)
    # None = expose every tool the server offers.
    allowed_tools: list[str] | None = Field(default=None, max_length=MAX_ALLOWED_TOOLS)
    is_enabled: bool = True


class McpConnectionUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=32, pattern=NAME_PATTERN)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    # None = leave unchanged; "" = clear the stored token.
    auth_token: str | None = Field(default=None, max_length=4096)
    allowed_tools: list[str] | None = Field(default=None, max_length=MAX_ALLOWED_TOOLS)
    # Explicit marker to reset allowed_tools back to "all tools" (since None
    # in a PATCH body is indistinguishable from "not provided").
    clear_allowed_tools: bool = False
    is_enabled: bool | None = None


class McpConnectionRead(TimestampSchema, BaseSchema):
    id: UUID
    name: str
    url: str
    # The token itself never leaves the backend.
    has_auth_token: bool
    allowed_tools: list[str] | None
    is_enabled: bool
    # "bearer" or "oauth".
    auth_type: str
    # OAuth connection that has completed the consent flow (has usable tokens).
    # False for a bearer connection or an OAuth connection still awaiting consent.
    oauth_authorized: bool
    last_status: str | None
    last_error: str | None
    last_checked_at: datetime | None

    @classmethod
    def from_model(cls, connection: McpConnection) -> McpConnectionRead:
        # Authorized once the live payload is written, which happens only after
        # a successful token exchange — this avoids decrypting it just to render
        # the list. A pending re-authorization lives in oauth_pending_payload
        # and must not flip a working connection back to "not connected".
        oauth_authorized = (
            connection.auth_type == "oauth" and connection.oauth_payload is not None
        )
        return cls(
            id=connection.id,
            name=connection.name,
            url=connection.url,
            has_auth_token=connection.auth_token is not None,
            allowed_tools=connection.allowed_tools,
            is_enabled=connection.is_enabled,
            auth_type=connection.auth_type,
            oauth_authorized=oauth_authorized,
            last_status=connection.last_status,
            last_error=connection.last_error,
            last_checked_at=connection.last_checked_at,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )


class McpConnectionList(BaseSchema):
    items: list[McpConnectionRead]
    total: int


class McpToolRead(BaseSchema):
    name: str
    description: str


class WorkspaceMcpServerRead(BaseSchema):
    """Deployment-managed server from MCP_SERVERS — read-only in the UI.

    Deliberately omits the URL and headers: those are deployment config and
    may point at internal infrastructure.
    """

    name: str
    allowed_tools: list[str] | None


class WorkspaceMcpServerList(BaseSchema):
    items: list[WorkspaceMcpServerRead]
    total: int


class McpConnectionTestResult(BaseSchema):
    ok: bool
    error: str | None = None
    tools: list[McpToolRead] = []


class McpOAuthStart(BaseSchema):
    """Begin the OAuth flow for a server (catalog or custom)."""

    name: str = Field(..., min_length=1, max_length=32, pattern=NAME_PATTERN)
    url: str = Field(..., min_length=1, max_length=2048)


class McpOAuthStartResult(BaseSchema):
    # The provider consent URL the browser should be redirected to.
    authorization_url: str


class McpOAuthCallback(BaseSchema):
    """Payload the frontend callback route forwards from the provider redirect."""

    state: str = Field(..., min_length=1, max_length=128)
    code: str = Field(..., min_length=1, max_length=4096)


class McpOAuthCallbackResult(BaseSchema):
    ok: bool
    connection_name: str | None = None
    error: str | None = None
