{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
"""Project repository (PostgreSQL async)."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.project import Project, ProjectMember


async def get_project_by_id(
    db: AsyncSession,
    project_id: UUID,
) -> Project | None:
    """Get project by ID."""
    return await db.get(Project, project_id)


async def get_projects_for_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
) -> list[Project]:
    """Get projects where user is owner or member."""
    member_project_ids = select(ProjectMember.project_id).where(
        ProjectMember.user_id == user_id
    )
    query = select(Project).where(
        or_(Project.owner_id == user_id, Project.id.in_(member_project_ids))
    )
    if not include_archived:
        query = query.where(Project.archived_at.is_(None))
    query = (
        query.order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_projects_for_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    include_archived: bool = False,
) -> int:
    """Count projects accessible to a user."""
    member_project_ids = select(ProjectMember.project_id).where(
        ProjectMember.user_id == user_id
    )
    query = select(func.count(Project.id)).where(
        or_(Project.owner_id == user_id, Project.id.in_(member_project_ids))
    )
    if not include_archived:
        query = query.where(Project.archived_at.is_(None))
    result = await db.execute(query)
    return result.scalar() or 0


async def create_project(
    db: AsyncSession,
    *,
    project_id: UUID | None = None,
    owner_id: UUID,
    name: str,
    description: str | None = None,
    image: str = "python:3.12-slim",
    container_name: str,
    volume_name: str,
) -> Project:
    """Create a new project record."""
    project = Project(
        owner_id=owner_id,
        name=name,
        description=description,
        image=image,
        container_name=container_name,
        volume_name=volume_name,
    )
    if project_id is not None:
        project.id = project_id
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


async def update_project(
    db: AsyncSession,
    *,
    db_project: Project,
    update_data: dict[str, Any],
) -> Project:
    """Update project fields."""
    for field, value in update_data.items():
        setattr(db_project, field, value)
    db.add(db_project)
    await db.flush()
    await db.refresh(db_project)
    return db_project


async def archive_project(
    db: AsyncSession,
    project_id: UUID,
) -> Project | None:
    """Soft-delete a project by setting archived_at."""
    project = await get_project_by_id(db, project_id)
    if project:
        project.archived_at = datetime.now(UTC)
        db.add(project)
        await db.flush()
        await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: UUID) -> bool:
    """Hard-delete a project (cascades to members and conversations)."""
    project = await get_project_by_id(db, project_id)
    if project:
        await db.delete(project)
        await db.flush()
        return True
    return False



async def get_project_member(
    db: AsyncSession,
    project_id: UUID,
    user_id: UUID,
) -> ProjectMember | None:
    """Get a specific project member record."""
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_project_members(
    db: AsyncSession,
    project_id: UUID,
) -> list[ProjectMember]:
    """Get all members of a project."""
    result = await db.execute(
        select(ProjectMember)
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.created_at.asc())
    )
    return list(result.scalars().all())


async def add_project_member(
    db: AsyncSession,
    *,
    project_id: UUID,
    user_id: UUID,
    role: str = "viewer",
    invited_by: UUID | None = None,
) -> ProjectMember:
    """Add a user to a project."""
    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=role,
        invited_by=invited_by,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def update_member_role(
    db: AsyncSession,
    *,
    db_member: ProjectMember,
    role: str,
) -> ProjectMember:
    """Update a member's role."""
    db_member.role = role
    db.add(db_member)
    await db.flush()
    await db.refresh(db_member)
    return db_member


async def remove_project_member(
    db: AsyncSession,
    project_id: UUID,
    user_id: UUID,
) -> bool:
    """Remove a user from a project."""
    member = await get_project_member(db, project_id, user_id)
    if member:
        await db.delete(member)
        await db.flush()
        return True
    return False


{%- else %}
"""Project repository - requires use_pydantic_deep and use_jwt."""
{%- endif %}
