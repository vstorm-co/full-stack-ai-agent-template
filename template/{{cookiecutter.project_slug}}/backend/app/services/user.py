import contextlib
import logging
from typing import Any
from uuid import UUID

{%- if cookiecutter.enable_pagination %}
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
{%- endif %}
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.file_storage import get_file_storage
{%- if cookiecutter.enable_email %}
from app.services.email.service import get_email_service
{%- endif %}
{%- if cookiecutter.enable_teams %}
from app.services.organization import OrganizationService
{%- endif %}

from app.schemas.conversation_share import AdminUserList, AdminUserRead

logger = logging.getLogger(__name__)


class UserService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _is_first_user(self) -> bool:
        count = (await self.db.execute(select(func.count()).select_from(User))).scalar_one()
        return count == 0

    async def get_by_id(self, user_id: UUID) -> User:
        user = await user_repo.get_by_id(self.db, user_id)
        if not user:
            raise NotFoundError(
                message="User not found",
                details={"user_id": user_id},
            )
        return user

    async def get_by_email(self, email: str) -> User | None:
        return await user_repo.get_by_email(self.db, email)

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        return await user_repo.get_multi(self.db, skip=skip, limit=limit)

{%- if cookiecutter.enable_pagination %}
    async def list_paginated(self) -> Page[UserRead]:
        return await paginate(self.db, user_repo.list_query())
{%- endif %}

    async def delete_non_admins(self) -> int:
        return await user_repo.delete_non_admins(self.db)

    async def has_any(self) -> bool:
        return await user_repo.has_any(self.db)

    async def admin_list_with_counts(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> AdminUserList:
        rows, total = await user_repo.admin_list_with_counts(
            self.db,
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
        """The first user to register is auto-promoted to app-admin — no separate CLI step needed."""
        existing = await user_repo.get_by_email(self.db, user_in.email)
        if existing:
            raise AlreadyExistsError(
                message="Email already registered",
                details={"email": user_in.email},
            )

        is_first_user = await self._is_first_user()

        hashed_password = get_password_hash(user_in.password)
        user = await user_repo.create(
            self.db,
            email=user_in.email,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            role=UserRole.ADMIN.value if is_first_user else user_in.role.value,
            is_app_admin=is_first_user,
        )
{%- if cookiecutter.enable_teams %}
        org_service = OrganizationService(self.db)
        await org_service.create_personal_org(user.id, user_in.email)
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
            logger.exception(
                "welcome_email_failed",
                extra={"user_id": str(user.id), "email": user.email},
            )
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
        existing = await user_repo.get_by_external_user_id(self.db, external_user_id)
        if existing:
            return existing

        by_email = await user_repo.get_by_email(self.db, email)
        if by_email is not None:
            await user_repo.update(
                self.db,
                db_user=by_email,
                update_data={"external_user_id": external_user_id},
            )
            return by_email

        is_first_user = await self._is_first_user()

        user = await user_repo.create(
            self.db,
            email=email,
            hashed_password=None,
            full_name=full_name,
            external_user_id=external_user_id,
            role=UserRole.ADMIN.value if is_first_user else UserRole.USER.value,
            is_app_admin=is_first_user,
        )
{%- if cookiecutter.enable_teams %}
        org_service = OrganizationService(self.db)
        await org_service.create_personal_org(user.id, user.email)
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
        """Email-matched existing accounts get the OAuth identity attached rather than creating a duplicate."""
        existing = await user_repo.get_by_oauth(self.db, provider, provider_id)
        if existing:
            return existing

        by_email = await user_repo.get_by_email(self.db, email)
        if by_email is not None:
            await user_repo.update(
                self.db,
                db_user=by_email,
                update_data={"oauth_provider": provider, "oauth_id": provider_id},
            )
            return by_email

        user = await user_repo.create(
            self.db,
            email=email,
            hashed_password=None,
            full_name=full_name,
            oauth_provider=provider,
            oauth_id=provider_id,
        )
{%- if cookiecutter.enable_teams %}
        org_service = OrganizationService(self.db)
        await org_service.create_personal_org(user.id, user.email)
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
            logger.exception(
                "welcome_email_failed",
                extra={"user_id": str(user.id), "email": user.email},
            )
{%- endif %}
        return user
{%- endif %}

    async def authenticate(self, email: str, password: str) -> User:
        user = await user_repo.get_by_email(self.db, email)
        if (
            not user
            or not user.hashed_password
            or not verify_password(password, user.hashed_password)
        ):
            raise AuthenticationError(message="Invalid email or password")
        if not user.is_active:
            raise AuthenticationError(message="User account is disabled")
        return user

    async def update(self, user_id: UUID, user_in: UserUpdate) -> User:
        user = await self.get_by_id(user_id)

        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        return await user_repo.update(self.db, db_user=user, update_data=update_data)

    async def update_avatar(
        self, user_id: UUID, file_data: bytes, filename: str, content_type: str
    ) -> User:
        ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        if content_type not in ALLOWED_AVATAR_TYPES:
            raise ValueError("Only JPEG, PNG, WebP, and GIF images are allowed")
        if len(file_data) > 2 * 1024 * 1024:
            raise ValueError("Avatar image too large. Maximum 2MB.")

        storage = get_file_storage()

        user = await self.get_by_id(user_id)
        if user.avatar_url:
            with contextlib.suppress(Exception):
                await storage.delete(user.avatar_url)

        storage_path = await storage.save(f"avatars/{user_id}", filename, file_data)
        return await user_repo.update(self.db, db_user=user, update_data={"avatar_url": storage_path})

    def get_avatar_path(self, avatar_url: str) -> str | None:
        return get_file_storage().get_full_path(avatar_url)

    async def delete(self, user_id: UUID) -> User:
        user = await user_repo.delete(self.db, user_id)
        if not user:
            raise NotFoundError(
                message="User not found",
                details={"user_id": user_id},
            )
        return user

    async def issue_password_reset_token(self, email: str) -> tuple[User, str] | None:
        """Returns None (not raises) to avoid leaking whether the email is registered."""
        user = await user_repo.get_by_email(self.db, email)
        if user is None or not user.is_active:
            return None
        token = create_password_reset_token(subject=str(user.id))
        return user, token

    async def confirm_password_reset(self, token: str, new_password: str) -> User:
        payload = verify_special_token(token, expected_type="password_reset")
        if payload is None or "sub" not in payload:
            raise AuthenticationError(message="Reset link is invalid or has expired")
        try:
            user_id = UUID(str(payload["sub"]))
        except (TypeError, ValueError) as exc:
            raise AuthenticationError(
                message="Reset link is invalid or has expired"
            ) from exc

        user = await self.get_by_id(user_id)
        if not user.is_active:
            raise AuthenticationError(message="Account is disabled")

        await user_repo.update(
            self.db,
            db_user=user,
            update_data={"hashed_password": get_password_hash(new_password)},
        )
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
        # Revoke any active sessions so a previously-issued refresh token cannot
        # outlive a password reset. The current request returns no tokens — the
        # user must log in again.
        await session_repo.deactivate_all_user_sessions(self.db, user.id)
{%- endif %}
        return user

    async def issue_magic_link_token(self, email: str) -> tuple[User, str] | None:
        user = await user_repo.get_by_email(self.db, email)
        if user is None or not user.is_active:
            return None
        token = create_magic_link_token(subject=str(user.id))
        return user, token

    async def consume_magic_link_token(self, token: str) -> User:
        """Caller is responsible for minting access/refresh tokens for the returned user."""
        payload = verify_special_token(token, expected_type="magic_link")
        if payload is None or "sub" not in payload:
            raise AuthenticationError(message="Magic link is invalid or has expired")
        try:
            user_id = UUID(str(payload["sub"]))
        except (TypeError, ValueError) as exc:
            raise AuthenticationError(
                message="Magic link is invalid or has expired"
            ) from exc

        user = await self.get_by_id(user_id)
        if not user.is_active:
            raise AuthenticationError(message="Account is disabled")
        return user
