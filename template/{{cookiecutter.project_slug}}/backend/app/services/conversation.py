{%- if cookiecutter.use_postgresql %}
"""Conversation service (PostgreSQL async).

Contains business logic for conversation, message, and tool call operations.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.conversation import Conversation, Message, ToolCall
from app.repositories import conversation_repo
{%- if cookiecutter.use_jwt %}
from app.repositories import conversation_share_repo
{%- endif %}
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
    ToolCallCreate,
    ToolCallComplete,
)


logger = logging.getLogger(__name__)

# Maximum number of conversations to export in a single request to prevent DoS.
MAX_EXPORT_LIMIT = 1000


class ConversationService:
    """Service for conversation-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Export Methods

    async def export_all(self) -> list[dict[str, Any]]:
        """Export all conversations with messages for admin download."""
        import json

        items, _ = await self.list_conversations(skip=0, limit=10000, include_archived=True)
        export_data = []
        for conv in items:
            messages, _ = await self.list_messages(conv.id, skip=0, limit=10000, include_tool_calls=True)
            export_data.append({
                "id": str(conv.id), "title": conv.title,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "is_archived": conv.is_archived,
                "messages": [{"id": str(m.id), "role": m.role, "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "tool_calls": [{"tool_name": tc.tool_name,
                        "args": tc.args if isinstance(tc.args, dict) else json.loads(tc.args) if isinstance(tc.args, str) and tc.args.strip() else {},
                        "result": tc.result, "status": tc.status}
                        for tc in (m.tool_calls or [])] if hasattr(m, "tool_calls") and m.tool_calls else [],
                } for m in messages],
            })
        return export_data

    # Conversation Methods

    async def get_conversation(
        self,
        conversation_id: UUID,
        *,
        include_messages: bool = False,
{%- if cookiecutter.use_jwt %}
        user_id: UUID | None = None,
{%- endif %}
    ) -> Conversation:
        """Get conversation by ID.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        conversation = await conversation_repo.get_conversation_by_id(
            self.db, conversation_id, include_messages=include_messages
        )
        if not conversation:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": str(conversation_id)},
            )
{%- if cookiecutter.use_jwt %}
        if (
            user_id is not None
            and hasattr(conversation, "user_id")
            and conversation.user_id is not None
            and str(conversation.user_id) != str(user_id)
        ):
            # Not the owner — check if user has a share granting access
            share = await conversation_share_repo.get_share(
                self.db, conversation_id, user_id
            )
            if not share:
                raise NotFoundError(
                    message="Conversation not found",
                    details={"conversation_id": str(conversation_id)},
                )
{%- endif %}
        return conversation

    async def list_conversations(
        self,
{%- if cookiecutter.use_jwt %}
        user_id: UUID | None = None,
{%- endif %}
        *,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = False,
    ) -> tuple[list[Conversation], int]:
        """List conversations with pagination.

        Returns:
            Tuple of (conversations, total_count).
        """
        items = await conversation_repo.get_conversations_by_user(
            self.db,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
            skip=skip,
            limit=limit,
            include_archived=include_archived,
        )
        total = await conversation_repo.count_conversations(
            self.db,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
            include_archived=include_archived,
        )
        return items, total

    async def create_conversation(
        self,
        data: ConversationCreate,
    ) -> Conversation:
        """Create a new conversation."""
        return await conversation_repo.create_conversation(
            self.db,
{%- if cookiecutter.use_jwt %}
            user_id=data.user_id,
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
            project_id=data.project_id,
{%- endif %}
            title=data.title,
        )

    async def update_conversation(
        self,
        conversation_id: UUID,
        data: ConversationUpdate,
{%- if cookiecutter.use_jwt %}
        user_id: UUID | None = None,
{%- endif %}
    ) -> Conversation:
        """Update a conversation.

        Raises:
            NotFoundError: If conversation does not exist.
        """
        conversation = await self.get_conversation(
            conversation_id,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
        )
        update_data = data.model_dump(exclude_unset=True)
        return await conversation_repo.update_conversation(
            self.db, db_conversation=conversation, update_data=update_data
        )

    async def archive_conversation(
        self,
        conversation_id: UUID,
{%- if cookiecutter.use_jwt %}
        user_id: UUID | None = None,
{%- endif %}
    ) -> Conversation:
        """Archive a conversation.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        # Verify ownership first
        await self.get_conversation(
            conversation_id,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
        )
        conversation = await conversation_repo.archive_conversation(
            self.db, conversation_id
        )
        if not conversation:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": str(conversation_id)},
            )
        return conversation

    async def delete_conversation(
        self,
        conversation_id: UUID,
{%- if cookiecutter.use_jwt %}
        user_id: UUID | None = None,
{%- endif %}
    ) -> bool:
        """Delete a conversation.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        # Verify ownership first
        await self.get_conversation(
            conversation_id,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
        )
        deleted = await conversation_repo.delete_conversation(self.db, conversation_id)
        if not deleted:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": str(conversation_id)},
            )
        return True

    # Message Methods

    async def get_message(self, message_id: UUID) -> Message:
        """Get message by ID.

        Raises:
            NotFoundError: If message does not exist.
        """
        message = await conversation_repo.get_message_by_id(self.db, message_id)
        if not message:
            raise NotFoundError(
                message="Message not found",
                details={"message_id": str(message_id)},
            )
        return message

    async def list_messages(
        self,
        conversation_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        include_tool_calls: bool = False,
    ) -> tuple[list[Message], int]:
        """List messages in a conversation.

        Returns:
            Tuple of (messages, total_count).
        """
        # Verify conversation exists
        await self.get_conversation(conversation_id)
        items = await conversation_repo.get_messages_by_conversation(
            self.db,
            conversation_id,
            skip=skip,
            limit=limit,
            include_tool_calls=include_tool_calls,
        )
        total = await conversation_repo.count_messages(self.db, conversation_id)
        return items, total

    async def add_message(
        self,
        conversation_id: UUID,
        data: MessageCreate,
    ) -> Message:
        """Add a message to a conversation.

        Raises:
            NotFoundError: If conversation does not exist.
        """
        # Verify conversation exists
        await self.get_conversation(conversation_id)
        return await conversation_repo.create_message(
            self.db,
            conversation_id=conversation_id,
            role=data.role,
            content=data.content,
            model_name=data.model_name,
            tokens_used=data.tokens_used,
        )

    async def delete_message(self, message_id: UUID) -> bool:
        """Delete a message.

        Raises:
            NotFoundError: If message does not exist.
        """
        deleted = await conversation_repo.delete_message(self.db, message_id)
        if not deleted:
            raise NotFoundError(
                message="Message not found",
                details={"message_id": str(message_id)},
            )
        return True

    # Tool Call Methods

    async def get_tool_call(self, tool_call_id: UUID) -> ToolCall:
        """Get tool call by ID.

        Raises:
            NotFoundError: If tool call does not exist.
        """
        tool_call = await conversation_repo.get_tool_call_by_id(self.db, tool_call_id)
        if not tool_call:
            raise NotFoundError(
                message="Tool call not found",
                details={"tool_call_id": str(tool_call_id)},
            )
        return tool_call

    async def list_tool_calls(self, message_id: UUID) -> list[ToolCall]:
        """List tool calls for a message."""
        # Verify message exists
        await self.get_message(message_id)
        return await conversation_repo.get_tool_calls_by_message(self.db, message_id)

    async def start_tool_call(
        self,
        message_id: UUID,
        data: ToolCallCreate,
    ) -> ToolCall:
        """Record the start of a tool call.

        Raises:
            NotFoundError: If message does not exist.
        """
        # Verify message exists
        await self.get_message(message_id)
        return await conversation_repo.create_tool_call(
            self.db,
            message_id=message_id,
            tool_call_id=data.tool_call_id,
            tool_name=data.tool_name,
            args=data.args,
            started_at=data.started_at or datetime.now(UTC),
        )

    async def complete_tool_call(
        self,
        tool_call_id: UUID,
        data: ToolCallComplete,
    ) -> ToolCall:
        """Mark a tool call as completed.

        Raises:
            NotFoundError: If tool call does not exist.
        """
        tool_call = await self.get_tool_call(tool_call_id)
        return await conversation_repo.complete_tool_call(
            self.db,
            db_tool_call=tool_call,
            result=data.result,
            completed_at=data.completed_at or datetime.now(UTC),
            success=data.success,
        )


    async def link_files_to_message(self, message_id: UUID, file_ids: list[str]) -> None:
        """Link uploaded chat files to a message."""
        if not file_ids:
            return
        from app.db.models.chat_file import ChatFile
        from sqlalchemy import update as sa_update
        file_uuids = [UUID(fid) for fid in file_ids]
        await self.db.execute(
            sa_update(ChatFile).where(ChatFile.id.in_(file_uuids)).values(message_id=message_id)
        )
        await self.db.flush()


{%- elif cookiecutter.use_sqlite %}
"""Conversation service (SQLite sync).

