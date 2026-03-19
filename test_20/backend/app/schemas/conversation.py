"""Conversation schemas for AI chat persistence.

This module contains Pydantic schemas for Conversation, Message, and ToolCall entities.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema

# =============================================================================
# Tool Call Schemas
# =============================================================================


class ToolCallBase(BaseSchema):
    """Base tool call schema."""

    tool_call_id: str = Field(..., description="External tool call ID from AI framework")
    tool_name: str = Field(..., max_length=100, description="Name of the tool called")
    args: dict = Field(default_factory=dict, description="Tool arguments")


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


# =============================================================================
# Message Schemas
# =============================================================================


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


class MessageReadSimple(MessageBase, TimestampSchema):
    """Simplified message schema without tool calls."""

    id: UUID
    conversation_id: UUID
    model_name: str | None = None
    tokens_used: int | None = None


# =============================================================================
# Conversation Schemas
# =============================================================================


class ConversationBase(BaseSchema):
    """Base conversation schema."""

    title: str | None = Field(default=None, max_length=255, description="Conversation title")


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation."""

    user_id: UUID | None = Field(default=None, description="Owner user ID")
    pass


class ConversationUpdate(BaseSchema):
    """Schema for updating a conversation."""

    title: str | None = Field(default=None, max_length=255)
    is_archived: bool | None = None


class ConversationRead(ConversationBase, TimestampSchema):
    """Schema for reading a conversation (API response)."""

    id: UUID
    user_id: UUID | None = None
    is_archived: bool = False


class ConversationReadWithMessages(ConversationRead):
    """Conversation with all messages."""

    messages: list[MessageRead] = Field(default_factory=list)


class ConversationList(BaseSchema):
    """Schema for listing conversations."""

    items: list[ConversationRead]
    total: int


# =============================================================================
# Aggregated Schemas for API Responses
# =============================================================================


class MessageList(BaseSchema):
    """Schema for listing messages."""

    items: list[MessageRead]
    total: int


class ConversationWithLatestMessage(ConversationRead):
    """Conversation with its latest message for list views."""

    latest_message: MessageReadSimple | None = None
    message_count: int = 0
