{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Organization CRUD routes."""

import mimetypes
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, OrganizationSvc
from app.db.models.organization import OrgRole
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationList,
    OrganizationRead,
    OrganizationUpdate,
)

router = APIRouter()


def _build_org_read(org: Any, member_count: int, role: str) -> OrganizationRead:
    return OrganizationRead(
        id=org.id,
        name=org.name,
        slug=org.slug,
        is_personal=org.is_personal,
        avatar_url=org.avatar_url,
        member_count=member_count,
        role=role,
        created_at=org.created_at,
        updated_at=org.updated_at,
{%- if cookiecutter.enable_billing %}
        subscription_tier=getattr(org, "subscription_tier", "free"),
        credits_balance=getattr(org, "credits_balance", 0),
{%- endif %}
    )


@router.get("", response_model=OrganizationList)
async def list_organizations(
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
    """List all organizations the current user belongs to."""
    rows = await service.list_for_user(user.id)
    items = [
        _build_org_read(row["org"], row["member_count"], row["role"])
        for row in rows
    ]
    return OrganizationList(items=items, total=len(items))


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
    """Create a new organization. The requesting user becomes Owner."""
    org = await service.create(data, owner_id=user.id)
    return _build_org_read(org, member_count=1, role=OrgRole.OWNER.value)


@router.get("/{org_id}", response_model=OrganizationRead)
async def get_organization(
    org_id: UUID,
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
    """Get a single organization the current user is a member of."""
    org, membership = await service.get_for_user(org_id, user.id)
    member_count = await service.get_member_count(org_id)
    return _build_org_read(org, member_count, membership.role)


@router.patch("/{org_id}", response_model=OrganizationRead)
async def update_organization(
    org_id: UUID,
    data: OrganizationUpdate,
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
    """Update organization name or avatar. Requires Admin or Owner role."""
    org = await service.update(org_id, data, requester_id=user.id)
    rows = await service.list_for_user(user.id)
    member_count = next((r["member_count"] for r in rows if r["org"].id == org.id), 0)
    role = next((r["role"] for r in rows if r["org"].id == org.id), "member")
    return _build_org_read(org, member_count, role)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_organization(
    org_id: UUID,
    service: OrganizationSvc,
    user: CurrentUser,
) -> None:
    """Delete an organization. Requires Owner role. Personal orgs cannot be deleted."""
    await service.delete(org_id, requester_id=user.id)


@router.post("/{org_id}/avatar", response_model=OrganizationRead)
async def upload_organization_avatar(
    org_id: UUID,
    service: OrganizationSvc,
    user: CurrentUser,
    file: UploadFile = File(...),
) -> Any:
    """Upload or replace the organization avatar. Requires Admin or Owner role."""
    data = await file.read()
    updated = await service.upload_avatar(
        org_id,
        requester_id=user.id,
        file_data=data,
        filename=file.filename or "avatar.jpg",
        content_type=file.content_type,
    )
    rows = await service.list_for_user(user.id)
    member_count = next((r["member_count"] for r in rows if r["org"].id == updated.id), 0)
    role = next((r["role"] for r in rows if r["org"].id == updated.id), "member")
    return _build_org_read(updated, member_count, role)


@router.get("/{org_id}/avatar", response_model=None)
async def get_organization_avatar(
    org_id: UUID,
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
    """Stream the organization avatar image. Membership is required to view."""
    org, _ = await service.get_for_user(org_id, user.id)
    if not org.avatar_url:
        raise HTTPException(status_code=404, detail="No avatar set")
    file_path = service.get_avatar_path(org.avatar_url)
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Avatar file missing")
    media_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    return FileResponse(path=file_path, media_type=media_type)


{%- else %}
"""Organization routes — not configured (enable_teams=false or no JWT)."""
{%- endif %}
