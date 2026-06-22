{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
"""Billing schemas — Stripe Checkout, Portal, Plans, Subscriptions, Credits."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class PriceRead(BaseSchema):
    id: UUID
    stripe_price_id: str
    interval: str
    amount_cents: int
    currency: str
    trial_period_days: int | None = None
    is_active: bool
    billing_scheme: str
    credits_grant: int | None = None


class PlanRead(BaseSchema):
    id: UUID
    code: str
    display_name: str
    description: str | None = None
    is_active: bool
    sort_order: int
    features: dict[str, Any] = Field(default_factory=dict)
    base_amount_cents: int
    included_seats: int
    extra_seat_amount_cents: int
    seats_min: int
    seats_max: int | None = None
    monthly_credits_base: int
    monthly_credits_per_seat: int
    prices: list[PriceRead] = Field(default_factory=list)


class PlanList(BaseSchema):
    plans: list[PlanRead]


class SubscriptionRead(BaseSchema, TimestampSchema):
    id: UUID
    organization_id: UUID
    price_id: UUID
    stripe_subscription_id: str
    stripe_customer_id: str
    seats_quantity: int
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    canceled_at: datetime | None = None
    trial_start: datetime | None = None
    trial_end: datetime | None = None


class SubscriptionChangePlan(BaseSchema):
    new_price_id: UUID


class CheckoutSessionCreate(BaseSchema):
    seats: int = Field(default=1, ge=1, le=500)
    price_id: UUID
    success_url: str = Field(..., description="Redirect URL on success")
    cancel_url: str = Field(..., description="Redirect URL on cancel")


class CheckoutSessionRead(BaseSchema):
    url: str
    session_id: str = ""


class PortalSessionRead(BaseSchema):
    url: str


{%- if cookiecutter.enable_credits_system %}

class CreditBalanceRead(BaseSchema):
    balance: int
    low_threshold: int


class CreditTransactionRead(BaseSchema, TimestampSchema):
    id: UUID
    organization_id: UUID
    actor_user_id: UUID | None = None
    usage_event_id: UUID | None = None
    delta: int
    balance_after: int
    type: str
    description: str
    stripe_reference: str | None = None


class CreditTransactionList(BaseSchema):
    items: list[CreditTransactionRead]
    total: int


class UsageEventRead(BaseSchema, TimestampSchema):
    id: UUID
    organization_id: UUID
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    credits_charged: int
    ai_framework: str


class UsageByModelRead(BaseSchema):
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    credits_charged: int
    total_calls: int


class UsageAggregateRead(BaseSchema):
    total_input_tokens: int
    total_output_tokens: int
    total_cached_tokens: int
    total_credits_charged: int
    total_calls: int
    by_model: list[UsageByModelRead] = Field(default_factory=list)


class UsageDailyBucket(BaseSchema):
    day: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    credits_charged: int
    total_calls: int


class UsageTimelineRead(BaseSchema):
    buckets: list[UsageDailyBucket]
    days: int


{%- endif %}


class InvoiceRead(BaseSchema):
    id: str
    number: str
    status: str
    amount_due: int
    amount_paid: int
    currency: str
    period_start: datetime
    period_end: datetime
    invoice_pdf: str | None = None
    hosted_invoice_url: str | None = None
    created_at: datetime


class InvoiceList(BaseSchema):
    items: list[InvoiceRead]
    total: int


class StorageUsageRead(BaseSchema):
    chat_files_bytes: int
    rag_documents_bytes: int
    total_bytes: int

{%- else %}
"""Billing schemas — not configured (enable_billing or enable_teams is false)."""
{%- endif %}
