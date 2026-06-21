{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
"""add billing and seats columns to organizations

Revision ID: 0010_org_billing_seats
Revises: 0009_conv_active_kb_ids
Create Date: {{ cookiecutter.generated_at }}

Adds Stripe billing fields to the organizations table:
  - stripe_subscription_id  (VARCHAR 128, nullable, unique, indexed)
  - seats_limit             (INTEGER, nullable)

The stripe_customer_id column was added in migration 0001 when enable_billing
was first introduced. This migration adds the new fields for seat management.
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_org_billing_seats"
down_revision = "0009_conv_active_kb_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("stripe_subscription_id", sa.String(128), nullable=True),
    )
    op.create_index(
        "ix_organizations_stripe_subscription_id",
        "organizations",
        ["stripe_subscription_id"],
        unique=True,
    )
    op.add_column(
        "organizations",
        sa.Column("seats_limit", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "seats_limit")
    op.drop_index("ix_organizations_stripe_subscription_id", table_name="organizations")
    op.drop_column("organizations", "stripe_subscription_id")


{%- else %}
"""add billing seats to organizations — skipped (enable_billing/enable_teams=false or no SQL DB)

Revision ID: 0010_org_billing_seats
"""

revision = "0010_org_billing_seats"
down_revision = "0009_conv_active_kb_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
