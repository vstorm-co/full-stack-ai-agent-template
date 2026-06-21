{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
{%- if cookiecutter.use_sqlmodel %}
"""ChannelBot model — one row per registered bot instance (SQLModel + PostgreSQL)."""

import uuid

from sqlalchemy import Boolean, Column, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.services.channels.base import DEFAULT_ACCESS_POLICY
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


{%- else %}
"""ChannelBot model — one row per registered bot instance (PostgreSQL async)."""

import uuid

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.services.channels.base import DEFAULT_ACCESS_POLICY
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


{%- endif %}
{%- endif %}
