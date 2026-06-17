"""User service (PostgreSQL async).

Contains business logic for user operations. Uses UserRepository for database access.
"""

import logging
from typing import TYPE_CHECKING, Any

{%- if cookiecutter.use_postgresql %}
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Postgres primary keys are UUIDs.
UserId = UUID
{%- elif cookiecutter.use_sqlite %}
from sqlalchemy import func, select
from sqlalchemy.orm import Session

# SQLite stores UUIDs as text, so IDs flow through the service as ``str``.
UserId = str
{%- else %}
# MongoDB document ids are strings.
UserId = str
{%- endif %}

from app.core.config import settings
from app.core.exceptions import AlreadyExistsError, AuthenticationError, NotFoundError
from app.core.security import (
    create_magic_link_token,
    create_password_reset_token,
    get_password_hash,
    verify_password,
    verify_special_token,
)
from app.db.models.user import User, UserRole
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
from app.repositories import session_repo, user_repo
{%- else %}
from app.repositories import user_repo
{%- endif %}
from app.schemas.user import UserCreate, UserUpdate
{%- if cookiecutter.enable_email %}
from app.services.email.service import get_email_service
{%- endif %}
{%- if cookiecutter.enable_teams %}
from app.services.organization import OrganizationService
{%- endif %}

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.schemas.conversation_share import AdminUserList


class UserService:
    """Service for user-related business logic."""

{%- if cookiecutter.use_postgresql %}
    def __init__(self, db: AsyncSession):
        self.db = db
{%- elif cookiecutter.use_sqlite %}
    def __init__(self, db: Session):
        self.db = db
{%- else %}
    def __init__(self, db: Any = None):
        self.db = db
{%- endif %}

