{%- if cookiecutter.enable_ai_agent and cookiecutter.enable_conversation_persistence %}
{%- if cookiecutter.use_postgresql and cookiecutter.use_sqlmodel %}
"""ChatFile database model - stores metadata for files uploaded in chat."""

import uuid

from sqlalchemy import Column, ForeignKey, String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class ChatFile(TimestampMixin, SQLModel, table=True):
    """Tracks files uploaded by users in chat conversations."""

    __tablename__ = "chat_files"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True),
    )
    message_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True),
    )
    filename: str = Field(sa_column=Column(String(255), nullable=False))
    mime_type: str = Field(sa_column=Column(String(100), nullable=False))
    size: int = Field(sa_column=Column(Integer, nullable=False))
    storage_path: str = Field(sa_column=Column(String(500), nullable=False))
    file_type: str = Field(sa_column=Column(String(20), nullable=False))
    parsed_content: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    def __repr__(self) -> str:
        return f"<ChatFile(id={self.id}, filename={self.filename}, type={self.file_type})>"
{%- elif cookiecutter.use_postgresql and cookiecutter.use_sqlalchemy %}
"""ChatFile database model - stores metadata for files uploaded in chat."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ChatFile(Base, TimestampMixin):
    """Tracks files uploaded by users in chat conversations."""

    __tablename__ = "chat_files"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    parsed_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ChatFile(id={self.id}, filename={self.filename}, type={self.file_type})>"
{%- elif cookiecutter.use_sqlite and cookiecutter.use_sqlmodel %}
"""ChatFile database model - stores metadata for files uploaded in chat."""

import uuid

from sqlalchemy import Column, ForeignKey, String, Text, Integer
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class ChatFile(TimestampMixin, SQLModel, table=True):
    """Tracks files uploaded by users in chat conversations."""

    __tablename__ = "chat_files"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), sa_column=Column(String(36), primary_key=True))
    user_id: str = Field(sa_column=Column(String(36), ForeignKey("users.id"), nullable=False, index=True))
    message_id: str | None = Field(default=None, sa_column=Column(String(36), ForeignKey("messages.id"), nullable=True))
    filename: str = Field(max_length=255)
    mime_type: str = Field(max_length=100)
    size: int = Field(default=0)
    storage_path: str = Field(max_length=500)
    file_type: str = Field(max_length=20)
    parsed_content: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    def __repr__(self) -> str:
        return f"<ChatFile(id={self.id}, filename={self.filename}, type={self.file_type})>"
{%- endif %}
{%- endif %}
