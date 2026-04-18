{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
{%- if cookiecutter.use_postgresql and cookiecutter.use_sqlmodel %}
"""ChannelSession model — active bot + chat conversation thread (SQLModel + PostgreSQL)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class ChannelSession(TimestampMixin, SQLModel, table=True):
    """Active conversation thread between a bot and a chat."""

    __tablename__ = "channel_sessions"
    __table_args__ = (UniqueConstraint("bot_id", "platform_chat_id", name="uq_channel_session_bot_chat"),)

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    bot_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("channel_bots.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    identity_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("channel_identities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    conversation_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("conversations.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    platform_chat_id: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    chat_type: str = Field(default="private", sa_column=Column(String(20), nullable=False, default="private"))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True))
    last_message_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
{%- endif %}

    def __repr__(self) -> str:
        return f"<ChannelSession(id={self.id}, bot_id={self.bot_id}, platform_chat_id={self.platform_chat_id})>"


{%- elif cookiecutter.use_postgresql %}
"""ChannelSession model — active bot + chat conversation thread (PostgreSQL async)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ChannelSession(Base, TimestampMixin):
    """Active conversation thread between a bot and a chat."""

    __tablename__ = "channel_sessions"
    __table_args__ = (UniqueConstraint("bot_id", "platform_chat_id", name="uq_channel_session_bot_chat"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    platform_chat_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    chat_type: Mapped[str] = mapped_column(String(20), nullable=False, default="private")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
{%- endif %}

    def __repr__(self) -> str:
        return f"<ChannelSession(id={self.id}, bot_id={self.bot_id}, platform_chat_id={self.platform_chat_id})>"


{%- elif cookiecutter.use_sqlite and cookiecutter.use_sqlmodel %}
"""ChannelSession model — active bot + chat conversation thread (SQLite + SQLModel)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class ChannelSession(TimestampMixin, SQLModel, table=True):
    """Active conversation thread between a bot and a chat."""

    __tablename__ = "channel_sessions"
    __table_args__ = (UniqueConstraint("bot_id", "platform_chat_id", name="uq_channel_session_bot_chat"),)

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    bot_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("channel_bots.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    identity_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("channel_identities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    conversation_id: str | None = Field(
        default=None,
        sa_column=Column(
            String(36),
            ForeignKey("conversations.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    platform_chat_id: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    chat_type: str = Field(default="private", sa_column=Column(String(20), nullable=False, default="private"))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True))
    last_message_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: str | None = Field(
        default=None,
        sa_column=Column(
            String(36),
            ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
{%- endif %}

    def __repr__(self) -> str:
        return f"<ChannelSession(id={self.id}, bot_id={self.bot_id}, platform_chat_id={self.platform_chat_id})>"


{%- elif cookiecutter.use_sqlite %}
"""ChannelSession model — active bot + chat conversation thread (SQLite sync)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ChannelSession(Base, TimestampMixin):
    """Active conversation thread between a bot and a chat."""

    __tablename__ = "channel_sessions"
    __table_args__ = (UniqueConstraint("bot_id", "platform_chat_id", name="uq_channel_session_bot_chat"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    bot_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("channel_bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identity_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("channel_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    platform_chat_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    chat_type: Mapped[str] = mapped_column(String(20), nullable=False, default="private")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
{%- endif %}

    def __repr__(self) -> str:
        return f"<ChannelSession(id={self.id}, bot_id={self.bot_id}, platform_chat_id={self.platform_chat_id})>"


{%- elif cookiecutter.use_mongodb %}
"""ChannelSession document model (MongoDB)."""

from datetime import UTC, datetime
from typing import Optional

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class ChannelSession(Document):
    """Active conversation thread between a bot and a chat."""

    bot_id: str
    identity_id: str
    conversation_id: Optional[str] = None
    platform_chat_id: str
    chat_type: str = "private"
    is_active: bool = True
    last_message_at: Optional[datetime] = None
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: Optional[str] = None
{%- endif %}
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = None

    class Settings:
        name = "channel_sessions"
        indexes = [
            IndexModel(
                [("bot_id", ASCENDING), ("platform_chat_id", ASCENDING)],
                unique=True,
            ),
            "identity_id",
            "is_active",
        ]

    def __repr__(self) -> str:
        return f"<ChannelSession(id={self.id}, bot_id={self.bot_id}, platform_chat_id={self.platform_chat_id})>"


{%- else %}
"""ChannelSession model — no supported database configured."""
{%- endif %}
{%- endif %}
