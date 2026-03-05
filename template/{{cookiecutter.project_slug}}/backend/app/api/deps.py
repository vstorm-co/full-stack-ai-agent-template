"""API dependencies.

Dependency injection factories for services, repositories, and authentication.
"""
{%- if cookiecutter.use_database or cookiecutter.use_jwt or cookiecutter.use_api_key or cookiecutter.enable_redis %}
# ruff: noqa: I001, E402 - Imports structured for Jinja2 template conditionals
{%- endif %}
{%- if cookiecutter.use_database or cookiecutter.use_jwt or cookiecutter.use_api_key or cookiecutter.enable_redis %}

from typing import Annotated

from fastapi import Depends
{%- endif %}
{%- if cookiecutter.use_jwt %}
from fastapi.security import OAuth2PasswordBearer
{%- endif %}
{%- if cookiecutter.use_jwt or cookiecutter.use_api_key %}

from app.core.config import settings
{%- endif %}
{%- if cookiecutter.use_database %}
from app.db.session import get_db_session
{%- endif %}

{%- if cookiecutter.use_postgresql %}
from sqlalchemy.ext.asyncio import AsyncSession

DBSession = Annotated[AsyncSession, Depends(get_db_session)]
{%- endif %}

{%- if cookiecutter.use_sqlite %}
from sqlalchemy.orm import Session

DBSession = Annotated[Session, Depends(get_db_session)]
{%- endif %}

{%- if cookiecutter.use_mongodb %}
from motor.motor_asyncio import AsyncIOMotorDatabase

DBSession = Annotated[AsyncIOMotorDatabase, Depends(get_db_session)]
{%- endif %}

{%- if cookiecutter.use_sqlserver %}
from sqlalchemy.ext.asyncio import AsyncSession

DBSession = Annotated[AsyncSession, Depends(get_db_session)]
{%- endif %}

{%- if cookiecutter.enable_redis %}
from fastapi import Request

from app.clients.redis import RedisClient


async def get_redis(request: Request) -> RedisClient:
    """Get Redis client from lifespan state."""
    return request.state.redis


Redis = Annotated[RedisClient, Depends(get_redis)]
{%- endif %}

{%- if cookiecutter.use_jwt %}


# === Service Dependencies ===

from app.services.user import UserService
{%- if cookiecutter.enable_session_management %}
from app.services.session import SessionService
{%- endif %}
{%- endif %}
{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}
from app.services.webhook import WebhookService
{%- endif %}
{%- if cookiecutter.include_example_crud and cookiecutter.use_database %}
from app.services.item import ItemService
{%- endif %}
{%- if cookiecutter.enable_conversation_persistence and cookiecutter.use_database %}
from app.services.conversation import ConversationService
{%- endif %}
{%- if cookiecutter.use_jwt %}
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite or cookiecutter.use_sqlserver %}


def get_user_service(db: DBSession) -> UserService:
    """Create UserService instance with database session."""
    return UserService(db)

{%- if cookiecutter.enable_session_management %}


def get_session_service(db: DBSession) -> SessionService:
    """Create SessionService instance with database session."""
    return SessionService(db)
{%- endif %}
{%- elif cookiecutter.use_mongodb %}


def get_user_service() -> UserService:
    """Create UserService instance."""
    return UserService()

{%- if cookiecutter.enable_session_management %}


def get_session_service() -> SessionService:
    """Create SessionService instance."""
    return SessionService()
{%- endif %}
{%- endif %}


UserSvc = Annotated[UserService, Depends(get_user_service)]
{%- if cookiecutter.enable_session_management %}
SessionSvc = Annotated[SessionService, Depends(get_session_service)]
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite or cookiecutter.use_sqlserver %}


def get_webhook_service(db: DBSession) -> WebhookService:
    """Create WebhookService instance with database session."""
    return WebhookService(db)
{%- elif cookiecutter.use_mongodb %}


def get_webhook_service() -> WebhookService:
    """Create WebhookService instance."""
    return WebhookService()
{%- endif %}


WebhookSvc = Annotated[WebhookService, Depends(get_webhook_service)]
{%- endif %}

