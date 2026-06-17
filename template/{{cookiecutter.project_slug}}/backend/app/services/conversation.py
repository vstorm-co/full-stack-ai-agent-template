{%- if cookiecutter.use_postgresql %}
"""Conversation service (PostgreSQL async).

Contains business logic for conversation, message, and tool call operations.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.core.exceptions import NotFoundError
from app.db.models.conversation import Conversation, Message, ToolCall
{%- if cookiecutter.use_jwt %}
from app.db.models.message_rating import MessageRating
from app.db.models.user import User
{%- endif %}
from app.repositories import conversation_repo
{%- if cookiecutter.use_jwt %}
from app.repositories import conversation_share_repo, message_rating_repo
{%- endif %}
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
    MessageRead,
    ToolCallCreate,
    ToolCallComplete,
{%- if cookiecutter.use_jwt %}
    ConversationWithLatestMessage,
{%- endif %}
)
{%- if cookiecutter.use_jwt %}

if TYPE_CHECKING:
    from app.schemas.conversation_share import AdminConversationList
{%- endif %}


logger = logging.getLogger(__name__)

# Maximum number of conversations to export in a single request to prevent DoS.
MAX_EXPORT_LIMIT = 1000


class ConversationService:
    """Service for conversation-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Export Methods

    EXPORT_CHUNK_SIZE = 1000
    MESSAGE_EXPORT_LIMIT = 10000

    async def export_all(self) -> list[dict[str, Any]]:
        """Export all conversations with messages and ratings for admin download.

        Uses keyset pagination on (created_at, id) to avoid skipping or
        duplicating conversations when data changes during export.
        """
        import json

        export_data: list[dict[str, Any]] = []
        last_created_at: datetime | None = None
        last_id: UUID | None = None

        while True:
            items = await conversation_repo.export_chunk(
                self.db,
                last_created_at=last_created_at,
                last_id=last_id,
                limit=self.EXPORT_CHUNK_SIZE,
            )
            if not items:
                break

            # Collect all message IDs to fetch ratings in bulk
            all_message_ids: list[UUID] = []
            conv_messages_map: dict[str, list[Message{%- if cookiecutter.use_jwt %} | MessageRead{%- endif %}]] = {}

            for conv in items:
                messages, _ = await self.list_messages(conv.id, skip=0, limit=self.MESSAGE_EXPORT_LIMIT, include_tool_calls=True)
                conv_messages_map[str(conv.id)] = messages
                all_message_ids.extend([m.id for m in messages if m.id])

{%- if cookiecutter.use_jwt %}
            # Fetch ratings for this chunk of messages
            message_ratings_map: dict[str, list[dict[str, Any]]] = {}
            ratings = await message_rating_repo.get_ratings_with_users_for_messages(
                self.db, message_ids=all_message_ids
            )
            for rating, user in ratings:
                msg_id = str(rating.message_id)
                if msg_id not in message_ratings_map:
                    message_ratings_map[msg_id] = []
                message_ratings_map[msg_id].append({
                    "id": str(rating.id),
                    "user_id": str(rating.user_id),
                    "user_email": getattr(user, "email", None),
                    "user_name": user.full_name if user else None,
                    "rating": rating.rating,
                    "comment": rating.comment,
                    "created_at": rating.created_at.isoformat() if rating.created_at else None,
                    "updated_at": rating.updated_at.isoformat() if rating.updated_at else None,
                })
{%- endif %}

            # Build export data for this chunk
            for conv in items:
                messages = conv_messages_map.get(str(conv.id), [])
                export_data.append({
                    "id": str(conv.id),
{%- if cookiecutter.use_jwt %}
                    "user_id": str(conv.user_id) if conv.user_id else None,
{%- endif %}
                    "title": conv.title,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                    "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                    "is_archived": conv.is_archived,
                    "messages": [{
                        "id": str(m.id),
                        "role": m.role,
                        "content": m.content,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                        "model_name": m.model_name,
                        "tokens_used": m.tokens_used,
                        "tool_calls": [{
                            "tool_name": tc.tool_name,
                            "args": tc.args if isinstance(tc.args, dict) else json.loads(tc.args) if isinstance(tc.args, str) and tc.args.strip() else {},
                            "result": tc.result,
                            "status": tc.status
                        }
                            for tc in (m.tool_calls or [])] if hasattr(m, "tool_calls") and m.tool_calls else [],
{%- if cookiecutter.use_jwt %}
                        "ratings": message_ratings_map.get(str(m.id), []),
{%- endif %}
                    } for m in messages],
                })

            # Advance cursor for keyset pagination
            last_created_at = items[-1].created_at
            last_id = items[-1].id

            if len(items) < self.EXPORT_CHUNK_SIZE:
                break

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
        if include_messages and user_id is not None and conversation.messages:
            message_ids = [m.id for m in conversation.messages]
            user_ratings = await message_rating_repo.get_user_ratings_for_messages(
                self.db, message_ids=message_ids, user_id=user_id
            )
            rating_counts = await message_rating_repo.get_rating_counts_for_messages(
                self.db, message_ids=message_ids
            )
            for msg in conversation.messages:
                msg.user_rating = user_ratings.get(msg.id)  # ty: ignore[unresolved-attribute]
                msg.rating_count = rating_counts.get(msg.id)  # ty: ignore[unresolved-attribute]
{%- endif %}
        return conversation

