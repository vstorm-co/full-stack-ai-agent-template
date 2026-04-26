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

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import JSONResponse

{%- if cookiecutter.use_mongodb %}
from app.api.deps import ConversationSvc
{%- else %}
from app.api.deps import DBSession, ConversationSvc
{%- endif %}
{%- if cookiecutter.use_jwt %}
from app.api.deps import ConversationShareSvc, CurrentAdmin, CurrentUser
{%- if cookiecutter.use_database %}
from app.api.deps import MessageRatingSvc
{%- endif %}
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
{%- if cookiecutter.use_jwt %}
    ConversationAdminList,
{%- endif %}
)
{%- if cookiecutter.use_jwt %}
from app.schemas.conversation_share import ConversationShareCreate, ConversationShareList, ConversationShareRead
from app.schemas.message_rating import (
    MessageRatingCreate,
    MessageRatingRead,
)
{%- endif %}

router = APIRouter()


{%- if cookiecutter.use_postgresql %}


@router.get("/export")
async def export_conversations(
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Export all conversations with messages and tool calls (admin only)."""
    export_data = await conversation_service.export_all()
    return JSONResponse(content={"conversations": export_data, "total": len(export_data)},
        headers={"Content-Disposition": 'attachment; filename="conversations_export.json"'})


{%- if cookiecutter.use_jwt %}
@router.get("/admin-list", response_model=ConversationAdminList)
async def list_conversations_admin(
    conversation_service: ConversationSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_archived: bool = Query(True, description="Include archived conversations"),
    search: str | None = Query(None, max_length=100, description="Search by title or ID prefix"),
) -> Any:
    """List all conversations with message counts (admin only).

    Returns paginated conversations without message content.
    """
    items, total = await conversation_service.list_conversations_admin(
        skip=skip,
        limit=limit,
        include_archived=include_archived,
        search=search,
    )
    return ConversationAdminList(items=items, total=total)
{%- endif %}


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
    data = data.model_copy(update={"user_id": current_user.id})
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
    items, total = await conversation_service.list_messages(
        conversation_id,
        skip=skip,
        limit=limit,
        include_tool_calls=True,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )
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


{%- if cookiecutter.use_jwt %}


@router.post(
    "/{conversation_id}/messages/{message_id}/rate",
    response_model=MessageRatingRead,
    status_code=status.HTTP_200_OK,
)
async def rate_message(
    conversation_id: UUID,
    message_id: UUID,
    data: MessageRatingCreate,
    rating_service: MessageRatingSvc,
    current_user: CurrentUser,
    response: Response,
) -> Any:
    """Rate an assistant message.

    Creates a new rating or updates an existing one.
    Only assistant messages can be rated.

    Args:
        conversation_id: The conversation containing the message
        message_id: The message to rate
        data: Rating value (1 for like, -1 for dislike) and optional comment

    Returns:
        201 Created for new rating, 200 OK when updating existing rating.
    """
    rating, is_new = await rating_service.rate_message(
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=current_user.id,
        data=data,
    )
    if is_new:
        response.status_code = status.HTTP_201_CREATED
    return rating


@router.delete(
    "/{conversation_id}/messages/{message_id}/rate",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_rating(
    conversation_id: UUID,
    message_id: UUID,
    rating_service: MessageRatingSvc,
    current_user: CurrentUser,
) -> None:
    """Remove your rating from a message.

    Args:
        conversation_id: The conversation containing the message
        message_id: The message to remove rating from
    """
    await rating_service.remove_rating(
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=current_user.id,
    )


{%- endif %}


{%- elif cookiecutter.use_sqlite %}


@router.get("/export")
def export_conversations(
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Export all conversations with messages and tool calls (admin only)."""
    export_data = conversation_service.export_all()
    return JSONResponse(content={"conversations": export_data, "total": len(export_data)},
        headers={"Content-Disposition": 'attachment; filename="conversations_export.json"'})


{%- if cookiecutter.use_jwt %}
@router.get("/admin-list", response_model=ConversationAdminList)
def list_conversations_admin(
    conversation_service: ConversationSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_archived: bool = Query(True, description="Include archived conversations"),
    search: str | None = Query(None, max_length=100, description="Search by title or ID prefix"),
) -> Any:
    """List all conversations with message counts (admin only).

    Returns paginated conversations without message content.
    """
    items, total = conversation_service.list_conversations_admin(
        skip=skip,
        limit=limit,
        include_archived=include_archived,
        search=search,
    )
    return ConversationAdminList(items=items, total=total)
{%- endif %}


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
    data = data.model_copy(update={"user_id": str(current_user.id)})
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
    return conversation_service.get_conversation(
        conversation_id, include_messages=True,
{%- if cookiecutter.use_jwt %}
        user_id=str(current_user.id),
{%- endif %}
    )


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
        user_id=str(current_user.id),
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
        user_id=str(current_user.id),
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
        user_id=str(current_user.id),
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
    items, total = conversation_service.list_messages(
        conversation_id,
        skip=skip,
        limit=limit,
        include_tool_calls=True,
{%- if cookiecutter.use_jwt %}
        user_id=str(current_user.id),
{%- endif %}
    )
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


{%- if cookiecutter.use_jwt %}


@router.post(
    "/{conversation_id}/messages/{message_id}/rate",
    response_model=MessageRatingRead,
    status_code=status.HTTP_200_OK,
)
def rate_message(
    conversation_id: str,
    message_id: str,
    data: MessageRatingCreate,
    rating_service: MessageRatingSvc,
    current_user: CurrentUser,
    response: Response,
) -> Any:
    """Rate an assistant message.

    Creates a new rating or updates an existing one.
    Only assistant messages can be rated.

    Args:
        conversation_id: The conversation containing the message
        message_id: The message to rate
        data: Rating value (1 for like, -1 for dislike) and optional comment

    Returns:
        201 Created for new rating, 200 OK when updating existing rating.
    """
    rating, is_new = rating_service.rate_message(
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=str(current_user.id),
        data=data,
    )
    if is_new:
        response.status_code = status.HTTP_201_CREATED
    return rating


@router.delete(
    "/{conversation_id}/messages/{message_id}/rate",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def remove_rating(
    conversation_id: str,
    message_id: str,
    rating_service: MessageRatingSvc,
    current_user: CurrentUser,
) -> None:
    """Remove your rating from a message.

    Args:
        conversation_id: The conversation containing the message
        message_id: The message to remove rating from
    """
    rating_service.remove_rating(
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=str(current_user.id),
    )


{%- endif %}


{%- elif cookiecutter.use_mongodb %}


{%- if cookiecutter.use_jwt %}
@router.get("/admin-list", response_model=ConversationAdminList)
async def list_conversations_admin(
    conversation_service: ConversationSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_archived: bool = Query(True, description="Include archived conversations"),
    search: str | None = Query(None, max_length=100, description="Search by title or ID prefix"),
) -> Any:
    """List all conversations with message counts (admin only).

    Returns paginated conversations without message content.
    """
    items, total = await conversation_service.list_conversations_admin(
        skip=skip,
        limit=limit,
        include_archived=include_archived,
        search=search,
    )
    return ConversationAdminList(items=items, total=total)


{%- endif %}


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
    data = data.model_copy(update={"user_id": str(current_user.id)})
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
        user_id=str(current_user.id),
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
        user_id=str(current_user.id),
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
        user_id=str(current_user.id),
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
        user_id=str(current_user.id),
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
    items, total = await conversation_service.list_messages(
        conversation_id,
        skip=skip,
        limit=limit,
        include_tool_calls=True,
{%- if cookiecutter.use_jwt %}
        user_id=str(current_user.id),
{%- endif %}
    )
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


{%- if cookiecutter.use_jwt %}


@router.post(
    "/{conversation_id}/messages/{message_id}/rate",
    response_model=MessageRatingRead,
    status_code=status.HTTP_200_OK,
)
async def rate_message(
    conversation_id: str,
    message_id: str,
    data: MessageRatingCreate,
    rating_service: MessageRatingSvc,
    current_user: CurrentUser,
    response: Response,
) -> Any:
    """Rate an assistant message.

    Creates a new rating or updates an existing one.
    Only assistant messages can be rated.

    Args:
        conversation_id: The conversation containing the message
        message_id: The message to rate
        data: Rating value (1 for like, -1 for dislike) and optional comment

    Returns:
        201 Created for new rating, 200 OK when updating existing rating.
    """
    rating, is_new = await rating_service.rate_message(
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=str(current_user.id),
        data=data,
    )
    if is_new:
        response.status_code = status.HTTP_201_CREATED
    return rating


@router.delete(
    "/{conversation_id}/messages/{message_id}/rate",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_rating(
    conversation_id: str,
    message_id: str,
    rating_service: MessageRatingSvc,
    current_user: CurrentUser,
) -> None:
    """Remove your rating from a message.

    Args:
        conversation_id: The conversation containing the message
        message_id: The message to remove rating from
    """
    await rating_service.remove_rating(
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=str(current_user.id),
    )


{%- endif %}


{%- endif %}

{%- if cookiecutter.use_jwt %}


{%- if cookiecutter.use_postgresql %}


@router.get("/shared-with-me", response_model=ConversationList)
async def list_shared_with_me(
    share_service: ConversationShareSvc,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List conversations shared with the current user."""
    items, total = await share_service.list_shared_with_me(current_user.id, skip=skip, limit=limit)
    return ConversationList(items=items, total=total)


@router.post("/{conversation_id}/shares", response_model=ConversationShareRead, status_code=status.HTTP_201_CREATED)
async def share_conversation(
    conversation_id: UUID,
    data: ConversationShareCreate,
    share_service: ConversationShareSvc,
    current_user: CurrentUser,
) -> Any:
    """Share a conversation with another user or generate a public link."""
    result = await share_service.share_conversation(
        conversation_id,
        shared_by=current_user.id,
        shared_with=data.shared_with,
        generate_link=data.generate_link,
        permission=data.permission,
    )
    return result["share"]


@router.get("/{conversation_id}/shares", response_model=ConversationShareList)
async def list_shares(
    conversation_id: UUID,
    share_service: ConversationShareSvc,
    current_user: CurrentUser,
) -> Any:
    """List all shares for a conversation (owner only)."""
    shares = await share_service.list_shares(conversation_id, current_user.id)
    return ConversationShareList(items=shares, total=len(shares))


@router.delete("/{conversation_id}/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def revoke_share(
    conversation_id: UUID,
    share_id: UUID,
    share_service: ConversationShareSvc,
    current_user: CurrentUser,
) -> None:
    """Revoke a conversation share."""
    await share_service.revoke_share(share_id, current_user.id)


@router.get("/shared/{token}")
async def get_shared_conversation(
    token: str,
    share_service: ConversationShareSvc,
) -> Any:
    """Access a shared conversation via public token (no auth required)."""
    return await share_service.get_by_token(token)


{%- elif cookiecutter.use_sqlite %}


@router.get("/shared-with-me", response_model=ConversationList)
def list_shared_with_me(
    share_service: ConversationShareSvc,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List conversations shared with the current user."""
    items, total = share_service.list_shared_with_me(str(current_user.id), skip=skip, limit=limit)
    return ConversationList(items=items, total=total)


@router.post("/{conversation_id}/shares", response_model=ConversationShareRead, status_code=status.HTTP_201_CREATED)
def share_conversation(
    conversation_id: str,
    data: ConversationShareCreate,
    share_service: ConversationShareSvc,
    current_user: CurrentUser,
) -> Any:
    """Share a conversation with another user or generate a public link."""
    result = share_service.share_conversation(
        conversation_id,
        shared_by=str(current_user.id),
        shared_with=data.shared_with,
        generate_link=data.generate_link,
        permission=data.permission,
    )
    return result["share"]


@router.get("/{conversation_id}/shares", response_model=ConversationShareList)
def list_shares(
    conversation_id: str,
    share_service: ConversationShareSvc,
    current_user: CurrentUser,
) -> Any:
    """List all shares for a conversation (owner only)."""
    shares = share_service.list_shares(conversation_id, str(current_user.id))
    return ConversationShareList(items=shares, total=len(shares))


@router.delete("/{conversation_id}/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def revoke_share(
    conversation_id: str,
    share_id: str,
    share_service: ConversationShareSvc,
    current_user: CurrentUser,
) -> None:
    """Revoke a conversation share."""
    share_service.revoke_share(share_id, str(current_user.id))


@router.get("/shared/{token}")
def get_shared_conversation(
    token: str,
    share_service: ConversationShareSvc,
) -> Any:
    """Access a shared conversation via public token (no auth required)."""
    return share_service.get_by_token(token)


{%- elif cookiecutter.use_mongodb %}


@router.get("/shared-with-me", response_model=ConversationList)
async def list_shared_with_me(
    share_service: ConversationShareSvc,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List conversations shared with the current user."""
    items, total = await share_service.list_shared_with_me(str(current_user.id), skip=skip, limit=limit)
    return ConversationList(items=items, total=total)


@router.post("/{conversation_id}/shares", response_model=ConversationShareRead, status_code=status.HTTP_201_CREATED)
async def share_conversation(
    conversation_id: str,
    data: ConversationShareCreate,
    share_service: ConversationShareSvc,
    current_user: CurrentUser,
) -> Any:
    """Share a conversation with another user or generate a public link."""
    result = await share_service.share_conversation(
        conversation_id,
        shared_by=str(current_user.id),
        shared_with=data.shared_with,
        generate_link=data.generate_link,
        permission=data.permission,
    )
    return result["share"]


@router.get("/{conversation_id}/shares", response_model=ConversationShareList)
async def list_shares(
    conversation_id: str,
    share_service: ConversationShareSvc,
    current_user: CurrentUser,
) -> Any:
    """List all shares for a conversation (owner only)."""
    shares = await share_service.list_shares(conversation_id, str(current_user.id))
    return ConversationShareList(items=shares, total=len(shares))


@router.delete("/{conversation_id}/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def revoke_share(
    conversation_id: str,
    share_id: str,
    share_service: ConversationShareSvc,
    current_user: CurrentUser,
) -> None:
    """Revoke a conversation share."""
    await share_service.revoke_share(share_id, str(current_user.id))


@router.get("/shared/{token}")
async def get_shared_conversation(
    token: str,
    share_service: ConversationShareSvc,
) -> Any:
    """Access a shared conversation via public token (no auth required)."""
    return await share_service.get_by_token(token)


{%- endif %}
{%- endif %}
