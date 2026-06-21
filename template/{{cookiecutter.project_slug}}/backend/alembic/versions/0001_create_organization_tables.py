{%- if cookiecutter.enable_teams %}
"""create organization tables

Revision ID: 0001_org
Revises:
Create Date: {{ cookiecutter.generated_at }}

Tables: organizations, organization_members, invitations
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_org"
down_revision = "0000_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("is_personal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
{%- if cookiecutter.enable_billing %}
        sa.Column("stripe_customer_id", sa.String(64), nullable=True),
        sa.Column("subscription_tier", sa.String(32), nullable=False, server_default="free"),
        sa.Column("credits_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
{%- endif %}
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
            name="fk_organization_created_by",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_organization_slug"),
    )
    op.create_index("ix_organization_slug", "organizations", ["slug"], unique=True)
    op.create_index("ix_organization_is_personal", "organizations", ["is_personal"])
    op.create_index("ix_organization_created_by", "organizations", ["created_by_user_id"])
{%- if cookiecutter.enable_billing %}
    op.create_index("ix_organization_stripe_customer", "organizations", ["stripe_customer_id"], unique=True)
    op.create_index("ix_organization_tier", "organizations", ["subscription_tier"])
{%- endif %}

    op.create_table(
        "organization_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column(
            "invited_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
            name="fk_org_member_org",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_org_member_user",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"],
            ["users.id"],
            name="fk_org_member_invited_by",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
    )
    op.create_index("ix_org_member_org_id", "organization_members", ["organization_id"])
    op.create_index("ix_org_member_user_id", "organization_members", ["user_id"])
    op.create_index(
        "ix_org_member_org_role", "organization_members", ["organization_id", "role"]
    )

    op.create_table(
        "invitations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column(
            "invited_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "accepted_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
            name="fk_invitation_org",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"],
            ["users.id"],
            name="fk_invitation_invited_by",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by_user_id"],
            ["users.id"],
            name="fk_invitation_accepted_by",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_invitation_token"),
    )
    op.create_index("ix_invitation_org_id", "invitations", ["organization_id"])
    op.create_index("ix_invitation_email", "invitations", ["email"])
    op.create_index("ix_invitation_token", "invitations", ["token"], unique=True)
    op.create_index("ix_invitation_status", "invitations", ["status"])
    # Partial unique index: only one pending invite per (org, email)
    op.create_index(
        "uq_pending_invitation",
        "invitations",
        ["organization_id", "email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_table("invitations")
    op.drop_table("organization_members")
    op.drop_table("organizations")


{%- else %}
"""create organization tables — skipped (enable_teams=false or no SQL DB)

Revision ID: 0001_org
"""
# This migration is a no-op when enable_teams is false.

revision = "0001_org"
down_revision = "0000_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
