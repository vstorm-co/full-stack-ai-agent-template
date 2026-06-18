"""Health endpoint tests."""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Test liveness probe."""
    response = await client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.anyio
async def test_readiness_check(client: AsyncClient):
    """Test readiness probe with mocked dependencies."""
    response = await client.get(f"{settings.API_V1_STR}/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ready", "degraded"]
    assert "checks" in data


@pytest.mark.anyio
async def test_readiness_check_redis_healthy(client: AsyncClient, mock_redis):
    """Test readiness when Redis is healthy."""
    mock_redis.ping = AsyncMock(return_value=True)

    response = await client.get(f"{settings.API_V1_STR}/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["checks"]["redis"]["status"] == "healthy"
    assert "latency_ms" in data["checks"]["redis"]


@pytest.mark.anyio
async def test_readiness_check_redis_unhealthy(client: AsyncClient, mock_redis):
    """Test readiness when Redis is unhealthy."""
    mock_redis.ping = AsyncMock(side_effect=Exception("Connection failed"))

    response = await client.get(f"{settings.API_V1_STR}/ready")
    # Should return 503 when Redis is down
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["redis"]["status"] == "unhealthy"
    assert "error" in data["checks"]["redis"]


@pytest.mark.anyio
async def test_readiness_check_db_healthy(client: AsyncClient, mock_db_session):
    """Test readiness when database is healthy."""
    # Mock successful DB query
    mock_db_session.execute = AsyncMock()

    response = await client.get(f"{settings.API_V1_STR}/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["checks"]["database"]["status"] == "healthy"


@pytest.mark.anyio
async def test_readiness_check_db_unhealthy(client: AsyncClient, mock_db_session):
    """Test readiness when database is unhealthy."""
    mock_db_session.execute = AsyncMock(side_effect=Exception("DB connection failed"))

    response = await client.get(f"{settings.API_V1_STR}/ready")
    # Should return 503 when DB is down
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["database"]["status"] == "unhealthy"
