"""Conversation schemas for AI chat persistence.

This module contains Pydantic schemas for Conversation, Message, and ToolCall entities.
"""

from datetime import datetime
from typing import Any, Literal

{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from pydantic import Field
{%- if cookiecutter.use_sqlite %}
from pydantic import field_validator
{%- endif %}

from app.schemas.base import BaseSchema, TimestampSchema


# Tool Call Schemas


class ToolCallBase(BaseSchema):
    """Base tool call schema."""

    tool_call_id: str = Field(..., description="External tool call ID from AI framework")
    tool_name: str = Field(..., max_length=100, description="Name of the tool called")
    args: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")

{%- if cookiecutter.use_sqlite %}

    @field_validator("args", mode="before")
    @classmethod
    def deserialize_args(cls, v: object) -> dict[str, Any]:
        """Deserialize args from JSON string (SQLite stores as TEXT)."""
        if isinstance(v, str):
            import json
            try:
                result: dict[str, Any] = json.loads(v)
                return result
            except (json.JSONDecodeError, TypeError):
                return {}
        if isinstance(v, dict):
            return {str(k): val for k, val in v.items()}
        return {}
{%- endif %}


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

{%- if cookiecutter.use_postgresql %}
    id: UUID
    message_id: UUID
{%- else %}
    id: str
    message_id: str
{%- endif %}
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


# Message Schemas


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

{%- if cookiecutter.use_postgresql %}
    id: UUID
{%- else %}
    id: str
{%- endif %}
    filename: str
    mime_type: str
    file_type: str


class MessageRead(MessageBase, TimestampSchema):
    """Schema for reading a message (API response)."""

{%- if cookiecutter.use_postgresql %}
    id: UUID
    conversation_id: UUID
{%- else %}
    id: str
    conversation_id: str
{%- endif %}
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

{%- if cookiecutter.use_postgresql %}
    id: UUID
    conversation_id: UUID
{%- else %}
    id: str
    conversation_id: str
{%- endif %}
    model_name: str | None = None
    tokens_used: int | None = None


# Conversation Schemas


class ConversationBase(BaseSchema):
    """Base conversation schema."""

    title: str | None = Field(default=None, max_length=255, description="Conversation title")


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation."""

{%- if cookiecutter.use_jwt %}
{%- if cookiecutter.use_postgresql %}
    user_id: UUID | None = Field(default=None, description="Owner user ID")
{%- else %}
    user_id: str | None = Field(default=None, description="Owner user ID")
{%- endif %}
{%- endif %}
{%- if cookiecutter.use_external_user_id_in_conversations %}
    external_user_id: str | None = Field(
        default=None,
        max_length=255,
        description="Denormalized IdP `sub` for client-side lookup",
    )
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
{%- if cookiecutter.use_postgresql %}
    project_id: UUID | None = Field(default=None, description="Project this conversation belongs to")
{%- else %}
    project_id: str | None = Field(default=None, description="Project this conversation belongs to")
{%- endif %}
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
{%- if cookiecutter.use_postgresql %}
    organization_id: UUID | None = Field(default=None, description="Organization this conversation belongs to")
{%- else %}
    organization_id: str | None = Field(default=None, description="Organization this conversation belongs to")
{%- endif %}
{%- endif %}


class ConversationUpdate(BaseSchema):
    """Schema for updating a conversation."""

    title: str | None = Field(default=None, max_length=255)
    is_archived: bool | None = None
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

{%- if cookiecutter.use_postgresql %}
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
{%- else %}
    id: str
{%- if cookiecutter.use_jwt %}
    user_id: str | None = None
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: str | None = None
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    organization_id: str | None = None
{%- endif %}
{%- endif %}
    is_archived: bool = False
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
    active_knowledge_base_ids: list[str] | None = None
{%- if cookiecutter.use_sqlite %}

    @field_validator("active_knowledge_base_ids", mode="before")
    @classmethod
    def deserialize_active_kb_ids(cls, v: object) -> list[str] | None:
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                return parsed  # type: ignore[return-value]
            except (json.JSONDecodeError, TypeError):
                return None
        return v  # type: ignore[return-value]
{%- endif %}
{%- endif %}


class ConversationReadWithMessages(ConversationRead):
    """Conversation with all messages."""

    messages: list[MessageRead] = Field(default_factory=list)


class ConversationList(BaseSchema):
    """Schema for listing conversations."""

    items: list[ConversationRead]
    total: int


# Aggregated Schemas for API Responses


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
