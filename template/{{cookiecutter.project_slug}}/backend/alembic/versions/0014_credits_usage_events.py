{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
"""create credit_transaction and usage_event tables

Revision ID: 0014_credits_usage_events
Revises: 0013_create_stripe_event_table
Create Date: {{ cookiecutter.generated_at }}

Creates:
  - credit_transaction (immutable ledger of credit changes per org)
  - usage_event        (raw token usage per agent call)
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from alembic import op

revision = "0014_credits_usage_events"
down_revision = "0013_create_stripe_event_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credit_transaction",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("stripe_reference", sa.String(128), nullable=True),
        sa.Column("usage_event_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_credit_transaction_organization_id", "credit_transaction", ["organization_id"])
    op.create_index("ix_credit_transaction_type", "credit_transaction", ["type"])
    op.create_index("ix_credit_transaction_stripe_reference", "credit_transaction", ["stripe_reference"])

    op.create_table(
        "usage_event",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("conversation_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cached_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credits_charged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_framework", sa.String(32), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_usage_event_organization_id", "usage_event", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_usage_event_organization_id", table_name="usage_event")
    op.drop_table("usage_event")
    op.drop_index("ix_credit_transaction_stripe_reference", table_name="credit_transaction")
    op.drop_index("ix_credit_transaction_type", table_name="credit_transaction")
    op.drop_index("ix_credit_transaction_organization_id", table_name="credit_transaction")
    op.drop_table("credit_transaction")


{%- else %}
"""create credit_transaction and usage_event — skipped (enable_billing/enable_credits_system=false or no SQL DB)

Revision ID: 0014_credits_usage_events
"""

revision = "0014_credits_usage_events"
down_revision = "0013_create_stripe_event_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