Contains business logic for conversation, message, and tool call operations.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models.conversation import Conversation, Message, ToolCall
from app.repositories import conversation_repo
{%- if cookiecutter.use_jwt %}
from app.repositories import conversation_share_repo
{%- endif %}
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
    ToolCallCreate,
    ToolCallComplete,
)


class ConversationService:
    """Service for conversation-related business logic."""

    def __init__(self, db: Session):
        self.db = db

    # Export Methods

    def export_all(self) -> list[dict[str, Any]]:
        """Export all conversations with messages for admin download."""
        import json as _json

        items, _ = self.list_conversations(skip=0, limit=10000, include_archived=True)
        export_data = []
        for conv in items:
            messages, _ = self.list_messages(conv.id, skip=0, limit=10000, include_tool_calls=True)
            export_data.append({
                "id": str(conv.id), "title": conv.title,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "is_archived": conv.is_archived,
                "messages": [{"id": str(m.id), "role": m.role, "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "tool_calls": [{"tool_name": tc.tool_name,
                        "args": _json.loads(tc.args) if isinstance(tc.args, str) else tc.args,
                        "result": tc.result, "status": tc.status}
                        for tc in (m.tool_calls or [])] if hasattr(m, "tool_calls") and m.tool_calls else [],
                } for m in messages],
            })
        return export_data

    # Conversation Methods

    def get_conversation(
        self,
        conversation_id: str,
        *,
        include_messages: bool = False,
{%- if cookiecutter.use_jwt %}
        user_id: str | None = None,
{%- endif %}
    ) -> Conversation:
        """Get conversation by ID.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        conversation = conversation_repo.get_conversation_by_id(
            self.db, conversation_id, include_messages=include_messages
        )
        if not conversation:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": conversation_id},
            )
{%- if cookiecutter.use_jwt %}
        if (
            user_id is not None
            and hasattr(conversation, "user_id")
            and conversation.user_id is not None
            and str(conversation.user_id) != str(user_id)
        ):
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": conversation_id},
            )
{%- endif %}
        return conversation

    def list_conversations(
        self,
{%- if cookiecutter.use_jwt %}
        user_id: str | None = None,
{%- endif %}
        *,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = False,
    ) -> tuple[list[Conversation], int]:
        """List conversations with pagination.

        Returns:
            Tuple of (conversations, total_count).
        """
        items = conversation_repo.get_conversations_by_user(
            self.db,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
            skip=skip,
            limit=limit,
            include_archived=include_archived,
        )
        total = conversation_repo.count_conversations(
            self.db,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
            include_archived=include_archived,
        )
        return items, total

    def create_conversation(
        self,
        data: ConversationCreate,
    ) -> Conversation:
        """Create a new conversation."""
        return conversation_repo.create_conversation(
            self.db,
{%- if cookiecutter.use_jwt %}
            user_id=data.user_id,
{%- endif %}
            title=data.title,
        )

    def update_conversation(
        self,
        conversation_id: str,
        data: ConversationUpdate,
{%- if cookiecutter.use_jwt %}
        user_id: str | None = None,
{%- endif %}
    ) -> Conversation:
        """Update a conversation.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        conversation = self.get_conversation(
            conversation_id,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
        )
        update_data = data.model_dump(exclude_unset=True)
        return conversation_repo.update_conversation(
            self.db, db_conversation=conversation, update_data=update_data
        )

    def archive_conversation(
        self,
        conversation_id: str,
{%- if cookiecutter.use_jwt %}
        user_id: str | None = None,
{%- endif %}
    ) -> Conversation:
        """Archive a conversation.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        self.get_conversation(
            conversation_id,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
        )
        conversation = conversation_repo.archive_conversation(self.db, conversation_id)
        if not conversation:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": conversation_id},
            )
        return conversation

    def delete_conversation(
        self,
        conversation_id: str,
{%- if cookiecutter.use_jwt %}
        user_id: str | None = None,
{%- endif %}
    ) -> bool:
        """Delete a conversation.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        self.get_conversation(
            conversation_id,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
        )
        deleted = conversation_repo.delete_conversation(self.db, conversation_id)
        if not deleted:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": conversation_id},
            )
        return True

    # Message Methods

    def get_message(self, message_id: str) -> Message:
        """Get message by ID.

        Raises:
            NotFoundError: If message does not exist.
        """
        message = conversation_repo.get_message_by_id(self.db, message_id)
        if not message:
            raise NotFoundError(
                message="Message not found",
                details={"message_id": message_id},
            )
        return message

    def list_messages(
        self,
        conversation_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
        include_tool_calls: bool = False,
    ) -> tuple[list[Message], int]:
        """List messages in a conversation.

        Returns:
            Tuple of (messages, total_count).
        """
        # Verify conversation exists
        self.get_conversation(conversation_id)
        items = conversation_repo.get_messages_by_conversation(
            self.db,
            conversation_id,
            skip=skip,
            limit=limit,
            include_tool_calls=include_tool_calls,
        )
        total = conversation_repo.count_messages(self.db, conversation_id)
        return items, total

    def add_message(
        self,
        conversation_id: str,
        data: MessageCreate,
    ) -> Message:
        """Add a message to a conversation.

        Raises:
            NotFoundError: If conversation does not exist.
        """
        # Verify conversation exists
        self.get_conversation(conversation_id)
        return conversation_repo.create_message(
            self.db,
            conversation_id=conversation_id,
            role=data.role,
            content=data.content,
            model_name=data.model_name,
            tokens_used=data.tokens_used,
        )

    def delete_message(self, message_id: str) -> bool:
        """Delete a message.

        Raises:
            NotFoundError: If message does not exist.
        """
        deleted = conversation_repo.delete_message(self.db, message_id)
        if not deleted:
            raise NotFoundError(
                message="Message not found",
                details={"message_id": message_id},
            )
        return True

    # Tool Call Methods

    def get_tool_call(self, tool_call_id: str) -> ToolCall:
        """Get tool call by ID.

        Raises:
            NotFoundError: If tool call does not exist.
        """
        tool_call = conversation_repo.get_tool_call_by_id(self.db, tool_call_id)
        if not tool_call:
            raise NotFoundError(
                message="Tool call not found",
                details={"tool_call_id": tool_call_id},
            )
        return tool_call

    def list_tool_calls(self, message_id: str) -> list[ToolCall]:
        """List tool calls for a message."""
        # Verify message exists
        self.get_message(message_id)
        return conversation_repo.get_tool_calls_by_message(self.db, message_id)

    def start_tool_call(
        self,
        message_id: str,
        data: ToolCallCreate,
    ) -> ToolCall:
        """Record the start of a tool call.

        Raises:
            NotFoundError: If message does not exist.
        """
        # Verify message exists
        self.get_message(message_id)
        return conversation_repo.create_tool_call(
            self.db,
            message_id=message_id,
            tool_call_id=data.tool_call_id,
            tool_name=data.tool_name,
            args=data.args,
            started_at=data.started_at or datetime.now(UTC),
        )

    def complete_tool_call(
        self,
        tool_call_id: str,
        data: ToolCallComplete,
    ) -> ToolCall:
        """Mark a tool call as completed.

        Raises:
            NotFoundError: If tool call does not exist.
        """
        tool_call = self.get_tool_call(tool_call_id)
        return conversation_repo.complete_tool_call(
            self.db,
            db_tool_call=tool_call,
            result=data.result,
            completed_at=data.completed_at or datetime.now(UTC),
            success=data.success,
        )


    def link_files_to_message(self, message_id: str, file_ids: list[str]) -> None:
        """Link uploaded chat files to a message."""
        if not file_ids:
            return
        from app.db.models.chat_file import ChatFile
        from sqlalchemy import update as sa_update
        self.db.execute(
            sa_update(ChatFile).where(ChatFile.id.in_(file_ids)).values(message_id=message_id)
        )
        self.db.commit()


