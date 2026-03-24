{%- if cookiecutter.use_postgresql %}
"""Conversation repository (PostgreSQL async).

Contains database operations for Conversation, Message, and ToolCall entities.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.conversation import Conversation, Message, ToolCall


# Conversation Operations


async def get_conversation_by_id(
    db: AsyncSession,
    conversation_id: UUID,
    *,
    include_messages: bool = False,
) -> Conversation | None:
    """Get conversation by ID, optionally with messages."""
    if include_messages:
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages).selectinload(Message.tool_calls))
            .where(Conversation.id == conversation_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    return await db.get(Conversation, conversation_id)


async def get_conversations_by_user(
    db: AsyncSession,
{%- if cookiecutter.use_jwt %}
    user_id: UUID | None = None,
{%- endif %}
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
) -> list[Conversation]:
    """Get conversations for a user with pagination."""
    query = select(Conversation)
{%- if cookiecutter.use_jwt %}
    if user_id:
        query = query.where(Conversation.user_id == user_id)
{%- endif %}
    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    query = query.order_by(func.coalesce(Conversation.updated_at, Conversation.created_at).desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_conversations(
    db: AsyncSession,
{%- if cookiecutter.use_jwt %}
    user_id: UUID | None = None,
{%- endif %}
    *,
    include_archived: bool = False,
) -> int:
    """Count conversations for a user."""
    query = select(func.count(Conversation.id))
{%- if cookiecutter.use_jwt %}
    if user_id:
        query = query.where(Conversation.user_id == user_id)
{%- endif %}
    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    result = await db.execute(query)
    return result.scalar() or 0


async def create_conversation(
    db: AsyncSession,
    *,
{%- if cookiecutter.use_jwt %}
    user_id: UUID | None = None,
{%- endif %}
    title: str | None = None,
) -> Conversation:
    """Create a new conversation."""
    conversation = Conversation(
{%- if cookiecutter.use_jwt %}
        user_id=user_id,
{%- endif %}
        title=title,
    )
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    return conversation


async def update_conversation(
    db: AsyncSession,
    *,
    db_conversation: Conversation,
    update_data: dict[str, Any],
) -> Conversation:
    """Update a conversation."""
    for field, value in update_data.items():
        setattr(db_conversation, field, value)

    db.add(db_conversation)
    await db.flush()
    await db.refresh(db_conversation)
    return db_conversation


async def archive_conversation(
    db: AsyncSession,
    conversation_id: UUID,
) -> Conversation | None:
    """Archive a conversation."""
    conversation = await get_conversation_by_id(db, conversation_id)
    if conversation:
        conversation.is_archived = True
        db.add(conversation)
        await db.flush()
        await db.refresh(conversation)
    return conversation


async def delete_conversation(db: AsyncSession, conversation_id: UUID) -> bool:
    """Delete a conversation and all related messages/tool_calls (cascades)."""
    conversation = await get_conversation_by_id(db, conversation_id)
    if conversation:
        await db.delete(conversation)
        await db.flush()
        return True
    return False


# Message Operations


async def get_message_by_id(db: AsyncSession, message_id: UUID) -> Message | None:
    """Get message by ID."""
    return await db.get(Message, message_id)


async def get_messages_by_conversation(
    db: AsyncSession,
    conversation_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
    include_tool_calls: bool = False,
) -> list[Message]:
    """Get messages for a conversation with pagination."""
    query = select(Message).where(Message.conversation_id == conversation_id)
    if include_tool_calls:
        query = query.options(selectinload(Message.tool_calls))
    query = query.order_by(Message.created_at.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_messages(db: AsyncSession, conversation_id: UUID) -> int:
    """Count messages in a conversation."""
    query = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
    result = await db.execute(query)
    return result.scalar() or 0


async def create_message(
    db: AsyncSession,
    *,
    conversation_id: UUID,
    role: str,
    content: str,
    model_name: str | None = None,
    tokens_used: int | None = None,
) -> Message:
    """Create a new message."""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        model_name=model_name,
        tokens_used=tokens_used,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)

    # Update conversation's updated_at timestamp
    await db.execute(
        sql_update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(updated_at=message.created_at)
    )

    return message


async def delete_message(db: AsyncSession, message_id: UUID) -> bool:
    """Delete a message."""
    message = await get_message_by_id(db, message_id)
    if message:
        await db.delete(message)
        await db.flush()
        return True
    return False


# ToolCall Operations


async def get_tool_call_by_id(db: AsyncSession, tool_call_id: UUID) -> ToolCall | None:
    """Get tool call by ID."""
    return await db.get(ToolCall, tool_call_id)


async def get_tool_calls_by_message(
    db: AsyncSession,
    message_id: UUID,
) -> list[ToolCall]:
    """Get tool calls for a message."""
    query = (
        select(ToolCall)
        .where(ToolCall.message_id == message_id)
        .order_by(ToolCall.started_at.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_tool_call(
    db: AsyncSession,
    *,
    message_id: UUID,
    tool_call_id: str,
    tool_name: str,
    args: dict[str, Any],
    started_at: datetime,
) -> ToolCall:
    """Create a new tool call record."""
    tool_call = ToolCall(
        message_id=message_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        args=args,
        started_at=started_at,
        status="running",
    )
    db.add(tool_call)
    await db.flush()
    await db.refresh(tool_call)
    return tool_call


async def complete_tool_call(
    db: AsyncSession,
    *,
    db_tool_call: ToolCall,
    result: str,
    completed_at: datetime,
    success: bool = True,
) -> ToolCall:
    """Mark a tool call as completed."""
    db_tool_call.result = result
    db_tool_call.completed_at = completed_at
    db_tool_call.status = "completed" if success else "failed"

    # Calculate duration
    if db_tool_call.started_at:
        delta = completed_at - db_tool_call.started_at
        db_tool_call.duration_ms = int(delta.total_seconds() * 1000)

    db.add(db_tool_call)
    await db.flush()
    await db.refresh(db_tool_call)
    return db_tool_call


{%- elif cookiecutter.use_sqlite %}
"""Conversation repository (SQLite sync).

