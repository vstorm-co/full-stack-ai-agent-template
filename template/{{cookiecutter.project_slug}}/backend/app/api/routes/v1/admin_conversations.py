{%- if cookiecutter.use_jwt %}
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import ConversationSvc, CurrentAdmin
from app.schemas.conversation import ConversationRead, ConversationReadWithMessages, ConversationUpdate
from app.schemas.conversation_share import AdminConversationList

router = APIRouter()


@router.get("", response_model=AdminConversationList)
async def admin_list_conversations(
    service: ConversationSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
    search: str | None = Query(default=None, description="Search by title"),
    user_id: UUID | None = Query(default=None, description="Filter by user ID"),
    status: Literal["active", "archived", "all"] = Query(
        "active", description="Filter by archival status"
    ),
    sort_by: Literal["title", "owner", "messages", "created_at", "updated_at"] = Query(
        "updated_at", description="Sort column"
    ),
    sort_dir: Literal["asc", "desc"] = Query("desc", description="Sort direction"),
) -> Any:
    """List all conversations across all users (admin only)."""
    return await service.admin_list_with_users(
        skip=skip,
        limit=limit,
        search=search,
        user_id=user_id,
        include_archived=status == "all",
        archived_only=status == "archived",
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/{conversation_id}", response_model=ConversationReadWithMessages)
async def admin_get_conversation(
    conversation_id: UUID,
    service: ConversationSvc,
    _: CurrentAdmin,
) -> Any:
    """Get any conversation with messages (admin read-only access)."""
    return await service.get_conversation_with_messages(conversation_id)


@router.patch("/{conversation_id}/demo", response_model=ConversationRead)
async def admin_set_demo_flag(
    conversation_id: UUID,
    service: ConversationSvc,
    _: CurrentAdmin,
    is_demo: bool = Query(..., description="Mark (true) or unmark (false) as a public demo"),
) -> Any:
    """Toggle a conversation's public-demo flag (admin only).

    Demo conversations are served without auth on the public demo gallery for replay.
    """
    return await service.update_conversation(
        conversation_id,
        ConversationUpdate(is_demo=is_demo),
        user_id=None,  # admin bypass — no ownership check
    )


{%- else %}
"""Admin conversation routes — requires JWT authentication (use_jwt)."""
router = APIRouter()
{%- endif %}
