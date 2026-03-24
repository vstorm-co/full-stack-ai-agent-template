{%- if cookiecutter.use_jwt %}
"""Tests for user routes."""
{%- if cookiecutter.use_database or cookiecutter.enable_redis %}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
{%- endif %}

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
{%- if cookiecutter.use_sqlite %}
ServiceMock = MagicMock
{%- else %}
ServiceMock = AsyncMock
{%- endif %}
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_active_superuser, get_current_user, get_user_service
{%- if cookiecutter.use_database %}
from app.api.deps import get_db_session
{%- endif %}
{%- if cookiecutter.enable_redis %}
from app.api.deps import get_redis
{%- endif %}
from app.core.config import settings
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
{%- if cookiecutter.use_postgresql %}
        self.id = id or uuid4()
{%- else %}
        self.id = id or str(uuid4())
{%- endif %}
        self.email = email
        self.full_name = full_name
        self.is_active = is_active
        self.role = role
        self.hashed_password = "hashed"
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def has_role(self, role) -> bool:
        """Check if user has the specified role."""
        if hasattr(role, "value"):
            return self.role == role.value
        return self.role == role


@pytest.fixture
def mock_user() -> MockUser:
    """Create a mock regular user."""
    return MockUser()


@pytest.fixture
def mock_superuser() -> MockUser:
    """Create a mock superuser."""
    return MockUser(role="admin", email="admin@example.com")


@pytest.fixture
def mock_user_service(mock_user: MockUser) -> MagicMock:
    """Create a mock user service."""
    service = MagicMock()
{%- if cookiecutter.use_sqlite %}
    service.get_by_id = MagicMock(return_value=mock_user)
    service.get_multi = MagicMock(return_value=[mock_user])
    service.update = MagicMock(return_value=mock_user)
    service.delete = MagicMock(return_value=mock_user)
{%- else %}
    service.get_by_id = ServiceMock(return_value=mock_user)
    service.get_multi = ServiceMock(return_value=[mock_user])
    service.update = ServiceMock(return_value=mock_user)
    service.delete = ServiceMock(return_value=mock_user)
{%- endif %}
    return service


@pytest.fixture
async def auth_client(
    mock_user: MockUser,
    mock_user_service: MagicMock,
{%- if cookiecutter.enable_redis %}
    mock_redis: MagicMock,
{%- endif %}
{%- if cookiecutter.use_database %}
    mock_db_session,
{%- endif %}
) -> AsyncClient:
    """Client with authenticated regular user."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
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


@pytest.fixture
async def superuser_client(
    mock_superuser: MockUser,
    mock_user_service: MagicMock,
{%- if cookiecutter.enable_redis %}
    mock_redis: MagicMock,
{%- endif %}
{%- if cookiecutter.use_database %}
    mock_db_session,
{%- endif %}
) -> AsyncClient:
    """Client with authenticated superuser."""
    app.dependency_overrides[get_current_user] = lambda: mock_superuser
    app.dependency_overrides[get_current_active_superuser] = lambda: mock_superuser
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
async def test_read_current_user(auth_client: AsyncClient, mock_user: MockUser):
    """Test getting current user."""
    response = await auth_client.get(f"{settings.API_V1_STR}/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_user.email


@pytest.mark.anyio
async def test_update_current_user(auth_client: AsyncClient, mock_user_service: MagicMock):
    """Test updating current user."""
    response = await auth_client.patch(
        f"{settings.API_V1_STR}/users/me",
        json={"full_name": "Updated Name"},
    )
    assert response.status_code == 200
    mock_user_service.update.assert_called_once()


{%- if not cookiecutter.enable_pagination %}


@pytest.mark.anyio
async def test_read_users_superuser(superuser_client: AsyncClient, mock_user_service: MagicMock):
    """Test getting all users as superuser."""
    response = await superuser_client.get(f"{settings.API_V1_STR}/users")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
{%- endif %}


@pytest.mark.anyio
async def test_read_user_by_id(
    superuser_client: AsyncClient,
    mock_user: MockUser,
    mock_user_service: MagicMock,
):
    """Test getting user by ID as superuser."""
    response = await superuser_client.get(
        f"{settings.API_V1_STR}/users/{mock_user.id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_user.email


@pytest.mark.anyio
async def test_read_user_by_id_not_found(
    superuser_client: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test getting non-existent user."""
    from app.core.exceptions import NotFoundError

    mock_user_service.get_by_id = ServiceMock(
        side_effect=NotFoundError(message="User not found")
    )

    response = await superuser_client.get(
        f"{settings.API_V1_STR}/users/{uuid4()}"
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_user_by_id(
    superuser_client: AsyncClient,
    mock_user: MockUser,
    mock_user_service: MagicMock,
):
    """Test updating user by ID as superuser."""
    response = await superuser_client.patch(
        f"{settings.API_V1_STR}/users/{mock_user.id}",
        json={"full_name": "Admin Updated"},
    )
    assert response.status_code == 200
    mock_user_service.update.assert_called_once()


@pytest.mark.anyio
async def test_delete_user_by_id(
    superuser_client: AsyncClient,
    mock_user: MockUser,
    mock_user_service: MagicMock,
):
    """Test deleting user by ID as superuser."""
    response = await superuser_client.delete(
        f"{settings.API_V1_STR}/users/{mock_user.id}"
    )
    assert response.status_code == 204
    mock_user_service.delete.assert_called_once()


@pytest.mark.anyio
async def test_delete_user_by_id_not_found(
    superuser_client: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test deleting non-existent user."""
    from app.core.exceptions import NotFoundError

    mock_user_service.delete = ServiceMock(
        side_effect=NotFoundError(message="User not found")
    )

    response = await superuser_client.delete(
        f"{settings.API_V1_STR}/users/{uuid4()}"
    )
    assert response.status_code == 404
{%- endif %}
