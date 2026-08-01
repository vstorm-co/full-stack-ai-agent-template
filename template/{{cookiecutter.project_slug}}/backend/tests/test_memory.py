"""Tests for the agent memory capability factory and the user memory service."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from pydantic_ai_harness.memory import InMemoryStore, Memory

from app.agents import memory as memory_module
from app.agents.memory import (
    MEMORY_AGENT_NAME,
    MEMORY_TOOL_NAMES,
    build_memory_capability,
    canonical_memory_filename,
    memory_namespace,
    memory_scope_prefix,
)
from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsError,
    BadRequestError,
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.user_memory import MemoryFileWrite
from app.services.user_memory import _LIST_LIMIT, UserMemoryService


class TestScope:
    def test_namespace_is_prefixed_user_id(self):
        assert memory_namespace("abc") == "user-abc"

    def test_scope_prefix_nests_agent_under_namespace(self):
        uid = str(uuid4())
        assert memory_scope_prefix(uid) == f"user-{uid}/{MEMORY_AGENT_NAME}/"

    def test_tool_names_match_harness_toolset(self):
        """The harness owns these names; a rename there must fail here, loudly."""
        toolset = Memory(store=InMemoryStore(), namespace="user-test").get_toolset()
        assert set(toolset.tools) == MEMORY_TOOL_NAMES

    @pytest.mark.parametrize(
        ("given", "expected"),
        [("preferences", "preferences.md"), ("notes.md", "notes.md"), (" x.md ", "x.md")],
    )
    def test_canonical_filename_normalizes_flat_names(self, given: str, expected: str):
        assert canonical_memory_filename(given) == expected

    @pytest.mark.parametrize("bad", ["notes/deals.md", "..", "a" * 100, ".hidden.md", "-x.md"])
    def test_canonical_filename_rejects_names_the_agent_cannot_use(self, bad: str):
        with pytest.raises(ValueError):
            canonical_memory_filename(bad)


@pytest.mark.anyio
class TestBuildMemoryCapability:
    async def test_none_when_flag_off(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_MEMORY", False)
        assert await build_memory_capability(str(uuid4())) is None

    async def test_none_when_store_unavailable(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_MEMORY", True)
        with patch.object(memory_module, "get_memory_store", return_value=None):
            assert await build_memory_capability(str(uuid4())) is None

    async def test_builds_capability_with_user_namespace(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_MEMORY", True)
        store = InMemoryStore()
        uid = str(uuid4())
        with patch.object(memory_module, "get_memory_store", return_value=store):
            cap = await build_memory_capability(uid)
        assert isinstance(cap, Memory)
        assert cap.store is store
        assert cap.namespace == f"user-{uid}"
        assert cap.agent_name == MEMORY_AGENT_NAME


@pytest.fixture
def service() -> UserMemoryService:
    return UserMemoryService(InMemoryStore())


@pytest.mark.anyio
class TestUserMemoryService:
    async def test_store_none_raises_503(self):
        svc = UserMemoryService(None)
        with pytest.raises(ExternalServiceError):
            await svc.list_files(user_id=uuid4())

    async def test_create_list_read_roundtrip(self, service: UserMemoryService):
        uid = uuid4()
        created = await service.write_file(
            user_id=uid, path="MEMORY.md", data=MemoryFileWrite(content="- base currency: EUR")
        )
        assert created.path == "MEMORY.md"
        assert created.content == "- base currency: EUR"
        assert created.truncated is False

        listing = await service.list_files(user_id=uid)
        assert listing.total == 1
        assert listing.items[0].path == "MEMORY.md"
        assert listing.items[0].size_chars == len("- base currency: EUR")

        read = await service.read_file(user_id=uid, path="MEMORY.md")
        assert read.version == created.version

    async def test_read_missing_raises_404(self, service: UserMemoryService):
        with pytest.raises(NotFoundError):
            await service.read_file(user_id=uuid4(), path="MEMORY.md")

    async def test_cas_update_and_stale_conflict(self, service: UserMemoryService):
        uid = uuid4()
        created = await service.write_file(
            user_id=uid, path="MEMORY.md", data=MemoryFileWrite(content="v1")
        )
        updated = await service.write_file(
            user_id=uid,
            path="MEMORY.md",
            data=MemoryFileWrite(content="v2", version=created.version),
        )
        assert updated.content == "v2"

        with pytest.raises(AlreadyExistsError) as exc_info:
            await service.write_file(
                user_id=uid,
                path="MEMORY.md",
                data=MemoryFileWrite(content="v3", version=created.version),
            )
        assert exc_info.value.code == "MEMORY_VERSION_CONFLICT"

    async def test_create_only_conflicts_when_file_exists(self, service: UserMemoryService):
        uid = uuid4()
        await service.write_file(user_id=uid, path="MEMORY.md", data=MemoryFileWrite(content="x"))
        with pytest.raises(AlreadyExistsError):
            await service.write_file(
                user_id=uid, path="MEMORY.md", data=MemoryFileWrite(content="y")
            )

    async def test_delete_with_stale_version_conflicts(self, service: UserMemoryService):
        uid = uuid4()
        created = await service.write_file(
            user_id=uid, path="notes.md", data=MemoryFileWrite(content="v1")
        )
        await service.write_file(
            user_id=uid,
            path="notes.md",
            data=MemoryFileWrite(content="v2", version=created.version),
        )
        with pytest.raises(AlreadyExistsError):
            await service.delete_file(user_id=uid, path="notes.md", version=created.version)

    async def test_delete_roundtrip(self, service: UserMemoryService):
        uid = uuid4()
        created = await service.write_file(
            user_id=uid, path="notes.md", data=MemoryFileWrite(content="x")
        )
        await service.delete_file(user_id=uid, path="notes.md", version=created.version)
        with pytest.raises(NotFoundError):
            await service.read_file(user_id=uid, path="notes.md")

    async def test_delete_missing_raises_404(self, service: UserMemoryService):
        with pytest.raises(NotFoundError):
            await service.delete_file(user_id=uuid4(), path="nope.md", version="1")

    @pytest.mark.parametrize("bad_path", ["../escape", "a//b", "", "a/", "/a", "a b"])
    async def test_invalid_paths_raise_400(self, service: UserMemoryService, bad_path: str):
        with pytest.raises(BadRequestError):
            await service.read_file(user_id=uuid4(), path=bad_path)

    async def test_users_are_isolated(self, service: UserMemoryService):
        uid_a, uid_b = uuid4(), uuid4()
        await service.write_file(
            user_id=uid_a, path="MEMORY.md", data=MemoryFileWrite(content="secret")
        )
        listing = await service.list_files(user_id=uid_b)
        assert listing.total == 0
        with pytest.raises(NotFoundError):
            await service.read_file(user_id=uid_b, path="MEMORY.md")

    async def test_content_length_is_schema_bounded(self):
        with pytest.raises(ValueError):
            MemoryFileWrite(content="x" * 65_537)

    async def test_write_normalizes_name_to_markdown(self, service: UserMemoryService):
        written = await service.write_file(
            user_id=uuid4(), path="preferences", data=MemoryFileWrite(content="x")
        )
        assert written.path == "preferences.md"

    @pytest.mark.parametrize("bad_path", ["notes/deals.md", "a" * 100, ".hidden.md"])
    async def test_write_rejects_names_the_agent_cannot_use(
        self, service: UserMemoryService, bad_path: str
    ):
        with pytest.raises(BadRequestError):
            await service.write_file(
                user_id=uuid4(), path=bad_path, data=MemoryFileWrite(content="x")
            )

    async def test_write_keeps_content_whitespace_verbatim(self, service: UserMemoryService):
        uid = uuid4()
        content = "  - indented\n\n"
        written = await service.write_file(
            user_id=uid, path="MEMORY.md", data=MemoryFileWrite(content=content)
        )
        assert written.content == content
        assert (await service.read_file(user_id=uid, path="MEMORY.md")).content == content

    async def test_duplicate_create_reports_its_own_code(self, service: UserMemoryService):
        uid = uuid4()
        await service.write_file(user_id=uid, path="MEMORY.md", data=MemoryFileWrite(content="x"))
        with pytest.raises(AlreadyExistsError) as exc_info:
            await service.write_file(
                user_id=uid, path="MEMORY.md", data=MemoryFileWrite(content="y")
            )
        assert exc_info.value.code == "MEMORY_FILE_EXISTS"

    async def test_list_flags_truncation_past_the_cap(self, service: UserMemoryService):
        uid = uuid4()
        for index in range(_LIST_LIMIT + 1):
            await service.write_file(
                user_id=uid, path=f"note-{index:03d}.md", data=MemoryFileWrite(content="x")
            )
        listing = await service.list_files(user_id=uid)
        assert listing.truncated is True
        assert len(listing.items) == _LIST_LIMIT

    async def test_list_reports_no_truncation_within_the_cap(self, service: UserMemoryService):
        uid = uuid4()
        await service.write_file(user_id=uid, path="notes.md", data=MemoryFileWrite(content="x"))
        listing = await service.list_files(user_id=uid)
        assert listing.truncated is False
