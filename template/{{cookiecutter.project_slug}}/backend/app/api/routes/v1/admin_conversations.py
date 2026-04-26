{%- if cookiecutter.use_jwt %}
"""Admin conversation and user browsing routes.

All endpoints require admin role.

Endpoints:
    GET  /admin/conversations           — List all conversations (paginated, filterable)
    GET  /admin/conversations/{id}      — Get any conversation with messages (read-only)
    GET  /admin/users                   — List all users with conversation counts
    GET  /admin/users/{user_id}/conversations — List conversations for a specific user
"""

from typing import Any

{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from fastapi import APIRouter, Query

from app.api.deps import ConversationSvc, CurrentAdmin, UserSvc
from app.schemas.conversation import ConversationReadWithMessages
from app.schemas.conversation_share import AdminConversationList, AdminUserList

router = APIRouter()


{%- if cookiecutter.use_postgresql %}


@router.get("", response_model=AdminConversationList)
async def admin_list_conversations(
    service: ConversationSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
    search: str | None = Query(default=None, description="Search by title"),
    user_id: UUID | None = Query(default=None, description="Filter by user ID"),
    include_archived: bool = Query(False, description="Include archived conversations"),
) -> Any:
    """List all conversations across all users (admin only)."""
    return await service.admin_list_with_users(
        skip=skip,
        limit=limit,
        search=search,
        user_id=user_id,
        include_archived=include_archived,
    )


@router.get("/users", response_model=AdminUserList)
async def admin_list_users(
    user_service: UserSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = Query(default=None, description="Search by email or name"),
) -> Any:
    """List all users with conversation counts (admin only)."""
    return await user_service.admin_list_with_counts(skip=skip, limit=limit, search=search)


@router.get("/{conversation_id}", response_model=ConversationReadWithMessages)
async def admin_get_conversation(
    conversation_id: UUID,
    service: ConversationSvc,
    _: CurrentAdmin,
) -> Any:
    """Get any conversation with messages (admin read-only access)."""
    return await service.get_conversation_with_messages(conversation_id)


{%- elif cookiecutter.use_sqlite %}


@router.get("", response_model=AdminConversationList)
def admin_list_conversations(
    service: ConversationSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
    search: str | None = Query(default=None, description="Search by title"),
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    include_archived: bool = Query(False, description="Include archived conversations"),
) -> Any:
    """List all conversations across all users (admin only)."""
    return service.admin_list_with_users(
        skip=skip,
        limit=limit,
        search=search,
        user_id=user_id,
        include_archived=include_archived,
    )


@router.get("/users", response_model=AdminUserList)
def admin_list_users(
    user_service: UserSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = Query(default=None, description="Search by email or name"),
) -> Any:
    """List all users with conversation counts (admin only)."""
    return user_service.admin_list_with_counts(skip=skip, limit=limit, search=search)


@router.get("/{conversation_id}", response_model=ConversationReadWithMessages)
def admin_get_conversation(
    conversation_id: str,
    service: ConversationSvc,
    _: CurrentAdmin,
) -> Any:
    """Get any conversation with messages (admin read-only access)."""
    return service.get_conversation_with_messages(conversation_id)


{%- elif cookiecutter.use_mongodb %}


@router.get("", response_model=AdminConversationList)
async def admin_list_conversations(
    service: ConversationSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
    search: str | None = Query(default=None, description="Search by title"),
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    include_archived: bool = Query(False, description="Include archived conversations"),
) -> Any:
    """List all conversations across all users (admin only)."""
    return await service.admin_list_with_users(
        skip=skip,
        limit=limit,
        search=search,
        user_id=user_id,
        include_archived=include_archived,
    )


@router.get("/users", response_model=AdminUserList)
async def admin_list_users(
    user_service: UserSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = Query(default=None, description="Search by email or name"),
) -> Any:
    """List all users with conversation counts (admin only)."""
    return await user_service.admin_list_with_counts(skip=skip, limit=limit, search=search)


@router.get("/{conversation_id}", response_model=ConversationReadWithMessages)
async def admin_get_conversation(
    conversation_id: str,
    service: ConversationSvc,
    _: CurrentAdmin,
) -> Any:
    """Get any conversation with messages (admin read-only access)."""
    return await service.get_conversation_with_messages(conversation_id)


{%- endif %}
{%- else %}
"""Admin conversation routes — requires JWT authentication (use_jwt)."""
{%- endif %}
