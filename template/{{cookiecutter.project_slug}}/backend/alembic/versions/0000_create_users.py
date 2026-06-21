"""create users table

Revision ID: 0000_users
Revises:
Create Date: {{ cookiecutter.generated_at }}

Base table required by every later migration. Mirrors the current User model
including is_app_admin (later flagged in 0003 — included here so the table
is usable immediately when enable_teams=false) and onboarding_completed_at
(0016 mirror — same reason). OAuth columns are present only when an OAuth
provider was selected, keeping the schema minimal for password-only setups.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision = "0000_users"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("role", sa.String(50), nullable=False, server_default="user"),
        sa.Column("is_app_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
{%- if cookiecutter.enable_oauth %}
        sa.Column("oauth_provider", sa.String(32), nullable=True, index=True),
        sa.Column("oauth_id", sa.String(255), nullable=True, index=True),
{%- endif %}
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("users")
