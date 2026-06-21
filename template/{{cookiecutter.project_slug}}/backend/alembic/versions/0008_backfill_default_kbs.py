{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
"""backfill default Knowledge Bases per org + assign existing rag_documents

Revision ID: 0008_backfill_default_kbs
Revises: 0007_knowledge_bases
Create Date: {{ cookiecutter.generated_at }}

For each existing organization:
  1. Creates a "Default" org-scoped KnowledgeBase using the org's first
     collection (or a placeholder "default" collection name).
  2. Assigns all rag_documents belonging to that org to its Default KB.
  3. For rag_documents with no organization_id, assigns them to a special
     "unclaimed" app-scoped KB (created here if needed).

This migration is idempotent — safe to re-run.
"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "0008_backfill_default_kbs"
down_revision = "0007_knowledge_bases"
branch_labels = None
depends_on = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    conn = op.get_bind()

    orgs = conn.execute(sa.text("SELECT id, name FROM organizations")).fetchall()
    for org in orgs:
        org_id = str(org.id)

        existing = conn.execute(sa.text(
            "SELECT id FROM knowledge_bases WHERE organization_id = :org_id AND is_default = TRUE LIMIT 1"
        ), {"org_id": org_id}).fetchone()

        if existing:
            continue

        first_doc = conn.execute(sa.text(
            "SELECT collection_name FROM rag_documents WHERE organization_id = :org_id LIMIT 1"
        ), {"org_id": org_id}).fetchone()
        collection_name = first_doc.collection_name if first_doc else f"org_{org_id[:8]}"

        kb_id = str(uuid.uuid4())
        conn.execute(sa.text("""
            INSERT INTO knowledge_bases (id, name, description, scope, collection_name, is_default, organization_id, created_at)
            VALUES (:id, 'Default', 'Default knowledge base', 'org', :collection_name, TRUE, :org_id, :now)
        """), {"id": kb_id, "collection_name": collection_name, "org_id": org_id, "now": _now()})

        conn.execute(sa.text("""
            UPDATE rag_documents
            SET knowledge_base_id = :kb_id
            WHERE organization_id = :org_id AND knowledge_base_id IS NULL
        """), {"kb_id": kb_id, "org_id": org_id})

    unclaimed = conn.execute(sa.text(
        "SELECT COUNT(*) FROM rag_documents WHERE organization_id IS NULL AND knowledge_base_id IS NULL"
    )).scalar()
    if unclaimed and unclaimed > 0:
        first_unclaimed = conn.execute(sa.text(
            "SELECT collection_name FROM rag_documents WHERE organization_id IS NULL LIMIT 1"
        )).fetchone()
        collection_name = first_unclaimed.collection_name if first_unclaimed else "default"

        app_kb_id = str(uuid.uuid4())
        conn.execute(sa.text("""
            INSERT INTO knowledge_bases (id, name, description, scope, collection_name, is_default, created_at)
            VALUES (:id, 'Global', 'Pre-existing unclaimed documents', 'app', :collection_name, FALSE, :now)
        """), {"id": app_kb_id, "collection_name": collection_name, "now": _now()})

        conn.execute(sa.text("""
            UPDATE rag_documents SET knowledge_base_id = :kb_id
            WHERE organization_id IS NULL AND knowledge_base_id IS NULL
        """), {"kb_id": app_kb_id})



def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE rag_documents SET knowledge_base_id = NULL"))
    conn.execute(sa.text("DELETE FROM knowledge_bases"))


{%- else %}
"""backfill default KBs — skipped (enable_teams/enable_rag/use_jwt=false or no SQL DB)

Revision ID: 0008_backfill_default_kbs
"""

revision = "0008_backfill_default_kbs"
down_revision = "0007_knowledge_bases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
