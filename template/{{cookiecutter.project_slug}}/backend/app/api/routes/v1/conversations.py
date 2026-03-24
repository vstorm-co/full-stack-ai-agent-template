"""Conversation API routes for AI chat persistence.

Provides CRUD operations for conversations and messages.

The endpoints are:
- GET /conversations - List user's conversations
- POST /conversations - Create a new conversation
- GET /conversations/{id} - Get a conversation with messages
- PATCH /conversations/{id} - Update conversation title/archived status
- DELETE /conversations/{id} - Delete a conversation
- POST /conversations/{id}/messages - Add a message to conversation
- GET /conversations/{id}/messages - List messages in conversation
"""

{%- if cookiecutter.use_postgresql %}
from typing import Any
from uuid import UUID
{%- else %}
from typing import Any
{%- endif %}

from fastapi import APIRouter, Query, status

{%- if cookiecutter.use_mongodb %}
from app.api.deps import ConversationSvc
{%- else %}
from app.api.deps import DBSession, ConversationSvc
{%- endif %}
{%- if cookiecutter.use_jwt %}
from app.api.deps import CurrentAdmin, CurrentUser
{%- endif %}
from app.schemas.conversation import (
    ConversationCreate,
    ConversationList,
    ConversationRead,
    ConversationReadWithMessages,
    ConversationUpdate,
    MessageCreate,
    MessageList,
    MessageRead,
    MessageReadSimple,
)

router = APIRouter()


{%- if cookiecutter.use_postgresql %}


@router.get("/export")
async def export_conversations(
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentAdmin,
{%- endif %}
) -> Any:
    """Export all conversations with messages and tool calls (admin only)."""
    from fastapi.responses import JSONResponse

    export_data = await conversation_service.export_all()
    return JSONResponse(content={"conversations": export_data, "total": len(export_data)},
        headers={"Content-Disposition": 'attachment; filename="conversations_export.json"'})


@router.get("", response_model=ConversationList)
async def list_conversations(
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum conversations to return"),
    include_archived: bool = Query(False, description="Include archived conversations"),
) -> Any:
    """List conversations for the current user.

    Returns conversations ordered by most recently updated.
    """
    items, total = await conversation_service.list_conversations(
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
        skip=skip,
        limit=limit,
        include_archived=include_archived,
    )
    return ConversationList(items=items, total=total)  # type: ignore[arg-type]


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    data: ConversationCreate | None = None,
) -> Any:
    """Create a new conversation.

    The title is optional and can be set later.
    """
    if data is None:
        data = ConversationCreate()
{%- if cookiecutter.use_jwt %}
    data.user_id = current_user.id
{%- endif %}
    return await conversation_service.create_conversation(data)


