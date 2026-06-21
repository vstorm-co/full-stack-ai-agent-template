{%- if cookiecutter.enable_teams %}
"""Invitation repository (PostgreSQL async)."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.organization import Invitation, InvitationStatus, OrgRole

_INVITE_TTL_DAYS = 7


async def get_by_token(db: AsyncSession, token: str) -> Invitation | None:
    result = await db.execute(select(Invitation).where(Invitation.token == token))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, invitation_id: UUID) -> Invitation | None:
    return await db.get(Invitation, invitation_id)


async def get_pending_for_org_email(
    db: AsyncSession, *, organization_id: UUID, email: str
) -> Invitation | None:
    result = await db.execute(
        select(Invitation).where(
            Invitation.organization_id == organization_id,
            Invitation.email == email.lower(),
            Invitation.status == InvitationStatus.PENDING.value,
        )
    )
    return result.scalar_one_or_none()


async def list_for_org(
    db: AsyncSession,
    organization_id: UUID,
    *,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Invitation]:
    query = select(Invitation).where(Invitation.organization_id == organization_id)
    if status:
        query = query.where(Invitation.status == status)
    query = query.order_by(Invitation.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    organization_id: UUID,
    email: str,
    role: str = OrgRole.MEMBER.value,
    invited_by_user_id: UUID,
    ttl_days: int = _INVITE_TTL_DAYS,
) -> Invitation:
    invite = Invitation(
        organization_id=organization_id,
        email=email.lower(),
        role=role,
        invited_by_user_id=invited_by_user_id,
        token=secrets.token_urlsafe(32),
        status=InvitationStatus.PENDING.value,
        expires_at=datetime.now(UTC) + timedelta(days=ttl_days),
    )
    db.add(invite)
    await db.flush()
    await db.refresh(invite)
    return invite


async def accept(
    db: AsyncSession,
    invite: Invitation,
    *,
    accepted_by_user_id: UUID,
) -> Invitation:
    invite.status = InvitationStatus.ACCEPTED.value
    invite.accepted_at = datetime.now(UTC)
    invite.accepted_by_user_id = accepted_by_user_id
    await db.flush()
    await db.refresh(invite)
    return invite


async def revoke(db: AsyncSession, invite: Invitation) -> Invitation:
    invite.status = InvitationStatus.REVOKED.value
    await db.flush()
    await db.refresh(invite)
    return invite


async def expire_stale(db: AsyncSession) -> int:
    """Mark all PENDING invitations past their expiry as EXPIRED. Returns count updated."""
    result = await db.execute(
        update(Invitation)
        .where(
            Invitation.status == InvitationStatus.PENDING.value,
            Invitation.expires_at < datetime.now(UTC),
        )
        .values(status=InvitationStatus.EXPIRED.value)
    )
    await db.flush()
    return result.rowcount  # ty: ignore[unresolved-attribute]


{%- else %}
"""Invitation repository — not configured (enable_teams=false)."""
{%- endif %}
