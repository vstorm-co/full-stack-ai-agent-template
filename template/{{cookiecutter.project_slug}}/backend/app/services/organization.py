{%- if cookiecutter.enable_teams %}
import contextlib
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AlreadyExistsError, AuthorizationError, BadRequestError, NotFoundError
from app.db.models.organization import OrgRole, Organization, OrganizationMember
from app.repositories import invitation_repo, member_repo, organization_repo
from app.schemas.organization import OrganizationCreate, OrganizationRead, OrganizationUpdate
from app.services.file_storage import get_file_storage
{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
from app.services.billing.credit_service import CreditService
{%- endif %}

logger = logging.getLogger(__name__)


class OrganizationService:
    _ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, org_id: UUID) -> Organization:
        org = await organization_repo.get_by_id(self.db, org_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": str(org_id)})
        return org

    async def get_for_user(self, org_id: UUID, user_id: UUID) -> tuple[Organization, OrganizationMember]:
        """Get org and verify current user is a member. Returns (org, membership)."""
        membership = await member_repo.get(self.db, organization_id=org_id, user_id=user_id)
        if not membership:
            raise NotFoundError(message="Organization not found", details={"org_id": str(org_id)})
        org = await organization_repo.get_by_id(self.db, org_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": str(org_id)})
        return org, membership

    async def get_member_count(self, org_id: UUID) -> int:
        return await organization_repo.count_members(self.db, org_id)

    async def list_for_user(self, user_id: UUID) -> list[dict]:
        orgs = await organization_repo.list_for_user(self.db, user_id)
        result = []
        for org in orgs:
            membership = await member_repo.get(self.db, organization_id=org.id, user_id=user_id)
            count = await organization_repo.count_members(self.db, org.id)
            result.append({
                "org": org,
                "role": membership.role if membership else OrgRole.MEMBER.value,
                "member_count": count,
            })
        return result

    async def create(self, data: OrganizationCreate, owner_id: UUID) -> Organization:
        """Create a new team organization (non-personal)."""
        slug = data.slug
        if slug:
            if await organization_repo.slug_exists(self.db, slug):
                raise AlreadyExistsError(
                    message="Slug already taken",
                    details={"slug": slug},
                )
        else:
            slug = await organization_repo.generate_unique_slug(self.db, data.name)

        org = await organization_repo.create(
            self.db,
            name=data.name,
            slug=slug,
            created_by_user_id=owner_id,
            is_personal=False,
        )
        await member_repo.create(
            self.db,
            organization_id=org.id,
            user_id=owner_id,
            role=OrgRole.OWNER.value,
        )
        return org

    async def create_personal_org(self, user_id: UUID, email: str) -> Organization:
        """Create the Personal Organization for a newly registered user.

        Also grants the configured free-tier credit bonus so AI usage works on
        the free plan up to the granted amount.
        """
        slug = await organization_repo.generate_unique_slug(self.db, email.split("@")[0])
        org = await organization_repo.create(
            self.db,
            name="Personal",
            slug=slug,
            created_by_user_id=user_id,
            is_personal=True,
        )
        await member_repo.create(
            self.db,
            organization_id=org.id,
            user_id=user_id,
            role=OrgRole.OWNER.value,
        )
{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
        if settings.CREDITS_FREE_TIER_GRANT > 0:
            try:
                await CreditService(self.db).grant_signup_bonus(organization_id=org.id)
            except Exception:
                logger.exception(
                    "free_tier_grant_failed", extra={"org_id": str(org.id)}
                )
{%- endif %}
        return org

    async def update(
        self,
        org_id: UUID,
        data: OrganizationUpdate,
        requester_id: UUID,
    ) -> Organization:
        """Update org metadata. Requires ADMIN or OWNER role."""
        org, membership = await self.get_for_user(org_id, requester_id)
        if membership.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
            raise AuthorizationError(message="Only Owner or Admin can update the organization")

        return await organization_repo.update(
            self.db,
            org,
            name=data.name,
            avatar_url=data.avatar_url,
        )

    async def delete(self, org_id: UUID, requester_id: UUID) -> None:
        """Delete org. Requires OWNER role. Personal orgs cannot be deleted."""
        org, membership = await self.get_for_user(org_id, requester_id)

        if org.is_personal:
            raise BadRequestError(message="Personal organization cannot be deleted")
        if membership.role != OrgRole.OWNER.value:
            raise AuthorizationError(message="Only the Owner can delete the organization")

        await organization_repo.delete(self.db, org)

    async def upload_avatar(
        self,
        org_id: UUID,
        requester_id: UUID,
        file_data: bytes,
        filename: str,
        content_type: str | None,
    ) -> Organization:
        """Replace the organization avatar. Requires ADMIN or OWNER role.

        Raises:
            BadRequestError: If file type or size is invalid.
            AuthorizationError: If requester is not Owner or Admin.
        """
        if content_type not in self._ALLOWED_AVATAR_TYPES:
            raise BadRequestError(message="Only JPEG, PNG, WebP, and GIF images are allowed")
        if len(file_data) > 2 * 1024 * 1024:
            raise BadRequestError(message="Avatar image too large. Maximum 2MB.")

        org, membership = await self.get_for_user(org_id, requester_id)
        if membership.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
            raise AuthorizationError(message="Only Owner or Admin can update the org")

        storage = get_file_storage()
        if org.avatar_url:
            with contextlib.suppress(Exception):
                await storage.delete(org.avatar_url)
        storage_path = await storage.save(f"avatars/orgs/{org_id}", filename, file_data)
        return await organization_repo.update(self.db, org, avatar_url=storage_path)

    def get_avatar_path(self, avatar_url: str) -> str | None:
        return get_file_storage().get_full_path(avatar_url)


{%- else %}
"""Organization service — not configured (enable_teams=false)."""
{%- endif %}
