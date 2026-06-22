"""Conversation schemas for AI chat persistence.

This module contains Pydantic schemas for Conversation, Message, and ToolCall entities.
"""

from datetime import datetime
from typing import Any, Literal

from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema




class ToolCallBase(BaseSchema):
    """Base tool call schema."""

    tool_call_id: str = Field(..., description="External tool call ID from AI framework")
    tool_name: str = Field(..., max_length=100, description="Name of the tool called")
    args: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")



class ToolCallCreate(ToolCallBase):
    """Schema for creating a tool call record."""

    started_at: datetime | None = Field(default=None, description="When the tool call started")


class ToolCallComplete(BaseSchema):
    """Schema for completing a tool call."""

    result: str = Field(..., description="Tool execution result")
    completed_at: datetime | None = Field(default=None, description="When the tool call completed")
    success: bool = Field(default=True, description="Whether the tool call succeeded")


class ToolCallRead(ToolCallBase):
    """Schema for reading a tool call (API response)."""

    id: UUID
    message_id: UUID
    result: str | None = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None


class ToolCallStat(BaseSchema):
    """One tool's aggregated stats over a window."""

    tool_name: str
    total_calls: int
    failed_calls: int
    avg_duration_ms: int | None = None
    last_used_at: datetime | None = None


class ToolCallStatList(BaseSchema):
    items: list[ToolCallStat]
    days: int




class MessageBase(BaseSchema):
    """Base message schema."""

    role: Literal["user", "assistant", "system"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")


class MessageCreate(MessageBase):
    """Schema for creating a message."""

    model_name: str | None = Field(default=None, max_length=100, description="AI model used")
    tokens_used: int | None = Field(default=None, ge=0, description="Token count")


class MessageFileRead(BaseSchema):
    """Schema for file attached to a message."""

    id: UUID
    filename: str
    mime_type: str
    file_type: str


class MessageRead(MessageBase, TimestampSchema):
    """Schema for reading a message (API response)."""

    id: UUID
    conversation_id: UUID
    model_name: str | None = None
    tokens_used: int | None = None
    tool_calls: list[ToolCallRead] = Field(default_factory=list)
    files: list[MessageFileRead] = Field(default_factory=list)
{%- if cookiecutter.use_jwt %}
    user_rating: int | None = Field(
        default=None,
        description="Current user's rating (1 or -1)",
    )
    rating_count: dict[str, int] | None = Field(
        default=None,
        description="Aggregate counts {likes: N, dislikes: N}",
    )
{%- endif %}


class MessageReadSimple(MessageBase, TimestampSchema):
    """Simplified message schema without tool calls."""

    id: UUID
    conversation_id: UUID
    model_name: str | None = None
    tokens_used: int | None = None




class ConversationBase(BaseSchema):
    """Base conversation schema."""

    title: str | None = Field(default=None, max_length=255, description="Conversation title")


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation."""

{%- if cookiecutter.use_jwt %}
    user_id: UUID | None = Field(default=None, description="Owner user ID")
{%- endif %}
{%- if cookiecutter.use_external_user_id_in_conversations %}
    external_user_id: str | None = Field(
        default=None,
        max_length=255,
        description="Denormalized IdP `sub` for client-side lookup",
    )
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: UUID | None = Field(default=None, description="Project this conversation belongs to")
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    organization_id: UUID | None = Field(default=None, description="Organization this conversation belongs to")
{%- endif %}


class ConversationUpdate(BaseSchema):
    """Schema for updating a conversation."""

    title: str | None = Field(default=None, max_length=255)
    is_archived: bool | None = None
    is_demo: bool | None = None
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
    active_knowledge_base_ids: list[UUID] | None = Field(
        default=None,
        description="null=no change, []=RAG disabled, [id,...]=explicit KB selection",
    )
{%- endif %}

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}


class ConversationKBSettings(BaseSchema):
    """Schema for updating KB selection on a conversation.

    null  = use defaults (personal+org KBs on, app KBs off)
    []    = RAG disabled for this conversation
    [id1] = explicit KB selection
    """

    active_knowledge_base_ids: list[str] | None = Field(
        default=None,
        description="null=use defaults, []=RAG disabled, [id,...]=explicit KB selection",
    )
{%- endif %}


class ConversationRead(ConversationBase, TimestampSchema):
    """Schema for reading a conversation (API response)."""

    id: UUID
{%- if cookiecutter.use_jwt %}
    user_id: UUID | None = None
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: UUID | None = None
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    organization_id: UUID | None = None
{%- endif %}
    is_archived: bool = False
    is_demo: bool = False
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
    active_knowledge_base_ids: list[str] | None = None
{%- endif %}


class ConversationReadWithMessages(ConversationRead):
    """Conversation with all messages."""

    messages: list[MessageRead] = Field(default_factory=list)


class ConversationList(BaseSchema):
    """Schema for listing conversations."""

    items: list[ConversationRead]
    total: int




class MessageList(BaseSchema):
    """Schema for listing messages."""

    items: list[MessageRead]
    total: int


class ConversationWithLatestMessage(ConversationRead):
    """Conversation with its latest message for list views."""

    latest_message: MessageReadSimple | None = None
    message_count: int = 0


{%- if cookiecutter.use_jwt %}
class ConversationAdminList(BaseSchema):
    """Schema for admin conversation list with message counts."""

    items: list[ConversationWithLatestMessage]
    total: int
{%- endif %}


class ConversationExport(BaseSchema):
    conversations: list[Any]
    total: int


class DemoConversationSummary(BaseSchema):
    """Lightweight card for the public demo gallery."""

    id: UUID
    title: str | None = None
    message_count: int = 0
    preview: str | None = Field(default=None, description="First user prompt, truncated to 200 chars")
    created_at: datetime
    updated_at: datetime | None = None


class DemoConversationList(BaseSchema):
    """Paginated list of public demo conversations."""

    items: list[DemoConversationSummary]
    total: int
