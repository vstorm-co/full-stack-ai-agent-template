{%- if cookiecutter.enable_billing %}
"""create stripe_event table

Revision ID: 0013_create_stripe_event_table
Revises: 0012_create_subscription_table
Create Date: {{ cookiecutter.generated_at }}

Creates:
  - stripe_event (idempotency log for incoming Stripe webhook events)
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from alembic import op

revision = "0013_create_stripe_event_table"
down_revision = "0012_create_subscription_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stripe_event",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("stripe_event_id", sa.String(64), unique=True, nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_stripe_event_stripe_event_id", "stripe_event", ["stripe_event_id"])
    op.create_index("ix_stripe_event_event_type", "stripe_event", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_stripe_event_event_type", table_name="stripe_event")
    op.drop_index("ix_stripe_event_stripe_event_id", table_name="stripe_event")
    op.drop_table("stripe_event")


{%- else %}
"""create stripe_event table — skipped (enable_billing=false or no SQL DB)

Revision ID: 0013_create_stripe_event_table
"""

revision = "0013_create_stripe_event_table"
down_revision = "0012_create_subscription_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
