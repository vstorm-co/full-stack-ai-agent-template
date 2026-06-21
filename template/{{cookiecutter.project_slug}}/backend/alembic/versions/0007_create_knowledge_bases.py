{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
"""create knowledge_bases table + add knowledge_base_id to rag_documents

Revision ID: 0007_knowledge_bases
Revises: 0006_backfill_conv_org
Create Date: {{ cookiecutter.generated_at }}

Creates the knowledge_bases table (scoped RAG collection wrappers) and adds
the optional knowledge_base_id FK to rag_documents. Existing rag_documents
will have knowledge_base_id = NULL until backfill migration 0008 runs.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0007_knowledge_bases"
down_revision = "0006_backfill_conv_org"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_bases",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("scope", sa.String(16), nullable=False, server_default="personal"),
        sa.Column("collection_name", sa.String(255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("owner_user_id", PG_UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("organization_id", PG_UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_knowledge_bases_scope", "knowledge_bases", ["scope"])
    op.create_index("ix_knowledge_bases_owner_user_id", "knowledge_bases", ["owner_user_id"])
    op.create_index("ix_knowledge_bases_organization_id", "knowledge_bases", ["organization_id"])
    op.create_index("ix_knowledge_bases_collection_name", "knowledge_bases", ["collection_name"])

    op.add_column(
        "rag_documents",
        sa.Column(
            "knowledge_base_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_rag_documents_knowledge_base_id", "rag_documents", ["knowledge_base_id"])


def downgrade() -> None:
    op.drop_index("ix_rag_documents_knowledge_base_id", table_name="rag_documents")
    op.drop_column("rag_documents", "knowledge_base_id")

    op.drop_index("ix_knowledge_bases_collection_name", table_name="knowledge_bases")
    op.drop_index("ix_knowledge_bases_organization_id", table_name="knowledge_bases")
    op.drop_index("ix_knowledge_bases_owner_user_id", table_name="knowledge_bases")
    op.drop_index("ix_knowledge_bases_scope", table_name="knowledge_bases")
    op.drop_table("knowledge_bases")


{%- else %}
"""create knowledge_bases — skipped (enable_teams/enable_rag/use_jwt=false or no SQL DB)

Revision ID: 0007_knowledge_bases
"""

revision = "0007_knowledge_bases"
down_revision = "0006_backfill_conv_org"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
