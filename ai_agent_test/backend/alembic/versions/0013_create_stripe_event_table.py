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