{%- if cookiecutter.use_sqlite %}
    async def _repo(self, func, /, *args, **kwargs):
        """Invoke a sync SQLite repo function from async context."""
        return func(self.db, *args, **kwargs)
{%- elif cookiecutter.use_mongodb %}
    async def _repo(self, func, /, *args, **kwargs):
        """Invoke an async MongoDB repo function (no db session)."""
        return await func(*args, **kwargs)
{%- else %}
    async def _repo(self, func, /, *args, **kwargs):
        """Invoke an async PostgreSQL repo function with the session."""
        return await func(self.db, *args, **kwargs)
{%- endif %}

    async def get_by_id(self, user_id: UserId) -> User:
        """Get user by ID.

        Raises:
            NotFoundError: If user does not exist.
        """
        user = await self._repo(user_repo.get_by_id, user_id)
        if not user:
            raise NotFoundError(
                message="User not found",
                details={"user_id": user_id},
            )
        return user

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email. Returns None if not found."""
        return await self._repo(user_repo.get_by_email, email)

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """Get multiple users with pagination."""
        return await self._repo(user_repo.get_multi, skip=skip, limit=limit)

    async def list_paginated(self) -> Any:
        """Return paginated user list (fastapi-pagination Page)."""
{%- if cookiecutter.use_mongodb %}
        from fastapi_pagination.ext.beanie import apaginate

        return await apaginate(User)  # ty: ignore[invalid-argument-type]
{%- else %}
        from fastapi_pagination.ext.sqlalchemy import paginate

        return await paginate(self.db, user_repo.list_query())
{%- endif %}

    async def delete_non_admins(self) -> int:
        """Bulk-delete users without the admin role. Returns affected row count."""
        return await self._repo(user_repo.delete_non_admins)

    async def has_any(self) -> bool:
        """Return True if at least one user exists."""
        return await self._repo(user_repo.has_any)

    async def admin_list_with_counts(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> "AdminUserList":
        """Admin: list users with conversation counts."""
        from app.schemas.conversation_share import AdminUserList, AdminUserRead

        rows, total = await self._repo(
            user_repo.admin_list_with_counts,
            skip=skip,
            limit=limit,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        items = [
            AdminUserRead(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
                is_app_admin=getattr(user, "is_app_admin", False),
                conversation_count=conv_count,
                created_at=user.created_at,
            )
            for user, conv_count in rows
        ]
        return AdminUserList(items=items, total=total)

    async def register(self, user_in: UserCreate) -> User:
        """Register a new user.

        The very first user to register is auto-promoted to app-admin so that a
        fresh deployment has someone who can reach the /admin pages without an
        extra CLI step.

        Raises:
            AlreadyExistsError: If email is already registered.
        """
        existing = await self._repo(user_repo.get_by_email, user_in.email)
        if existing:
            raise AlreadyExistsError(
                message="Email already registered",
                details={"email": user_in.email},
            )

{%- if cookiecutter.use_postgresql %}
        existing_count = (
            await self.db.execute(select(func.count()).select_from(User))
        ).scalar_one()
        is_first_user = existing_count == 0
{%- elif cookiecutter.use_sqlite %}
        existing_count = self.db.execute(select(func.count()).select_from(User)).scalar_one()
        is_first_user = existing_count == 0
{%- else %}
        is_first_user = not await user_repo.has_any()
{%- endif %}

        hashed_password = get_password_hash(user_in.password)
        user = await self._repo(
            user_repo.create,
            email=user_in.email,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            role=UserRole.ADMIN.value if is_first_user else user_in.role.value,
            is_app_admin=is_first_user,
        )
{%- if cookiecutter.enable_teams %}
{%- if cookiecutter.use_mongodb %}
        org_service = OrganizationService()
        await org_service.create_personal_org(str(user.id), user_in.email)
{%- elif cookiecutter.use_sqlite %}
        org_service = OrganizationService(self.db)
        org_service.create_personal_org(user.id, user_in.email)
{%- else %}
        org_service = OrganizationService(self.db)
        await org_service.create_personal_org(user.id, user_in.email)
{%- endif %}
{%- endif %}
{%- if cookiecutter.enable_email %}
        try:
            login_url = settings.FRONTEND_URL.rstrip("/") + "/login"
            await get_email_service().send_welcome(
                to=user.email,
                name=user.full_name or user.email,
                login_url=login_url,
            )
        except Exception:
            logger.exception("welcome_email_failed", extra={"user_id": str(user.id)})
{%- endif %}
        return user

{%- if cookiecutter.enable_oauth %}

{%- if cookiecutter.use_delegated_auth %}
    async def get_or_create_from_idp(
        self,
        *,
        external_user_id: str,
        email: str,
        full_name: str | None = None,
    ) -> User:
        """Auto-provision a local row for a delegated-auth IdP user.

        Lookup order:
        1. ``external_user_id`` (stable, IdP-issued) — fast path on every
           subsequent request.
        2. ``email`` — for users that pre-existed in the local DB before
           switching to delegated auth (e.g., migrated SaaS).
        3. Create new row + personal org + welcome email (best-effort).
        """
        existing = await self._repo(user_repo.get_by_external_user_id, external_user_id)
        if existing:
            return existing

        by_email = await self._repo(user_repo.get_by_email, email)
        if by_email is not None:
            await self._repo(
                user_repo.update,
                db_user=by_email,
                update_data={"external_user_id": external_user_id},
            )
            return by_email

        existing_count = (
            await self.db.execute(select(func.count()).select_from(User))
        ).scalar_one()
        is_first_user = existing_count == 0

        user = await self._repo(
            user_repo.create,
            email=email,
            hashed_password=None,
            full_name=full_name,
            external_user_id=external_user_id,
            role=UserRole.ADMIN.value if is_first_user else UserRole.USER.value,
            is_app_admin=is_first_user,
        )
{%- if cookiecutter.enable_teams %}
{%- if cookiecutter.use_mongodb %}
        org_service = OrganizationService()
        await org_service.create_personal_org(str(user.id), user.email)
{%- elif cookiecutter.use_sqlite %}
        org_service = OrganizationService(self.db)
        org_service.create_personal_org(user.id, user.email)
{%- else %}
        org_service = OrganizationService(self.db)
        await org_service.create_personal_org(user.id, user.email)
{%- endif %}
{%- endif %}
        return user

{%- endif %}
    async def get_or_create_oauth_user(
        self,
        *,
        provider: str,
        provider_id: str,
        email: str,
        full_name: str | None = None,
    ) -> User:
        """Find an existing OAuth user by (provider, provider_id), or create one.

        If a user already has the email but no OAuth link, the OAuth identity is
        attached to that account. New users get a Personal organization and a
        welcome email (best-effort).
        """
        existing = await self._repo(user_repo.get_by_oauth, provider, provider_id)
        if existing:
            return existing

        by_email = await self._repo(user_repo.get_by_email, email)
        if by_email is not None:
            await self._repo(
                user_repo.update,
                db_user=by_email,
                update_data={"oauth_provider": provider, "oauth_id": provider_id},
            )
            return by_email

        user = await self._repo(
            user_repo.create,
            email=email,
            hashed_password=None,
            full_name=full_name,
            oauth_provider=provider,
            oauth_id=provider_id,
        )
{%- if cookiecutter.enable_teams %}
{%- if cookiecutter.use_mongodb %}
        org_service = OrganizationService()
        await org_service.create_personal_org(str(user.id), user.email)
{%- elif cookiecutter.use_sqlite %}
        org_service = OrganizationService(self.db)
        org_service.create_personal_org(user.id, user.email)
{%- else %}
        org_service = OrganizationService(self.db)
        await org_service.create_personal_org(user.id, user.email)
{%- endif %}
{%- endif %}
{%- if cookiecutter.enable_email %}
        try:
            login_url = settings.FRONTEND_URL.rstrip("/") + "/login"
            await get_email_service().send_welcome(
                to=user.email,
                name=user.full_name or user.email,
                login_url=login_url,
            )
        except Exception:
            logger.exception("welcome_email_failed", extra={"user_id": str(user.id)})
{%- endif %}
        return user
{%- endif %}

    async def authenticate(self, email: str, password: str) -> User:
        """Authenticate user by email and password.

        Raises:
            AuthenticationError: If credentials are invalid or user is inactive.
        """
        user = await self._repo(user_repo.get_by_email, email)
        if (
            not user
            or not user.hashed_password
            or not verify_password(password, user.hashed_password)
        ):
            raise AuthenticationError(message="Invalid email or password")
        if not user.is_active:
            raise AuthenticationError(message="User account is disabled")
        return user

    async def update(self, user_id: UserId, user_in: UserUpdate) -> User:
        """Update user.

        Raises:
            NotFoundError: If user does not exist.
        """
        user = await self.get_by_id(user_id)

        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        return await self._repo(user_repo.update, db_user=user, update_data=update_data)

    async def update_avatar(
        self, user_id: UserId, file_data: bytes, filename: str, content_type: str
    ) -> User:
        """Upload or replace avatar image.

        Raises:
            ValueError: If content type is not allowed or file is too large.
        """
        import contextlib

        from app.services.file_storage import get_file_storage

        ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        if content_type not in ALLOWED_AVATAR_TYPES:
            raise ValueError("Only JPEG, PNG, WebP, and GIF images are allowed")
        if len(file_data) > 2 * 1024 * 1024:
            raise ValueError("Avatar image too large. Maximum 2MB.")

        storage = get_file_storage()

        # Delete old avatar if exists
        user = await self.get_by_id(user_id)
        if user.avatar_url:
            with contextlib.suppress(Exception):
                await storage.delete(user.avatar_url)

        # Save new avatar
        storage_path = await storage.save(f"avatars/{user_id}", filename, file_data)
        return await self._repo(user_repo.update, db_user=user, update_data={"avatar_url": storage_path})

    async def delete(self, user_id: UserId) -> User:
        """Delete user.

        Raises:
            NotFoundError: If user does not exist.
        """
        user = await self._repo(user_repo.delete, user_id)
        if not user:
            raise NotFoundError(
                message="User not found",
                details={"user_id": str(user_id)},
            )
        return user

    # ------------------------------------------------------------------
    # Password reset flow
    # ------------------------------------------------------------------

    async def issue_password_reset_token(self, email: str) -> tuple[User, str] | None:
        """Issue a short-lived JWT for the user with this email, or return None
        if no such user exists.

        Caller should email the token to the user as part of a reset URL.
        Returning None lets the route degrade gracefully without leaking
        existence — the public API always returns the same "if an account
        exists, you'll get a link" response.
        """
        user = await self._repo(user_repo.get_by_email, email)
        if user is None or not user.is_active:
            return None
        token = create_password_reset_token(subject=str(user.id))
        return user, token

    async def confirm_password_reset(self, token: str, new_password: str) -> User:
        """Verify the reset token and set a new password.

        Raises AuthenticationError if the token is invalid, expired, or of
        the wrong type. NotFoundError if the user disappeared between issuing
        and confirming.
        """
        payload = verify_special_token(token, expected_type="password_reset")
        if payload is None or "sub" not in payload:
            raise AuthenticationError(message="Reset link is invalid or has expired")
{%- if cookiecutter.use_postgresql %}
        try:
            user_id = UUID(str(payload["sub"]))
        except (TypeError, ValueError) as exc:
            raise AuthenticationError(
                message="Reset link is invalid or has expired"
            ) from exc
{%- else %}
        user_id = str(payload["sub"])
{%- endif %}

        user = await self.get_by_id(user_id)
        if not user.is_active:
            raise AuthenticationError(message="Account is disabled")

        await self._repo(
            user_repo.update,
            db_user=user,
            update_data={"hashed_password": get_password_hash(new_password)},
        )
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
        # Revoke any active sessions so a previously-issued refresh token cannot
        # outlive a password reset. The current request returns no tokens — the
        # user must log in again.
        await self._repo(session_repo.deactivate_all_user_sessions, user.id)
{%- endif %}
        return user

    # ------------------------------------------------------------------
    # Magic-link sign-in flow
    # ------------------------------------------------------------------

    async def issue_magic_link_token(self, email: str) -> tuple[User, str] | None:
        user = await self._repo(user_repo.get_by_email, email)
        if user is None or not user.is_active:
            return None
        token = create_magic_link_token(subject=str(user.id))
        return user, token

    async def consume_magic_link_token(self, token: str) -> User:
        """Verify the magic-link token and return the user. Caller mints
        access/refresh tokens for the resolved user.
        """
        payload = verify_special_token(token, expected_type="magic_link")
        if payload is None or "sub" not in payload:
            raise AuthenticationError(message="Magic link is invalid or has expired")
{%- if cookiecutter.use_postgresql %}
        try:
            user_id = UUID(str(payload["sub"]))
        except (TypeError, ValueError) as exc:
            raise AuthenticationError(
                message="Magic link is invalid or has expired"
            ) from exc
{%- else %}
        user_id = str(payload["sub"])
{%- endif %}

        user = await self.get_by_id(user_id)
        if not user.is_active:
            raise AuthenticationError(message="Account is disabled")
        return user
