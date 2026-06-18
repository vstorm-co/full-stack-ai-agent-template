"""ConversationShareService — sharing conversations between users (PostgreSQL async)."""

import logging
import secrets
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, AuthorizationError, NotFoundError
from app.repositories import conversation_repo, conversation_share_repo, user_repo

logger = logging.getLogger(__name__)


class ConversationShareService:
    """Business logic for conversation sharing."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def check_edit_permission(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> None:
        """Verify the user is the owner or has an 'edit' share.

        Raises:
            NotFoundError: If conversation does not exist.
            AuthorizationError: If user has no edit access.
        """
        conv = await conversation_repo.get_conversation_by_id(self.db, conversation_id)
        if not conv:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": str(conversation_id)},
            )
        if conv.user_id == user_id:
            return
        share = await conversation_share_repo.get_share(self.db, conversation_id, user_id)
        if share and share.permission == "edit":
            return
        raise AuthorizationError(
            message="You do not have edit permission for this conversation",
            details={"conversation_id": str(conversation_id)},
        )

    async def share_conversation(
        self,
        conversation_id: UUID,
        shared_by: UUID,
        *,
        shared_with: UUID | None = None,
        generate_link: bool = False,
        permission: str = "view",
    ) -> dict:
        """Share a conversation with a user or generate a public link.

        Only the conversation owner can share.
        """
        conv = await conversation_repo.get_conversation_by_id(self.db, conversation_id)
        if not conv:
            raise NotFoundError(
                message="Conversation not found", details={"conversation_id": str(conversation_id)}
            )
        if conv.user_id != shared_by:
            raise AuthorizationError(message="Only the conversation owner can share it")

        share_token = None

        if generate_link:
            share_token = secrets.token_urlsafe(32)
            share = await conversation_share_repo.create(
                self.db,
                conversation_id=conversation_id,
                shared_by=shared_by,
                share_token=share_token,
                permission=permission,
            )
            return {"share": share, "share_url": f"/shared/{share_token}"}

        if shared_with is None:
            raise NotFoundError(message="Must provide shared_with user ID or generate_link=true")
        if shared_with == shared_by:
            raise AlreadyExistsError(message="Cannot share a conversation with yourself")

        # Verify target user exists
        target_user = await user_repo.get_by_id(self.db, shared_with)
        if not target_user:
            raise NotFoundError(message="User not found", details={"user_id": str(shared_with)})

        existing = await conversation_share_repo.get_share(self.db, conversation_id, shared_with)
        if existing:
            raise AlreadyExistsError(
                message="Conversation already shared with this user",
                details={"shared_with": str(shared_with)},
            )

        share = await conversation_share_repo.create(
            self.db,
            conversation_id=conversation_id,
            shared_by=shared_by,
            shared_with=shared_with,
            permission=permission,
        )
        return {"share": share}

    async def list_shares(self, conversation_id: UUID, user_id: UUID) -> list:
        """List all shares for a conversation. Owner only."""
        conv = await conversation_repo.get_conversation_by_id(self.db, conversation_id)
        if not conv:
            raise NotFoundError(message="Conversation not found")
        if conv.user_id != user_id:
            raise AuthorizationError(message="Only the conversation owner can view shares")

        return await conversation_share_repo.get_shares_for_conversation(self.db, conversation_id)

    async def revoke_share(self, share_id: UUID, user_id: UUID) -> None:
        """Revoke a share. Owner of conversation or the shared_with user can revoke."""
        share = await conversation_share_repo.get_by_id(self.db, share_id)
        if not share:
            raise NotFoundError(message="Share not found", details={"share_id": str(share_id)})

        # Owner or the recipient can revoke
        if share.shared_by != user_id and share.shared_with != user_id:
            raise AuthorizationError(message="Not authorized to revoke this share")

        await conversation_share_repo.delete(self.db, share_id)

    async def list_shared_with_me(
        self, user_id: UUID, *, skip: int = 0, limit: int = 50
    ) -> tuple[list, int]:
        """List conversations shared with the current user."""
        items = await conversation_share_repo.get_conversations_shared_with_user(
            self.db, user_id, skip=skip, limit=limit
        )
        total = await conversation_share_repo.count_conversations_shared_with_user(self.db, user_id)
        return items, total

    async def get_by_token(self, token: str) -> dict:
        """Get a shared conversation by its public token."""
        share = await conversation_share_repo.get_by_token(self.db, token)
        if not share:
            raise NotFoundError(message="Share link not found or expired")
        conv = await conversation_repo.get_conversation_by_id(
            self.db, share.conversation_id, include_messages=True
        )
        if not conv:
            raise NotFoundError(message="Conversation not found")
        return {
            "conversation": {
                "id": str(conv.id),
                "title": conv.title,
                "messages": [
                    {
                        "id": str(m.id),
                        "role": m.role,
                        "content": m.content,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in (conv.messages or [])
                ],
            },
            "share": {
                "id": str(share.id),
                "permission": share.permission,
                "share_token": share.share_token,
            },
        }