{%- if cookiecutter.enable_teams %}

    async def aggregate_tool_calls(
        self,
        organization_id: UUID,
        *,
        days: int = 7,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Top tool calls for an org over the last ``days``."""
        since = datetime.now(UTC) - timedelta(days=days)
        return await conversation_repo.aggregate_tool_calls_for_org(
            self.db, organization_id, since=since, limit=limit
        )
{%- endif %}

    async def list_conversations(
        self,
{%- if cookiecutter.use_jwt %}
        user_id: UUID | None = None,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
        organization_id: UUID | None = None,
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
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
            organization_id=organization_id,
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
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
            organization_id=organization_id,
{%- endif %}
            include_archived=include_archived,
        )
        return items, total

{%- if cookiecutter.use_jwt %}
    async def list_conversations_admin(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = False,
        search: str | None = None,
    ) -> tuple[list[ConversationWithLatestMessage], int]:
        """List all conversations for admin with message counts.

        Returns conversations with message_count but no message content.
        """
        from app.schemas.conversation import ConversationRead

        rows, total = await conversation_repo.get_all_conversations_with_count(
            self.db,
            skip=skip,
            limit=limit,
            include_archived=include_archived,
            search=search,
        )

        items = []
        for conv, msg_count in rows:
            conv_dict = {**ConversationRead.model_validate(conv).model_dump(), "message_count": msg_count}
            items.append(ConversationWithLatestMessage.model_validate(conv_dict))

        return items, total

    async def admin_list_with_users(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
        user_id: UUID | None = None,
        include_archived: bool = False,
        archived_only: bool = False,
        sort_by: str = "updated_at",
        sort_dir: str = "desc",
    ) -> "AdminConversationList":
        """Admin: list conversations with owner email and message counts."""
        from app.schemas.conversation_share import AdminConversationList, AdminConversationRead

        rows, total = await conversation_repo.admin_list_with_users(
            self.db,
            skip=skip,
            limit=limit,
            search=search,
            user_id=user_id,
            include_archived=include_archived,
            archived_only=archived_only,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        items = [
            AdminConversationRead(
                id=conv.id,
                user_id=conv.user_id,
{%- if cookiecutter.use_pydantic_deep %}
                project_id=getattr(conv, "project_id", None),
{%- endif %}
                title=conv.title,
                is_archived=conv.is_archived,
                message_count=msg_count,
                user_email=email,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
            for conv, msg_count, email in rows
        ]
        return AdminConversationList(items=items, total=total)
{%- endif %}

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
{%- if cookiecutter.use_external_user_id_in_conversations %}
            external_user_id=getattr(data, "external_user_id", None),
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
            project_id=data.project_id,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
            organization_id=getattr(data, "organization_id", None),
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
        if "active_knowledge_base_ids" in update_data and update_data["active_knowledge_base_ids"] is not None:
            update_data["active_knowledge_base_ids"] = [str(kb_id) for kb_id in update_data["active_knowledge_base_ids"]]
        return await conversation_repo.update_conversation(
            self.db, db_conversation=conversation, update_data=update_data
        )

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
    async def update_kb_settings(
        self,
        conversation_id: UUID,
        active_knowledge_base_ids: list[str] | None,
        user_id: UUID | None = None,
    ) -> Conversation:
        """Update active KB selection for a conversation.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        conversation = await self.get_conversation(conversation_id, user_id=user_id)
        return await conversation_repo.update_conversation(
            self.db,
            db_conversation=conversation,
            update_data={"active_knowledge_base_ids": active_knowledge_base_ids},
        )
{%- endif %}

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

    async def get_conversation_with_messages(
        self,
        conversation_id: UUID,
    ) -> Conversation:
        """Get conversation with messages (admin access).

        Raises:
            NotFoundError: If conversation does not exist.
        """
        return await self.get_conversation(conversation_id, include_messages=True)

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
{%- if cookiecutter.use_jwt %}
        user_id: UUID | None = None,
{%- endif %}
{%- if cookiecutter.use_jwt %}
    ) -> tuple[list[Message | MessageRead], int]:
        """List messages in a conversation.

        Returns:
            Tuple of (messages, total_count).

        When user_id is provided, messages will be enriched with:
        - user_rating: The user's rating for the message (1, -1, or None)
        - rating_count: Aggregate counts {likes: N, dislikes: N}
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

        # Enrich messages with rating data if user_id is provided
        if user_id is not None and items:
            message_ids = [msg.id for msg in items]
            user_ratings = await message_rating_repo.get_user_ratings_for_messages(
                self.db, message_ids=message_ids, user_id=user_id
            )
            rating_counts = await message_rating_repo.get_rating_counts_for_messages(
                self.db, message_ids=message_ids
            )

            # Construct enriched schema objects with rating data
            enriched: list[Message | MessageRead] = []
            for msg in items:
                msg_schema = MessageRead.model_validate(msg)
                msg_schema.user_rating = user_ratings.get(msg.id)
                msg_schema.rating_count = rating_counts.get(msg.id)
                enriched.append(msg_schema)
            return enriched, total
        return list(items), total
{%- else %}
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
        return list(items), total
{%- endif %}

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
        from app.repositories import chat_file_repo

        await chat_file_repo.link_to_message(
            self.db,
            message_id=message_id,
            file_ids=[UUID(fid) for fid in file_ids],
        )

    async def list_attached_files(self, file_ids: list[str]) -> list[Any]:
        """Batch-load chat files referenced as message attachments."""
        from app.repositories import chat_file_repo

        return await chat_file_repo.get_many(self.db, [UUID(fid) for fid in file_ids])


{%- elif cookiecutter.use_sqlite %}
"""Conversation service (SQLite sync).

