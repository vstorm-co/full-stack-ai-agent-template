"""add is_app_admin to users

Revision ID: 0003_is_app_admin
Revises: 0002_backfill_orgs
Create Date: 2026-06-21T15:41:05.040089+00:00

Adds the is_app_admin boolean flag to the users table. App admins can
manage the platform across all organizations (create global KBs, view all
orgs, etc.). Default false — grant via the ``create-app-admin`` CLI command.
"""

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0003_is_app_admin"
down_revision = "0002_backfill_orgs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in inspect(bind).get_columns("users")}
    if "is_app_admin" in columns:
        return
    op.add_column(
        "users",
        sa.Column("is_app_admin", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("users", "is_app_admin")
