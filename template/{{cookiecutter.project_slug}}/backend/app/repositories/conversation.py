"""Conversation repository."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select, tuple_, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
{%- if cookiecutter.use_jwt %}
from sqlalchemy import String, literal
from app.db.models.chat_file import ChatFile
from app.db.models.user import User
{%- endif %}

from app.db.models.conversation import Conversation, Message, ToolCall


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
            .options(
                selectinload(Conversation.messages).selectinload(Message.tool_calls),
                selectinload(Conversation.messages).selectinload(Message.files),
            )
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
{%- if cookiecutter.enable_teams %}
    organization_id: UUID | None = None,
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
{%- if cookiecutter.enable_teams %}
    if organization_id is not None:
        query = query.where(Conversation.organization_id == organization_id)
{%- endif %}
    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    query = query.order_by(func.coalesce(Conversation.updated_at, Conversation.created_at).desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


{%- if cookiecutter.use_jwt %}
async def get_all_conversations_with_count(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
    search: str | None = None,
) -> tuple[list[tuple[Conversation, int]], int]:
    """Get all conversations with message counts for admin (paginated).

    Returns list of (conversation, message_count) tuples and total count.
    """
    message_count_subq = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )

    query = select(Conversation, message_count_subq.label("message_count"))

    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
        query = query.where(
            (Conversation.title.ilike(f"%{safe_search}%", escape="\\"))
            | Conversation.id.cast(String).ilike(f"{safe_search}%", escape="\\")
        )

    query = query.order_by(
        func.coalesce(Conversation.updated_at, Conversation.created_at).desc()
    ).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    count_query = select(func.count(Conversation.id))
    if not include_archived:
        count_query = count_query.where(Conversation.is_archived == False)  # noqa: E712
    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
        count_query = count_query.where(
            (Conversation.title.ilike(f"%{safe_search}%", escape="\\"))
            | Conversation.id.cast(String).ilike(f"{safe_search}%", escape="\\")
        )
    total: int = (await db.execute(count_query)).scalar() or 0

    return [tuple(row) for row in rows], total
{%- endif %}


{%- if cookiecutter.use_jwt %}


async def export_chunk(
    db: AsyncSession,
    *,
    last_created_at: datetime | None,
    last_id: UUID | None,
    limit: int,
) -> list[Conversation]:
    """Keyset-paginated chunk for admin export of all conversations."""
    query = (
        select(Conversation)
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        .limit(limit)
    )
    if last_created_at is not None and last_id is not None:
        query = query.where(
            tuple_(Conversation.created_at, Conversation.id) < (last_created_at, last_id)
        )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_demo_conversations_with_count(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[tuple[Conversation, int, str | None]], int]:
    """Get admin-curated demo conversations with message count + first user prompt preview."""
    message_count_subq = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    preview_subq = (
        select(Message.content)
        .where(Message.conversation_id == Conversation.id, Message.role == "user")
        .correlate(Conversation)
        .order_by(Message.created_at.asc())
        .limit(1)
        .scalar_subquery()
    )
    query = (
        select(
            Conversation,
            message_count_subq.label("message_count"),
            preview_subq.label("preview"),
        )
        .where(Conversation.is_demo.is_(True))
        .order_by(func.coalesce(Conversation.updated_at, Conversation.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    total: int = (
        await db.execute(
            select(func.count(Conversation.id)).where(Conversation.is_demo.is_(True))
        )
    ).scalar() or 0

    return [tuple(row) for row in rows], total  # type: ignore[return-value]


async def admin_list_with_users(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    user_id: UUID | None = None,
    include_archived: bool = False,
    archived_only: bool = False,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
) -> tuple[list[tuple[Conversation, int, str | None]], int]:
    """Admin: list conversations across all users with message counts and owner email.

    Returns list of (conversation, message_count, user_email) tuples and total count.
    """
    msg_count_col = func.count(Message.id).label("message_count")
    query = (
        select(Conversation, msg_count_col, User.email.label("user_email"))
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .outerjoin(User, User.id == Conversation.user_id)
        .group_by(Conversation.id, User.email)
    )
    count_query = select(func.count()).select_from(Conversation)

    if search:
        query = query.where(Conversation.title.ilike(f"%{search}%"))
        count_query = count_query.where(Conversation.title.ilike(f"%{search}%"))
    if user_id is not None:
        query = query.where(Conversation.user_id == user_id)
        count_query = count_query.where(Conversation.user_id == user_id)
    if archived_only:
        query = query.where(Conversation.is_archived.is_(True))
        count_query = count_query.where(Conversation.is_archived.is_(True))
    elif not include_archived:
        query = query.where(Conversation.is_archived.is_(False))
        count_query = count_query.where(Conversation.is_archived.is_(False))

    sort_columns: dict[str, Any] = {
        "title": Conversation.title,
        "created_at": Conversation.created_at,
        "updated_at": Conversation.updated_at,
        "owner": User.email,
        "messages": msg_count_col,
    }
    sort_col = sort_columns.get(sort_by, Conversation.updated_at)
    sort_col = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
    query = query.order_by(sort_col).offset(skip).limit(limit)

    total = await db.scalar(count_query) or 0
    rows = (await db.execute(query)).all()
    return [(conv, msg_count, email) for conv, msg_count, email in rows], total
{%- endif %}


async def count_conversations(
    db: AsyncSession,
{%- if cookiecutter.use_jwt %}
    user_id: UUID | None = None,
{%- endif %}
{%- if cookiecutter.enable_teams %}
    organization_id: UUID | None = None,
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
{%- if cookiecutter.enable_teams %}
    if organization_id is not None:
        query = query.where(Conversation.organization_id == organization_id)
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
{%- if cookiecutter.use_external_user_id_in_conversations %}
    external_user_id: str | None = None,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    organization_id: UUID | None = None,
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: UUID | None = None,
{%- endif %}
    title: str | None = None,
) -> Conversation:
    """Create a new conversation."""
    conversation = Conversation(
{%- if cookiecutter.use_jwt %}
        user_id=user_id,
{%- endif %}
{%- if cookiecutter.use_external_user_id_in_conversations %}
        external_user_id=external_user_id,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
        organization_id=organization_id,
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
        project_id=project_id,
{%- endif %}
        title=title,
    )
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    return conversation


{%- if cookiecutter.use_external_user_id_in_conversations %}


async def list_conversations_by_external_user_id(
    db: AsyncSession,
    external_user_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
) -> list[Conversation]:
    """Fetch conversations by client-known IdP `sub` (delegated mode).

    Lets the client list a user's chats without ever knowing the internal
    User UUID. No FK join — direct index scan on the denormalized column.
    """
    query = select(Conversation).where(Conversation.external_user_id == external_user_id)
    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    query = (
        query.order_by(Conversation.updated_at.desc().nullslast(), Conversation.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
{%- endif %}


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
    *,
    db_conversation: Conversation,
) -> Conversation:
    """Archive a conversation."""
    db_conversation.is_archived = True
    db.add(db_conversation)
    await db.flush()
    await db.refresh(db_conversation)
    return db_conversation


async def delete_conversation(db: AsyncSession, *, db_conversation: Conversation) -> None:
    """Delete a conversation and all related messages/tool_calls (cascades)."""
    await db.delete(db_conversation)
    await db.flush()



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
{%- if cookiecutter.use_jwt %}
    query = query.options(selectinload(Message.files))
{%- endif %}
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


{%- if cookiecutter.enable_teams %}


async def aggregate_tool_calls_for_org(
    db: AsyncSession,
    organization_id: UUID,
    *,
    since: datetime,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return per-tool aggregates for an org, ordered by call count desc.

    Joins ``tool_calls → messages → conversations`` so the same org filter the
    rest of the dashboard uses applies here. Excludes tool calls whose backing
    conversation has no ``organization_id`` (orphans).
    """
    query = (
        select(
            ToolCall.tool_name.label("tool_name"),
            func.count().label("total_calls"),
            func.sum(case((ToolCall.status == "failed", 1), else_=0)).label("failed_calls"),
            func.avg(ToolCall.duration_ms).label("avg_duration_ms"),
            func.max(ToolCall.started_at).label("last_used_at"),
        )
        .join(Message, Message.id == ToolCall.message_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Conversation.organization_id == organization_id,
            ToolCall.started_at >= since,
        )
        .group_by(ToolCall.tool_name)
        .order_by(func.count().desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return [
        {
            "tool_name": row.tool_name,
            "total_calls": int(row.total_calls or 0),
            "failed_calls": int(row.failed_calls or 0),
            "avg_duration_ms": int(row.avg_duration_ms) if row.avg_duration_ms else None,
            "last_used_at": row.last_used_at,
        }
        for row in result.all()
    ]
{%- endif %}


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

    if db_tool_call.started_at:
        delta = completed_at - db_tool_call.started_at
        db_tool_call.duration_ms = int(delta.total_seconds() * 1000)

    db.add(db_tool_call)
    await db.flush()
    await db.refresh(db_tool_call)
    return db_tool_call


