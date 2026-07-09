"""messages: add thinking column for the reasoning trace

Revision ID: 0024
Revises: 0023

Adds a nullable ``thinking`` text column to messages so the assistant's
reasoning trace (streamed live as ``thinking_delta``) is persisted alongside
the turn. Enables loaded conversations — and the self-contained HTML export —
to show the THINKING block, not just live streaming.
"""

import sqlalchemy as sa

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("thinking", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "thinking")
