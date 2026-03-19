"""Conversation and message models for AI chat persistence using SQLModel."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.chat_file import ChatFile

from app.db.base import TimestampMixin


class Conversation(TimestampMixin, SQLModel, table=True):
    """Conversation model - groups messages in a chat session.

    Attributes:
        id: Unique conversation identifier
        user_id: Optional user who owns this conversation (if auth enabled)
        title: Auto-generated or user-defined title
        is_archived: Whether the conversation is archived
        messages: List of messages in this conversation
    """

    __tablename__ = "conversations"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    title: str | None = Field(default=None, max_length=255)
    is_archived: bool = Field(default=False)

    # Relationships
    messages: list["Message"] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "Message.created_at"},
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title={self.title})>"


class Message(TimestampMixin, SQLModel, table=True):
    """Message model - individual message in a conversation.

    Attributes:
        id: Unique message identifier
        conversation_id: The conversation this message belongs to
        role: Message role (user, assistant, system)
        content: Message text content
        model_name: AI model used (for assistant messages)
        tokens_used: Token count for this message
        tool_calls: List of tool calls made in this message
    """

    __tablename__ = "messages"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    conversation_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    role: str = Field(max_length=20)  # user, assistant, system
    content: str = Field(sa_column=Column(Text, nullable=False))
    model_name: str | None = Field(default=None, max_length=100)
    tokens_used: int | None = Field(default=None)

    # Relationships
    conversation: "Conversation" = Relationship(back_populates="messages")
    tool_calls: list["ToolCall"] = Relationship(
        back_populates="message",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "ToolCall.started_at"},
    )
    files: list["ChatFile"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "ChatFile.message_id", "lazy": "selectin"},
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role})>"


class ToolCall(SQLModel, table=True):
    """ToolCall model - record of a tool invocation.

    Attributes:
        id: Unique tool call identifier
        message_id: The assistant message that triggered this call
        tool_call_id: External ID from PydanticAI
        tool_name: Name of the tool that was called
        args: JSON arguments passed to the tool
        result: Result returned by the tool
        status: Current status (pending, running, completed, failed)
        started_at: When the tool call started
        completed_at: When the tool call completed
        duration_ms: Execution time in milliseconds
    """

    __tablename__ = "tool_calls"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    message_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    tool_call_id: str = Field(max_length=100)
    tool_name: str = Field(max_length=100)
    args: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False, default=dict))
    result: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    status: str = Field(default="pending", max_length=20)  # pending, running, completed, failed
    started_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    duration_ms: int | None = Field(default=None)

    # Relationships
    message: "Message" = Relationship(back_populates="tool_calls")

    def __repr__(self) -> str:
        return f"<ToolCall(id={self.id}, tool_name={self.tool_name}, status={self.status})>"
