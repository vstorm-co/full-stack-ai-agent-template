"""messages: add thinking column for the reasoning trace

Revision ID: 0025
Revises: 0024_create_webhook_tables

Adds a nullable ``thinking`` text column to messages so the assistant's
reasoning trace (streamed live as ``thinking_delta``) is persisted alongside
the turn. Enables loaded conversations — and the self-contained HTML export —
to show the THINKING block, not just live streaming.
"""

import sqlalchemy as sa

from alembic import op

revision = "0025"
down_revision = "0024_create_webhook_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("thinking", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "thinking")
