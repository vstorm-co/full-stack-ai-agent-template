"""Data access for user-configured MCP server connections (PostgreSQL async)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from app.db.models.mcp_connection import McpConnection


async def get_by_id(db: AsyncSession, connection_id: UUID) -> McpConnection | None:
    result = await db.execute(select(McpConnection).where(McpConnection.id == connection_id))
    return result.scalar_one_or_none()


async def get_by_id_for_update(db: AsyncSession, connection_id: UUID) -> McpConnection | None:
    """Fetch a connection and lock the row (``SELECT ... FOR UPDATE``).

    Used before spending an OAuth refresh token, so two concurrent chat turns
    can't both redeem it. ``lazyload`` drops the model's eager join on ``users``
    (PostgreSQL refuses ``FOR UPDATE`` on the nullable side of an outer join),
    and ``populate_existing`` re-reads the columns so the caller sees what the
    other transaction committed rather than the stale identity-map copy.
    """
    result = await db.execute(
        select(McpConnection)
        .where(McpConnection.id == connection_id)
        .options(lazyload(McpConnection.user))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def get_by_name(db: AsyncSession, *, user_id: UUID, name: str) -> McpConnection | None:
    result = await db.execute(
        select(McpConnection).where(
            McpConnection.user_id == user_id,
            McpConnection.name == name,
        )
    )
    return result.scalar_one_or_none()


async def get_by_oauth_state(db: AsyncSession, state: str) -> McpConnection | None:
    """Find the connection awaiting this OAuth callback (state is the CSRF token)."""
    result = await db.execute(select(McpConnection).where(McpConnection.oauth_state == state))
    return result.scalar_one_or_none()


async def list_for_user(
    db: AsyncSession, *, user_id: UUID, enabled_only: bool = False
) -> tuple[list[McpConnection], int]:
    stmt = (
        select(McpConnection)
        .where(McpConnection.user_id == user_id)
        .order_by(McpConnection.created_at.asc())
    )
    if enabled_only:
        stmt = stmt.where(McpConnection.is_enabled.is_(True))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    items = list((await db.execute(stmt)).scalars())
    return items, total


async def create(
    db: AsyncSession,
    *,
    user_id: UUID,
    name: str,
    url: str,
    auth_token: str | None,
    allowed_tools: list[str] | None,
    is_enabled: bool = True,
    auth_type: str = "bearer",
    oauth_state: str | None = None,
    oauth_payload: str | None = None,
    oauth_pending_payload: str | None = None,
) -> McpConnection:
    connection = McpConnection(
        user_id=user_id,
        name=name,
        url=url,
        auth_token=auth_token,
        allowed_tools=allowed_tools,
        is_enabled=is_enabled,
        auth_type=auth_type,
        oauth_state=oauth_state,
        oauth_payload=oauth_payload,
        oauth_pending_payload=oauth_pending_payload,
    )
    db.add(connection)
    await db.flush()
    await db.refresh(connection)
    return connection


async def update(
    db: AsyncSession,
    *,
    db_connection: McpConnection,
    update_data: dict[str, Any],
) -> McpConnection:
    for field, value in update_data.items():
        setattr(db_connection, field, value)
    await db.flush()
    await db.refresh(db_connection)
    return db_connection


async def delete(db: AsyncSession, *, db_connection: McpConnection) -> None:
    await db.delete(db_connection)
    await db.flush()
