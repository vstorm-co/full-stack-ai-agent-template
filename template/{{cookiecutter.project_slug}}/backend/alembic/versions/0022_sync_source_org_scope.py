"""sync_source: add organization_id, make collection_name nullable

Revision ID: 0022
Revises: 0021_create_items
Create Date: 2026-06-21

SyncSource is now org-scoped. collection_name is nullable so an integration
can be created at org level before being assigned to a specific knowledge base.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0022"
{%- if cookiecutter.include_example_crud %}
down_revision = "0021_create_items"
{%- elif cookiecutter.use_external_user_id_in_conversations %}
down_revision = "0020_conv_external_user_id"
{%- elif cookiecutter.use_delegated_auth %}
down_revision = "0019_user_external_id"
{%- else %}
down_revision = "0018_user_slash_commands"
{%- endif %}
branch_labels = None
depends_on = None


def upgrade() -> None:
{%- if cookiecutter.enable_rag %}
    op.add_column(
        "sync_sources",
        sa.Column(
            "organization_id",
            PG_UUID(as_uuid=True),
            nullable=True,
        ),
    )
{%- if cookiecutter.enable_teams %}
    op.create_foreign_key(
        "sync_sources_organization_id_fkey",
        "sync_sources",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
{%- endif %}
    op.create_index("ix_sync_sources_organization_id", "sync_sources", ["organization_id"])
    op.alter_column("sync_sources", "collection_name", nullable=True)
{%- else %}
    pass
{%- endif %}


def downgrade() -> None:
{%- if cookiecutter.enable_rag %}
    # Restore NOT NULL (set empty string for any nulls first)
    op.execute("UPDATE sync_sources SET collection_name = '' WHERE collection_name IS NULL")
    op.alter_column("sync_sources", "collection_name", nullable=False)
    op.drop_index("ix_sync_sources_organization_id", table_name="sync_sources")
{%- if cookiecutter.enable_teams %}
    op.drop_constraint("sync_sources_organization_id_fkey", "sync_sources", type_="foreignkey")
{%- endif %}
    op.drop_column("sync_sources", "organization_id")
{%- else %}
    pass
{%- endif %}
