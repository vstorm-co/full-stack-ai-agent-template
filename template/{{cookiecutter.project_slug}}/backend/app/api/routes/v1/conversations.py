from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import JSONResponse

from app.api.deps import ConversationSvc
{%- if cookiecutter.use_jwt %}
from app.api.deps import ConversationShareSvc, CurrentAdmin, CurrentUser
{%- if cookiecutter.use_database %}
from app.api.deps import MessageRatingSvc
{%- endif %}
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
from app.api.deps import ActiveOrg
{%- endif %}
from app.db.models.user import UserRole
from app.schemas.conversation import (
    ConversationCreate,
    ConversationExport,
    ConversationList,
    ConversationRead,
    ConversationReadWithMessages,
    ConversationUpdate,
    MessageCreate,
    MessageList,
    MessageRead,
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    ToolCallStatList,
{%- endif %}
{%- if cookiecutter.use_jwt %}
    ConversationAdminList,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
    ConversationKBSettings,
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


@router.get("/export", response_model=ConversationExport)
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
    """List all conversations with message counts (admin only)."""
    items, total = await conversation_service.list_conversations_admin(
        skip=skip,
        limit=limit,
        include_archived=include_archived,
        search=search,
    )
    return ConversationAdminList(items=items, total=total)


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


@router.get("/shared/{token}", response_model=ConversationReadWithMessages)
async def get_shared_conversation(
    token: str,
    share_service: ConversationShareSvc,
) -> Any:
    """Access a shared conversation via public token (no auth required)."""
    return await share_service.get_by_token(token)
{%- endif %}


@router.get("", response_model=ConversationList)
async def list_conversations(
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    active_org: ActiveOrg,
{%- endif %}
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum conversations to return"),
    include_archived: bool = Query(False, description="Include archived conversations"),
) -> Any:
    """List conversations for the current user."""
    items, total = await conversation_service.list_conversations(
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
        organization_id=active_org.id,
{%- endif %}
        skip=skip,
        limit=limit,
        include_archived=include_archived,
    )
    return ConversationList(items=items, total=total)  # ty: ignore[invalid-argument-type]


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    active_org: ActiveOrg,
{%- endif %}
    data: ConversationCreate | None = None,
) -> Any:
    """Create a new conversation."""
    if data is None:
        data = ConversationCreate()
{%- if cookiecutter.use_jwt %}
    data = data.model_copy(update={"user_id": current_user.id})
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    data = data.model_copy(update={"organization_id": active_org.id})
{%- endif %}
    return await conversation_service.create_conversation(data)

{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}


@router.get("/tool-stats", response_model=ToolCallStatList)
async def get_tool_stats(
    conversation_service: ConversationSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    days: int = Query(7, ge=1, le=90, description="Window in days"),
    limit: int = Query(10, ge=1, le=50, description="Max tools to return"),
) -> Any:
    """Top tools used by the active org over the given window."""
    items = await conversation_service.aggregate_tool_calls(
        active_org.id, days=days, limit=limit
    )
    return ToolCallStatList(items=items, days=days)  # ty: ignore[invalid-argument-type]
{%- endif %}


@router.get("/{conversation_id}", response_model=ConversationReadWithMessages)
async def get_conversation(
    conversation_id: UUID,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> Any:
    """Get a conversation with all its messages."""
{%- if cookiecutter.use_jwt %}
    uid = None if current_user.has_role(UserRole.ADMIN) else current_user.id
{%- endif %}
    return await conversation_service.get_conversation(
        conversation_id, include_messages=True,
{%- if cookiecutter.use_jwt %}
        user_id=uid,
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
    """Update a conversation's title or archived status."""
    return await conversation_service.update_conversation(
        conversation_id, data,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )


{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}


@router.patch("/{conversation_id}/kb-settings", response_model=ConversationRead)
async def update_kb_settings(
    conversation_id: UUID,
    data: ConversationKBSettings,
    conversation_service: ConversationSvc,
    current_user: CurrentUser,
) -> Any:
    """Update which Knowledge Bases are active for this conversation.

    Send null to restore defaults, [] to disable RAG, or [id,...] for explicit selection.
    """
    return await conversation_service.update_kb_settings(
        conversation_id,
        data.active_knowledge_base_ids,
        user_id=current_user.id,
    )
{%- endif %}


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_conversation(
    conversation_id: UUID,
    conversation_service: ConversationSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
) -> None:
    """Delete a conversation and all its messages."""
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
    """List messages in a conversation."""
{%- if cookiecutter.use_jwt %}
    uid = None if current_user.has_role(UserRole.ADMIN) else current_user.id
{%- endif %}
    items, total = await conversation_service.list_messages(
        conversation_id,
        skip=skip,
        limit=limit,
        include_tool_calls=True,
{%- if cookiecutter.use_jwt %}
        user_id=uid,
{%- endif %}
    )
    return MessageList(items=items, total=total)  # ty: ignore[invalid-argument-type]


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
    """Add a message to a conversation."""
    return await conversation_service.add_message(conversation_id, data)


{%- if cookiecutter.use_jwt and cookiecutter.use_database %}


@router.post(
    "/{conversation_id}/messages/{message_id}/rate",
    response_model=MessageRatingRead,
)
async def rate_message(
    conversation_id: UUID,
    message_id: UUID,
    data: MessageRatingCreate,
    rating_service: MessageRatingSvc,
    current_user: CurrentUser,
    response: Response,
) -> Any:
    """Rate an assistant message — 201 for new rating, 200 when updating."""
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
    """Remove your rating from a message."""
    await rating_service.remove_rating(
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=current_user.id,
    )


{%- endif %}

{%- if cookiecutter.use_jwt %}


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


{%- endif %}
