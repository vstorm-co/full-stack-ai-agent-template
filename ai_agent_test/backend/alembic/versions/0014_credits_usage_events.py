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
