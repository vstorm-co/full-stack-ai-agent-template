{%- if cookiecutter.use_jwt %}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""User management routes."""

from typing import Any

from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile, status
from fastapi.responses import FileResponse
{%- if cookiecutter.enable_pagination %}
from fastapi_pagination import Page
{%- endif %}

from app.api.deps import (
    CurrentAdmin,
    CurrentUser,
    UserSvc,
)
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.user import UserRole
from app.schemas.user import UserRead, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: CurrentUser,
) -> Any:
    """Get current user profile."""
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_current_user(
    user_in: UserUpdate,
    current_user: CurrentUser,
    user_service: UserSvc,
) -> Any:
    """Update current user profile."""
    if user_in.role is not None and not current_user.has_role(UserRole.ADMIN):
        user_in.role = None
    user = await user_service.update(current_user.id, user_in)
    return user


@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(
    user_service: UserSvc,
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> Any:
    """Upload or replace avatar image for the current user."""
    data = await file.read()
    try:
        user = await user_service.update_avatar(
            current_user.id, data, file.filename or "avatar.jpg", file.content_type or ""
        )
    except ValueError as e:
        raise BadRequestError(message=str(e)) from None
    return user


@router.get("/avatar/{user_id}", response_model=None)
async def get_avatar(user_id: UUID, user_service: UserSvc) -> Any:
    """Get user avatar image."""
    user = await user_service.get_by_id(user_id)
    if not user.avatar_url:
        raise NotFoundError(message="No avatar set")
    file_path = user_service.get_avatar_path(user.avatar_url)
    if not file_path:
        raise NotFoundError(message="Avatar file not found")
    return FileResponse(path=file_path, media_type="image/jpeg")


{%- if cookiecutter.enable_pagination %}


@router.get("", response_model=Page[UserRead])
async def read_users(
    user_service: UserSvc,
    _: CurrentAdmin,
) -> Any:
    """Get all users (admin only)."""
    return await user_service.list_paginated()


{%- else %}


@router.get("", response_model=list[UserRead])
async def read_users(
    user_service: UserSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(100, ge=1, le=200, description="Max items to return"),
) -> Any:
    """Get all users (admin only)."""
    users = await user_service.get_multi(skip=skip, limit=limit)
    return users


{%- endif %}


@router.get("/{user_id}", response_model=UserRead)
async def read_user(
    user_id: UUID,
    user_service: UserSvc,
    _: CurrentAdmin,
) -> Any:
    """Get user by ID (admin only)."""
    user = await user_service.get_by_id(user_id)
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user_by_id(
    user_id: UUID,
    user_in: UserUpdate,
    user_service: UserSvc,
    _: CurrentAdmin,
) -> Any:
    """Update user by ID (admin only)."""
    user = await user_service.update(user_id, user_in)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_user_by_id(
    user_id: UUID,
    user_service: UserSvc,
    _: CurrentAdmin,
) -> None:
    """Delete user by ID (admin only)."""
    await user_service.delete(user_id)


{%- else %}
"""User routes - not configured."""
{%- endif %}
