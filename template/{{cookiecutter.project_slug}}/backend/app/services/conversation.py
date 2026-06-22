import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.core.exceptions import NotFoundError
from app.db.models.conversation import Conversation, Message, ToolCall
{%- if cookiecutter.use_jwt %}
from app.db.models.message_rating import MessageRating
from app.db.models.user import User
{%- endif %}
from app.repositories import conversation_repo
{%- if cookiecutter.use_jwt %}
from app.repositories import chat_file_repo, conversation_share_repo, message_rating_repo
{%- endif %}
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    DemoConversationSummary,
    MessageCreate,
    MessageRead,
    ToolCallCreate,
    ToolCallComplete,
{%- if cookiecutter.use_jwt %}
    ConversationWithLatestMessage,
{%- endif %}
)
{%- if cookiecutter.use_jwt %}
from app.schemas.conversation_share import AdminConversationList, AdminConversationRead
{%- endif %}


logger = logging.getLogger(__name__)

# Maximum number of conversations to export in a single request to prevent DoS.
MAX_EXPORT_LIMIT = 1000


def _safe_parse_args(args: Any) -> dict:
    """Parse tool call args to a dict; returns {} on failure."""
    if isinstance(args, dict):
        return args
    if isinstance(args, str) and args.strip():
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return {}
    return {}


class ConversationService:

    def __init__(self, db: AsyncSession):
        self.db = db

    EXPORT_CHUNK_SIZE = 1000
    MESSAGE_EXPORT_LIMIT = 10000

    async def export_all(self) -> list[dict[str, Any]]:
        """Export all conversations with messages and ratings for admin download.

        Uses keyset pagination on (created_at, id) to avoid skipping or
        duplicating conversations when data changes during export.
        """
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

            all_message_ids: list[UUID] = []
            conv_messages_map: dict[str, list[Message{%- if cookiecutter.use_jwt %} | MessageRead{%- endif %}]] = {}

            for conv in items:
                messages, _ = await self.list_messages(conv.id, skip=0, limit=self.MESSAGE_EXPORT_LIMIT, include_tool_calls=True)
                conv_messages_map[str(conv.id)] = messages
                all_message_ids.extend([m.id for m in messages if m.id])

{%- if cookiecutter.use_jwt %}
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
                            "args": _safe_parse_args(tc.args),
                            "result": tc.result,
                            "status": tc.status
                        }
                            for tc in (m.tool_calls or [])] if hasattr(m, "tool_calls") and m.tool_calls else [],
{%- if cookiecutter.use_jwt %}
                        "ratings": message_ratings_map.get(str(m.id), []),
{%- endif %}
                    } for m in messages],
                })

            last_created_at = items[-1].created_at
            last_id = items[-1].id

            if len(items) < self.EXPORT_CHUNK_SIZE:
                break

        return export_data

    async def get_conversation(
        self,
        conversation_id: UUID,
        *,
        include_messages: bool = False,
{%- if cookiecutter.use_jwt %}
        user_id: UUID | None = None,
{%- endif %}
    ) -> Conversation:
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
        rows, total = await conversation_repo.get_all_conversations_with_count(
            self.db,
            skip=skip,
            limit=limit,
            include_archived=include_archived,
            search=search,
        )

        items = [
            ConversationWithLatestMessage(
                id=conv.id,
{%- if cookiecutter.use_jwt %}
                user_id=conv.user_id,
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
                project_id=getattr(conv, "project_id", None),
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
                organization_id=getattr(conv, "organization_id", None),
{%- endif %}
                title=conv.title,
                is_archived=conv.is_archived,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=msg_count,
            )
            for conv, msg_count in rows
        ]
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
    ) -> AdminConversationList:
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
                is_demo=conv.is_demo,
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
        conversation = await self.get_conversation(
            conversation_id,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
        )
        return await conversation_repo.archive_conversation(
            self.db, db_conversation=conversation
        )

    async def delete_conversation(
        self,
        conversation_id: UUID,
{%- if cookiecutter.use_jwt %}
        user_id: UUID | None = None,
{%- endif %}
    ) -> bool:
        conversation = await self.get_conversation(
            conversation_id,
{%- if cookiecutter.use_jwt %}
            user_id=user_id,
{%- endif %}
        )
        await conversation_repo.delete_conversation(self.db, db_conversation=conversation)
        return True

    async def get_conversation_with_messages(
        self,
        conversation_id: UUID,
    ) -> Conversation:
        return await self.get_conversation(conversation_id, include_messages=True)

    async def list_demo_conversations(
        self, *, skip: int = 0, limit: int = 50
    ) -> tuple[list[DemoConversationSummary], int]:
        """List admin-curated demo conversations for the public gallery."""
        rows, total = await conversation_repo.get_demo_conversations_with_count(
            self.db, skip=skip, limit=limit
        )
        items = [
            DemoConversationSummary(
                id=conv.id,
                title=conv.title,
                message_count=msg_count,
                preview=preview[:200] if preview else None,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
            for conv, msg_count, preview in rows
        ]
        return items, total

    async def get_demo_conversation(self, conversation_id: UUID) -> Conversation:
        """Get a single demo conversation with messages (public, no auth required)."""
        conversation = await conversation_repo.get_conversation_by_id(
            self.db, conversation_id, include_messages=True
        )
        if not conversation or not conversation.is_demo:
            raise NotFoundError(
                message="Demo not found",
                details={"conversation_id": str(conversation_id)},
            )
        return conversation

    async def get_message(self, message_id: UUID) -> Message:
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
        """When user_id is provided, messages are enriched with user_rating and rating_count."""
{%- else %}
    ) -> tuple[list[Message], int]:
{%- endif %}
        await self.get_conversation(conversation_id)
        items = await conversation_repo.get_messages_by_conversation(
            self.db,
            conversation_id,
            skip=skip,
            limit=limit,
            include_tool_calls=include_tool_calls,
        )
        total = await conversation_repo.count_messages(self.db, conversation_id)

