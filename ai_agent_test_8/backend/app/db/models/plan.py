"""Plan and Price models — local mirror of Stripe Products/Prices."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Plan(Base, TimestampMixin):
    __tablename__ = "plan"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
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

    prices: Mapped[list["Price"]] = relationship(
        "Price", back_populates="plan", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Plan(code={self.code}, name={self.display_name})>"


class Price(Base, TimestampMixin):
    __tablename__ = "price"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("plan.id", ondelete="CASCADE"), index=True, nullable=False
    )
    stripe_price_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")
    trial_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    billing_scheme: Mapped[str] = mapped_column(String(16), default="per_unit", nullable=False)
    tiers_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tiers: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    credits_grant: Mapped[int | None] = mapped_column(Integer, nullable=True)

    plan: Mapped[Plan] = relationship("Plan", back_populates="prices")

    def __repr__(self) -> str:
        return f"<Price(stripe_price_id={self.stripe_price_id}, interval={self.interval})>"
