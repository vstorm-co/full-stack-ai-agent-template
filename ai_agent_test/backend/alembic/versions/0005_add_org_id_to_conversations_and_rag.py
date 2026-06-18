"""add organization_id to conversations — skipped (enable_teams=false or no SQL DB)

Revision ID: 0005_org_tenant_isolation
"""

revision = "0005_org_tenant_isolation"
down_revision = "0004_5_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
