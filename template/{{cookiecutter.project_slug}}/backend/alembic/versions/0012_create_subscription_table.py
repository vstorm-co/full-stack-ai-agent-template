{%- if cookiecutter.enable_billing %}
"""create subscription table

Revision ID: 0012_create_subscription_table
Revises: 0011_create_plan_price_tables
Create Date: {{ cookiecutter.generated_at }}

Creates:
  - subscription (local mirror of Stripe Subscription, one per org)
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from alembic import op

revision = "0012_create_subscription_table"
down_revision = "0011_create_plan_price_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("price_id", PG_UUID(as_uuid=True), sa.ForeignKey("price.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, index=True),
        sa.Column("stripe_subscription_id", sa.String(64), unique=True, nullable=False),
        sa.Column("stripe_customer_id", sa.String(64), nullable=False),
        sa.Column("stripe_item_id", sa.String(64), nullable=False),
        sa.Column("seats_quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_subscription_organization_id", "subscription", ["organization_id"])
    op.create_index("ix_subscription_stripe_subscription_id", "subscription", ["stripe_subscription_id"])
    op.create_index("ix_subscription_stripe_customer_id", "subscription", ["stripe_customer_id"])


def downgrade() -> None:
    op.drop_index("ix_subscription_stripe_customer_id", table_name="subscription")
    op.drop_index("ix_subscription_stripe_subscription_id", table_name="subscription")
    op.drop_index("ix_subscription_organization_id", table_name="subscription")
    op.drop_table("subscription")


{%- else %}
"""create subscription table — skipped (enable_billing=false or no SQL DB)

Revision ID: 0012_create_subscription_table
"""

revision = "0012_create_subscription_table"
down_revision = "0011_create_plan_price_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
