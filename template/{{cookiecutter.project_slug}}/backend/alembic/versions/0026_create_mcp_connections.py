{%- if cookiecutter.enable_mcp_client %}
"""create mcp_connections table

Revision ID: 0026_create_mcp_connections
Revises: 0025
Create Date: {{ cookiecutter.generated_at }}

User-configured MCP server connections (Settings → Integrations). Each row
is one remote MCP server attached to the user's assistant.

``auth_token`` is Fernet-encrypted (static-bearer connections); ``allowed_tools``
is NULL when every tool the server offers is exposed. OAuth 2.1 connections
(``auth_type = "oauth"``) instead keep the discovered endpoints, registered
client credentials and access/refresh tokens Fernet-encrypted in
``oauth_payload``. An authorization redirect that is still in flight is staged
in ``oauth_pending_payload`` and keyed by the CSRF token in ``oauth_state``, so
re-authorizing never overwrites credentials that still work.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision = "0026_create_mcp_connections"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_connections",
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
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("auth_token", sa.Text(), nullable=True),
        sa.Column("allowed_tools", JSONB(), nullable=True),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "auth_type",
            sa.String(16),
            nullable=False,
            server_default="bearer",
        ),
        sa.Column("oauth_state", sa.String(128), nullable=True),
        sa.Column("oauth_payload", sa.Text(), nullable=True),
        sa.Column("oauth_pending_payload", sa.Text(), nullable=True),
        sa.Column("last_status", sa.String(16), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "name", name="uq_mcp_connections_user_name"),
    )
    op.create_index("ix_mcp_connections_user_id", "mcp_connections", ["user_id"])
    op.create_index("ix_mcp_connections_oauth_state", "mcp_connections", ["oauth_state"])


def downgrade() -> None:
    op.drop_index("ix_mcp_connections_oauth_state", table_name="mcp_connections")
    op.drop_index("ix_mcp_connections_user_id", table_name="mcp_connections")
    op.drop_table("mcp_connections")
{%- endif %}
