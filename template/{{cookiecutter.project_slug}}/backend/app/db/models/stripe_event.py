{%- if cookiecutter.enable_billing %}
"""StripeEvent model — idempotency log for incoming webhook events."""

import uuid
from datetime import UTC, datetime

{%- if cookiecutter.use_sqlmodel %}
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlmodel import Field, SQLModel
from app.db.base import TimestampMixin


class StripeEvent(TimestampMixin, SQLModel, table=True):
    """Every incoming Stripe webhook event. Insert before processing — idempotency guard."""

    __tablename__ = "stripe_event"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    stripe_event_id: str = Field(sa_column=Column(String(64), unique=True, index=True, nullable=False))
    event_type: str = Field(sa_column=Column(String(64), index=True, nullable=False))
    payload: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    status: str = Field(default="pending", sa_column=Column(String(16), nullable=False))
    error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    def __repr__(self) -> str:
        return f"<StripeEvent(type={self.event_type}, id={self.stripe_event_id})>"


{%- elif cookiecutter.use_sqlalchemy %}
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class StripeEvent(Base, TimestampMixin):
    __tablename__ = "stripe_event"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stripe_event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<StripeEvent(type={self.event_type}, id={self.stripe_event_id})>"


{%- endif %}
{%- else %}
"""StripeEvent model — not enabled (enable_billing=false)."""
{%- endif %}
