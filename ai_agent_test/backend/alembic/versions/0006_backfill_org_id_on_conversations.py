"""backfill organization_id on conversations — skipped (enable_teams=false or no JWT)

Revision ID: 0006_backfill_conv_org
"""

revision = "0006_backfill_conv_org"
down_revision = "0005_org_tenant_isolation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