{%- elif cookiecutter.use_mongodb %}
"""Conversation service (MongoDB).

Contains business logic for conversation, message, and tool call operations.
"""

from datetime import UTC, datetime

from app.core.exceptions import NotFoundError
from app.db.models.conversation import Conversation, Message, ToolCall
from app.repositories import conversation_repo
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
    ToolCallCreate,
    ToolCallComplete,
)


class ConversationService:
    """Service for conversation-related business logic."""

    # Conversation Methods

    async def get_conversation(
        self,
        conversation_id: str,
        *,
        include_messages: bool = False,
{%- if cookiecutter.use_jwt %}
        user_id: str | None = None,
{%- endif %}
    ) -> Conversation:
        """Get conversation by ID.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        conversation = await conversation_repo.get_conversation_by_id(
            conversation_id, include_messages=include_messages
        )
        if not conversation:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": conversation_id},
            )
{%- if cookiecutter.use_jwt %}
        if (
            user_id is not None
            and hasattr(conversation, "user_id")
            and conversation.user_id is not None
            and str(conversation.user_id) != str(user_id)
        ):
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": conversation_id},
            )
{%- endif %}
        return conversation

    async def list_conversations(
        self,
{%- if cookiecutter.use_jwt %}
        user_id: str | None = None,
{%- endif %}
        *,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = False,
    ) -> tuple[list[Conversation], int]:
        """List conversations with pagination.

        Returns:
            Tuple of (conversations, total_count).
        """
        items = await conversation_repo.get_conversations_by_user(
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
            skip=skip,
            limit=limit,
            include_archived=include_archived,
        )
        total = await conversation_repo.count_conversations(
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
            include_archived=include_archived,
        )
        return items, total

    async def create_conversation(
        self,
        data: ConversationCreate,
    ) -> Conversation:
        """Create a new conversation."""
        return await conversation_repo.create_conversation(
{%- if cookiecutter.use_jwt %}
            user_id=data.user_id,
{%- endif %}
            title=data.title,
        )

    async def update_conversation(
        self,
        conversation_id: str,
        data: ConversationUpdate,
{%- if cookiecutter.use_jwt %}
        user_id: str | None = None,
{%- endif %}
    ) -> Conversation:
        """Update a conversation.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        conversation = await self.get_conversation(
            conversation_id,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
        )
        update_data = data.model_dump(exclude_unset=True)
        return await conversation_repo.update_conversation(
            db_conversation=conversation, update_data=update_data
        )

    async def archive_conversation(
        self,
        conversation_id: str,
{%- if cookiecutter.use_jwt %}
        user_id: str | None = None,
{%- endif %}
    ) -> Conversation:
        """Archive a conversation.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        await self.get_conversation(
            conversation_id,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
        )
        conversation = await conversation_repo.archive_conversation(conversation_id)
        if not conversation:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": conversation_id},
            )
        return conversation

    async def delete_conversation(
        self,
        conversation_id: str,
{%- if cookiecutter.use_jwt %}
        user_id: str | None = None,
{%- endif %}
    ) -> bool:
        """Delete a conversation.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        await self.get_conversation(
            conversation_id,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
        )
        deleted = await conversation_repo.delete_conversation(conversation_id)
        if not deleted:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": conversation_id},
            )
        return True

    async def get_conversation_with_messages(
        self,
        conversation_id: str,
    ) -> Conversation:
        """Get conversation with messages (admin access).

        Raises:
            NotFoundError: If conversation does not exist.
        """
        return await self.get_conversation(conversation_id, include_messages=True)

    # Message Methods

    async def get_message(self, message_id: str) -> Message:
        """Get message by ID.

        Raises:
            NotFoundError: If message does not exist.
        """
        message = await conversation_repo.get_message_by_id(message_id)
        if not message:
            raise NotFoundError(
                message="Message not found",
                details={"message_id": message_id},
            )
        return message

    async def list_messages(
        self,
        conversation_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
        include_tool_calls: bool = False,
    ) -> tuple[list[Message], int]:
        """List messages in a conversation.

        Returns:
            Tuple of (messages, total_count).
        """
        # Verify conversation exists
        await self.get_conversation(conversation_id)
        items = await conversation_repo.get_messages_by_conversation(
            conversation_id,
            skip=skip,
            limit=limit,
        )
        total = await conversation_repo.count_messages(conversation_id)
        return items, total

    async def add_message(
        self,
        conversation_id: str,
        data: MessageCreate,
    ) -> Message:
        """Add a message to a conversation.

        Raises:
            NotFoundError: If conversation does not exist.
        """
        # Verify conversation exists
        await self.get_conversation(conversation_id)
        return await conversation_repo.create_message(
            conversation_id=conversation_id,
            role=data.role,
            content=data.content,
            model_name=data.model_name,
            tokens_used=data.tokens_used,
        )

    async def delete_message(self, message_id: str) -> bool:
        """Delete a message.

        Raises:
            NotFoundError: If message does not exist.
        """
        deleted = await conversation_repo.delete_message(message_id)
        if not deleted:
            raise NotFoundError(
                message="Message not found",
                details={"message_id": message_id},
            )
        return True

    # Tool Call Methods

    async def get_tool_call(self, tool_call_id: str) -> ToolCall:
        """Get tool call by ID.

        Raises:
            NotFoundError: If tool call does not exist.
        """
        tool_call = await conversation_repo.get_tool_call_by_id(tool_call_id)
        if not tool_call:
            raise NotFoundError(
                message="Tool call not found",
                details={"tool_call_id": tool_call_id},
            )
        return tool_call

    async def list_tool_calls(self, message_id: str) -> list[ToolCall]:
        """List tool calls for a message."""
        # Verify message exists
        await self.get_message(message_id)
        return await conversation_repo.get_tool_calls_by_message(message_id)

    async def start_tool_call(
        self,
        message_id: str,
        data: ToolCallCreate,
    ) -> ToolCall:
        """Record the start of a tool call.

        Raises:
            NotFoundError: If message does not exist.
        """
        # Verify message exists
        await self.get_message(message_id)
        return await conversation_repo.create_tool_call(
            message_id=message_id,
            tool_call_id=data.tool_call_id,
            tool_name=data.tool_name,
            args=data.args,
            started_at=data.started_at or datetime.now(UTC),
        )

    async def complete_tool_call(
        self,
        tool_call_id: str,
        data: ToolCallComplete,
    ) -> ToolCall:
        """Mark a tool call as completed.

        Raises:
            NotFoundError: If tool call does not exist.
        """
        tool_call = await self.get_tool_call(tool_call_id)
        return await conversation_repo.complete_tool_call(
            db_tool_call=tool_call,
            result=data.result,
            completed_at=data.completed_at or datetime.now(UTC),
            success=data.success,
        )


{%- else %}
"""Conversation service - not configured."""
{%- endif %}
