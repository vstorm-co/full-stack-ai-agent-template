"""add active_knowledge_base_ids to conversations

Revision ID: 0009_conv_active_kb_ids
Revises: 0008_backfill_default_kbs
Create Date: 2026-06-21T15:41:05.040089+00:00

Adds the optional JSONB (PostgreSQL) / TEXT (SQLite) column
`active_knowledge_base_ids` to `conversations`.

Semantics:
  NULL  → use defaults: personal + org KBs active, app KBs off
  []    → RAG disabled for this conversation
  [id1] → explicit KB selection
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0009_conv_active_kb_ids"
down_revision = "0008_backfill_default_kbs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "active_knowledge_base_ids",
            JSONB(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("conversations", "active_knowledge_base_ids")
