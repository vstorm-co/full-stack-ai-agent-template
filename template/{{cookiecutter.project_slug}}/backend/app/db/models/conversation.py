{%- if cookiecutter.enable_conversation_persistence and cookiecutter.use_postgresql and cookiecutter.use_sqlmodel %}
"""Conversation and message models for AI chat persistence using SQLModel."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from app.db.base import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.chat_file import ChatFile


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
{%- if cookiecutter.use_jwt %}
    user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
{%- endif %}
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


{%- elif cookiecutter.enable_conversation_persistence and cookiecutter.use_postgresql %}
"""Conversation and message models for AI chat persistence."""

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """Conversation model - groups messages in a chat session.

    Attributes:
        id: Unique conversation identifier
        user_id: Optional user who owns this conversation (if auth enabled)
        title: Auto-generated or user-defined title
        is_archived: Whether the conversation is archived
        messages: List of messages in this conversation
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
{%- if cookiecutter.use_jwt %}
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
{%- endif %}
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title={self.title})>"


class Message(Base, TimestampMixin):
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

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
    tool_calls: Mapped[list["ToolCall"]] = relationship(
        "ToolCall",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="ToolCall.started_at",
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role})>"


class ToolCall(Base):
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

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_call_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    args: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, running, completed, failed
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="tool_calls")

    def __repr__(self) -> str:
        return f"<ToolCall(id={self.id}, tool_name={self.tool_name}, status={self.status})>"


{%- elif cookiecutter.enable_conversation_persistence and cookiecutter.use_sqlite and cookiecutter.use_sqlmodel %}
"""Conversation and message models for AI chat persistence using SQLModel."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlmodel import Field, Relationship, SQLModel

from app.db.base import TimestampMixin


class Conversation(TimestampMixin, SQLModel, table=True):
    """Conversation model - groups messages in a chat session."""

    __tablename__ = "conversations"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
{%- if cookiecutter.use_jwt %}
    user_id: str | None = Field(
        default=None,
        sa_column=Column(
            String(36),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
{%- endif %}
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
    """Message model - individual message in a conversation."""

    __tablename__ = "messages"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    conversation_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    role: str = Field(max_length=20)
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
    """ToolCall model - record of a tool invocation."""

    __tablename__ = "tool_calls"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    message_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    tool_call_id: str = Field(max_length=100)
    tool_name: str = Field(max_length=100)
    args: str = Field(default="{}", sa_column=Column(Text, nullable=False, default="{}"))  # JSON as string
    result: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    status: str = Field(default="pending", max_length=20)
    started_at: datetime = Field(sa_column=Column(DateTime, nullable=False))
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True),
    )
    duration_ms: int | None = Field(default=None)

    # Relationships
    message: "Message" = Relationship(back_populates="tool_calls")

    def __repr__(self) -> str:
        return f"<ToolCall(id={self.id}, tool_name={self.tool_name})>"


{%- elif cookiecutter.enable_conversation_persistence and cookiecutter.use_sqlite %}
"""Conversation and message models for AI chat persistence."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """Conversation model - groups messages in a chat session."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
{%- if cookiecutter.use_jwt %}
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
{%- endif %}
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title={self.title})>"


class Message(Base, TimestampMixin):
    """Message model - individual message in a conversation."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
    tool_calls: Mapped[list["ToolCall"]] = relationship(
        "ToolCall",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="ToolCall.started_at",
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role})>"


class ToolCall(Base):
    """ToolCall model - record of a tool invocation."""

    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_call_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    args: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON as string
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="tool_calls")

    def __repr__(self) -> str:
        return f"<ToolCall(id={self.id}, tool_name={self.tool_name})>"


{%- elif cookiecutter.enable_conversation_persistence and cookiecutter.use_mongodb %}
"""Conversation and message models for AI chat persistence (MongoDB)."""

from datetime import UTC, datetime
from typing import Literal, Optional

from beanie import Document, Link
from pydantic import Field


class ToolCall(Document):
    """ToolCall document model - record of a tool invocation."""

    message_id: str
    tool_call_id: str
    tool_name: str
    args: dict = Field(default_factory=dict)
    result: Optional[str] = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    class Settings:
        name = "tool_calls"
        indexes = ["message_id"]


class Message(Document):
    """Message document model - individual message in a conversation."""

    conversation_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    model_name: Optional[str] = None
    tokens_used: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "messages"
        indexes = ["conversation_id"]


class Conversation(Document):
    """Conversation document model - groups messages in a chat session."""

{%- if cookiecutter.use_jwt %}
    user_id: Optional[str] = None
{%- endif %}
    title: Optional[str] = None
    is_archived: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = None

    class Settings:
        name = "conversations"
{%- if cookiecutter.use_jwt %}
        indexes = ["user_id"]
{%- endif %}


{%- else %}
"""Conversation models - not configured."""
{%- endif %}
