{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
"""CreditTransaction and UsageEvent models."""

import enum
import uuid
from datetime import UTC, datetime

{%- if cookiecutter.use_sqlmodel %}
from sqlalchemy import Column, String, Text, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel
from app.db.base import TimestampMixin


class CreditTransactionType(enum.StrEnum):
    GRANT_SUBSCRIPTION = "grant_subscription"
    GRANT_TRIAL = "grant_trial"
    PURCHASE_TOPUP = "purchase_topup"
    DEBIT_AGENT = "debit_agent"
    DEBIT_RAG_INGEST = "debit_rag_ingest"
    REFUND = "refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    EXPIRATION = "expiration"


class CreditTransaction(TimestampMixin, SQLModel, table=True):
    """Immutable ledger of credit changes per organization."""

    __tablename__ = "credit_transaction"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    organization_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    )
    actor_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    delta: int = Field(sa_column=Column(Integer, nullable=False))
    balance_after: int = Field(sa_column=Column(Integer, nullable=False))
    # Stored as a plain VARCHAR(32) to match the migration. CreditTransactionType
    # is a `str, enum.Enum` so its members serialize cleanly via their .value.
    type: str = Field(sa_column=Column(String(32), index=True, nullable=False))
    description: str = Field(sa_column=Column(Text, nullable=False))
    stripe_reference: str | None = Field(default=None, sa_column=Column(String(128), nullable=True, index=True))
    usage_event_id: uuid.UUID | None = Field(default=None, sa_column=Column(PG_UUID(as_uuid=True), nullable=True))

    def __repr__(self) -> str:
        return f"<CreditTransaction(delta={self.delta}, type={self.type})>"


class UsageEvent(TimestampMixin, SQLModel, table=True):
    """Raw token usage capture per agent invocation."""

    __tablename__ = "usage_event"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    organization_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    )
    actor_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    conversation_id: uuid.UUID | None = Field(default=None, sa_column=Column(PG_UUID(as_uuid=True), nullable=True))
    model: str = Field(sa_column=Column(String(128), nullable=False))
    provider: str = Field(sa_column=Column(String(64), nullable=False))
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    cached_tokens: int = Field(default=0)
    credits_charged: int = Field(default=0)
    ai_framework: str = Field(default="", sa_column=Column(String(32), nullable=False))

    def __repr__(self) -> str:
        return f"<UsageEvent(model={self.model}, credits={self.credits_charged})>"


{%- elif cookiecutter.use_sqlalchemy %}
from sqlalchemy import Column, String, Text, Integer, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class CreditTransactionType(enum.StrEnum):
    GRANT_SUBSCRIPTION = "grant_subscription"
    GRANT_TRIAL = "grant_trial"
    PURCHASE_TOPUP = "purchase_topup"
    DEBIT_AGENT = "debit_agent"
    DEBIT_RAG_INGEST = "debit_rag_ingest"
    REFUND = "refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    EXPIRATION = "expiration"


class CreditTransaction(Base, TimestampMixin):
    __tablename__ = "credit_transaction"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    delta: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    # Stored as a plain VARCHAR(32) to match the migration. CreditTransactionType
    # is a `str, enum.Enum` so its members serialize cleanly via their .value.
    type: Mapped[str] = mapped_column(String(32), index=True)
    description: Mapped[str] = mapped_column(Text)
    stripe_reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    usage_event_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    def __repr__(self) -> str:
        return f"<CreditTransaction(delta={self.delta}, type={self.type})>"


class UsageEvent(Base, TimestampMixin):
    __tablename__ = "usage_event"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    model: Mapped[str] = mapped_column(String(128))
    provider: Mapped[str] = mapped_column(String(64))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    credits_charged: Mapped[int] = mapped_column(Integer, default=0)
    ai_framework: Mapped[str] = mapped_column(String(32), default="")

    def __repr__(self) -> str:
        return f"<UsageEvent(model={self.model}, credits={self.credits_charged})>"


{%- endif %}
{%- else %}
"""CreditTransaction and UsageEvent models — not enabled (enable_credits_system=false)."""
{%- endif %}
