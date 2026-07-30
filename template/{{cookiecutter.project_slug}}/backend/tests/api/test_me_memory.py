"""Tests for the /me/memory routes."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic_ai_harness.memory import InMemoryStore

from app.api.deps import get_current_user, get_user_memory_service
{%- if cookiecutter.use_database %}
from app.api.deps import get_db_session
{%- endif %}
{%- if cookiecutter.enable_redis %}
from app.api.deps import get_redis
{%- endif %}
from app.core.config import settings
from app.main import app
from app.services.user_memory import UserMemoryService

ROOT = f"{settings.API_V1_STR}/me/memory"


class MockUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "test@example.com"
        self.full_name = "Test User"
        self.is_active = True
        self.role = "user"
        self.hashed_password = "hashed"
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def has_role(self, role) -> bool:
        if hasattr(role, "value"):
            return self.role == role.value
        return self.role == role


@pytest.fixture
def mock_user() -> MockUser:
    return MockUser()


@pytest.fixture
def memory_service() -> UserMemoryService:
    return UserMemoryService(InMemoryStore())


@pytest.fixture
async def auth_client(
    mock_user: MockUser,
    memory_service: UserMemoryService,
{%- if cookiecutter.enable_redis %}
    mock_redis,
{%- endif %}
{%- if cookiecutter.use_database %}
    mock_db_session,
{%- endif %}
) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_user_memory_service] = lambda: memory_service
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
class TestMeMemoryRoutes:
    async def test_list_with_no_files_returns_empty_listing(self, auth_client: AsyncClient):
        response = await auth_client.get(ROOT)
        assert response.status_code == 200
        assert response.json() == {"items": [], "total": 0, "truncated": False}

    async def test_create_list_read(self, auth_client: AsyncClient):
        create = await auth_client.put(
            f"{ROOT}/file",
            params={"path": "MEMORY.md"},
            json={"content": "- prefers EUR", "version": None},
        )
        assert create.status_code == 200
        body = create.json()
        assert body["path"] == "MEMORY.md"
        assert body["content"] == "- prefers EUR"

        listing = await auth_client.get(ROOT)
        assert listing.json()["total"] == 1

        read = await auth_client.get(f"{ROOT}/file", params={"path": "MEMORY.md"})
        assert read.status_code == 200
        assert read.json()["version"] == body["version"]

    async def test_read_missing_returns_404(self, auth_client: AsyncClient):
        response = await auth_client.get(f"{ROOT}/file", params={"path": "MEMORY.md"})
        assert response.status_code == 404

    async def test_stale_write_returns_409(self, auth_client: AsyncClient):
        create = await auth_client.put(
            f"{ROOT}/file", params={"path": "MEMORY.md"}, json={"content": "v1"}
        )
        version = create.json()["version"]
        update = await auth_client.put(
            f"{ROOT}/file",
            params={"path": "MEMORY.md"},
            json={"content": "v2", "version": version},
        )
        assert update.status_code == 200

        stale = await auth_client.put(
            f"{ROOT}/file",
            params={"path": "MEMORY.md"},
            json={"content": "v3", "version": version},
        )
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "MEMORY_VERSION_CONFLICT"

    async def test_delete_returns_204_then_404(self, auth_client: AsyncClient):
        create = await auth_client.put(
            f"{ROOT}/file", params={"path": "notes.md"}, json={"content": "x"}
        )
        version = create.json()["version"]

        response = await auth_client.delete(
            f"{ROOT}/file", params={"path": "notes.md", "version": version}
        )
        assert response.status_code == 204

        read = await auth_client.get(f"{ROOT}/file", params={"path": "notes.md"})
        assert read.status_code == 404

    async def test_invalid_path_returns_400(self, auth_client: AsyncClient):
        response = await auth_client.get(f"{ROOT}/file", params={"path": "../escape"})
        assert response.status_code == 400

    async def test_oversize_content_returns_422(self, auth_client: AsyncClient):
        response = await auth_client.put(
            f"{ROOT}/file", params={"path": "big.md"}, json={"content": "x" * 65_537}
        )
        assert response.status_code == 422

    async def test_nested_write_path_returns_400(self, auth_client: AsyncClient):
        response = await auth_client.put(
            f"{ROOT}/file", params={"path": "notes/deals.md"}, json={"content": "x"}
        )
        assert response.status_code == 400

    async def test_write_returns_canonical_markdown_name(self, auth_client: AsyncClient):
        response = await auth_client.put(
            f"{ROOT}/file", params={"path": "preferences"}, json={"content": "x"}
        )
        assert response.status_code == 200
        assert response.json()["path"] == "preferences.md"

    async def test_duplicate_create_returns_409_with_exists_code(self, auth_client: AsyncClient):
        await auth_client.put(f"{ROOT}/file", params={"path": "notes.md"}, json={"content": "x"})
        duplicate = await auth_client.put(
            f"{ROOT}/file", params={"path": "notes.md"}, json={"content": "y"}
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "MEMORY_FILE_EXISTS"

    async def test_write_preserves_content_whitespace(self, auth_client: AsyncClient):
        content = "  - indented\n\n"
        response = await auth_client.put(
            f"{ROOT}/file", params={"path": "MEMORY.md"}, json={"content": content}
        )
        assert response.json()["content"] == content
        read = await auth_client.get(f"{ROOT}/file", params={"path": "MEMORY.md"})
        assert read.json()["content"] == content


@pytest.mark.anyio
async def test_returns_503_when_memory_disabled(
{%- if cookiecutter.enable_redis %}
    mock_redis,
{%- endif %}
{%- if cookiecutter.use_database %}
    mock_db_session,
{%- endif %}
):
    app.dependency_overrides[get_current_user] = MockUser
    app.dependency_overrides[get_user_memory_service] = lambda: UserMemoryService(None)
{%- if cookiecutter.enable_redis %}
    app.dependency_overrides[get_redis] = lambda: mock_redis
{%- endif %}
{%- if cookiecutter.use_database %}
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
{%- endif %}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(ROOT)

    app.dependency_overrides.clear()
    assert response.status_code == 503
