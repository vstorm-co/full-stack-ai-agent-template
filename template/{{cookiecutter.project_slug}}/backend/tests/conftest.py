"""Test configuration and fixtures.

Uses anyio for async testing instead of pytest-asyncio.
This allows using the same async primitives that Starlette uses internally.
See: https://anyio.readthedocs.io/en/stable/testing.html
"""
{%- if cookiecutter.enable_redis or cookiecutter.use_database or cookiecutter.use_api_key %}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
{%- endif %}

from collections.abc import AsyncGenerator
{%- if cookiecutter.enable_redis %}
from unittest.mock import AsyncMock, MagicMock
{%- elif cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
from unittest.mock import AsyncMock
{%- elif cookiecutter.use_sqlite %}
from unittest.mock import MagicMock
{%- endif %}

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
{%- if cookiecutter.use_api_key %}
from app.core.config import settings
{%- endif %}
{%- if cookiecutter.enable_redis %}
from app.api.deps import get_redis
from app.clients.redis import RedisClient
{%- endif %}
{%- if cookiecutter.use_database %}
from app.api.deps import get_db_session
{%- endif %}


@pytest.fixture
def anyio_backend() -> str:
    """Specify the async backend for anyio tests.

    Options: "asyncio" or "trio". We use asyncio since that's what uvicorn uses.
    """
    return "asyncio"


{%- if cookiecutter.enable_redis %}


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create a mock Redis client for testing."""
    mock = MagicMock(spec=RedisClient)
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.incr = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    return mock
{%- endif %}


{%- if cookiecutter.use_postgresql %}


@pytest.fixture
async def mock_db_session() -> AsyncGenerator[AsyncMock, None]:
    """Create a mock database session for testing."""
    mock = AsyncMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.close = AsyncMock()
    yield mock
{%- endif %}


{%- if cookiecutter.use_sqlite %}


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Create a mock database session for testing."""
    mock = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock.execute.return_value = mock_result
    mock.commit = MagicMock()
    mock.rollback = MagicMock()
    mock.close = MagicMock()
    return mock
{%- endif %}


{%- if cookiecutter.use_mongodb %}


@pytest.fixture
async def mock_db_session() -> AsyncMock:
    """Create a mock MongoDB session for testing."""
    mock = AsyncMock()
    mock.command = AsyncMock(return_value={"ok": 1})
    return mock
{%- endif %}


@pytest.fixture
async def client(
{%- if cookiecutter.enable_redis %}
    mock_redis: MagicMock,
{%- endif %}
{%- if cookiecutter.use_database %}
    mock_db_session,
{%- endif %}
) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing.

    Uses HTTPX AsyncClient with ASGITransport instead of Starlette's TestClient.
    This allows proper async testing without thread pool overhead.
    """
    # Override dependencies for testing
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

    # Clear overrides after test
    app.dependency_overrides.clear()


{%- if cookiecutter.use_api_key %}


@pytest.fixture
def api_key_headers() -> dict[str, str]:
    """Headers with valid API key."""
    return {settings.API_KEY_HEADER: settings.API_KEY}
{%- endif %}


{%- if cookiecutter.use_jwt %}
# Note: For integration tests requiring authenticated users,
# use dependency overrides with mock users instead of test_user fixture.
# See tests/api/test_auth.py and tests/api/test_users.py for examples.
{%- endif %}
