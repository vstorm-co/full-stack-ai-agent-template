{%- if cookiecutter.enable_webhooks %}
"""create webhook tables

Revision ID: 0024_create_webhook_tables
Revises: 0023
Create Date: {{ cookiecutter.generated_at }}

Creates:
  - webhooks (outbound webhook subscriptions)
  - webhook_deliveries (per-attempt delivery log)
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from alembic import op

revision = "0024_create_webhook_tables"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhooks",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("secret", sa.String(255), nullable=False),
        sa.Column("events", ARRAY(sa.String()), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
{%- if cookiecutter.use_jwt %}
        sa.Column("user_id", PG_UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
{%- endif %}
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
{%- if cookiecutter.use_jwt %}
    op.create_index("ix_webhooks_user_id", "webhooks", ["user_id"])
{%- endif %}

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("webhook_id", PG_UUID(as_uuid=True), sa.ForeignKey("webhooks.id"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("success", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"])
    op.create_index("ix_webhook_deliveries_created_at", "webhook_deliveries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_created_at", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_webhook_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
{%- if cookiecutter.use_jwt %}
    op.drop_index("ix_webhooks_user_id", table_name="webhooks")
{%- endif %}
    op.drop_table("webhooks")


{%- else %}
"""create webhook tables — skipped (enable_webhooks=false or no SQL DB)

Revision ID: 0024_create_webhook_tables
"""

revision = "0024_create_webhook_tables"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