@router.get("/{conversation_id}", response_model=ConversationReadWithMessages)
async def get_conversation(
    conversation_id: UUID,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> Any:
    """Get a conversation with all its messages.

    Raises 404 if the conversation does not exist.
    """
    return await conversation_service.get_conversation(
        conversation_id, include_messages=True,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )


@router.patch("/{conversation_id}", response_model=ConversationRead)
async def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> Any:
    """Update a conversation's title or archived status.

    Raises 404 if the conversation does not exist.
    """
    return await conversation_service.update_conversation(
        conversation_id, data,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_conversation(
    conversation_id: UUID,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> None:
    """Delete a conversation and all its messages.

    Raises 404 if the conversation does not exist.
    """
    await conversation_service.delete_conversation(
        conversation_id,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )


@router.post(
    "/{conversation_id}/archive",
    response_model=ConversationRead,
)
async def archive_conversation(
    conversation_id: UUID,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> Any:
    """Archive a conversation.

    Archived conversations are hidden from the default list view.
    """
    return await conversation_service.archive_conversation(
        conversation_id,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )


@router.get("/{conversation_id}/messages", response_model=MessageList)
async def list_messages(
    conversation_id: UUID,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> Any:
    """List messages in a conversation.

    Returns messages ordered by creation time (oldest first).
    """
    items, total = await conversation_service.list_messages(conversation_id, skip=skip, limit=limit, include_tool_calls=True)
    return MessageList(items=items, total=total)  # type: ignore[arg-type]


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_message(
    conversation_id: UUID,
    data: MessageCreate,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> Any:
    """Add a message to a conversation.

    Raises 404 if the conversation does not exist.
    """
    return await conversation_service.add_message(conversation_id, data)


{%- elif cookiecutter.use_sqlite %}


@router.get("/export")
def export_conversations(
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentAdmin,
{%- endif %}
) -> Any:
    """Export all conversations with messages and tool calls (admin only)."""
    from fastapi.responses import JSONResponse

    export_data = conversation_service.export_all()
    return JSONResponse(content={"conversations": export_data, "total": len(export_data)},
        headers={"Content-Disposition": 'attachment; filename="conversations_export.json"'})


@router.get("", response_model=ConversationList)
def list_conversations(
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum conversations to return"),
    include_archived: bool = Query(False, description="Include archived conversations"),
) -> Any:
    """List conversations for the current user.

    Returns conversations ordered by most recently updated.
    """
    items, total = conversation_service.list_conversations(
{%- if cookiecutter.use_jwt %}
        user_id=str(current_user.id),
{%- endif %}
        skip=skip,
        limit=limit,
        include_archived=include_archived,
    )
    return ConversationList(items=items, total=total)  # type: ignore[arg-type]


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    data: ConversationCreate | None = None,
) -> Any:
    """Create a new conversation.

    The title is optional and can be set later.
    """
    if data is None:
        data = ConversationCreate()
{%- if cookiecutter.use_jwt %}
    data.user_id = str(current_user.id)
{%- endif %}
    return conversation_service.create_conversation(data)


@router.get("/{conversation_id}", response_model=ConversationReadWithMessages)
def get_conversation(
    conversation_id: str,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> Any:
    """Get a conversation with all its messages.

    Raises 404 if the conversation does not exist.
    """
    return conversation_service.get_conversation(conversation_id, include_messages=True)


@router.patch("/{conversation_id}", response_model=ConversationRead)
def update_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> Any:
    """Update a conversation's title or archived status.

    Raises 404 if the conversation does not exist.
    """
    return conversation_service.update_conversation(
        conversation_id, data,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_conversation(
    conversation_id: str,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> None:
    """Delete a conversation and all its messages.

    Raises 404 if the conversation does not exist.
    """
    conversation_service.delete_conversation(
        conversation_id,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )


@router.post(
    "/{conversation_id}/archive",
    response_model=ConversationRead,
)
def archive_conversation(
    conversation_id: str,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> Any:
    """Archive a conversation.

    Archived conversations are hidden from the default list view.
    """
    return conversation_service.archive_conversation(
        conversation_id,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )


@router.get("/{conversation_id}/messages", response_model=MessageList)
def list_messages(
    conversation_id: str,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> Any:
    """List messages in a conversation.

    Returns messages ordered by creation time (oldest first).
    """
    items, total = conversation_service.list_messages(conversation_id, skip=skip, limit=limit, include_tool_calls=True)
    return MessageList(items=items, total=total)  # type: ignore[arg-type]


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
def add_message(
    conversation_id: str,
    data: MessageCreate,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> Any:
    """Add a message to a conversation.

    Raises 404 if the conversation does not exist.
    """
    return conversation_service.add_message(conversation_id, data)


{%- elif cookiecutter.use_mongodb %}


@router.get("", response_model=ConversationList)
async def list_conversations(
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum conversations to return"),
    include_archived: bool = Query(False, description="Include archived conversations"),
) -> Any:
    """List conversations for the current user.

    Returns conversations ordered by most recently updated.
    """
    items, total = await conversation_service.list_conversations(
{%- if cookiecutter.use_jwt %}
        user_id=str(current_user.id),
{%- endif %}
        skip=skip,
        limit=limit,
        include_archived=include_archived,
    )
    return ConversationList(items=items, total=total)  # type: ignore[arg-type]


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    data: ConversationCreate | None = None,
) -> Any:
    """Create a new conversation.

    The title is optional and can be set later.
    """
    if data is None:
        data = ConversationCreate()
{%- if cookiecutter.use_jwt %}
    data.user_id = str(current_user.id)
{%- endif %}
    return await conversation_service.create_conversation(data)


@router.get("/{conversation_id}", response_model=ConversationReadWithMessages)
async def get_conversation(
    conversation_id: str,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> Any:
    """Get a conversation with all its messages.

    Raises 404 if the conversation does not exist.
    """
    return await conversation_service.get_conversation(
        conversation_id, include_messages=True,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )


@router.patch("/{conversation_id}", response_model=ConversationRead)
async def update_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> Any:
    """Update a conversation's title or archived status.

    Raises 404 if the conversation does not exist.
    """
    return await conversation_service.update_conversation(
        conversation_id, data,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_conversation(
    conversation_id: str,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> None:
    """Delete a conversation and all its messages.

    Raises 404 if the conversation does not exist.
    """
    await conversation_service.delete_conversation(
        conversation_id,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )


@router.post(
    "/{conversation_id}/archive",
    response_model=ConversationRead,
)
async def archive_conversation(
    conversation_id: str,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> Any:
    """Archive a conversation.

    Archived conversations are hidden from the default list view.
    """
    return await conversation_service.archive_conversation(
        conversation_id,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )


@router.get("/{conversation_id}/messages", response_model=MessageList)
async def list_messages(
    conversation_id: str,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> Any:
    """List messages in a conversation.

    Returns messages ordered by creation time (oldest first).
    """
    items, total = await conversation_service.list_messages(conversation_id, skip=skip, limit=limit, include_tool_calls=True)
    return MessageList(items=items, total=total)  # type: ignore[arg-type]


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_message(
    conversation_id: str,
    data: MessageCreate,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> Any:
    """Add a message to a conversation.

    Raises 404 if the conversation does not exist.
    """
    return await conversation_service.add_message(conversation_id, data)


{%- endif %}
