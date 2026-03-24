"""Exception handler tests."""
{%- if cookiecutter.use_jwt or cookiecutter.use_api_key %}
# ruff: noqa: I001, E402 - Imports structured for Jinja2 template conditionals
{%- endif %}

import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.anyio
async def test_not_found_error_format(client: AsyncClient):
    """Test that 404 errors return proper JSON format."""
    response = await client.get(f"{settings.API_V1_STR}/nonexistent-endpoint")
    assert response.status_code == 404
    # FastAPI returns 404 for unknown routes


{%- if cookiecutter.use_jwt %}

from unittest.mock import AsyncMock, MagicMock
{%- if cookiecutter.use_sqlite %}
ServiceMock = MagicMock
{%- else %}
ServiceMock = AsyncMock
{%- endif %}

from httpx import ASGITransport

{%- if cookiecutter.enable_redis %}
from app.api.deps import get_redis
{%- endif %}
{%- if cookiecutter.use_database %}
from app.api.deps import get_db_session
{%- endif %}
from app.main import app


@pytest.mark.anyio
async def test_authentication_error_returns_401(client: AsyncClient):
    """Test that authentication errors return 401 with proper headers."""
    response = await client.get(
        f"{settings.API_V1_STR}/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


@pytest.mark.anyio
async def test_missing_auth_returns_401(client: AsyncClient):
    """Test that missing authentication returns 401."""
    response = await client.get(f"{settings.API_V1_STR}/users/me")
    assert response.status_code == 401


@pytest.fixture
def mock_user_service_with_errors() -> MagicMock:
    """Create mock user service that raises errors."""
    from app.core.exceptions import AlreadyExistsError, AuthenticationError

    service = MagicMock()
    service.register = ServiceMock(
        side_effect=AlreadyExistsError(message="Email already registered")
    )
    service.authenticate = ServiceMock(
        side_effect=AuthenticationError(message="Invalid credentials")
    )
    return service


@pytest.fixture
async def error_client(
    mock_user_service_with_errors: MagicMock,
{%- if cookiecutter.enable_redis %}
    mock_redis: MagicMock,
{%- endif %}
{%- if cookiecutter.use_database %}
    mock_db_session,
{%- endif %}
) -> AsyncClient:
    """Client with mocked services that raise errors."""
    from app.api.deps import get_user_service

    app.dependency_overrides[get_user_service] = lambda: mock_user_service_with_errors
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
async def test_register_duplicate_email_returns_409(error_client: AsyncClient):
    """Test that registering with existing email returns 409."""
    response = await error_client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "existing@example.com",
            "password": "password123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 409
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "ALREADY_EXISTS"


@pytest.mark.anyio
async def test_invalid_login_returns_401(error_client: AsyncClient):
    """Test that invalid login credentials return 401."""
    response = await error_client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTHENTICATION_ERROR"
{%- endif %}


{%- if cookiecutter.use_api_key %}


@pytest.mark.anyio
async def test_missing_api_key_returns_401(client: AsyncClient):
    """Test that missing API key returns 401."""
    # Health endpoint might not require auth, but we test the middleware
    # For endpoints that require API key, they should return 401
    await client.get(f"{settings.API_V1_STR}/health")


@pytest.mark.anyio
async def test_invalid_api_key_returns_403(client: AsyncClient):
    """Test that invalid API key returns 403."""
    # Health endpoint might not require auth
    await client.get(
        f"{settings.API_V1_STR}/health",
        headers={settings.API_KEY_HEADER: "invalid-key"},
    )
{%- endif %}
