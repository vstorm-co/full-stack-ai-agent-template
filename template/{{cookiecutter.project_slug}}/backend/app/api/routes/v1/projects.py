{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
"""Project management routes — CRUD and member management for DeepAgents projects."""

from typing import Any
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, ProjectSvc
from app.schemas.project import (
    ProjectCreate,
    ProjectList,
    ProjectMemberCreate,
    ProjectMemberList,
    ProjectMemberRead,
    ProjectMemberUpdate,
    ProjectRead,
    ProjectUpdate,
)

router = APIRouter()


# Project CRUD


@router.get("", response_model=ProjectList)
async def list_projects(
    service: ProjectSvc,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
    include_archived: bool = Query(False, description="Include archived projects"),
) -> Any:
    """List all projects accessible to the current user (owned + member)."""
    items, total = await service.list_for_user(
{%- if cookiecutter.use_postgresql %}
        user.id,
{%- else %}
        str(user.id),
{%- endif %}
        skip=skip,
        limit=limit,
        include_archived=include_archived,
    )
    return ProjectList(items=items, total=total)  # ty: ignore[invalid-argument-type]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    service: ProjectSvc,
    user: CurrentUser,
) -> Any:
    """Create a new project. A Docker volume is provisioned on creation."""
    return await service.create(data, owner_id=user.id)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
{%- if cookiecutter.use_postgresql %}
    project_id: UUID,
{%- else %}
    project_id: str,
{%- endif %}
    service: ProjectSvc,
    user: CurrentUser,
) -> Any:
    """Get a project by ID. Requires at least viewer access."""
    return await service.get(project_id, user_id=user.id)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
{%- if cookiecutter.use_postgresql %}
    project_id: UUID,
{%- else %}
    project_id: str,
{%- endif %}
    data: ProjectUpdate,
    service: ProjectSvc,
    user: CurrentUser,
) -> Any:
    """Update a project. Requires admin role or ownership."""
    return await service.update(project_id, data, user_id=user.id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_project(
{%- if cookiecutter.use_postgresql %}
    project_id: UUID,
{%- else %}
    project_id: str,
{%- endif %}
    service: ProjectSvc,
    user: CurrentUser,
) -> None:
    """Delete a project permanently (removes Docker container and volume).

    Only the project owner can delete it.
    """
    await service.delete(project_id, user_id=user.id)


@router.post("/{project_id}/archive", response_model=ProjectRead)
async def archive_project(
{%- if cookiecutter.use_postgresql %}
    project_id: UUID,
{%- else %}
    project_id: str,
{%- endif %}
    service: ProjectSvc,
    user: CurrentUser,
) -> Any:
    """Archive a project (soft-delete). Only the owner can archive."""
    return await service.archive(project_id, user_id=user.id)


# Member Management


@router.get("/{project_id}/members", response_model=ProjectMemberList)
async def list_members(
{%- if cookiecutter.use_postgresql %}
    project_id: UUID,
{%- else %}
    project_id: str,
{%- endif %}
    service: ProjectSvc,
    user: CurrentUser,
) -> Any:
    """List all members of a project. Requires viewer access."""
    members = await service.list_members(project_id, user_id=user.id)
    return ProjectMemberList(items=members, total=len(members))  # ty: ignore[invalid-argument-type]


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
{%- if cookiecutter.use_postgresql %}
    project_id: UUID,
{%- else %}
    project_id: str,
{%- endif %}
    data: ProjectMemberCreate,
    service: ProjectSvc,
    user: CurrentUser,
) -> Any:
    """Add a user to a project. Requires admin role or ownership."""
    return await service.add_member(project_id, data, inviter_id=user.id)


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberRead)
async def update_member(
{%- if cookiecutter.use_postgresql %}
    project_id: UUID,
    user_id: UUID,
{%- else %}
    project_id: str,
    user_id: str,
{%- endif %}
    data: ProjectMemberUpdate,
    service: ProjectSvc,
    user: CurrentUser,
) -> Any:
    """Update a member's role. Requires admin role or ownership."""
    return await service.update_member(
        project_id, user_id, data, requester_id=user.id
    )


@router.delete(
    "/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_member(
{%- if cookiecutter.use_postgresql %}
    project_id: UUID,
    user_id: UUID,
{%- else %}
    project_id: str,
    user_id: str,
{%- endif %}
    service: ProjectSvc,
    user: CurrentUser,
) -> None:
    """Remove a member from a project.

    Members can remove themselves. Admin/owner can remove anyone.
    """
    await service.remove_member(project_id, user_id, requester_id=user.id)
{%- else %}
"""Project routes - requires use_pydantic_deep and use_jwt."""
{%- endif %}
