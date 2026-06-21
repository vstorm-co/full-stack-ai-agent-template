{%- if cookiecutter.enable_billing %}
"""Plan and Price models — local mirror of Stripe Products/Prices."""

import uuid
from datetime import UTC, datetime

{%- if cookiecutter.use_sqlmodel %}
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlmodel import Field, Relationship, SQLModel
from app.db.base import TimestampMixin


class Plan(TimestampMixin, SQLModel, table=True):
    """Local mirror of a Stripe Product. Source of truth = Stripe Dashboard."""

    __tablename__ = "plan"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    code: str = Field(sa_column=Column(String(32), unique=True, nullable=False))
    display_name: str = Field(sa_column=Column(String(64), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, default=True, nullable=False))
    sort_order: int = Field(default=0, sa_column=Column(Integer, default=0, nullable=False))
    features: dict = Field(default_factory=dict, sa_column=Column(JSONB, default=dict, nullable=False))
    base_amount_cents: int = Field(default=0, sa_column=Column(Integer, default=0, nullable=False))
    included_seats: int = Field(default=1, sa_column=Column(Integer, default=1, nullable=False))
    extra_seat_amount_cents: int = Field(default=0, sa_column=Column(Integer, default=0, nullable=False))
    seats_min: int = Field(default=1, sa_column=Column(Integer, default=1, nullable=False))
    seats_max: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    monthly_credits_base: int = Field(default=0, sa_column=Column(Integer, default=0, nullable=False))
    monthly_credits_per_seat: int = Field(default=0, sa_column=Column(Integer, default=0, nullable=False))

    prices: list["Price"] = Relationship(
        back_populates="plan",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def __repr__(self) -> str:
        return f"<Plan(code={self.code}, name={self.display_name})>"


class Price(TimestampMixin, SQLModel, table=True):
    """Local mirror of a Stripe Price. Source of truth = Stripe Dashboard."""

    __tablename__ = "price"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    plan_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("plan.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    stripe_price_id: str = Field(sa_column=Column(String(64), unique=True, index=True, nullable=False))
    interval: str = Field(sa_column=Column(String(16), nullable=False))  # month, year, one_time
    amount_cents: int = Field(default=0, sa_column=Column(Integer, default=0, nullable=False))
    currency: str = Field(default="{{ cookiecutter.billing_default_currency }}", sa_column=Column(String(3), nullable=False))
    trial_period_days: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, default=True, nullable=False))
    billing_scheme: str = Field(default="per_unit", sa_column=Column(String(16), nullable=False))
    tiers_mode: str | None = Field(default=None, sa_column=Column(String(16), nullable=True))
    tiers: list | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    credits_grant: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))

    plan: Plan = Relationship(back_populates="prices")

    def __repr__(self) -> str:
        return f"<Price(stripe_price_id={self.stripe_price_id}, interval={self.interval})>"


{%- elif cookiecutter.use_sqlalchemy %}
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Plan(Base, TimestampMixin):
    __tablename__ = "plan"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    base_amount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    included_seats: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    extra_seat_amount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    seats_min: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    seats_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_credits_base: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_credits_per_seat: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    prices: Mapped[list["Price"]] = relationship("Price", back_populates="plan", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Plan(code={self.code}, name={self.display_name})>"


class Price(Base, TimestampMixin):
    __tablename__ = "price"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("plan.id", ondelete="CASCADE"), index=True, nullable=False)
    stripe_price_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="{{ cookiecutter.billing_default_currency }}")
    trial_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    billing_scheme: Mapped[str] = mapped_column(String(16), default="per_unit", nullable=False)
    tiers_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tiers: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    credits_grant: Mapped[int | None] = mapped_column(Integer, nullable=True)

    plan: Mapped[Plan] = relationship("Plan", back_populates="prices")

    def __repr__(self) -> str:
        return f"<Price(stripe_price_id={self.stripe_price_id}, interval={self.interval})>"


{%- endif %}
{%- else %}
"""Plan and Price models — not enabled (enable_billing=false)."""
{%- endif %}
