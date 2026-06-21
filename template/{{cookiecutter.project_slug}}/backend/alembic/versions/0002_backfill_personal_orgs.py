{%- if cookiecutter.enable_teams %}
"""backfill personal orgs for existing users

Revision ID: 0002_backfill_orgs
Revises: 0001_org
Create Date: {{ cookiecutter.generated_at }}

DATA MIGRATION — creates a Personal Organization for every existing user
that does not already have one. Safe to run multiple times (idempotent).
"""

import re
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0002_backfill_orgs"
down_revision = "0001_org"
branch_labels = None
depends_on = None

_UUID = sa.dialects.postgresql.UUID(as_uuid=True)
_ID_DEFAULT = lambda: uuid.uuid4()  # noqa: E731


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:64] or "user"


def _unique_slug(conn, base: str) -> str:
    candidate = _slugify(base)
    orgs_t = sa.table("organizations", sa.column("slug", sa.String))
    exists = conn.execute(
        sa.select(sa.func.count()).select_from(orgs_t).where(orgs_t.c.slug == candidate)
    ).scalar()
    if not exists:
        return candidate
    for i in range(2, 1000):
        suffixed = f"{candidate}-{i}"
        exists = conn.execute(
            sa.select(sa.func.count()).select_from(orgs_t).where(orgs_t.c.slug == suffixed)
        ).scalar()
        if not exists:
            return suffixed
    return f"{candidate}-{uuid.uuid4().hex[:6]}"


def upgrade() -> None:
    conn = op.get_bind()

    users_t = sa.table("users", sa.column("id"), sa.column("email"))
    orgs_t = sa.table(
        "organizations",
        sa.column("id"),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("is_personal", sa.Boolean),
        sa.column("created_by_user_id"),
        sa.column("created_at"),
        sa.column("updated_at"),
    )
    members_t = sa.table(
        "organization_members",
        sa.column("id"),
        sa.column("organization_id"),
        sa.column("user_id"),
        sa.column("role", sa.String),
        sa.column("joined_at"),
    )

    users = conn.execute(sa.select(users_t.c.id, users_t.c.email)).fetchall()

    for user_id, email in users:
        existing = conn.execute(
            sa.select(sa.func.count())
            .select_from(orgs_t)
            .where(
                sa.and_(
                    orgs_t.c.created_by_user_id == user_id,
                    orgs_t.c.is_personal.is_(True),
                )
            )
        ).scalar()

        if existing:
            continue

        org_id = _ID_DEFAULT()
        slug = _unique_slug(conn, (email or "").split("@")[0] or "user")

        conn.execute(
            orgs_t.insert().values(
                id=org_id,
                name="Personal",
                slug=slug,
                is_personal=True,
                created_by_user_id=user_id,
            )
        )
        conn.execute(
            members_t.insert().values(
                id=_ID_DEFAULT(),
                organization_id=org_id,
                user_id=user_id,
                role="owner",
            )
        )


def downgrade() -> None:
    # Removing auto-generated personal orgs is destructive — skipped intentionally.
    # Run manually if needed: DELETE FROM organizations WHERE is_personal = true.
    pass


{%- else %}
"""backfill personal orgs — skipped (enable_teams=false or no SQL DB)

Revision ID: 0002_backfill_orgs
"""

revision = "0002_backfill_orgs"
down_revision = "0001_org"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
