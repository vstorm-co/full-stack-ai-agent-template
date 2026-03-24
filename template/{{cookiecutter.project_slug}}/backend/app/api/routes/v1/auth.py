{%- if cookiecutter.use_jwt %}
"""Authentication routes."""

from typing import Annotated, Any
{%- if cookiecutter.use_postgresql and not cookiecutter.enable_session_management %}
from uuid import UUID
{%- endif %}

from fastapi import APIRouter, Depends{% if cookiecutter.enable_session_management %}, Request{% endif %}, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser{% if cookiecutter.enable_session_management %}, SessionSvc{% endif %}, UserSvc
from app.core.exceptions import AuthenticationError
from app.core.security import create_access_token, create_refresh_token, verify_token
from app.schemas.token import RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserRead, UserRole

router = APIRouter()


{%- if cookiecutter.use_postgresql %}


@router.post("/login", response_model=Token)
async def login(
{%- if cookiecutter.enable_session_management %}
    request: Request,
{%- endif %}
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserSvc,
{%- if cookiecutter.enable_session_management %}
    session_service: SessionSvc,
{%- endif %}
) -> Any:
    """OAuth2 compatible token login.

    Returns access token and refresh token.
    Raises domain exceptions handled by exception handlers.
    """
    user = await user_service.authenticate(form_data.username, form_data.password)
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
{%- if cookiecutter.enable_session_management %}

    # Create session to track this login
    await session_service.create_session(
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
{%- endif %}
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    user_service: UserSvc,
) -> Any:
    """Register a new user.

    Raises AlreadyExistsError if email is already registered.
    """
    user = await user_service.register(user_in)
    return user


