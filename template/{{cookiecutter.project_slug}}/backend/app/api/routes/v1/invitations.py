{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, InvitationSvc
from app.schemas.organization import (
    InvitationCreate,
    InvitationList,
    InvitationRead,
)

org_router = APIRouter()
token_router = APIRouter()


@org_router.post("/{org_id}/invitations", response_model=InvitationRead, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    org_id: UUID,
    data: InvitationCreate,
    service: InvitationSvc,
    user: CurrentUser,
) -> Any:
    """Invite a user to the organization by email. Requires Owner or Admin."""
    invite = await service.invite(org_id, data.email, data.role, requester_id=user.id)
    return InvitationRead(
        id=invite.id,
        organization_id=invite.organization_id,
        email=invite.email,
        role=invite.role,
        status=invite.status,
        token=invite.token,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@org_router.get("/{org_id}/invitations", response_model=InvitationList)
async def list_invitations(
    org_id: UUID,
    service: InvitationSvc,
    user: CurrentUser,
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
) -> Any:
    """List invitations for an organization. Requires Owner or Admin."""
    invites = await service.list_for_org(
        org_id, user.id, status=status_filter, skip=skip, limit=limit
    )
    items = [
        InvitationRead(
            id=inv.id,
            organization_id=inv.organization_id,
            email=inv.email,
            role=inv.role,
            status=inv.status,
            token=inv.token,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )
        for inv in invites
    ]
    return InvitationList(items=items, total=len(items))


@token_router.post("/invitations/{token}/accept", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def accept_invitation(
    token: str,
    service: InvitationSvc,
    user: CurrentUser,
) -> None:
    """Accept an invitation token. Adds the current user to the organization."""
    await service.accept(token, accepting_user_id=user.id)


@token_router.delete("/invitations/{token}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def revoke_invitation(
    token: str,
    service: InvitationSvc,
    user: CurrentUser,
) -> None:
    """Revoke a pending invitation. Owner/Admin of the org, or the invitee themselves."""
    await service.revoke(token, requester_id=user.id)


{%- else %}
"""Invitation routes — not configured (enable_teams=false or no JWT)."""

from fastapi import APIRouter

org_router = APIRouter()
token_router = APIRouter()
{%- endif %}
