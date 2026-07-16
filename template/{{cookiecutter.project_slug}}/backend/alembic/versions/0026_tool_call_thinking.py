"""tool_calls: add thinking column for per-call reasoning

Revision ID: 0026
Revises: 0025

Adds a nullable ``thinking`` text column to tool_calls so the reasoning the model
produced immediately before each tool call is persisted alongside it. This preserves
the ordered timeline (reasoning → tool → reasoning → tool) when a turn is reloaded or
exported, instead of collapsing every reasoning block into the single message-level
``thinking`` field (which rendered as one node at the top).
"""

import sqlalchemy as sa

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tool_calls", sa.Column("thinking", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tool_calls", "thinking")