Contains database operations for Conversation, Message, and ToolCall entities.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update as sql_update
from sqlalchemy.orm import Session, selectinload

from app.db.models.conversation import Conversation, Message, ToolCall


# Conversation Operations


def get_conversation_by_id(
    db: Session,
    conversation_id: str,
    *,
    include_messages: bool = False,
) -> Conversation | None:
    """Get conversation by ID, optionally with messages."""
    if include_messages:
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages).selectinload(Message.tool_calls))
            .where(Conversation.id == conversation_id)
        )
        result = db.execute(query)
        return result.scalar_one_or_none()
    return db.get(Conversation, conversation_id)


def get_conversations_by_user(
    db: Session,
{%- if cookiecutter.use_jwt %}
    user_id: str | None = None,
{%- endif %}
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
) -> list[Conversation]:
    """Get conversations for a user with pagination."""
    query = select(Conversation)
{%- if cookiecutter.use_jwt %}
    if user_id:
        query = query.where(Conversation.user_id == user_id)
{%- endif %}
    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    query = query.order_by(func.coalesce(Conversation.updated_at, Conversation.created_at).desc()).offset(skip).limit(limit)
    result = db.execute(query)
    return list(result.scalars().all())


def count_conversations(
    db: Session,
{%- if cookiecutter.use_jwt %}
    user_id: str | None = None,
{%- endif %}
    *,
    include_archived: bool = False,
) -> int:
    """Count conversations for a user."""
    query = select(func.count(Conversation.id))
{%- if cookiecutter.use_jwt %}
    if user_id:
        query = query.where(Conversation.user_id == user_id)
{%- endif %}
    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    result = db.execute(query)
    return result.scalar() or 0


def create_conversation(
    db: Session,
    *,
{%- if cookiecutter.use_jwt %}
    user_id: str | None = None,
{%- endif %}
    title: str | None = None,
) -> Conversation:
    """Create a new conversation."""
    conversation = Conversation(
{%- if cookiecutter.use_jwt %}
        user_id=user_id,
{%- endif %}
        title=title,
    )
    db.add(conversation)
    db.flush()
    db.refresh(conversation)
    return conversation


def update_conversation(
    db: Session,
    *,
    db_conversation: Conversation,
    update_data: dict[str, Any],
) -> Conversation:
    """Update a conversation."""
    for field, value in update_data.items():
        setattr(db_conversation, field, value)

    db.add(db_conversation)
    db.flush()
    db.refresh(db_conversation)
    return db_conversation


def archive_conversation(
    db: Session,
    conversation_id: str,
) -> Conversation | None:
    """Archive a conversation."""
    conversation = get_conversation_by_id(db, conversation_id)
    if conversation:
        conversation.is_archived = True
        db.add(conversation)
        db.flush()
        db.refresh(conversation)
    return conversation


def delete_conversation(db: Session, conversation_id: str) -> bool:
    """Delete a conversation and all related messages/tool_calls (cascades)."""
    conversation = get_conversation_by_id(db, conversation_id)
    if conversation:
        db.delete(conversation)
        db.flush()
        return True
    return False


# Message Operations


def get_message_by_id(db: Session, message_id: str) -> Message | None:
    """Get message by ID."""
    return db.get(Message, message_id)


