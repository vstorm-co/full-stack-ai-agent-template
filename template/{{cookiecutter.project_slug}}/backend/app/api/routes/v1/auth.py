{%- if cookiecutter.use_delegated_auth %}
"""Authentication routes.

Delegated auth mode: identity is owned by the external IdP, so this module
exposes **only** ``/me``. Local email/password endpoints (login, register,
refresh, logout, password reset, magic link) are deliberately absent — see
``get_current_user`` in ``app/api/deps.py``, which validates IdP signatures and
would reject any token this backend minted. Leaving them mounted would also
mean an unauthenticated caller could create a local account, and the first such
account is auto-promoted to app-admin.
"""
{%- else %}
"""Authentication routes."""
{%- endif %}

import logging
{%- if cookiecutter.use_delegated_auth %}
from typing import Any
{%- else %}
from typing import Annotated, Any
{%- if not cookiecutter.enable_session_management %}
from uuid import UUID
{%- endif %}
{%- endif %}

from fastapi import APIRouter{% if not cookiecutter.use_delegated_auth %}, Depends, Request{% endif %}{% if not cookiecutter.use_delegated_auth %}, status{% endif %}
{%- if not cookiecutter.use_delegated_auth %}
from fastapi.security import OAuth2PasswordRequestForm
{%- endif %}

{%- if cookiecutter.enable_session_management %}
from app.api.deps import CurrentUser, SessionSvc, UserSvc
{%- elif not cookiecutter.use_delegated_auth %}
from app.api.deps import CurrentUser, UserSvc
{%- else %}
from app.api.deps import CurrentUser
{%- endif %}
{%- if cookiecutter.enable_email and not cookiecutter.use_delegated_auth %}
from app.core.config import settings
{%- endif %}
{%- if not cookiecutter.use_delegated_auth %}
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
{%- if not cookiecutter.enable_session_management %}
    verify_token,
{%- endif %}
)
{%- endif %}
{%- if cookiecutter.enable_email and not cookiecutter.use_delegated_auth %}
from app.services.email.service import get_email_service
from app.schemas.password_reset import (
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    PasswordResetConfirm,
    PasswordResetConfirmResponse,
    PasswordResetRequest,
    PasswordResetResponse,
)
{%- endif %}
{%- if not cookiecutter.use_delegated_auth %}
from app.schemas.token import RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserRead
{%- else %}
from app.schemas.user import UserRead
{%- endif %}
{%- if cookiecutter.enable_rate_limiting and not cookiecutter.use_delegated_auth %}
from app.services.rate_limit import RateLimitCategory, make_anonymous_rate_limit_dep

# Unauthenticated endpoints: the only scope available is the caller's IP, and
# these are exactly the routes that need one (credential stuffing, reset-email
# flooding). Default rule: 5 requests per 15 minutes per IP.
AuthRateLimit = make_anonymous_rate_limit_dep(RateLimitCategory.AUTH)
{%- endif %}

logger = logging.getLogger(__name__)

router = APIRouter()

{%- if not cookiecutter.use_delegated_auth %}


