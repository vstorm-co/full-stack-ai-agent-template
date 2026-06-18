"""ConversationShare repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation
from app.db.models.conversation_share import ConversationShare


async def get_by_id(db: AsyncSession, share_id: UUID) -> ConversationShare | None:
    """Get a share by ID."""
    return await db.get(ConversationShare, share_id)


async def get_share(
    db: AsyncSession, conversation_id: UUID, shared_with: UUID
) -> ConversationShare | None:
    """Get a share by conversation + user composite key."""
    result = await db.execute(
        select(ConversationShare).where(
            ConversationShare.conversation_id == conversation_id,
            ConversationShare.shared_with == shared_with,
        )
    )
    return result.scalar_one_or_none()


async def get_by_token(db: AsyncSession, token: str) -> ConversationShare | None:
    """Get a share by its public token."""
    result = await db.execute(
        select(ConversationShare).where(ConversationShare.share_token == token)
    )
    return result.scalar_one_or_none()


async def get_shares_for_conversation(
    db: AsyncSession, conversation_id: UUID
) -> list[ConversationShare]:
    """List all shares for a conversation."""
    result = await db.execute(
        select(ConversationShare)
        .where(ConversationShare.conversation_id == conversation_id)
        .order_by(ConversationShare.created_at.desc())
    )
    return list(result.scalars().all())


async def get_conversations_shared_with_user(
    db: AsyncSession, user_id: UUID, *, skip: int = 0, limit: int = 50
) -> list[Conversation]:
    """Get conversations shared with a specific user."""
    result = await db.execute(
        select(Conversation)
        .join(ConversationShare, ConversationShare.conversation_id == Conversation.id)
        .where(ConversationShare.shared_with == user_id)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_conversations_shared_with_user(db: AsyncSession, user_id: UUID) -> int:
    """Count conversations shared with a specific user."""
    result = await db.scalar(
        select(func.count())
        .select_from(ConversationShare)
        .where(ConversationShare.shared_with == user_id)
    )
    return result or 0


async def user_has_access(
    db: AsyncSession, conversation_id: UUID, user_id: UUID
) -> ConversationShare | None:
    """Check if user has any share access to a conversation."""
    return await get_share(db, conversation_id, user_id)


async def create(
    db: AsyncSession,
    *,
    conversation_id: UUID,
    shared_by: UUID,
    shared_with: UUID | None = None,
    share_token: str | None = None,
    permission: str = "view",
) -> ConversationShare:
    """Create a new conversation share."""
    share = ConversationShare(
        conversation_id=conversation_id,
        shared_by=shared_by,
        shared_with=shared_with,
        share_token=share_token,
        permission=permission,
    )
    db.add(share)
    await db.flush()
    await db.refresh(share)
    return share


async def update(
    db: AsyncSession,
    *,
    db_share: ConversationShare,
    update_data: dict,
) -> ConversationShare:
    """Update a conversation share."""
    for field, value in update_data.items():
        setattr(db_share, field, value)
    db.add(db_share)
    await db.flush()
    await db.refresh(db_share)
    return db_share


async def delete(db: AsyncSession, share_id: UUID) -> bool:
    """Delete a share by ID."""
    share = await get_by_id(db, share_id)
    if not share:
        return False
    await db.delete(share)
    await db.flush()
    return True
