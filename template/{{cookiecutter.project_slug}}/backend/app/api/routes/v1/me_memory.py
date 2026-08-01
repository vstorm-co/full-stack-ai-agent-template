"""Current user's agent memory files.

Nested under ``/me/memory`` because these routes always operate on the calling
user's own namespace. File paths contain ``/``, so they travel as a query
parameter rather than a path segment.
"""

from typing import Any

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, UserMemorySvc
from app.schemas.user_memory import MemoryFileList, MemoryFileRead, MemoryFileWrite

router = APIRouter()

PathParam = Query(min_length=1, max_length=512)


@router.get("", response_model=MemoryFileList)
async def list_memory_files(service: UserMemorySvc, user: CurrentUser) -> Any:
    """List the current user's memory files."""
    return await service.list_files(user_id=user.id)


@router.get("/file", response_model=MemoryFileRead)
async def read_memory_file(
    service: UserMemorySvc,
    user: CurrentUser,
    path: str = PathParam,
) -> Any:
    """Read one memory file."""
    return await service.read_file(user_id=user.id, path=path)


@router.put("/file", response_model=MemoryFileRead)
async def write_memory_file(
    data: MemoryFileWrite,
    service: UserMemorySvc,
    user: CurrentUser,
    path: str = PathParam,
) -> Any:
    """Create (``version: null``) or CAS-update (``version`` set) one memory file."""
    return await service.write_file(user_id=user.id, path=path, data=data)


@router.delete("/file", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_memory_file(
    service: UserMemorySvc,
    user: CurrentUser,
    path: str = PathParam,
    version: str = Query(min_length=1),
) -> Any:
    """CAS-delete one memory file."""
    await service.delete_file(user_id=user.id, path=path, version=version)
    return None