def get_messages_by_conversation(
    db: Session,
    conversation_id: str,
    *,
    skip: int = 0,
    limit: int = 100,
    include_tool_calls: bool = False,
) -> list[Message]:
    """Get messages for a conversation with pagination."""
    query = select(Message).where(Message.conversation_id == conversation_id)
    if include_tool_calls:
        query = query.options(selectinload(Message.tool_calls))
    query = query.order_by(Message.created_at.asc()).offset(skip).limit(limit)
    result = db.execute(query)
    return list(result.scalars().all())


def count_messages(db: Session, conversation_id: str) -> int:
    """Count messages in a conversation."""
    query = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
    result = db.execute(query)
    return result.scalar() or 0


def create_message(
    db: Session,
    *,
    conversation_id: str,
    role: str,
    content: str,
    model_name: str | None = None,
    tokens_used: int | None = None,
) -> Message:
    """Create a new message."""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        model_name=model_name,
        tokens_used=tokens_used,
    )
    db.add(message)
    db.flush()
    db.refresh(message)

    # Update conversation's updated_at timestamp
    db.execute(
        sql_update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(updated_at=message.created_at)
    )

    return message


def delete_message(db: Session, message_id: str) -> bool:
    """Delete a message."""
    message = get_message_by_id(db, message_id)
    if message:
        db.delete(message)
        db.flush()
        return True
    return False


# ToolCall Operations


def get_tool_call_by_id(db: Session, tool_call_id: str) -> ToolCall | None:
    """Get tool call by ID."""
    return db.get(ToolCall, tool_call_id)


def get_tool_calls_by_message(
    db: Session,
    message_id: str,
) -> list[ToolCall]:
    """Get tool calls for a message."""
    query = (
        select(ToolCall)
        .where(ToolCall.message_id == message_id)
        .order_by(ToolCall.started_at.asc())
    )
    result = db.execute(query)
    return list(result.scalars().all())


def create_tool_call(
    db: Session,
    *,
    message_id: str,
    tool_call_id: str,
    tool_name: str,
    args: dict[str, Any],
    started_at: datetime,
) -> ToolCall:
    """Create a new tool call record."""
    import json

    tool_call = ToolCall(
        message_id=message_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        args=json.dumps(args),  # SQLite stores as JSON string
        started_at=started_at,
        status="running",
    )
    db.add(tool_call)
    db.flush()
    db.refresh(tool_call)
    return tool_call


def deserialize_tool_call_args(tool_call: ToolCall) -> dict[str, Any]:
    """Deserialize tool call args from JSON string (SQLite stores as TEXT)."""
    import json

    if isinstance(tool_call.args, str):
        try:
            result: dict[str, Any] = json.loads(tool_call.args)
            return result
        except (json.JSONDecodeError, TypeError):
            return {}
    return dict(tool_call.args) if isinstance(tool_call.args, dict) else {}


def complete_tool_call(
    db: Session,
    *,
    db_tool_call: ToolCall,
    result: str,
    completed_at: datetime,
    success: bool = True,
) -> ToolCall:
    """Mark a tool call as completed."""
    db_tool_call.result = result
    db_tool_call.completed_at = completed_at
    db_tool_call.status = "completed" if success else "failed"

    # Calculate duration
    if db_tool_call.started_at:
        delta = completed_at - db_tool_call.started_at
        db_tool_call.duration_ms = int(delta.total_seconds() * 1000)

    db.add(db_tool_call)
    db.flush()
    db.refresh(db_tool_call)
    return db_tool_call


{%- elif cookiecutter.use_mongodb %}
"""Conversation repository (MongoDB).

Contains database operations for Conversation, Message, and ToolCall entities.
"""

from datetime import UTC, datetime
from typing import Any

from app.db.models.conversation import Conversation, Message, ToolCall


# Conversation Operations


async def get_conversation_by_id(
    conversation_id: str,
    *,
    include_messages: bool = False,
) -> Conversation | None:
    """Get conversation by ID."""
    conversation = await Conversation.get(conversation_id)
    # Note: MongoDB doesn't auto-load related documents; handle in service layer
    return conversation


async def get_conversations_by_user(
{%- if cookiecutter.use_jwt %}
    user_id: str | None = None,
{%- endif %}
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
) -> list[Conversation]:
    """Get conversations for a user with pagination."""
    query_filter = {}
{%- if cookiecutter.use_jwt %}
    if user_id:
        query_filter["user_id"] = user_id
{%- endif %}
    if not include_archived:
        query_filter["is_archived"] = False

    return await Conversation.find(query_filter).sort("-created_at").skip(skip).limit(limit).to_list()


