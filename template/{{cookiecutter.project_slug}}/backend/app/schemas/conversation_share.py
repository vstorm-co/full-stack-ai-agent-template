{%- if cookiecutter.use_jwt %}
"""Conversation sharing schemas."""

from datetime import datetime
from typing import Literal

from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.user import AdminUserList, AdminUserRead  # re-exported for backward compatibility

__all__ = [
    "ConversationShareCreate",
    "ConversationShareRead",
    "ConversationShareList",
    "AdminConversationRead",
    "AdminConversationList",
    "AdminUserRead",
    "AdminUserList",
]


class ConversationShareCreate(BaseSchema):
    """Schema for creating a conversation share."""

    shared_with: UUID | None = Field(default=None, description="User ID to share with (omit for link sharing)")
    permission: Literal["view", "edit"] = Field(default="view", description="Access level")
    generate_link: bool = Field(default=False, description="Generate a public share link")


class ConversationShareRead(BaseSchema):
    """Schema for reading a conversation share."""

    id: UUID
    conversation_id: UUID
    shared_by: UUID
    shared_with: UUID | None = None
    share_token: str | None = None
    permission: Literal["view", "edit"] = "view"
    shared_with_email: str | None = Field(default=None, description="Email of the user shared with")
    shared_by_email: str | None = Field(default=None, description="Email of the user who shared")
    created_at: datetime


class ConversationShareList(BaseSchema):
    """Paginated list of conversation shares."""

    items: list[ConversationShareRead]
    total: int



class AdminConversationRead(BaseSchema):
    """Admin view of a conversation — includes owner email."""

    id: UUID
    user_id: UUID | None = None
{%- if cookiecutter.use_pydantic_deep %}
    project_id: UUID | None = None
{%- endif %}
    title: str | None = None
    is_archived: bool = False
    message_count: int = 0
    user_email: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class AdminConversationList(BaseSchema):
    """Paginated list of conversations for admin."""

    items: list[AdminConversationRead]
    total: int


{%- else %}
"""Conversation sharing schemas — requires JWT authentication (use_jwt)."""
{%- endif %}
