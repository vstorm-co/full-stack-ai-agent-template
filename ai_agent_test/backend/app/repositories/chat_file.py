"""Chat file repository (PostgreSQL async).

Contains database operations for ChatFile entities.
"""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat_file import ChatFile


async def get_by_id(db: AsyncSession, file_id: UUID) -> ChatFile | None:
    """Get a chat file by ID."""
    return await db.get(ChatFile, file_id)


async def get_many(db: AsyncSession, file_ids: Iterable[UUID]) -> list[ChatFile]:
    """Batch-load multiple chat files by IDs."""
    ids = list(file_ids)
    if not ids:
        return []
    result = await db.execute(select(ChatFile).where(ChatFile.id.in_(ids)))
    return list(result.scalars().all())


async def link_to_message(db: AsyncSession, *, message_id: UUID, file_ids: Iterable[UUID]) -> None:
    """Link multiple chat files to a message by setting message_id on each."""
    from sqlalchemy import update as sql_update

    ids = list(file_ids)
    if not ids:
        return
    await db.execute(sql_update(ChatFile).where(ChatFile.id.in_(ids)).values(message_id=message_id))
    await db.flush()


async def create(
    db: AsyncSession,
    *,
    user_id: UUID,
    filename: str,
    mime_type: str,
    size: int,
    storage_path: str,
    file_type: str,
    parsed_content: str | None = None,
) -> ChatFile:
    """Create a new chat file record."""
    chat_file = ChatFile(
        user_id=user_id,
        filename=filename,
        mime_type=mime_type,
        size=size,
        storage_path=storage_path,
        file_type=file_type,
        parsed_content=parsed_content,
    )
    db.add(chat_file)
    await db.flush()
    return chat_file
