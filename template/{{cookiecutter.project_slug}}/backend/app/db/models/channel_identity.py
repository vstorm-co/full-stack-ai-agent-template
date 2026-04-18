{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
{%- if cookiecutter.use_postgresql and cookiecutter.use_sqlmodel %}
"""ChannelIdentity model — maps platform user → app user (SQLModel + PostgreSQL)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class ChannelIdentity(TimestampMixin, SQLModel, table=True):
    """Mapping between a platform user and an app user account."""

    __tablename__ = "channel_identities"
    __table_args__ = (UniqueConstraint("platform", "platform_user_id", name="uq_channel_identity_platform_user"),)

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    platform: str = Field(sa_column=Column(String(20), nullable=False, index=True))
    platform_user_id: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    platform_username: str | None = Field(default=None, sa_column=Column(String(100), nullable=True))
    platform_display_name: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    link_code: str | None = Field(default=None, sa_column=Column(String(10), nullable=True))
    link_code_expires_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True))

    def __repr__(self) -> str:
        return f"<ChannelIdentity(id={self.id}, platform={self.platform}, platform_user_id={self.platform_user_id})>"


{%- elif cookiecutter.use_postgresql %}
"""ChannelIdentity model — maps platform user → app user (PostgreSQL async)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ChannelIdentity(Base, TimestampMixin):
    """Mapping between a platform user and an app user account."""

    __tablename__ = "channel_identities"
    __table_args__ = (UniqueConstraint("platform", "platform_user_id", name="uq_channel_identity_platform_user"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    platform_user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    platform_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    platform_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    link_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    link_code_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<ChannelIdentity(id={self.id}, platform={self.platform}, platform_user_id={self.platform_user_id})>"


{%- elif cookiecutter.use_sqlite and cookiecutter.use_sqlmodel %}
"""ChannelIdentity model — maps platform user → app user (SQLite + SQLModel)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class ChannelIdentity(TimestampMixin, SQLModel, table=True):
    """Mapping between a platform user and an app user account."""

    __tablename__ = "channel_identities"
    __table_args__ = (UniqueConstraint("platform", "platform_user_id", name="uq_channel_identity_platform_user"),)

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    platform: str = Field(sa_column=Column(String(20), nullable=False, index=True))
    platform_user_id: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    platform_username: str | None = Field(default=None, sa_column=Column(String(100), nullable=True))
    platform_display_name: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    user_id: str | None = Field(
        default=None,
        sa_column=Column(
            String(36),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    link_code: str | None = Field(default=None, sa_column=Column(String(10), nullable=True))
    link_code_expires_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True))

    def __repr__(self) -> str:
        return f"<ChannelIdentity(id={self.id}, platform={self.platform}, platform_user_id={self.platform_user_id})>"


{%- elif cookiecutter.use_sqlite %}
"""ChannelIdentity model — maps platform user → app user (SQLite sync)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ChannelIdentity(Base, TimestampMixin):
    """Mapping between a platform user and an app user account."""

    __tablename__ = "channel_identities"
    __table_args__ = (UniqueConstraint("platform", "platform_user_id", name="uq_channel_identity_platform_user"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    platform_user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    platform_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    platform_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    link_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    link_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<ChannelIdentity(id={self.id}, platform={self.platform}, platform_user_id={self.platform_user_id})>"


{%- elif cookiecutter.use_mongodb %}
"""ChannelIdentity document model (MongoDB)."""

from datetime import UTC, datetime
from typing import Optional

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class ChannelIdentity(Document):
    """Mapping between a platform user and an app user account."""

    platform: str
    platform_user_id: str
    platform_username: Optional[str] = None
    platform_display_name: Optional[str] = None
    user_id: Optional[str] = None
    link_code: Optional[str] = None
    link_code_expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = None

    class Settings:
        name = "channel_identities"
        indexes = [
            IndexModel(
                [("platform", ASCENDING), ("platform_user_id", ASCENDING)],
                unique=True,
            ),
            "user_id",
            "link_code",
        ]

    def __repr__(self) -> str:
        return f"<ChannelIdentity(id={self.id}, platform={self.platform}, platform_user_id={self.platform_user_id})>"


{%- else %}
"""ChannelIdentity model — no supported database configured."""
{%- endif %}
{%- endif %}