{%- if cookiecutter.use_jwt %}
        if user_id is not None and items:
            message_ids = [msg.id for msg in items]
            user_ratings = await message_rating_repo.get_user_ratings_for_messages(
                self.db, message_ids=message_ids, user_id=user_id
            )
            rating_counts = await message_rating_repo.get_rating_counts_for_messages(
                self.db, message_ids=message_ids
            )

            enriched: list[Message | MessageRead] = []
            for msg in items:
                msg_schema = MessageRead.model_validate(msg)
                msg_schema.user_rating = user_ratings.get(msg.id)
                msg_schema.rating_count = rating_counts.get(msg.id)
                enriched.append(msg_schema)
            return enriched, total
{%- endif %}
        return list(items), total

    async def add_message(
        self,
        conversation_id: UUID,
        data: MessageCreate,
    ) -> Message:
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
        deleted = await conversation_repo.delete_message(self.db, message_id)
        if not deleted:
            raise NotFoundError(
                message="Message not found",
                details={"message_id": str(message_id)},
            )
        return True

    async def get_tool_call(self, tool_call_id: UUID) -> ToolCall:
        tool_call = await conversation_repo.get_tool_call_by_id(self.db, tool_call_id)
        if not tool_call:
            raise NotFoundError(
                message="Tool call not found",
                details={"tool_call_id": str(tool_call_id)},
            )
        return tool_call

    async def list_tool_calls(self, message_id: UUID) -> list[ToolCall]:
        await self.get_message(message_id)
        return await conversation_repo.get_tool_calls_by_message(self.db, message_id)

    async def start_tool_call(
        self,
        message_id: UUID,
        data: ToolCallCreate,
    ) -> ToolCall:
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
        tool_call = await self.get_tool_call(tool_call_id)
        return await conversation_repo.complete_tool_call(
            self.db,
            db_tool_call=tool_call,
            result=data.result,
            completed_at=data.completed_at or datetime.now(UTC),
            success=data.success,
        )

    async def link_files_to_message(self, message_id: UUID, file_ids: list[str]) -> None:
        await chat_file_repo.link_to_message(
            self.db,
            message_id=message_id,
            file_ids=[UUID(fid) for fid in file_ids],
        )

    async def list_attached_files(self, file_ids: list[str]) -> list[Any]:
        return await chat_file_repo.get_many(self.db, [UUID(fid) for fid in file_ids])