async def count_conversations(
{%- if cookiecutter.use_jwt %}
    user_id: str | None = None,
{%- endif %}
    *,
    include_archived: bool = False,
) -> int:
    """Count conversations for a user."""
    query_filter = {}
{%- if cookiecutter.use_jwt %}
    if user_id:
        query_filter["user_id"] = user_id
{%- endif %}
    if not include_archived:
        query_filter["is_archived"] = False

    return await Conversation.find(query_filter).count()


async def create_conversation(
    *,
{%- if cookiecutter.use_jwt %}
    user_id: str | None = None,
{%- endif %}
    title: str | None = None,
) -> Conversation:
    """Create a new conversation."""
    conversation = Conversation(
{%- if cookiecutter.use_jwt %}
        user_id=user_id,
{%- endif %}
        title=title,
    )
    await conversation.insert()
    return conversation


async def update_conversation(
    *,
    db_conversation: Conversation,
    update_data: dict[str, Any],
) -> Conversation:
    """Update a conversation."""
    for field, value in update_data.items():
        setattr(db_conversation, field, value)
    db_conversation.updated_at = datetime.now(UTC)
    await db_conversation.save()
    return db_conversation


async def archive_conversation(
    conversation_id: str,
) -> Conversation | None:
    """Archive a conversation."""
    conversation = await get_conversation_by_id(conversation_id)
    if conversation:
        conversation.is_archived = True
        conversation.updated_at = datetime.now(UTC)
        await conversation.save()
    return conversation


async def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation and all related messages/tool_calls."""
    conversation = await get_conversation_by_id(conversation_id)
    if conversation:
        # Delete related messages and tool calls
        messages = await get_messages_by_conversation(str(conversation.id))
        for message in messages:
            await ToolCall.find(ToolCall.message_id == str(message.id)).delete()
        await Message.find(Message.conversation_id == str(conversation.id)).delete()
        await conversation.delete()
        return True
    return False


# Message Operations


async def get_message_by_id(message_id: str) -> Message | None:
    """Get message by ID."""
    return await Message.get(message_id)


async def get_messages_by_conversation(
    conversation_id: str,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Message]:
    """Get messages for a conversation with pagination."""
    return await (
        Message.find(Message.conversation_id == conversation_id)
        .sort("created_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )


async def count_messages(conversation_id: str) -> int:
    """Count messages in a conversation."""
    return await Message.find(Message.conversation_id == conversation_id).count()


async def create_message(
    *,
    conversation_id: str,
    role: str,
    content: str,
    model_name: str | None = None,
    tokens_used: int | None = None,
) -> Message:
    """Create a new message."""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        model_name=model_name,
        tokens_used=tokens_used,
    )
    await message.insert()

    # Update conversation's updated_at timestamp
    conversation = await get_conversation_by_id(conversation_id)
    if conversation:
        conversation.updated_at = datetime.now(UTC)
        await conversation.save()

    return message


async def delete_message(message_id: str) -> bool:
    """Delete a message and its tool calls."""
    message = await get_message_by_id(message_id)
    if message:
        await ToolCall.find(ToolCall.message_id == str(message.id)).delete()
        await message.delete()
        return True
    return False


# ToolCall Operations


async def get_tool_call_by_id(tool_call_id: str) -> ToolCall | None:
    """Get tool call by ID."""
    return await ToolCall.get(tool_call_id)


async def get_tool_calls_by_message(
    message_id: str,
) -> list[ToolCall]:
    """Get tool calls for a message."""
    return await (
        ToolCall.find(ToolCall.message_id == message_id)
        .sort("started_at")
        .to_list()
    )


async def create_tool_call(
    *,
    message_id: str,
    tool_call_id: str,
    tool_name: str,
    args: dict[str, Any],
    started_at: datetime,
) -> ToolCall:
    """Create a new tool call record."""
    tool_call = ToolCall(
        message_id=message_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        args=args,
        started_at=started_at,
        status="running",
    )
    await tool_call.insert()
    return tool_call


async def complete_tool_call(
    *,
    db_tool_call: ToolCall,
    result: str,
    completed_at: datetime,
    success: bool = True,
) -> ToolCall:
    """Mark a tool call as completed."""
    db_tool_call.result = result
    db_tool_call.completed_at = completed_at
    db_tool_call.status = "completed" if success else "failed"

    # Calculate duration
    if db_tool_call.started_at:
        delta = completed_at - db_tool_call.started_at
        db_tool_call.duration_ms = int(delta.total_seconds() * 1000)

    await db_tool_call.save()
    return db_tool_call


{%- else %}
"""Conversation repository - not configured."""
{%- endif %}