@router.post(
    "/login",
    response_model=Token,
{%- if cookiecutter.enable_rate_limiting %}
    dependencies=[AuthRateLimit],
{%- endif %}
)
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserSvc,
{%- if cookiecutter.enable_session_management %}
    session_service: SessionSvc,
{%- endif %}
) -> Any:
    """OAuth2 password login, returns access and refresh tokens."""
    user = await user_service.authenticate(form_data.username, form_data.password)
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
{%- if cookiecutter.enable_session_management %}

    # Track this login as a server-side session (enables remote logout).
    await session_service.create_session(
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
{%- endif %}
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
{%- if cookiecutter.enable_rate_limiting %}
    dependencies=[AuthRateLimit],
{%- endif %}
)
async def register(
    user_in: UserCreate,
    user_service: UserSvc,
) -> Any:
    """Register a new user."""
    user = await user_service.register(user_in)
    return user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    user_service: UserSvc,
{%- if cookiecutter.enable_session_management %}
    session_service: SessionSvc,
{%- endif %}
) -> Any:
    """Exchange a refresh token for a new access token."""
{%- if cookiecutter.enable_session_management %}

    session = await session_service.validate_refresh_token(body.refresh_token)
    if not session:
        raise AuthenticationError(message="Invalid or expired refresh token")

    user = await user_service.get_by_id(session.user_id)
{%- else %}

    # No DB-backed sessions — validate the refresh JWT directly.
    payload = verify_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise AuthenticationError(message="Invalid or expired refresh token")
    subject = payload.get("sub")
    if not subject:
        raise AuthenticationError(message="Invalid refresh token")
    try:
        user_id = UUID(str(subject))
    except ValueError as exc:
        raise AuthenticationError(message="Invalid refresh token") from exc
    user = await user_service.get_by_id(user_id)
{%- endif %}
    if not user.is_active:
        raise AuthenticationError(message="User account is disabled")

    access_token = create_access_token(subject=str(user.id))
    new_refresh_token = create_refresh_token(subject=str(user.id))
{%- if cookiecutter.enable_session_management %}

    await session_service.logout_by_refresh_token(body.refresh_token)
    await session_service.create_session(
        user_id=user.id,
        refresh_token=new_refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
{%- endif %}
    return Token(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(
    body: RefreshTokenRequest,
{%- if cookiecutter.enable_session_management %}
    session_service: SessionSvc,
{%- endif %}
) -> None:
{%- if cookiecutter.enable_session_management %}
    """Logout and invalidate the current session.

    Invalidates the refresh token, preventing further token refresh.
    """
    await session_service.logout_by_refresh_token(body.refresh_token)
{%- else %}
    """No-op without session tracking. Clients drop their JWTs locally."""
    return None
{%- endif %}
{%- endif %}


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: CurrentUser) -> Any:
    """Get current authenticated user information."""
    return current_user

{%- if cookiecutter.enable_email and not cookiecutter.use_delegated_auth %}



@router.post(
    "/password-reset/request",
    response_model=PasswordResetResponse,
{%- if cookiecutter.enable_rate_limiting %}
    dependencies=[AuthRateLimit],
{%- endif %}
)
async def request_password_reset(
    body: PasswordResetRequest,
    user_service: UserSvc,
) -> Any:
    """Email a single-use reset link to the address.

    Always returns 200 with the same body — we don't disclose whether the
    email is in our system. The caller (email service) is best-effort.
    """
    issued = await user_service.issue_password_reset_token(body.email)
    if issued is not None:
        reset_user, token = issued
        try:
            reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
            await get_email_service().send_password_reset(
                to=body.email,
                name=reset_user.full_name or body.email,
                reset_url=reset_url,
            )
        except Exception:
            logger.exception("password_reset_email_failed", extra={"email": body.email})
    return PasswordResetResponse()


@router.post("/password-reset/confirm", response_model=PasswordResetConfirmResponse)
async def confirm_password_reset(
    body: PasswordResetConfirm,
    user_service: UserSvc,
) -> Any:
    """Set a new password using a token from the reset email."""
    await user_service.confirm_password_reset(body.token, body.new_password)
    return PasswordResetConfirmResponse()



@router.post(
    "/magic-link/request",
    response_model=PasswordResetResponse,
{%- if cookiecutter.enable_rate_limiting %}
    dependencies=[AuthRateLimit],
{%- endif %}
)
async def request_magic_link(
    body: MagicLinkRequest,
    user_service: UserSvc,
) -> Any:
    """Email a single-use sign-in link.

    Symmetric response to request_password_reset to avoid email enumeration.
    """
    issued = await user_service.issue_magic_link_token(body.email)
    if issued is not None:
        link_user, token = issued
        try:
            login_url = f"{settings.FRONTEND_URL.rstrip('/')}/auth/magic-link?token={token}"
            await get_email_service().send_welcome(
                to=body.email,
                name=link_user.full_name or body.email,
                login_url=login_url,
            )
        except Exception:
            logger.exception("magic_link_email_failed", extra={"email": body.email})
    return PasswordResetResponse(message="Check your email for a sign-in link.")


@router.post("/magic-link/verify", response_model=Token)
async def verify_magic_link(
    request: Request,
    body: MagicLinkVerifyRequest,
    user_service: UserSvc,
{%- if cookiecutter.enable_session_management %}
    session_service: SessionSvc,
{%- endif %}
) -> Any:
    """Exchange a magic-link token for an access + refresh token pair."""
    user = await user_service.consume_magic_link_token(body.token)
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
{%- if cookiecutter.enable_session_management %}
    await session_service.create_session(
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
{%- endif %}
    return Token(access_token=access_token, refresh_token=refresh_token)
{%- endif %}
