{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
"""Project service (PostgreSQL async).

Business logic for project management, member access control, and Docker
volume lifecycle when the docker backend is configured.
"""

import logging
from uuid import UUID, uuid4 as _uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AlreadyExistsError, AuthorizationError, NotFoundError
from app.db.models.project import Project, ProjectMember
from app.repositories import project_repo
from app.schemas.project import ProjectCreate, ProjectMemberCreate, ProjectMemberUpdate, ProjectUpdate

logger = logging.getLogger(__name__)

# Role ordering — higher index = more permissions
_ROLE_ORDER = ["viewer", "editor", "admin"]


def _role_gte(role: str, min_role: str) -> bool:
    """Return True if role has at least the permissions of min_role."""
    try:
        return _ROLE_ORDER.index(role) >= _ROLE_ORDER.index(min_role)
    except ValueError:
        return False


class ProjectService:
    """Service for project management business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _make_names(self, project_id: str) -> tuple[str, str]:
        """Generate stable container and volume names for a project."""
        return f"pd-{project_id}", f"pd-vol-{project_id}"

    def _create_docker_volume(self, volume_name: str) -> None:
        """Create a Docker volume for the project (lazy — only if docker backend)."""
        if settings.PYDANTIC_DEEP_BACKEND_TYPE != "docker":
            return
        try:
            import docker  # type: ignore[import]

            client = docker.from_env()
            existing = [v.name for v in client.volumes.list()]
            if volume_name not in existing:
                client.volumes.create(name=volume_name)
                logger.info("Created Docker volume %s", volume_name)
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not create Docker volume %s: %s", volume_name, exc)

    def _remove_docker_resources(self, container_name: str, volume_name: str) -> None:
        """Stop & remove container and volume when a project is deleted."""
        if settings.PYDANTIC_DEEP_BACKEND_TYPE != "docker":
            return
        try:
            import docker  # type: ignore[import]

            client = docker.from_env()
            try:
                container = client.containers.get(container_name)
                container.stop(timeout=5)
                container.remove(force=True)
                logger.info("Removed Docker container %s", container_name)
            except docker.errors.NotFound:
                pass
            try:
                volume = client.volumes.get(volume_name)
                volume.remove(force=True)
                logger.info("Removed Docker volume %s", volume_name)
            except docker.errors.NotFound:
                pass
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not remove Docker resources for %s: %s", container_name, exc)

    async def create(self, data: ProjectCreate, *, owner_id: UUID) -> Project:
        """Create a project and provision its Docker volume."""
        project_id = _uuid4()
        container_name, volume_name = self._make_names(str(project_id))
        project = await project_repo.create_project(
            self.db,
            project_id=project_id,
            owner_id=owner_id,
            name=data.name,
            description=data.description,
            image=data.image,
            container_name=container_name,
            volume_name=volume_name,
        )
        self._create_docker_volume(volume_name)
        return project

    async def get(self, project_id: UUID, *, user_id: UUID | None = None) -> Project:
        """Get a project by ID, optionally verifying read access.

        Raises:
            NotFoundError: If the project does not exist.
            AuthorizationError: If user_id is given and has no access.
        """
        project = await project_repo.get_project_by_id(self.db, project_id)
        if not project:
            raise NotFoundError(
                message="Project not found",
                details={"project_id": str(project_id)},
            )
        if user_id is not None:
            await self._assert_access(project, user_id, min_role="viewer")
        return project

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = False,
    ) -> tuple[list[Project], int]:
        """List projects accessible to a user (owned + member)."""
        items = await project_repo.get_projects_for_user(
            self.db, user_id, skip=skip, limit=limit, include_archived=include_archived
        )
        total = await project_repo.count_projects_for_user(
            self.db, user_id, include_archived=include_archived
        )
        return items, total

    async def update(
        self, project_id: UUID, data: ProjectUpdate, *, user_id: UUID
    ) -> Project:
        """Update a project. Requires admin role or ownership."""
        project = await self.get(project_id)
        await self._assert_access(project, user_id, min_role="admin")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return project
        return await project_repo.update_project(
            self.db, db_project=project, update_data=update_data
        )

    async def archive(self, project_id: UUID, *, user_id: UUID) -> Project:
        """Archive (soft-delete) a project. Only owner can archive."""
        project = await self.get(project_id)
        if project.owner_id != user_id:
            raise AuthorizationError(message="Only the project owner can archive it")
        result = await project_repo.archive_project(self.db, project_id)
        if not result:
            raise NotFoundError(message="Project not found", details={"project_id": str(project_id)})
        return result

    async def delete(self, project_id: UUID, *, user_id: UUID) -> None:
        """Hard-delete a project and its Docker resources. Only owner can delete."""
        project = await self.get(project_id)
        if project.owner_id != user_id:
            raise AuthorizationError(message="Only the project owner can delete it")
        container_name = project.container_name
        volume_name = project.volume_name
        await project_repo.delete_project(self.db, project_id)
        self._remove_docker_resources(container_name, volume_name)

    async def list_members(
        self, project_id: UUID, *, user_id: UUID
    ) -> list[ProjectMember]:
        """List members of a project. Requires viewer access."""
        project = await self.get(project_id)
        await self._assert_access(project, user_id, min_role="viewer")
        return await project_repo.get_project_members(self.db, project_id)

    async def add_member(
        self,
        project_id: UUID,
        data: ProjectMemberCreate,
        *,
        inviter_id: UUID,
    ) -> ProjectMember:
        """Add a member to a project. Requires admin role or ownership."""
        project = await self.get(project_id)
        await self._assert_access(project, inviter_id, min_role="admin")

        existing = await project_repo.get_project_member(
            self.db, project_id, data.user_id
        )
        if existing:
            raise AlreadyExistsError(
                message="User is already a project member",
                details={"user_id": str(data.user_id)},
            )
        # Owner cannot be added as a member
        if data.user_id == project.owner_id:
            raise AlreadyExistsError(
                message="Project owner already has full access",
                details={"user_id": str(data.user_id)},
            )

        return await project_repo.add_project_member(
            self.db,
            project_id=project_id,
            user_id=data.user_id,
            role=data.role,
            invited_by=inviter_id,
        )

    async def update_member(
        self,
        project_id: UUID,
        target_user_id: UUID,
        data: ProjectMemberUpdate,
        *,
        requester_id: UUID,
    ) -> ProjectMember:
        """Update a member's role. Requires admin role or ownership."""
        project = await self.get(project_id)
        await self._assert_access(project, requester_id, min_role="admin")

        member = await project_repo.get_project_member(self.db, project_id, target_user_id)
        if not member:
            raise NotFoundError(
                message="Member not found",
                details={"user_id": str(target_user_id)},
            )
        return await project_repo.update_member_role(
            self.db, db_member=member, role=data.role
        )

    async def remove_member(
        self,
        project_id: UUID,
        target_user_id: UUID,
        *,
        requester_id: UUID,
    ) -> None:
        """Remove a member from a project.

        Admin/owner can remove anyone; members can remove themselves.
        """
        project = await self.get(project_id)

        if target_user_id == requester_id:
            if project.owner_id == requester_id:
                raise AuthorizationError(message="Owner cannot leave the project")
        else:
            await self._assert_access(project, requester_id, min_role="admin")

        removed = await project_repo.remove_project_member(
            self.db, project_id, target_user_id
        )
        if not removed:
            raise NotFoundError(
                message="Member not found",
                details={"user_id": str(target_user_id)},
            )

    async def _assert_access(
        self,
        project: Project,
        user_id: UUID,
        *,
        min_role: str = "viewer",
    ) -> None:
        """Raise AuthorizationError if user does not have the required role.

        Owner always passes. Members are checked against their role.
        """
        if project.owner_id == user_id:
            return

        member = await project_repo.get_project_member(self.db, project.id, user_id)
        if not member or not _role_gte(member.role, min_role):
            raise AuthorizationError(
                message=f"Project access requires '{min_role}' role",
                details={"project_id": str(project.id)},
            )

    async def get_user_role(self, project_id: UUID, user_id: UUID) -> str | None:
        """Return the user's effective role in a project, or None if no access."""
        project = await project_repo.get_project_by_id(self.db, project_id)
        if not project:
            return None
        if project.owner_id == user_id:
            return "owner"
        member = await project_repo.get_project_member(self.db, project_id, user_id)
        return member.role if member else None


{%- else %}
"""Project service - requires use_pydantic_deep and use_jwt."""
{%- endif %}