@router.post("/refresh", response_model=Token)
async def refresh_token(
{%- if cookiecutter.enable_session_management %}
    request: Request,
{%- endif %}
    body: RefreshTokenRequest,
    user_service: UserSvc,
{%- if cookiecutter.enable_session_management %}
    session_service: SessionSvc,
{%- endif %}
) -> Any:
    """Get new access token using refresh token.

    Raises AuthenticationError if refresh token is invalid or expired.
    """
{%- if cookiecutter.enable_session_management %}

    # Validate refresh token against stored session
    session = await session_service.validate_refresh_token(body.refresh_token)
    if not session:
        raise AuthenticationError(message="Invalid or expired refresh token")

    user = await user_service.get_by_id(session.user_id)
{%- else %}

    payload = verify_token(body.refresh_token)
    if payload is None:
        raise AuthenticationError(message="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(message="Invalid token payload")

    # Verify user still exists and is active
    user = await user_service.get_by_id(UUID(user_id))
{%- endif %}
    if not user.is_active:
        raise AuthenticationError(message="User account is disabled")

    access_token = create_access_token(subject=str(user.id))
    new_refresh_token = create_refresh_token(subject=str(user.id))
{%- if cookiecutter.enable_session_management %}

    # Invalidate old session and create new one
    await session_service.logout_by_refresh_token(body.refresh_token)
    await session_service.create_session(
        user_id=user.id,
        refresh_token=new_refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
{%- endif %}
    return Token(access_token=access_token, refresh_token=new_refresh_token)

{%- if cookiecutter.enable_session_management %}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(
    body: RefreshTokenRequest,
    session_service: SessionSvc,
) -> None:
    """Logout and invalidate the current session.

    Invalidates the refresh token, preventing further token refresh.
    """
    await session_service.logout_by_refresh_token(body.refresh_token)
{%- endif %}


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: CurrentUser) -> Any:
    """Get current authenticated user information."""
    return current_user
{%- elif cookiecutter.use_mongodb %}


@router.post("/login", response_model=Token)
async def login(
{%- if cookiecutter.enable_session_management %}
    request: Request,
{%- endif %}
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserSvc,
{%- if cookiecutter.enable_session_management %}
    session_service: SessionSvc,
{%- endif %}
) -> Any:
    """OAuth2 compatible token login.

    Returns access token and refresh token.
    Raises domain exceptions handled by exception handlers.
    """
    user = await user_service.authenticate(form_data.username, form_data.password)
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
{%- if cookiecutter.enable_session_management %}

    # Create session to track this login
    await session_service.create_session(
        user_id=str(user.id),
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
{%- endif %}
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    user_service: UserSvc,
) -> Any:
    """Register a new user.

    Raises AlreadyExistsError if email is already registered.
    """
    user = await user_service.register(user_in)
    return UserRead(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        role=UserRole(user.role),
{%- if cookiecutter.enable_oauth %}
        oauth_provider=user.oauth_provider,
{%- endif %}
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
{%- if cookiecutter.enable_session_management %}
    request: Request,
{%- endif %}
    body: RefreshTokenRequest,
    user_service: UserSvc,
{%- if cookiecutter.enable_session_management %}
    session_service: SessionSvc,
{%- endif %}
) -> Any:
    """Get new access token using refresh token.

    Raises AuthenticationError if refresh token is invalid or expired.
    """
{%- if cookiecutter.enable_session_management %}
    # Validate refresh token against stored session
    session = await session_service.validate_refresh_token(body.refresh_token)
    if not session:
        raise AuthenticationError(message="Invalid or expired refresh token")

    user = await user_service.get_by_id(session.user_id)
{%- else %}
    payload = verify_token(body.refresh_token)
    if payload is None:
        raise AuthenticationError(message="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(message="Invalid token payload")

    # Verify user still exists and is active
    user = await user_service.get_by_id(user_id)
{%- endif %}
    if not user.is_active:
        raise AuthenticationError(message="User account is disabled")

    access_token = create_access_token(subject=str(user.id))
    new_refresh_token = create_refresh_token(subject=str(user.id))
{%- if cookiecutter.enable_session_management %}

    # Invalidate old session and create new one
    await session_service.logout_by_refresh_token(body.refresh_token)
    await session_service.create_session(
        user_id=str(user.id),
        refresh_token=new_refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
{%- endif %}
    return Token(access_token=access_token, refresh_token=new_refresh_token)

{%- if cookiecutter.enable_session_management %}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(
    body: RefreshTokenRequest,
    session_service: SessionSvc,
) -> None:
    """Logout and invalidate the current session.

    Invalidates the refresh token, preventing further token refresh.
    """
    await session_service.logout_by_refresh_token(body.refresh_token)
{%- endif %}


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: CurrentUser) -> Any:
    """Get current authenticated user information."""
    return UserRead(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        role=UserRole(current_user.role),
{%- if cookiecutter.enable_oauth %}
        oauth_provider=current_user.oauth_provider,
{%- endif %}
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )
{%- elif cookiecutter.use_sqlite %}


@router.post("/login", response_model=Token)
def login(
{%- if cookiecutter.enable_session_management %}
    request: Request,
{%- endif %}
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserSvc,
{%- if cookiecutter.enable_session_management %}
    session_service: SessionSvc,
{%- endif %}
) -> Any:
    """OAuth2 compatible token login.

    Returns access token and refresh token.
    Raises domain exceptions handled by exception handlers.
    """
    user = user_service.authenticate(form_data.username, form_data.password)
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
{%- if cookiecutter.enable_session_management %}

    # Create session to track this login
    session_service.create_session(
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
{%- endif %}
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    user_service: UserSvc,
) -> Any:
    """Register a new user.

    Raises AlreadyExistsError if email is already registered.
    """
    user = user_service.register(user_in)
    return UserRead(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        role=UserRole(user.role),
{%- if cookiecutter.enable_oauth %}
        oauth_provider=user.oauth_provider,
{%- endif %}
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/refresh", response_model=Token)
def refresh_token(
{%- if cookiecutter.enable_session_management %}
    request: Request,
{%- endif %}
    body: RefreshTokenRequest,
    user_service: UserSvc,
{%- if cookiecutter.enable_session_management %}
    session_service: SessionSvc,
{%- endif %}
) -> Any:
    """Get new access token using refresh token.

    Raises AuthenticationError if refresh token is invalid or expired.
    """
{%- if cookiecutter.enable_session_management %}
    # Validate refresh token against stored session
    session = session_service.validate_refresh_token(body.refresh_token)
    if not session:
        raise AuthenticationError(message="Invalid or expired refresh token")

    user = user_service.get_by_id(session.user_id)
{%- else %}
    payload = verify_token(body.refresh_token)
    if payload is None:
        raise AuthenticationError(message="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(message="Invalid token payload")

    # Verify user still exists and is active
    user = user_service.get_by_id(user_id)
{%- endif %}
    if not user.is_active:
        raise AuthenticationError(message="User account is disabled")

    access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)
{%- if cookiecutter.enable_session_management %}

    # Invalidate old session and create new one
    session_service.logout_by_refresh_token(body.refresh_token)
    session_service.create_session(
        user_id=user.id,
        refresh_token=new_refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
{%- endif %}
    return Token(access_token=access_token, refresh_token=new_refresh_token)

{%- if cookiecutter.enable_session_management %}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(
    body: RefreshTokenRequest,
    session_service: SessionSvc,
) -> None:
    """Logout and invalidate the current session.

    Invalidates the refresh token, preventing further token refresh.
    """
    session_service.logout_by_refresh_token(body.refresh_token)
{%- endif %}


@router.get("/me", response_model=UserRead)
def get_current_user_info(current_user: CurrentUser) -> Any:
    """Get current authenticated user information."""
    return UserRead(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        role=UserRole(current_user.role),
{%- if cookiecutter.enable_oauth %}
        oauth_provider=current_user.oauth_provider,
{%- endif %}
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )
{%- endif %}
{%- else %}
"""Auth routes - not configured."""
{%- endif %}
