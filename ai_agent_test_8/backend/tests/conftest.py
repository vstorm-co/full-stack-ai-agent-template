"""Test configuration and fixtures.

Uses anyio for async testing instead of pytest-asyncio.
This allows using the same async primitives that Starlette uses internally.
See: https://anyio.readthedocs.io/en/stable/testing.html
"""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.config import settings
from app.api.deps import get_redis
from app.clients.redis import RedisClient
from app.api.deps import get_db_session


@pytest.fixture
def anyio_backend() -> str:
    """Specify the async backend for anyio tests.

    Options: "asyncio" or "trio". We use asyncio since that's what uvicorn uses.
    """
    return "asyncio"


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


@pytest.fixture
async def mock_db_session() -> AsyncGenerator[AsyncMock, None]:
    """Create a mock database session for testing."""
    mock = AsyncMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.close = AsyncMock()
    yield mock


@pytest.fixture
async def client(
    mock_redis: MagicMock,
    mock_db_session,
) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing.

    Uses HTTPX AsyncClient with ASGITransport instead of Starlette's TestClient.
    This allows proper async testing without thread pool overhead.
    """
    # Override dependencies for testing
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db_session] = lambda: mock_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def api_key_headers() -> dict[str, str]:
    """Headers with valid API key."""
    return {settings.API_KEY_HEADER: settings.API_KEY}


# Note: For integration tests requiring authenticated users,
# use dependency overrides with mock users instead of test_user fixture.
# See tests/api/test_auth.py and tests/api/test_users.py for examples.