{%- if cookiecutter.include_example_crud and cookiecutter.use_database %}
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite or cookiecutter.use_sqlserver %}


def get_item_service(db: DBSession) -> ItemService:
    """Create ItemService instance with database session."""
    return ItemService(db)
{%- elif cookiecutter.use_mongodb %}


def get_item_service() -> ItemService:
    """Create ItemService instance."""
    return ItemService()
{%- endif %}


ItemSvc = Annotated[ItemService, Depends(get_item_service)]
{%- endif %}

{%- if cookiecutter.enable_conversation_persistence and cookiecutter.use_database %}
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite or cookiecutter.use_sqlserver %}


def get_conversation_service(db: DBSession) -> ConversationService:
    """Create ConversationService instance with database session."""
    return ConversationService(db)
{%- elif cookiecutter.use_mongodb %}


def get_conversation_service() -> ConversationService:
    """Create ConversationService instance."""
    return ConversationService()
{%- endif %}


ConversationSvc = Annotated[ConversationService, Depends(get_conversation_service)]
{%- endif %}

{%- if cookiecutter.use_jwt %}

# === Authentication Dependencies ===

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.db.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlserver %}


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: UserSvc,
) -> User:
    """Get current authenticated user from JWT token.

    Returns the full User object including role information.

    Raises:
        AuthenticationError: If token is invalid or user not found.
    """
    from uuid import UUID

    from app.core.security import verify_token

    payload = verify_token(token)
    if payload is None:
        raise AuthenticationError(message="Invalid or expired token")

    # Ensure this is an access token, not a refresh token
    if payload.get("type") != "access":
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(message="Invalid token payload")

    user = await user_service.get_by_id(UUID(user_id))
    if not user.is_active:
        raise AuthenticationError(message="User account is disabled")

    return user


class RoleChecker:
    """Dependency class for role-based access control.

    Usage:
        # Require admin role
        @router.get("/admin-only")
        async def admin_endpoint(
            user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]
        ):
            ...

        # Require any authenticated user
        @router.get("/users")
        async def users_endpoint(
            user: Annotated[User, Depends(get_current_user)]
        ):
            ...
    """

    def __init__(self, required_role: UserRole) -> None:
        self.required_role = required_role

    async def __call__(
        self,
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check if user has the required role.

        Raises:
            AuthorizationError: If user doesn't have the required role.
        """
        if not user.has_role(self.required_role):
            raise AuthorizationError(
                message=f"Role '{self.required_role.value}' required for this action"
            )
        return user


async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user and verify they are a superuser.

    Raises:
        AuthorizationError: If user is not a superuser.
    """
    if not current_user.is_superuser:
        raise AuthorizationError(message="Superuser privileges required")
    return current_user
{%- elif cookiecutter.use_sqlite %}


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: UserSvc,
) -> User:
    """Get current authenticated user from JWT token.

    Returns the full User object including role information.

    Raises:
        AuthenticationError: If token is invalid or user not found.
    """
    from app.core.security import verify_token

    payload = verify_token(token)
    if payload is None:
        raise AuthenticationError(message="Invalid or expired token")

    # Ensure this is an access token, not a refresh token
    if payload.get("type") != "access":
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(message="Invalid token payload")

    user = user_service.get_by_id(user_id)
    if not user.is_active:
        raise AuthenticationError(message="User account is disabled")

    return user


class RoleChecker:
    """Dependency class for role-based access control.

    Usage:
        # Require admin role
        @router.get("/admin-only")
        def admin_endpoint(
            user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]
        ):
            ...

        # Require any authenticated user
        @router.get("/users")
        def users_endpoint(
            user: Annotated[User, Depends(get_current_user)]
        ):
            ...
    """

    def __init__(self, required_role: UserRole) -> None:
        self.required_role = required_role

    def __call__(
        self,
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check if user has the required role.

        Raises:
            AuthorizationError: If user doesn't have the required role.
        """
        if not user.has_role(self.required_role):
            raise AuthorizationError(
                message=f"Role '{self.required_role.value}' required for this action"
            )
        return user


def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user and verify they are a superuser.

    Raises:
        AuthorizationError: If user is not a superuser.
    """
    if not current_user.is_superuser:
        raise AuthorizationError(message="Superuser privileges required")
    return current_user
{%- elif cookiecutter.use_mongodb %}


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: UserSvc,
) -> User:
    """Get current authenticated user from JWT token.

    Returns the full User object including role information.

    Raises:
        AuthenticationError: If token is invalid or user not found.
    """
    from app.core.security import verify_token

    payload = verify_token(token)
    if payload is None:
        raise AuthenticationError(message="Invalid or expired token")

    # Ensure this is an access token, not a refresh token
    if payload.get("type") != "access":
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(message="Invalid token payload")

    user = await user_service.get_by_id(user_id)
    if not user.is_active:
        raise AuthenticationError(message="User account is disabled")

    return user


