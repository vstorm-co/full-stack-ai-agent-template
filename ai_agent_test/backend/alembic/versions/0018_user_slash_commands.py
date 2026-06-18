"""create user_slash_commands table

Revision ID: 0018_user_slash_commands
Revises: 0017_create_api_keys_table
Create Date: 2026-05-10T00:00:00+00:00

Stores per-user slash command settings for the chat palette:
  - Custom commands (``prompt`` is set) — quick prompt shortcuts.
  - Built-in overrides (``prompt`` is NULL) — record only ``is_enabled`` for
    one of the frontend's BUILTIN_COMMANDS, so users can hide ones they don't
    use.

The unique ``(user_id, name)`` constraint prevents both classes of row from
co-existing for the same name on a single user.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision = "0018_user_slash_commands"
down_revision = "0016_user_onboarding_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_slash_commands",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "name", name="uq_user_slash_commands_user_name"),
    )
    op.create_index("ix_user_slash_commands_user_id", "user_slash_commands", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_slash_commands_user_id", table_name="user_slash_commands")
    op.drop_table("user_slash_commands")