Contains business logic for conversation, message, and tool call operations.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session
from sqlalchemy import select, func, case

from app.core.exceptions import NotFoundError
from app.db.models.conversation import Conversation, Message, ToolCall
{%- if cookiecutter.use_jwt %}
from app.db.models.message_rating import MessageRating
from app.db.models.user import User
{%- endif %}
from app.repositories import conversation_repo
{%- if cookiecutter.use_jwt %}
from app.repositories import conversation_share_repo
{%- endif %}
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
    MessageRead,
    ToolCallCreate,
    ToolCallComplete,
{%- if cookiecutter.use_jwt %}
    ConversationWithLatestMessage,
{%- endif %}
)
{%- if cookiecutter.use_jwt %}

if TYPE_CHECKING:
    from app.schemas.conversation_share import AdminConversationList
{%- endif %}


class ConversationService:
    """Service for conversation-related business logic."""

    def __init__(self, db: Session):
        self.db = db

    # Export Methods

    EXPORT_CHUNK_SIZE = 1000
    MESSAGE_EXPORT_LIMIT = 10000

    def export_all(self) -> list[dict[str, Any]]:
        """Export all conversations with messages and ratings for admin download.

        Uses keyset pagination on (created_at, id) to avoid skipping or
        duplicating conversations when data changes during export.
        """
        import json as _json
{%- if cookiecutter.use_jwt %}

        from app.repositories import message_rating_repo
{%- endif %}

        export_data: list[dict[str, Any]] = []
        last_created_at: datetime | None = None
        last_id: str | None = None

        while True:
            items = conversation_repo.export_chunk(
                self.db,
                last_created_at=last_created_at,
                last_id=last_id,
                limit=self.EXPORT_CHUNK_SIZE,
            )
            if not items:
                break

            # Collect all message IDs to fetch ratings in bulk
            all_message_ids: list[str] = []
            conv_messages_map: dict[str, list[Message{%- if cookiecutter.use_jwt %} | MessageRead{%- endif %}]] = {}

            for conv in items:
                messages, _ = self.list_messages(conv.id, skip=0, limit=self.MESSAGE_EXPORT_LIMIT, include_tool_calls=True)
                conv_messages_map[str(conv.id)] = messages
                all_message_ids.extend([m.id for m in messages if m.id])

