{%- if cookiecutter.use_jwt %}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""User management routes."""

from typing import Annotated, Any
{%- if cookiecutter.use_postgresql %}

from uuid import UUID
{%- endif %}

from fastapi import APIRouter, Depends, UploadFile, File, status
{%- if cookiecutter.enable_pagination %}
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
{%- endif %}

from app.api.deps import (
    DBSession,
    RoleChecker,
    UserSvc,
    get_current_user,
)
from app.db.models.user import User, UserRole
from app.schemas.user import UserRead, UserUpdate

router = APIRouter()


{%- if cookiecutter.use_postgresql %}


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    """Get current user.

    Returns the authenticated user's profile including their role.
    """
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_current_user(
    user_in: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: UserSvc,
) -> Any:
    """Update current user.

    Users can update their own profile (email, full_name).
    Role changes require admin privileges.
    """
    # Prevent non-admin users from changing their own role
    if user_in.role is not None and not current_user.has_role(UserRole.ADMIN):
        user_in.role = None
    user = await user_service.update(current_user.id, user_in)
    return user


{%- if cookiecutter.use_jwt %}


@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    user_service: UserSvc = None,  # type: ignore[assignment]
) -> Any:
    """Upload or replace avatar image for the current user."""
    from fastapi import HTTPException

    data = await file.read()
    try:
        user = await user_service.update_avatar(
            current_user.id, data, file.filename or "avatar.jpg", file.content_type or ""
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return user


@router.get("/avatar/{user_id}")
async def get_avatar(user_id: UUID, user_service: UserSvc) -> Any:
    """Get user avatar image."""
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from app.services.file_storage import get_file_storage
    user = await user_service.get_by_id(user_id)
    if not user.avatar_url:
        raise HTTPException(status_code=404, detail="No avatar set")
    storage = get_file_storage()
    file_path = storage.get_full_path(user.avatar_url)
    if not file_path:
        raise HTTPException(status_code=404, detail="Avatar file not found")
    return FileResponse(path=file_path, media_type="image/jpeg")
{%- endif %}


{%- if cookiecutter.enable_pagination %}


@router.get("", response_model=Page[UserRead])
async def read_users(
    db: DBSession,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
) -> Any:
    """Get all users (admin only)."""
    return await paginate(db, select(User))


{%- else %}


@router.get("", response_model=list[UserRead])
async def read_users(
    user_service: UserSvc,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Get all users (admin only)."""
    users = await user_service.get_multi(skip=skip, limit=limit)
    return users


{%- endif %}


@router.get("/{user_id}", response_model=UserRead)
async def read_user(
    user_id: UUID,
    user_service: UserSvc,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
) -> Any:
    """Get user by ID (admin only).

    Raises NotFoundError if user does not exist.
    """
    user = await user_service.get_by_id(user_id)
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user_by_id(
    user_id: UUID,
    user_in: UserUpdate,
    user_service: UserSvc,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
) -> Any:
    """Update user by ID (admin only).

    Admins can update any user including their role.

    Raises NotFoundError if user does not exist.
    """
    user = await user_service.update(user_id, user_in)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_user_by_id(
    user_id: UUID,
    user_service: UserSvc,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
) -> None:
    """Delete user by ID (admin only).

    Raises NotFoundError if user does not exist.
    """
    await user_service.delete(user_id)


{%- elif cookiecutter.use_mongodb %}


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    """Get current user.

    Returns the authenticated user's profile including their role.
    """
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_current_user(
    user_in: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: UserSvc,
) -> Any:
    """Update current user.

    Users can update their own profile (email, full_name).
    Role changes require admin privileges.
    """
    # Prevent non-admin users from changing their own role
    if user_in.role is not None and not current_user.has_role(UserRole.ADMIN):
        user_in.role = None
    user = await user_service.update(str(current_user.id), user_in)
    return user


@router.get("", response_model=list[UserRead])
async def read_users(
    user_service: UserSvc,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Get all users (admin only)."""
    users = await user_service.get_multi(skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserRead)
async def read_user(
    user_id: str,
    user_service: UserSvc,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
) -> Any:
    """Get user by ID (admin only).

    Raises NotFoundError if user does not exist.
    """
    user = await user_service.get_by_id(user_id)
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user_by_id(
    user_id: str,
    user_in: UserUpdate,
    user_service: UserSvc,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
) -> Any:
    """Update user by ID (admin only).

    Admins can update any user including their role.

    Raises NotFoundError if user does not exist.
    """
    user = await user_service.update(user_id, user_in)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_user_by_id(
    user_id: str,
    user_service: UserSvc,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
) -> None:
    """Delete user by ID (admin only).

    Raises NotFoundError if user does not exist.
    """
    await user_service.delete(user_id)


{%- elif cookiecutter.use_sqlite %}


@router.get("/me", response_model=UserRead)
def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    """Get current user.

    Returns the authenticated user's profile including their role.
    """
    return current_user


@router.patch("/me", response_model=UserRead)
def update_current_user(
    user_in: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: UserSvc,
) -> Any:
    """Update current user.

    Users can update their own profile (email, full_name).
    Role changes require admin privileges.
    """
    # Prevent non-admin users from changing their own role
    if user_in.role is not None and not current_user.has_role(UserRole.ADMIN):
        user_in.role = None
    user = user_service.update(current_user.id, user_in)
    return user


{%- if cookiecutter.enable_pagination %}


@router.get("", response_model=Page[UserRead])
def read_users(
    db: DBSession,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
) -> Any:
    """Get all users (admin only)."""
    return paginate(db, select(User))


{%- else %}


@router.get("", response_model=list[UserRead])
def read_users(
    user_service: UserSvc,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Get all users (admin only)."""
    users = user_service.get_multi(skip=skip, limit=limit)
    return users


{%- endif %}


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: str,
    user_service: UserSvc,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
) -> Any:
    """Get user by ID (admin only).

    Raises NotFoundError if user does not exist.
    """
    user = user_service.get_by_id(user_id)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user_by_id(
    user_id: str,
    user_in: UserUpdate,
    user_service: UserSvc,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
) -> Any:
    """Update user by ID (admin only).

    Admins can update any user including their role.

    Raises NotFoundError if user does not exist.
    """
    user = user_service.update(user_id, user_in)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_user_by_id(
    user_id: str,
    user_service: UserSvc,
    current_user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))],
) -> None:
    """Delete user by ID (admin only).

    Raises NotFoundError if user does not exist.
    """
    user_service.delete(user_id)


{%- endif %}
{%- else %}
"""User routes - not configured."""
{%- endif %}
