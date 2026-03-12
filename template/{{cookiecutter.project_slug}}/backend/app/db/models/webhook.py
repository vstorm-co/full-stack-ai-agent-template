{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}
{%- if cookiecutter.use_postgresql and cookiecutter.use_sqlmodel %}
"""Webhook database models using SQLModel (PostgreSQL async)."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from app.db.base import TimestampMixin


class WebhookEventType(StrEnum):
    """Webhook event types."""

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Custom events (extend as needed)
    ITEM_CREATED = "item.created"
    ITEM_UPDATED = "item.updated"
    ITEM_DELETED = "item.deleted"


class Webhook(TimestampMixin, SQLModel, table=True):
    """Webhook subscription model."""

    __tablename__ = "webhooks"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    name: str = Field(max_length=255)
    url: str = Field(max_length=2048)
    secret: str = Field(max_length=255)
    events: list[str] = Field(sa_column=Column(ARRAY(String), nullable=False))
    is_active: bool = Field(default=True)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

{%- if cookiecutter.use_jwt %}
    user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True),
    )
{%- endif %}

    # Relationship to delivery logs
    deliveries: list["WebhookDelivery"] = Relationship(
        back_populates="webhook",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class WebhookDelivery(SQLModel, table=True):
    """Webhook delivery log model."""

    __tablename__ = "webhook_deliveries"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    webhook_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("webhooks.id"), nullable=False),
    )
    event_type: str = Field(max_length=100)
    payload: str = Field(sa_column=Column(Text, nullable=False))
    response_status: int | None = Field(default=None)
    response_body: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    attempt_count: int = Field(default=1)
    success: bool = Field(default=False)
    created_at: datetime = Field(sa_column=Column(DateTime, nullable=False))
    delivered_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True),
    )

    # Relationship
    webhook: "Webhook" = Relationship(back_populates="deliveries")


{%- elif cookiecutter.use_postgresql %}
"""Webhook database models (PostgreSQL async)."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class WebhookEventType(StrEnum):
    """Webhook event types."""

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Custom events (extend as needed)
    ITEM_CREATED = "item.created"
    ITEM_UPDATED = "item.updated"
    ITEM_DELETED = "item.deleted"


class Webhook(Base, TimestampMixin):
    """Webhook subscription model."""

    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    events: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional: Associate webhook with a user
{%- if cookiecutter.use_jwt %}
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
{%- endif %}

    # Relationship to delivery logs
    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        "WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan"
    )


class WebhookDelivery(Base):
    """Webhook delivery log model."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("webhooks.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationship
    webhook: Mapped["Webhook"] = relationship("Webhook", back_populates="deliveries")


{%- elif cookiecutter.use_sqlite and cookiecutter.use_sqlmodel %}
"""Webhook database models using SQLModel (SQLite sync)."""

import json
import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlmodel import Field, Relationship, SQLModel

from app.db.base import TimestampMixin


class WebhookEventType(StrEnum):
    """Webhook event types."""

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Custom events (extend as needed)
    ITEM_CREATED = "item.created"
    ITEM_UPDATED = "item.updated"
    ITEM_DELETED = "item.deleted"


class Webhook(TimestampMixin, SQLModel, table=True):
    """Webhook subscription model."""

    __tablename__ = "webhooks"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    name: str = Field(max_length=255)
    url: str = Field(max_length=2048)
    secret: str = Field(max_length=255)
    # Store events as JSON string for SQLite
    events_json: str = Field(sa_column=Column(Text, nullable=False))
    is_active: bool = Field(default=True)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

{%- if cookiecutter.use_jwt %}
    user_id: str | None = Field(
        default=None,
        sa_column=Column(String(36), ForeignKey("users.id"), nullable=True),
    )
{%- endif %}

    deliveries: list["WebhookDelivery"] = Relationship(
        back_populates="webhook",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    @property
    def events(self) -> list[str]:
        """Parse events from JSON string."""
        return json.loads(self.events_json) if self.events_json else []

    @events.setter
    def events(self, value: list[str]) -> None:
        """Store events as JSON string."""
        self.events_json = json.dumps(value)


class WebhookDelivery(SQLModel, table=True):
    """Webhook delivery log model."""

    __tablename__ = "webhook_deliveries"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    webhook_id: str = Field(
        sa_column=Column(String(36), ForeignKey("webhooks.id"), nullable=False),
    )
    event_type: str = Field(max_length=100)
    payload: str = Field(sa_column=Column(Text, nullable=False))
    response_status: int | None = Field(default=None)
    response_body: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    attempt_count: int = Field(default=1)
    success: bool = Field(default=False)
    created_at: datetime = Field(sa_column=Column(DateTime, nullable=False))
    delivered_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True),
    )

    webhook: "Webhook" = Relationship(back_populates="deliveries")


{%- elif cookiecutter.use_sqlite %}
"""Webhook database models (SQLite sync)."""

import json
import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class WebhookEventType(StrEnum):
    """Webhook event types."""

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Custom events (extend as needed)
    ITEM_CREATED = "item.created"
    ITEM_UPDATED = "item.updated"
    ITEM_DELETED = "item.deleted"


class Webhook(Base, TimestampMixin):
    """Webhook subscription model."""

    __tablename__ = "webhooks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    # Store events as comma-separated string for SQLite
    events_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

{%- if cookiecutter.use_jwt %}
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
{%- endif %}

    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        "WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan"
    )

    @property
    def events(self) -> list[str]:
        """Parse events from JSON string."""
        return json.loads(self.events_json) if self.events_json else []

    @events.setter
    def events(self, value: list[str]) -> None:
        """Store events as JSON string."""
        self.events_json = json.dumps(value)


class WebhookDelivery(Base):
    """Webhook delivery log model."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    webhook_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("webhooks.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    webhook: Mapped["Webhook"] = relationship("Webhook", back_populates="deliveries")


{%- elif cookiecutter.use_mongodb %}
"""Webhook document models (MongoDB)."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Optional

from beanie import Document
from pydantic import Field


class WebhookEventType(StrEnum):
    """Webhook event types."""

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Custom events
    ITEM_CREATED = "item.created"
    ITEM_UPDATED = "item.updated"
    ITEM_DELETED = "item.deleted"


class WebhookDelivery(Document):
    """Webhook delivery log document."""

    webhook_id: str
    event_type: str
    payload: str
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    attempt_count: int = 1
    success: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    delivered_at: Optional[datetime] = None

    class Settings:
        name = "webhook_deliveries"
        indexes = ["webhook_id", "event_type", "created_at"]


class Webhook(Document):
    """Webhook subscription document."""

    name: str
    url: str
    secret: str
    events: list[str]
    is_active: bool = True
    description: Optional[str] = None
{%- if cookiecutter.use_jwt %}
    user_id: Optional[str] = None
{%- endif %}
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = None

    class Settings:
        name = "webhooks"
        indexes = ["events", "is_active"]


{%- endif %}
{%- else %}
"""Webhook models - not configured."""
{%- endif %}
