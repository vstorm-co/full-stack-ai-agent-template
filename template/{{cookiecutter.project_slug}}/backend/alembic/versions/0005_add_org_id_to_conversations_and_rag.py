{%- if cookiecutter.enable_teams %}
"""add organization_id to conversations and rag_documents

Revision ID: 0005_org_tenant_isolation
Revises: 0004_audit_log
Create Date: {{ cookiecutter.generated_at }}

Adds optional organization_id FK (SET NULL on delete) to conversations and
rag_documents so every resource is scoped to one org context. Existing rows
are left NULL and will be backfilled by migration 0006.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0005_org_tenant_isolation"
down_revision = "0004_5_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    conv_cols = {col["name"] for col in inspect(bind).get_columns("conversations")}
    if "organization_id" not in conv_cols:
        op.add_column(
            "conversations",
            sa.Column(
                "organization_id",
                PG_UUID(as_uuid=True),
                sa.ForeignKey("organizations.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index("ix_conversations_organization_id", "conversations", ["organization_id"])
{%- if cookiecutter.enable_rag %}

    rag_cols = {col["name"] for col in inspect(bind).get_columns("rag_documents")}
    if "organization_id" not in rag_cols:
        op.add_column(
            "rag_documents",
            sa.Column(
                "organization_id",
                PG_UUID(as_uuid=True),
                sa.ForeignKey("organizations.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index("ix_rag_documents_organization_id", "rag_documents", ["organization_id"])
{%- endif %}


def downgrade() -> None:
    op.drop_index("ix_conversations_organization_id", table_name="conversations")
    op.drop_column("conversations", "organization_id")
{%- if cookiecutter.enable_rag %}

    op.drop_index("ix_rag_documents_organization_id", table_name="rag_documents")
    op.drop_column("rag_documents", "organization_id")
{%- endif %}


{%- else %}
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
{%- endif %}
