"""Data access for user-scoped slash command settings (PostgreSQL async)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_slash_command import UserSlashCommand


async def get_by_id(db: AsyncSession, command_id: UUID) -> UserSlashCommand | None:
    result = await db.execute(select(UserSlashCommand).where(UserSlashCommand.id == command_id))
    return result.scalar_one_or_none()


async def get_by_name(
    db: AsyncSession, *, user_id: UUID, name: str
) -> UserSlashCommand | None:
    result = await db.execute(
        select(UserSlashCommand).where(
            UserSlashCommand.user_id == user_id,
            UserSlashCommand.name == name,
        )
    )
    return result.scalar_one_or_none()


async def list_for_user(
    db: AsyncSession, *, user_id: UUID
) -> tuple[list[UserSlashCommand], int]:
    stmt = (
        select(UserSlashCommand)
        .where(UserSlashCommand.user_id == user_id)
        .order_by(UserSlashCommand.created_at.asc())
    )
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    items = list((await db.execute(stmt)).scalars())
    return items, total


async def create(
    db: AsyncSession,
    *,
    user_id: UUID,
    name: str,
    prompt: str | None,
    is_enabled: bool = True,
) -> UserSlashCommand:
    cmd = UserSlashCommand(
        user_id=user_id,
        name=name,
        prompt=prompt,
        is_enabled=is_enabled,
    )
    db.add(cmd)
    await db.flush()
    await db.refresh(cmd)
    return cmd


async def update(
    db: AsyncSession,
    *,
    db_command: UserSlashCommand,
    update_data: dict[str, Any],
) -> UserSlashCommand:
    for field, value in update_data.items():
        setattr(db_command, field, value)
    await db.flush()
    await db.refresh(db_command)
    return db_command


async def delete(db: AsyncSession, *, db_command: UserSlashCommand) -> None:
    await db.delete(db_command)
    await db.flush()


