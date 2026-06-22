"""conversations: add is_demo flag for public demo gallery

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-22

Adds ``is_demo`` boolean column to conversations so admins can flag curated
agent runs for the public demo replay gallery (served without authentication).
"""

from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_conversations_is_demo", "conversations", ["is_demo"])


def downgrade() -> None:
    op.drop_index("ix_conversations_is_demo", table_name="conversations")
    op.drop_column("conversations", "is_demo")
