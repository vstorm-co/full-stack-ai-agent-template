{%- if cookiecutter.enable_teams %}
"""OrganizationMember repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.organization import OrgRole, OrganizationMember
from app.db.models.user import User


async def get(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
) -> OrganizationMember | None:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_for_org(
    db: AsyncSession,
    organization_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[tuple[OrganizationMember, str, str | None, str | None]]:
    """Return (member, email, full_name, avatar_url) tuples ordered by join date."""
    result = await db.execute(
        select(OrganizationMember, User.email, User.full_name, User.avatar_url)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == organization_id)
        .order_by(OrganizationMember.joined_at.asc())
        .offset(skip)
        .limit(limit)
    )
    return [(row[0], row[1], row[2], row[3]) for row in result.all()]


async def count_for_org(db: AsyncSession, organization_id: UUID) -> int:
    result = await db.execute(
        select(func.count(OrganizationMember.id)).where(
            OrganizationMember.organization_id == organization_id
        )
    )
    return result.scalar() or 0


async def count_billable_for_org(db: AsyncSession, organization_id: UUID) -> int:
    """Count billable members (Owner + Admin + Member; Viewer excluded)."""
    result = await db.execute(
        select(func.count(OrganizationMember.id)).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role != OrgRole.VIEWER.value,
        )
    )
    return result.scalar() or 0


async def has_owner(db: AsyncSession, organization_id: UUID) -> bool:
    result = await db.execute(
        select(func.count(OrganizationMember.id)).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role == OrgRole.OWNER.value,
        )
    )
    return (result.scalar() or 0) > 0


async def list_orgs_for_user(db: AsyncSession, user_id: UUID) -> list[OrganizationMember]:
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user_id)
    )
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    role: str = OrgRole.MEMBER.value,
    invited_by_user_id: UUID | None = None,
) -> OrganizationMember:
    member = OrganizationMember(
        organization_id=organization_id,
        user_id=user_id,
        role=role,
        invited_by_user_id=invited_by_user_id,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def update_role(
    db: AsyncSession,
    member: OrganizationMember,
    *,
    role: str,
) -> OrganizationMember:
    member.role = role
    await db.flush()
    await db.refresh(member)
    return member


async def delete(db: AsyncSession, member: OrganizationMember) -> None:
    await db.delete(member)
    await db.flush()


{%- else %}
"""OrganizationMember repository — not configured (enable_teams=false)."""
{%- endif %}
