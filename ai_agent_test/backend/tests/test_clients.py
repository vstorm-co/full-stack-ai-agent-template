"""Tests for client modules."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.clients.redis import RedisClient


class TestRedisClient:
    """Tests for RedisClient."""

    @pytest.fixture
    def redis_client(self) -> RedisClient:
        """Create a RedisClient instance."""
        return RedisClient(url="redis://localhost:6379")

    @pytest.fixture
    def mock_aioredis(self) -> MagicMock:
        """Create a mock aioredis client."""
        mock = MagicMock()
        mock.get = AsyncMock(return_value="value")
        mock.set = AsyncMock()
        mock.delete = AsyncMock(return_value=1)
        mock.exists = AsyncMock(return_value=1)
        mock.ping = AsyncMock()
        mock.close = AsyncMock()
        return mock

    @pytest.mark.anyio
    async def test_connect(self, redis_client: RedisClient):
        """Test Redis connection."""
        with patch("app.clients.redis.aioredis") as mock_aioredis:
            mock_client = MagicMock()
            mock_aioredis.from_url.return_value = mock_client

            await redis_client.connect()

            assert redis_client.client is not None
            mock_aioredis.from_url.assert_called_once()

    @pytest.mark.anyio
    async def test_close(self, redis_client: RedisClient, mock_aioredis: MagicMock):
        """Test closing Redis connection."""
        redis_client.client = mock_aioredis

        await redis_client.close()

        mock_aioredis.close.assert_called_once()
        assert redis_client.client is None

    @pytest.mark.anyio
    async def test_close_when_not_connected(self, redis_client: RedisClient):
        """Test closing when not connected does nothing."""
        redis_client.client = None

        await redis_client.close()  # Should not raise

    @pytest.mark.anyio
    async def test_get(self, redis_client: RedisClient, mock_aioredis: MagicMock):
        """Test getting a value."""
        redis_client.client = mock_aioredis

        result = await redis_client.get("test_key")

        assert result == "value"
        mock_aioredis.get.assert_called_once_with("test_key")

    @pytest.mark.anyio
    async def test_get_not_connected(self, redis_client: RedisClient):
        """Test getting when not connected raises error."""
        redis_client.client = None

        with pytest.raises(RuntimeError, match="not connected"):
            await redis_client.get("test_key")

    @pytest.mark.anyio
    async def test_set(self, redis_client: RedisClient, mock_aioredis: MagicMock):
        """Test setting a value."""
        redis_client.client = mock_aioredis

        await redis_client.set("test_key", "test_value")

        mock_aioredis.set.assert_called_once_with("test_key", "test_value", ex=None)

    @pytest.mark.anyio
    async def test_set_with_ttl(self, redis_client: RedisClient, mock_aioredis: MagicMock):
        """Test setting a value with TTL."""
        redis_client.client = mock_aioredis

        await redis_client.set("test_key", "test_value", ttl=60)

        mock_aioredis.set.assert_called_once_with("test_key", "test_value", ex=60)

    @pytest.mark.anyio
    async def test_set_not_connected(self, redis_client: RedisClient):
        """Test setting when not connected raises error."""
        redis_client.client = None

        with pytest.raises(RuntimeError, match="not connected"):
            await redis_client.set("test_key", "test_value")

    @pytest.mark.anyio
    async def test_delete(self, redis_client: RedisClient, mock_aioredis: MagicMock):
        """Test deleting a key."""
        redis_client.client = mock_aioredis

        result = await redis_client.delete("test_key")

        assert result == 1
        mock_aioredis.delete.assert_called_once_with("test_key")

    @pytest.mark.anyio
    async def test_delete_not_connected(self, redis_client: RedisClient):
        """Test deleting when not connected raises error."""
        redis_client.client = None

        with pytest.raises(RuntimeError, match="not connected"):
            await redis_client.delete("test_key")

    @pytest.mark.anyio
    async def test_exists(self, redis_client: RedisClient, mock_aioredis: MagicMock):
        """Test checking if key exists."""
        redis_client.client = mock_aioredis

        result = await redis_client.exists("test_key")

        assert result is True
        mock_aioredis.exists.assert_called_once_with("test_key")

    @pytest.mark.anyio
    async def test_exists_not_connected(self, redis_client: RedisClient):
        """Test exists when not connected raises error."""
        redis_client.client = None

        with pytest.raises(RuntimeError, match="not connected"):
            await redis_client.exists("test_key")

    @pytest.mark.anyio
    async def test_ping_connected(self, redis_client: RedisClient, mock_aioredis: MagicMock):
        """Test ping when connected."""
        redis_client.client = mock_aioredis

        result = await redis_client.ping()

        assert result is True
        mock_aioredis.ping.assert_called_once()

    @pytest.mark.anyio
    async def test_ping_not_connected(self, redis_client: RedisClient):
        """Test ping when not connected returns False."""
        redis_client.client = None

        result = await redis_client.ping()

        assert result is False

    @pytest.mark.anyio
    async def test_ping_exception(self, redis_client: RedisClient, mock_aioredis: MagicMock):
        """Test ping when exception occurs returns False."""
        redis_client.client = mock_aioredis
        mock_aioredis.ping = AsyncMock(side_effect=Exception("Connection error"))

        result = await redis_client.ping()

        assert result is False

    def test_raw_property(self, redis_client: RedisClient, mock_aioredis: MagicMock):
        """Test accessing raw client."""
        redis_client.client = mock_aioredis

        result = redis_client.raw

        assert result == mock_aioredis

    def test_raw_property_not_connected(self, redis_client: RedisClient):
        """Test accessing raw client when not connected raises error."""
        redis_client.client = None

        with pytest.raises(RuntimeError, match="not connected"):
            _ = redis_client.raw
