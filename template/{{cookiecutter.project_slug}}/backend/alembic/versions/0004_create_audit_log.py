{%- if cookiecutter.enable_teams %}
"""create app_admin_audit_logs table

Revision ID: 0004_audit_log
Revises: 0003_is_app_admin
Create Date: {{ cookiecutter.generated_at }}

Stores privileged action records for app admins and org owners.
Used for security auditing and compliance.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

revision = "0004_audit_log"
down_revision = "0003_is_app_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_admin_audit_logs",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=True),
        sa.Column("target_id", sa.String(36), nullable=True),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_audit_actor_user_id", "app_admin_audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_organization_id", "app_admin_audit_logs", ["organization_id"])
    op.create_index("ix_audit_action", "app_admin_audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("app_admin_audit_logs")


{%- else %}
"""create audit log — skipped (enable_teams=false or no SQL DB)

Revision ID: 0004_audit_log
"""

revision = "0004_audit_log"
down_revision = "0003_is_app_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
