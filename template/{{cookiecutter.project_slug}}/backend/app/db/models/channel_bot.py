{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
{%- if cookiecutter.use_postgresql and cookiecutter.use_sqlmodel %}
"""ChannelBot model — one row per registered bot instance (SQLModel + PostgreSQL)."""

import uuid

from sqlalchemy import Boolean, Column, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.channels.base import DEFAULT_ACCESS_POLICY
from app.db.base import TimestampMixin


class ChannelBot(TimestampMixin, SQLModel, table=True):
    """Registered bot instance for a messaging platform."""

    __tablename__ = "channel_bots"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    platform: str = Field(sa_column=Column(String(20), nullable=False, index=True))
    name: str = Field(sa_column=Column(String(255), nullable=False))
    token_encrypted: str = Field(sa_column=Column(String(1000), nullable=False))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True))
    webhook_mode: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, default=False))
    webhook_url: str | None = Field(default=None, sa_column=Column(String(500), nullable=True))
    webhook_secret: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    access_policy: dict = Field(
        default_factory=lambda: dict(DEFAULT_ACCESS_POLICY),
        sa_column=Column(JSON, nullable=False),
    )
    ai_model_override: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    system_prompt_override: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
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
        return f"<ChannelBot(id={self.id}, platform={self.platform}, name={self.name})>"


{%- elif cookiecutter.use_postgresql %}
"""ChannelBot model — one row per registered bot instance (PostgreSQL async)."""

import uuid

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.channels.base import DEFAULT_ACCESS_POLICY
from app.db.base import Base, TimestampMixin


class ChannelBot(Base, TimestampMixin):
    """Registered bot instance for a messaging platform."""

    __tablename__ = "channel_bots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_encrypted: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    webhook_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_policy: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: dict(DEFAULT_ACCESS_POLICY),
    )
    ai_model_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    system_prompt_override: Mapped[str | None] = mapped_column(Text, nullable=True)
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
{%- endif %}

    def __repr__(self) -> str:
        return f"<ChannelBot(id={self.id}, platform={self.platform}, name={self.name})>"


{%- elif cookiecutter.use_sqlite and cookiecutter.use_sqlmodel %}
"""ChannelBot model — one row per registered bot instance (SQLite + SQLModel)."""

import uuid

from sqlalchemy import Boolean, Column, ForeignKey, JSON, String, Text
from sqlmodel import Field, SQLModel

from app.channels.base import DEFAULT_ACCESS_POLICY_JSON
from app.db.base import TimestampMixin


class ChannelBot(TimestampMixin, SQLModel, table=True):
    """Registered bot instance for a messaging platform."""

    __tablename__ = "channel_bots"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    platform: str = Field(sa_column=Column(String(20), nullable=False, index=True))
    name: str = Field(sa_column=Column(String(255), nullable=False))
    token_encrypted: str = Field(sa_column=Column(String(1000), nullable=False))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True))
    webhook_mode: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, default=False))
    webhook_url: str | None = Field(default=None, sa_column=Column(String(500), nullable=True))
    webhook_secret: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    access_policy: str = Field(
        default=DEFAULT_ACCESS_POLICY_JSON,
        sa_column=Column(Text, nullable=False),
    )
    ai_model_override: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    system_prompt_override: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
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
        return f"<ChannelBot(id={self.id}, platform={self.platform}, name={self.name})>"


{%- elif cookiecutter.use_sqlite %}
"""ChannelBot model — one row per registered bot instance (SQLite sync)."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.channels.base import DEFAULT_ACCESS_POLICY_JSON
from app.db.base import Base, TimestampMixin


class ChannelBot(Base, TimestampMixin):
    """Registered bot instance for a messaging platform."""

    __tablename__ = "channel_bots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_encrypted: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    webhook_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # JSON stored as text for SQLite — parse via @field_validator in schemas
    access_policy: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=DEFAULT_ACCESS_POLICY_JSON,
    )
    ai_model_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    system_prompt_override: Mapped[str | None] = mapped_column(Text, nullable=True)
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
{%- endif %}

    def __repr__(self) -> str:
        return f"<ChannelBot(id={self.id}, platform={self.platform}, name={self.name})>"


{%- elif cookiecutter.use_mongodb %}
"""ChannelBot document model (MongoDB)."""

from datetime import UTC, datetime
from typing import Optional

from beanie import Document
from pydantic import Field

from app.channels.base import DEFAULT_ACCESS_POLICY


class ChannelBot(Document):
    """Registered bot instance for a messaging platform."""

    platform: str
    name: str
    token_encrypted: str
    is_active: bool = True
    webhook_mode: bool = False
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    access_policy: dict = Field(
        default_factory=lambda: dict(DEFAULT_ACCESS_POLICY)
    )
    ai_model_override: Optional[str] = None
    system_prompt_override: Optional[str] = None
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: Optional[str] = None
{%- endif %}
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = None

    class Settings:
        name = "channel_bots"
        indexes = ["platform", "is_active"]

    def __repr__(self) -> str:
        return f"<ChannelBot(id={self.id}, platform={self.platform}, name={self.name})>"


{%- else %}
"""ChannelBot model — no supported database configured."""
{%- endif %}
{%- endif %}
