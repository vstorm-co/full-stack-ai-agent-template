{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}
{%- if cookiecutter.use_sqlmodel %}
"""Webhook database models using SQLModel (PostgreSQL async)."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from app.db.base import TimestampMixin


class WebhookEventType(StrEnum):
    """Webhook event types."""

    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Custom events (extend as needed)
    CUSTOM_EVENT = "custom.event"


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
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True),
    )
{%- endif %}

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
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("webhooks.id"), nullable=False, index=True),
    )
    event_type: str = Field(max_length=100)
    payload: str = Field(sa_column=Column(Text, nullable=False))
    response_status: int | None = Field(default=None)
    response_body: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    attempt_count: int = Field(default=1)
    success: bool = Field(default=False)
    created_at: datetime = Field(sa_column=Column(DateTime, nullable=False, index=True))
    delivered_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True),
    )

    webhook: "Webhook" = Relationship(back_populates="deliveries")


{%- else %}
"""Webhook database models (PostgreSQL async)."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class WebhookEventType(StrEnum):
    """Webhook event types."""

    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Custom events (extend as needed)
    CUSTOM_EVENT = "custom.event"


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

{%- if cookiecutter.use_jwt %}
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
{%- endif %}

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
        UUID(as_uuid=True), ForeignKey("webhooks.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    webhook: Mapped["Webhook"] = relationship("Webhook", back_populates="deliveries")


{%- endif %}
{%- else %}
"""Webhook models - not configured."""
{%- endif %}
