"""Read/write access to the current user's agent memory files.

Thin layer over the harness ``MemoryStore`` — the store *is* the data layer, so
there is no repository. Every path is resolved under the caller's namespace via
``memory_scope_prefix``; the namespace is never client-supplied, which is the
whole tenant boundary.

Writes are held to the flat ``<name>.md`` grammar the agent's tools accept, since
a file the agent can neither list, read nor search is worse than no file at all.
Reads and deletes stay permissive, so any name already present in the store can
still be inspected and removed.
"""

import asyncio
import logging
from uuid import UUID

from pydantic_ai_harness.memory import MemoryConflictError, MemoryStore
from pydantic_ai_harness.memory._store import validate_store_path

from app.agents.memory import (
    MAX_MEMORY_FILE_CHARS,
    canonical_memory_filename,
    memory_scope_prefix,
)
from app.core.exceptions import (
    AlreadyExistsError,
    BadRequestError,
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.user_memory import (
    MemoryFileEntry,
    MemoryFileList,
    MemoryFileRead,
    MemoryFileWrite,
)

logger = logging.getLogger(__name__)

_LIST_LIMIT = 100


class UserMemoryService:
    """CRUD over one user's memory files; raises domain exceptions."""

    def __init__(self, store: MemoryStore | None) -> None:
        self.store = store

    def _require_store(self) -> MemoryStore:
        if self.store is None:
            raise ExternalServiceError(message="Agent memory is not enabled")
        return self.store

    def _scoped_path(self, *, user_id: UUID, path: str) -> str:
        scoped = f"{memory_scope_prefix(str(user_id))}{path}"
        try:
            validate_store_path(scoped)
        except ValueError as e:
            raise BadRequestError(
                message=f"Invalid memory path: {path!r}", details={"path": path}
            ) from e
        return scoped

    def _canonical_name(self, path: str) -> str:
        try:
            return canonical_memory_filename(path)
        except ValueError as e:
            raise BadRequestError(
                message=(
                    f"Invalid memory file name: {path!r} — use a flat name such as "
                    "'preferences.md' (letters, digits, dots, dashes; no folders)"
                ),
                details={"path": path},
            ) from e

    async def list_files(self, *, user_id: UUID) -> MemoryFileList:
        """List the user's memory files with sizes and CAS versions."""
        store = self._require_store()
        prefix = memory_scope_prefix(str(user_id))
        # One over the cap tells the caller whether anything was left out.
        paths = await store.list_paths(prefix, limit=_LIST_LIMIT + 1)
        truncated = len(paths) > _LIST_LIMIT
        listed = paths[:_LIST_LIMIT]
        files = await asyncio.gather(
            *(store.read(path, max_chars=MAX_MEMORY_FILE_CHARS) for path in listed)
        )
        items = [
            MemoryFileEntry(
                path=path.removeprefix(prefix),
                size_chars=len(file.content),
                version=file.version,
            )
            for path, file in zip(listed, files, strict=True)
            if file is not None
        ]
        return MemoryFileList(items=items, total=len(items), truncated=truncated)

    async def read_file(self, *, user_id: UUID, path: str) -> MemoryFileRead:
        """Read one memory file."""
        store = self._require_store()
        scoped = self._scoped_path(user_id=user_id, path=path)
        file = await store.read(scoped, max_chars=MAX_MEMORY_FILE_CHARS)
        if file is None:
            raise NotFoundError(message=f"Memory file not found: {path!r}", details={"path": path})
        return MemoryFileRead(
            path=path, content=file.content, version=file.version, truncated=file.truncated
        )

    async def write_file(
        self, *, user_id: UUID, path: str, data: MemoryFileWrite
    ) -> MemoryFileRead:
        """Create (``version=None``) or CAS-update one memory file."""
        store = self._require_store()
        name = self._canonical_name(path)
        scoped = self._scoped_path(user_id=user_id, path=name)
        try:
            mutation = await store.write(scoped, data.content, expected_version=data.version)
        except MemoryConflictError as e:
            if data.version is None:
                raise AlreadyExistsError(
                    message=f"Memory file already exists: {name!r}",
                    code="MEMORY_FILE_EXISTS",
                    details={"path": name},
                ) from e
            raise AlreadyExistsError(
                message="Memory file changed since it was loaded",
                code="MEMORY_VERSION_CONFLICT",
                details={"path": name},
            ) from e
        if mutation.version is None:
            # ``version`` is only ever unset for a delete; re-read rather than
            # hand the client a version it cannot write back with.
            return await self.read_file(user_id=user_id, path=name)
        return MemoryFileRead(
            path=name, content=data.content, version=mutation.version, truncated=False
        )

    async def delete_file(self, *, user_id: UUID, path: str, version: str) -> None:
        """CAS-delete one memory file."""
        store = self._require_store()
        scoped = self._scoped_path(user_id=user_id, path=path)
        try:
            await store.delete(scoped, expected_version=version)
        except MemoryConflictError as e:
            # The store reports a missing file and a stale version the same way;
            # only a follow-up read tells them apart.
            if await store.read(scoped, max_chars=1) is None:
                raise NotFoundError(
                    message=f"Memory file not found: {path!r}", details={"path": path}
                ) from e
            raise AlreadyExistsError(
                message="Memory file changed since it was loaded",
                code="MEMORY_VERSION_CONFLICT",
                details={"path": path},
            ) from e
