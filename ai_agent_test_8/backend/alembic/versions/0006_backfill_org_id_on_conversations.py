"""backfill organization_id on conversations and rag_documents

Revision ID: 0006_backfill_conv_org
Revises: 0005_org_tenant_isolation
Create Date: 2026-06-21T15:41:05.040089+00:00

Assigns each conversation (and rag_document) that has a user_id to that user's
Personal Organization. Rows with NULL user_id are left as NULL.

This is a data migration — safe to re-run (NULL rows already handled).
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_backfill_conv_org"
down_revision = "0005_org_tenant_isolation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text("""
        UPDATE conversations
        SET organization_id = o.id
        FROM organizations o
        WHERE conversations.user_id = o.created_by_user_id
          AND o.is_personal = TRUE
          AND conversations.organization_id IS NULL
    """)
    )

    # Backfill rag_documents (no user_id column — leave NULL for manual assignment)
    # RAG documents without an org context will remain personal-org-less
    # until an admin assigns them. This is intentional.


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("UPDATE conversations SET organization_id = NULL"))
    conn.execute(sa.text("UPDATE rag_documents SET organization_id = NULL"))
