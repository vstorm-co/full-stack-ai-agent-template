{%- if cookiecutter.enable_teams %}
{%- if cookiecutter.use_postgresql %}
"""Invitation repository (PostgreSQL async)."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
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
    from sqlalchemy import update

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


{%- elif cookiecutter.use_sqlite %}
"""Invitation repository (SQLite sync)."""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models.organization import Invitation, InvitationStatus, OrgRole

_INVITE_TTL_DAYS = 7


def get_by_token(db: Session, token: str) -> Invitation | None:
    return db.execute(select(Invitation).where(Invitation.token == token)).scalar_one_or_none()


def get_by_id(db: Session, invitation_id: str) -> Invitation | None:
    return db.get(Invitation, invitation_id)


def get_pending_for_org_email(
    db: Session, *, organization_id: str, email: str
) -> Invitation | None:
    return db.execute(
        select(Invitation).where(
            Invitation.organization_id == organization_id,
            Invitation.email == email.lower(),
            Invitation.status == InvitationStatus.PENDING.value,
        )
    ).scalar_one_or_none()


def list_for_org(
    db: Session,
    organization_id: str,
    *,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Invitation]:
    query = select(Invitation).where(Invitation.organization_id == organization_id)
    if status:
        query = query.where(Invitation.status == status)
    query = query.order_by(Invitation.created_at.desc()).offset(skip).limit(limit)
    return list(db.execute(query).scalars().all())


def create(
    db: Session,
    *,
    organization_id: str,
    email: str,
    role: str = OrgRole.MEMBER.value,
    invited_by_user_id: str,
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
    db.flush()
    db.refresh(invite)
    return invite


def accept(db: Session, invite: Invitation, *, accepted_by_user_id: str) -> Invitation:
    invite.status = InvitationStatus.ACCEPTED.value
    invite.accepted_at = datetime.now(UTC)
    invite.accepted_by_user_id = accepted_by_user_id
    db.flush()
    db.refresh(invite)
    return invite


def revoke(db: Session, invite: Invitation) -> Invitation:
    invite.status = InvitationStatus.REVOKED.value
    db.flush()
    db.refresh(invite)
    return invite


def expire_stale(db: Session) -> int:
    result = db.execute(
        update(Invitation)
        .where(
            Invitation.status == InvitationStatus.PENDING.value,
            Invitation.expires_at < datetime.now(UTC),
        )
        .values(status=InvitationStatus.EXPIRED.value)
    )
    db.flush()
    return result.rowcount  # ty: ignore[unresolved-attribute]


{%- elif cookiecutter.use_mongodb %}
"""Invitation repository (MongoDB)."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional

from app.db.models.organization import Invitation, InvitationStatus, OrgRole

_INVITE_TTL_DAYS = 7


async def get_by_token(token: str) -> Optional[Invitation]:
    return await Invitation.find_one(Invitation.token == token)


async def get_by_id(invitation_id: str) -> Optional[Invitation]:
    return await Invitation.get(invitation_id)


async def get_pending_for_org_email(
    *, organization_id: str, email: str
) -> Optional[Invitation]:
    return await Invitation.find_one(
        Invitation.organization_id == organization_id,
        Invitation.email == email.lower(),
        Invitation.status == InvitationStatus.PENDING.value,
    )


async def list_for_org(
    organization_id: str,
    *,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Invitation]:
    q = Invitation.find(Invitation.organization_id == organization_id)
    if status:
        q = q.find(Invitation.status == status)
    return await q.skip(skip).limit(limit).to_list()


async def create(
    *,
    organization_id: str,
    email: str,
    role: str = OrgRole.MEMBER.value,
    invited_by_user_id: str,
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
    await invite.insert()
    return invite


async def accept(
    invite: Invitation, *, accepted_by_user_id: str
) -> Invitation:
    invite.status = InvitationStatus.ACCEPTED.value
    invite.accepted_at = datetime.now(UTC)
    invite.accepted_by_user_id = accepted_by_user_id
    await invite.save()
    return invite


async def revoke(invite: Invitation) -> Invitation:
    invite.status = InvitationStatus.REVOKED.value
    await invite.save()
    return invite


{%- else %}
"""Invitation repository — not configured."""
{%- endif %}
{%- else %}
"""Invitation repository — not configured (enable_teams=false)."""
{%- endif %}
