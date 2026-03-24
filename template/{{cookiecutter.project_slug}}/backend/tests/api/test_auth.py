{%- if cookiecutter.use_jwt %}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""Tests for authentication routes."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
{%- if cookiecutter.use_sqlite %}
ServiceMock = MagicMock
{%- else %}
ServiceMock = AsyncMock
{%- endif %}
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.deps import get_user_service
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.main import app


class MockUser:
    """Mock user for testing."""

    def __init__(
        self,
        id=None,
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        role="user",
    ):
        self.id = id or uuid4()
        self.email = email
        self.full_name = full_name
        self.is_active = is_active
        self.role = role
        self.hashed_password = "hashed"
        self.avatar_url = None
{%- if cookiecutter.enable_oauth %}
        self.oauth_provider = None
{%- endif %}
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)


@pytest.fixture
def mock_user() -> MockUser:
    """Create a mock user."""
    return MockUser()


@pytest.fixture
def mock_user_service(mock_user: MockUser) -> MagicMock:
    """Create a mock user service."""
    service = MagicMock()
{%- if cookiecutter.use_sqlite %}
    service.authenticate = MagicMock(return_value=mock_user)
    service.register = MagicMock(return_value=mock_user)
    service.get_by_id = MagicMock(return_value=mock_user)
    service.get_by_email = MagicMock(return_value=mock_user)
{%- else %}
    service.authenticate = ServiceMock(return_value=mock_user)
    service.register = ServiceMock(return_value=mock_user)
    service.get_by_id = ServiceMock(return_value=mock_user)
    service.get_by_email = ServiceMock(return_value=mock_user)
{%- endif %}
    return service


@pytest.fixture
async def client_with_mock_service(
    mock_user_service: MagicMock,
{%- if cookiecutter.enable_redis %}
    mock_redis: MagicMock,
{%- endif %}
{%- if cookiecutter.use_database %}
    mock_db_session,
{%- endif %}
) -> AsyncClient:
    """Client with mocked user service."""
{%- if cookiecutter.enable_redis %}
    from app.api.deps import get_redis
{%- endif %}
{%- if cookiecutter.use_database %}
    from app.api.deps import get_db_session
{%- endif %}
    from httpx import ASGITransport

    app.dependency_overrides[get_user_service] = lambda: mock_user_service
{%- if cookiecutter.enable_redis %}
    app.dependency_overrides[get_redis] = lambda: mock_redis
{%- endif %}
{%- if cookiecutter.use_database %}
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
{%- endif %}

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_login_success(client_with_mock_service: AsyncClient):
    """Test successful login."""
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_invalid_credentials(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test login with invalid credentials."""
    from app.core.exceptions import AuthenticationError

    mock_user_service.authenticate = ServiceMock(
        side_effect=AuthenticationError(message="Invalid credentials")
    )

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": "test@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_register_success(client_with_mock_service: AsyncClient):
    """Test successful registration."""
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "new@example.com",
            "password": "password123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"  # From mock


@pytest.mark.anyio
async def test_register_duplicate_email(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test registration with duplicate email."""
    from app.core.exceptions import AlreadyExistsError

    mock_user_service.register = ServiceMock(
        side_effect=AlreadyExistsError(message="Email already registered")
    )

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "existing@example.com",
            "password": "password123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 409


{%- if not cookiecutter.enable_session_management %}


@pytest.mark.anyio
async def test_refresh_token_success(
    client_with_mock_service: AsyncClient,
    mock_user: MockUser,
):
    """Test successful token refresh."""
    refresh_token = create_refresh_token(subject=str(mock_user.id))

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.anyio
async def test_refresh_token_invalid(client_with_mock_service: AsyncClient):
    """Test refresh with invalid token."""
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert response.status_code == 401
{%- endif %}


{%- if not cookiecutter.enable_session_management %}


@pytest.mark.anyio
async def test_refresh_token_wrong_type(
    client_with_mock_service: AsyncClient,
    mock_user: MockUser,
):
    """Test refresh with access token instead of refresh token."""
    access_token = create_access_token(subject=str(mock_user.id))

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_token_inactive_user(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test refresh token for inactive user."""
    inactive_user = MockUser(is_active=False)
    mock_user_service.get_by_id = ServiceMock(return_value=inactive_user)
    refresh_token = create_refresh_token(subject=str(inactive_user.id))

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 401
{%- endif %}


@pytest.mark.anyio
async def test_get_current_user(
    client_with_mock_service: AsyncClient,
    mock_user: MockUser,
    mock_user_service: MagicMock,
):
    """Test getting current user info."""
    from app.api.deps import get_current_user

    # Override get_current_user to return mock user
    app.dependency_overrides[get_current_user] = lambda: mock_user

    response = await client_with_mock_service.get(
        f"{settings.API_V1_STR}/auth/me",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_user.email
{%- endif %}