{%- if cookiecutter.use_jwt %}
            # Fetch ratings for this chunk of messages
            message_ratings_map: dict[str, list[dict[str, Any]]] = {}
            ratings = message_rating_repo.get_ratings_with_users_for_messages(
                self.db, message_ids=all_message_ids
            )
            for rating, user in ratings:
                msg_id = str(rating.message_id)
                if msg_id not in message_ratings_map:
                    message_ratings_map[msg_id] = []
                message_ratings_map[msg_id].append({
                    "id": str(rating.id),
                    "user_id": str(rating.user_id),
                    "user_email": getattr(user, "email", None),
                    "user_name": user.full_name if user else None,
                    "rating": rating.rating,
                    "comment": rating.comment,
                    "created_at": rating.created_at.isoformat() if rating.created_at else None,
                    "updated_at": rating.updated_at.isoformat() if rating.updated_at else None,
                })
{%- endif %}

            # Build export data for this chunk
            for conv in items:
                messages = conv_messages_map.get(str(conv.id), [])
                export_data.append({
                    "id": str(conv.id),
{%- if cookiecutter.use_jwt %}
                    "user_id": str(conv.user_id) if conv.user_id else None,
{%- endif %}
                    "title": conv.title,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                    "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                    "is_archived": conv.is_archived,
                    "messages": [{
                        "id": str(m.id),
                        "role": m.role,
                        "content": m.content,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                        "model_name": m.model_name,
                        "tokens_used": m.tokens_used,
                        "tool_calls": [{
                            "tool_name": tc.tool_name,
                            "args": _json.loads(tc.args) if isinstance(tc.args, str) else tc.args,
                            "result": tc.result,
                            "status": tc.status
                        }
                            for tc in (m.tool_calls or [])] if hasattr(m, "tool_calls") and m.tool_calls else [],
{%- if cookiecutter.use_jwt %}
                        "ratings": message_ratings_map.get(str(m.id), []),
{%- endif %}
                    } for m in messages],
                })

            # Advance cursor for keyset pagination
            last_created_at = items[-1].created_at
            last_id = items[-1].id

            if len(items) < self.EXPORT_CHUNK_SIZE:
                break

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
            # Not the owner — check if user has a share granting access
            share = conversation_share_repo.get_share(
                self.db, conversation_id, user_id
            )
            if not share:
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
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
        organization_id: str | None = None,
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
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
            organization_id=organization_id,
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
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
            organization_id=organization_id,
{%- endif %}
            include_archived=include_archived,
        )
        return items, total

