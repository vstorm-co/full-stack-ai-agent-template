{%- if cookiecutter.use_jwt %}
from datetime import timedelta
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.api.deps import CurrentAdmin, DBSession, UserSvc
{%- if cookiecutter.enable_teams %}
from app.core.audit import record_audit
{%- endif %}
from app.core.security import create_access_token
from app.schemas.user import AdminUserList, ImpersonateResponse, UserRead, UserUpdate

router = APIRouter()


@router.get("", response_model=AdminUserList)
async def list_users(
    _: CurrentAdmin,
    service: UserSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: str | None = Query(None),
    sort_by: Literal["email", "full_name", "conversations", "created_at"] = Query(
        "created_at", description="Sort column"
    ),
    sort_dir: Literal["asc", "desc"] = Query("desc", description="Sort direction"),
) -> Any:
    result = await service.admin_list_with_counts(
        skip=skip, limit=limit, search=search, sort_by=sort_by, sort_dir=sort_dir
    )
    return result


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    _: CurrentAdmin,
    service: UserSvc,
) -> Any:
    return await service.get_by_id(user_id)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
{%- if cookiecutter.enable_teams %}
    request: Request,
    admin: CurrentAdmin,
    db: DBSession,
{%- else %}
    _: CurrentAdmin,
{%- endif %}
    service: UserSvc,
) -> Any:
    user = await service.update(user_id, user_in)
{%- if cookiecutter.enable_teams %}
    await record_audit(
        db,
        actor_user_id=admin.id,
        action="admin.user.update",
        target_type="user",
        target_id=str(user_id),
        details=user_in.model_dump(exclude_unset=True),
        ip_address=request.client.host if request.client else None,
    )
{%- endif %}
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_user(
    user_id: UUID,
{%- if cookiecutter.enable_teams %}
    request: Request,
    admin: CurrentAdmin,
    db: DBSession,
{%- else %}
    _: CurrentAdmin,
{%- endif %}
    service: UserSvc,
) -> None:
{%- if cookiecutter.enable_teams %}
    target = await service.get_by_id(user_id)
{%- else %}
    await service.get_by_id(user_id)  # raises 404 if not found
{%- endif %}
    await service.delete(user_id)
{%- if cookiecutter.enable_teams %}
    await record_audit(
        db,
        actor_user_id=admin.id,
        action="admin.user.delete",
        target_type="user",
        target_id=str(user_id),
        details={"email": target.email},
        ip_address=request.client.host if request.client else None,
    )
{%- endif %}


@router.post("/{user_id}/impersonate", response_model=ImpersonateResponse)
async def impersonate_user(
    request: Request,
    user_id: UUID,
    admin: CurrentAdmin,
{%- if cookiecutter.enable_teams %}
    db: DBSession,
{%- endif %}
    service: UserSvc,
) -> Any:
    """Issue a short-lived (1h) access token to act as the target user."""
    target = await service.get_by_id(user_id)
    token = create_access_token(
        subject=str(target.id),
        expires_delta=timedelta(hours=1),
    )
{%- if cookiecutter.enable_teams %}
    await record_audit(
        db,
        actor_user_id=admin.id,
        action="admin.user.impersonate",
        target_type="user",
        target_id=str(target.id),
        details={"target_email": target.email, "expires_in": 3600},
        ip_address=request.client.host if request.client else None,
    )
{%- endif %}
    return ImpersonateResponse(
        access_token=token,
        token_type="bearer",
        impersonated_user_id=str(target.id),
        impersonated_by=str(admin.id),
        expires_in=3600,
    )

{%- endif %}
