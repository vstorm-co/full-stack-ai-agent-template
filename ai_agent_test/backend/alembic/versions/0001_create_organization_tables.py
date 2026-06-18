"""create organization tables — skipped (enable_teams=false or no SQL DB)

Revision ID: 0001_org
"""
# This migration is a no-op when enable_teams is false.

revision = "0001_org"
down_revision = "0000_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