{%- if cookiecutter.use_jwt %}
    def list_conversations_admin(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = False,
        search: str | None = None,
    ) -> tuple[list[ConversationWithLatestMessage], int]:
        """List all conversations for admin with message counts.

        Returns conversations with message_count but no message content.
        """
        from app.schemas.conversation import ConversationRead

        rows, total = conversation_repo.get_all_conversations_with_count(
            self.db,
            skip=skip,
            limit=limit,
            include_archived=include_archived,
            search=search,
        )

        items = []
        for conv, msg_count in rows:
            conv_dict = {**ConversationRead.model_validate(conv).model_dump(), "message_count": msg_count}
            items.append(ConversationWithLatestMessage.model_validate(conv_dict))

        return items, total

    def admin_list_with_users(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
        user_id: str | None = None,
        include_archived: bool = False,
        archived_only: bool = False,
        sort_by: str = "updated_at",
        sort_dir: str = "desc",
    ) -> "AdminConversationList":
        """Admin: list conversations with owner email and message counts."""
        from app.schemas.conversation_share import AdminConversationList, AdminConversationRead

        rows, total = conversation_repo.admin_list_with_users(
            self.db,
            skip=skip,
            limit=limit,
            search=search,
            user_id=user_id,
            include_archived=include_archived,
            archived_only=archived_only,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        items = [
            AdminConversationRead(
                id=conv.id,
                user_id=conv.user_id,
{%- if cookiecutter.use_pydantic_deep %}
                project_id=getattr(conv, "project_id", None),
{%- endif %}
                title=conv.title,
                is_archived=conv.is_archived,
                message_count=msg_count,
                user_email=email,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
            for conv, msg_count, email in rows
        ]
        return AdminConversationList(items=items, total=total)
{%- endif %}

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
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
            organization_id=getattr(data, "organization_id", None),
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
        if "active_knowledge_base_ids" in update_data:
            import json
            ids = update_data["active_knowledge_base_ids"]
            update_data["active_knowledge_base_ids"] = json.dumps([str(kb_id) for kb_id in ids]) if ids is not None else None
        return conversation_repo.update_conversation(
            self.db, db_conversation=conversation, update_data=update_data
        )

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
    def update_kb_settings(
        self,
        conversation_id: str,
        active_knowledge_base_ids: list[str] | None,
        user_id: str | None = None,
    ) -> Conversation:
        """Update active KB selection for a conversation.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        import json
        conversation = self.get_conversation(conversation_id, user_id=user_id)
        serialized = json.dumps(active_knowledge_base_ids) if active_knowledge_base_ids is not None else None
        return conversation_repo.update_conversation(
            self.db,
            db_conversation=conversation,
            update_data={"active_knowledge_base_ids": serialized},
        )
{%- endif %}

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

    def get_conversation_with_messages(
        self,
        conversation_id: str,
    ) -> Conversation:
        """Get conversation with messages (admin access).

        Raises:
            NotFoundError: If conversation does not exist.
        """
        return self.get_conversation(conversation_id, include_messages=True)

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
{%- if cookiecutter.use_jwt %}
        user_id: str | None = None,
{%- endif %}
{%- if cookiecutter.use_jwt %}
    ) -> tuple[list[Message | MessageRead], int]:
        """List messages in a conversation.

        Returns:
            Tuple of (messages, total_count).

        When user_id is provided, messages will be enriched with:
        - user_rating: The user's rating for the message (1, -1, or None)
        - rating_count: Aggregate counts {likes: N, dislikes: N}
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

        # Enrich messages with rating data if user_id is provided
        if user_id is not None and items:
            from app.repositories import message_rating_repo

            message_ids = [msg.id for msg in items]
            user_ratings = message_rating_repo.get_user_ratings_for_messages(
                self.db, message_ids=message_ids, user_id=user_id
            )
            rating_counts = message_rating_repo.get_rating_counts_for_messages(
                self.db, message_ids=message_ids
            )

            # Construct enriched schema objects with rating data
            enriched: list[Message | MessageRead] = []
            for msg in items:
                msg_schema = MessageRead.model_validate(msg)
                msg_schema.user_rating = user_ratings.get(msg.id)
                msg_schema.rating_count = rating_counts.get(msg.id)
                enriched.append(msg_schema)
            return enriched, total
        return list(items), total
{%- else %}
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
        return list(items), total
{%- endif %}

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
        from app.repositories import chat_file_repo

        chat_file_repo.link_to_message(self.db, message_id=message_id, file_ids=file_ids)

    def list_attached_files(self, file_ids: list[str]) -> list[Any]:
        """Batch-load chat files referenced as message attachments."""
        from app.repositories import chat_file_repo

        return chat_file_repo.get_many(self.db, file_ids)


{%- elif cookiecutter.use_mongodb %}
"""Conversation service (MongoDB).

Contains business logic for conversation, message, and tool call operations.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.core.exceptions import NotFoundError
from app.db.models.conversation import Conversation, Message, ToolCall
{%- if cookiecutter.use_jwt %}
from app.db.models.message_rating import MessageRating
{%- endif %}
from app.repositories import conversation_repo
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
    MessageRead,
    ToolCallCreate,
    ToolCallComplete,
{%- if cookiecutter.use_jwt %}
    ConversationWithLatestMessage,
{%- endif %}
)
{%- if cookiecutter.use_jwt %}

if TYPE_CHECKING:
    from app.schemas.conversation_share import AdminConversationList
{%- endif %}


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
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
        organization_id: str | None = None,
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
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
            organization_id=organization_id,
{%- endif %}
            skip=skip,
            limit=limit,
            include_archived=include_archived,
        )
        total = await conversation_repo.count_conversations(
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
            organization_id=organization_id,
{%- endif %}
            include_archived=include_archived,
        )
        return items, total

{%- if cookiecutter.use_jwt %}
    async def list_conversations_admin(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = False,
        search: str | None = None,
    ) -> tuple[list[ConversationWithLatestMessage], int]:
        """List all conversations for admin with message counts.

        Returns conversations with message_count but no message content.
        """
        from app.schemas.conversation import ConversationRead

        rows, total = await conversation_repo.get_all_conversations_with_count(
            skip=skip,
            limit=limit,
            include_archived=include_archived,
            search=search,
        )

        items = []
        for conv, msg_count in rows:
            conv_dict = {**ConversationRead.model_validate(conv).model_dump(), "message_count": msg_count}
            items.append(ConversationWithLatestMessage.model_validate(conv_dict))

        return items, total

    async def admin_list_with_users(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
        user_id: str | None = None,
        include_archived: bool = False,
        archived_only: bool = False,
        sort_by: str = "updated_at",
        sort_dir: str = "desc",
    ) -> "AdminConversationList":
        """Admin: list conversations with owner email and message counts."""
        from app.schemas.conversation_share import AdminConversationList, AdminConversationRead

        rows, total = await conversation_repo.admin_list_with_users(
            skip=skip,
            limit=limit,
            search=search,
            user_id=user_id,
            include_archived=include_archived,
            archived_only=archived_only,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        items = [
            AdminConversationRead(
                id=str(conv.id),
                user_id=conv.user_id,
{%- if cookiecutter.use_pydantic_deep %}
                project_id=getattr(conv, "project_id", None),
{%- endif %}
                title=conv.title,
                is_archived=conv.is_archived,
                message_count=msg_count,
                user_email=email,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
            for conv, msg_count, email in rows
        ]
        return AdminConversationList(items=items, total=total)
{%- endif %}

    async def create_conversation(
        self,
        data: ConversationCreate,
    ) -> Conversation:
        """Create a new conversation."""
        return await conversation_repo.create_conversation(
{%- if cookiecutter.use_jwt %}
            user_id=data.user_id,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
            organization_id=getattr(data, "organization_id", None),
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
        if "active_knowledge_base_ids" in update_data and update_data["active_knowledge_base_ids"] is not None:
            update_data["active_knowledge_base_ids"] = [str(kb_id) for kb_id in update_data["active_knowledge_base_ids"]]
        return await conversation_repo.update_conversation(
            db_conversation=conversation, update_data=update_data
        )

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
    async def update_kb_settings(
        self,
        conversation_id: str,
        active_knowledge_base_ids: list[str] | None,
        user_id: str | None = None,
    ) -> Conversation:
        """Update active KB selection for a conversation.

        Raises:
            NotFoundError: If conversation does not exist or user has no access.
        """
        conversation = await self.get_conversation(conversation_id, user_id=user_id)
        return await conversation_repo.update_conversation(
            db_conversation=conversation,
            update_data={"active_knowledge_base_ids": active_knowledge_base_ids},
        )
{%- endif %}

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
{%- if cookiecutter.use_jwt %}
        user_id: str | None = None,
{%- endif %}
{%- if cookiecutter.use_jwt %}
    ) -> tuple[list[Message | MessageRead], int]:
        """List messages in a conversation.

        Returns:
            Tuple of (messages, total_count).

        When user_id is provided, messages will be enriched with:
        - user_rating: The user's rating for the message (1, -1, or None)
        - rating_count: Aggregate counts {likes: N, dislikes: N}
        """
        # Verify conversation exists
        await self.get_conversation(conversation_id)
        items = await conversation_repo.get_messages_by_conversation(
            conversation_id,
            skip=skip,
            limit=limit,
            include_tool_calls=include_tool_calls,
        )
        total = await conversation_repo.count_messages(conversation_id)

        # Enrich messages with rating data if user_id is provided
        if user_id is not None and items:
            # Get all message IDs
            message_ids = [msg.id for msg in items]

            # Fetch user ratings for these messages
            user_ratings = await MessageRating.find({
                "message_id": {"$in": message_ids},
                "user_id": user_id,
            }).to_list()

            user_rating_map = {
                rating.message_id: rating.rating
                for rating in user_ratings
            }

            # Fetch aggregate rating counts for these messages
            pipeline = [
                {"$match": {"message_id": {"$in": message_ids}}},
                {
                    "$group": {
                        "_id": "$message_id",
                        "likes": {
                            "$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}
                        },
                        "dislikes": {
                            "$sum": {"$cond": [{"$eq": ["$rating", -1]}, 1, 0]}
                        },
                    }
                },
            ]

            rating_counts = await MessageRating.aggregate(pipeline).to_list()
            rating_count_map = {
                doc["_id"]: {"likes": doc["likes"], "dislikes": doc["dislikes"]}
                for doc in rating_counts
            }

            # Construct enriched schema objects with rating data
            enriched: list[Message | MessageRead] = []
            for msg in items:
                msg_schema = MessageRead.model_validate(msg)
                msg_schema.user_rating = user_rating_map.get(msg.id)
                msg_schema.rating_count = rating_count_map.get(msg.id)
                enriched.append(msg_schema)
            return enriched, total
        return list(items), total
{%- else %}
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
        return list(items), total
{%- endif %}

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
