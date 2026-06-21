{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Member management routes (nested under /orgs/{org_id}/members)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, MemberSvc
from app.schemas.organization import (
    OrganizationMemberList,
    OrganizationMemberRead,
    OrganizationMemberUpdate,
    TransferOwnershipRequest,
)

router = APIRouter()


@router.get("/{org_id}/members", response_model=OrganizationMemberList)
async def list_members(
    org_id: UUID,
    service: MemberSvc,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
) -> Any:
    """List members of an organization. Any member may call this."""
    rows, total = await service.list_for_org(org_id, user.id, skip=skip, limit=limit)
    items = [
        OrganizationMemberRead(
            id=m.id,
            organization_id=m.organization_id,
            user_id=m.user_id,
            role=m.role,
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
            joined_at=m.joined_at,
        )
        for m, email, full_name, avatar_url in rows
    ]
    return OrganizationMemberList(items=items, total=total)


@router.patch("/{org_id}/members/{target_user_id}", response_model=OrganizationMemberRead)
async def update_member_role(
    org_id: UUID,
    target_user_id: UUID,
    data: OrganizationMemberUpdate,
    service: MemberSvc,
    user: CurrentUser,
) -> Any:
    """Change a member's role. Requires Owner or Admin."""
    member, email, full_name, avatar_url = await service.change_role(org_id, target_user_id, data.role, requester_id=user.id)
    return OrganizationMemberRead(
        id=member.id,
        organization_id=member.organization_id,
        user_id=member.user_id,
        role=member.role,
        email=email,
        full_name=full_name,
        avatar_url=avatar_url,
        joined_at=member.joined_at,
    )


@router.delete(
    "/{org_id}/members/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_member(
    org_id: UUID,
    target_user_id: UUID,
    service: MemberSvc,
    user: CurrentUser,
) -> None:
    """Remove a member from the organization. Requires Owner or Admin."""
    await service.remove(org_id, target_user_id, requester_id=user.id)


@router.post("/{org_id}/leave", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def leave_organization(
    org_id: UUID,
    service: MemberSvc,
    user: CurrentUser,
) -> None:
    """Leave an organization. Owner must transfer ownership first if others remain."""
    await service.leave(org_id, requester_id=user.id)


@router.post("/{org_id}/transfer-ownership", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def transfer_ownership(
    org_id: UUID,
    data: TransferOwnershipRequest,
    service: MemberSvc,
    user: CurrentUser,
) -> None:
    """Transfer Owner role to another member. Caller becomes Admin."""
    await service.transfer_ownership(org_id, data.new_owner_user_id, requester_id=user.id)


{%- else %}
"""Member routes — not configured (enable_teams=false or no JWT)."""
{%- endif %}
