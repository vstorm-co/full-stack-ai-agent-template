"""User-configured MCP server connections (Settings → Integrations).

Each row is one remote MCP server the user attached to their assistant.
``auth_token`` is stored Fernet-encrypted (see :mod:`app.core.crypto`) —
it must be recoverable to send as a Bearer header on every request, so
hashing is not an option, but a DB dump alone must not leak it.

``allowed_tools`` is NULL when the user exposes every tool the server
offers; otherwise it's the list of unprefixed tool names they picked.

``auth_type`` is ``"bearer"`` (a static token in ``auth_token``) or
``"oauth"`` (the OAuth 2.1 authorization-code flow, RFC 9728 / 8414 /
7591 + PKCE). For OAuth connections the discovered endpoints, registered
client credentials and access/refresh tokens live Fernet-encrypted in
``oauth_payload`` (a JSON blob). An authorization redirect that is still
in flight is staged separately in ``oauth_pending_payload`` (keyed by the
CSRF token in ``oauth_state``) and only replaces ``oauth_payload`` once
the callback brings back real tokens.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class McpConnection(Base, TimestampMixin):
    """One user-scoped MCP server connection."""

    __tablename__ = "mcp_connections"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_mcp_connections_user_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    auth_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_tools: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # "bearer" (static token in auth_token) or "oauth" (authorization-code flow).
    auth_type: Mapped[str] = mapped_column(String(16), nullable=False, default="bearer")
    # CSRF token for an in-flight OAuth authorization redirect; NULL once done.
    oauth_state: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    # Fernet-encrypted JSON: endpoints, client creds, tokens. Written only by a
    # completed flow, so a connection that has this is usable right now.
    oauth_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Same shape, for a consent redirect that is still in flight (endpoints,
    # client creds, PKCE verifier, no tokens). Kept apart from oauth_payload so
    # re-authorizing never destroys credentials that still work.
    oauth_pending_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Result of the most recent connectivity check ("ok" / "error").
    last_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return f"<McpConnection(name={self.name} url={self.url} enabled={self.is_enabled})>"