class RoleChecker:
    """Dependency class for role-based access control.

    Usage:
        # Require admin role
        @router.get("/admin-only")
        async def admin_endpoint(
            user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]
        ):
            ...

        # Require any authenticated user
        @router.get("/users")
        async def users_endpoint(
            user: Annotated[User, Depends(get_current_user)]
        ):
            ...
    """

    def __init__(self, required_role: UserRole) -> None:
        self.required_role = required_role

    async def __call__(
        self,
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check if user has the required role.

        Raises:
            AuthorizationError: If user doesn't have the required role.
        """
        if not user.has_role(self.required_role):
            raise AuthorizationError(
                message=f"Role '{self.required_role.value}' required for this action"
            )
        return user


async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user and verify they are a superuser.

    Raises:
        AuthorizationError: If user is not a superuser.
    """
    if not current_user.is_superuser:
        raise AuthorizationError(message="Superuser privileges required")
    return current_user
{%- endif %}


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_active_superuser)]
CurrentAdmin = Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]


# WebSocket authentication dependency
from fastapi import WebSocket, Query, Cookie


async def get_current_user_ws(
    websocket: WebSocket,
    token: str | None = Query(None, alias="token"),
    access_token: str | None = Cookie(None),
) -> User:
    """Get current user from WebSocket JWT token.

    Token can be passed either as:
    - Query parameter: ws://...?token=<jwt>
    - Cookie: access_token cookie (set by HTTP login)

    Raises:
        AuthenticationError: If token is invalid or user not found.
    """
    from uuid import UUID

    from app.core.security import verify_token

    # Try query parameter first, then cookie
    auth_token = token or access_token

    if not auth_token:
        await websocket.close(code=4001, reason="Missing authentication token")
        raise AuthenticationError(message="Missing authentication token")

    payload = verify_token(auth_token)
    if payload is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        raise AuthenticationError(message="Invalid or expired token")

    if payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid token type")
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid token payload")
        raise AuthenticationError(message="Invalid token payload")
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlserver %}

    from app.db.session import get_db_context

    async with get_db_context() as db:
        user_service = UserService(db)
        user = await user_service.get_by_id(UUID(user_id))
{%- elif cookiecutter.use_mongodb %}

    db = await get_db_session()
    user_service = UserService(db)
    user = await user_service.get_by_id(UUID(user_id))
{%- elif cookiecutter.use_sqlite %}

    with get_db_session() as db:
        user_service = UserService(db)
        user = user_service.get_by_id(user_id)
{%- endif %}

    if not user.is_active:
        await websocket.close(code=4001, reason="User account is disabled")
        raise AuthenticationError(message="User account is disabled")

    return user
{%- endif %}

{%- if cookiecutter.use_api_key %}

import secrets

from fastapi.security import APIKeyHeader

from app.core.exceptions import AuthenticationError, AuthorizationError

api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def verify_api_key(
    api_key: Annotated[str | None, Depends(api_key_header)],
) -> str:
    """Verify API key from header.

    Uses constant-time comparison to prevent timing attacks.

    Raises:
        AuthenticationError: If API key is missing.
        AuthorizationError: If API key is invalid.
    """
    if api_key is None:
        raise AuthenticationError(message="API Key header missing")
    if not secrets.compare_digest(api_key, settings.API_KEY):
        raise AuthorizationError(message="Invalid API Key")
    return api_key


ValidAPIKey = Annotated[str, Depends(verify_api_key)]
{%- endif %}
