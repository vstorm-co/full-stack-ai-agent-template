{%- if cookiecutter.enable_billing %}
"""create plan and price tables

Revision ID: 0011_create_plan_price_tables
Revises: 0010_org_billing_seats
Create Date: {{ cookiecutter.generated_at }}

Creates:
  - plan  (local mirror of Stripe Products)
  - price (local mirror of Stripe Prices)
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from alembic import op

revision = "0011_create_plan_price_tables"
down_revision = "0010_org_billing_seats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(32), unique=True, nullable=False),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("features", JSONB(), nullable=False, server_default="{}"),
        sa.Column("base_amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("included_seats", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("extra_seat_amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("seats_min", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("seats_max", sa.Integer(), nullable=True),
        sa.Column("monthly_credits_base", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_credits_per_seat", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "price",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", PG_UUID(as_uuid=True), sa.ForeignKey("plan.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("stripe_price_id", sa.String(64), unique=True, nullable=False),
        sa.Column("interval", sa.String(16), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="usd"),
        sa.Column("trial_period_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("billing_scheme", sa.String(16), nullable=False, server_default="per_unit"),
        sa.Column("tiers_mode", sa.String(16), nullable=True),
        sa.Column("tiers", JSONB(), nullable=True),
        sa.Column("credits_grant", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_plan_code", "plan", ["code"])
    op.create_index("ix_price_stripe_price_id", "price", ["stripe_price_id"])


def downgrade() -> None:
    op.drop_index("ix_price_stripe_price_id", table_name="price")
    op.drop_index("ix_plan_code", table_name="plan")
    op.drop_table("price")
    op.drop_table("plan")


{%- else %}
"""create plan and price tables — skipped (enable_billing=false or no SQL DB)

Revision ID: 0011_create_plan_price_tables
"""

revision = "0011_create_plan_price_tables"
down_revision = "0010_org_billing_seats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
