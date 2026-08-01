"""Schemas for the current user's agent memory files."""

from pydantic import ConfigDict, Field

from app.agents.memory import MAX_MEMORY_FILE_CHARS
from app.schemas.base import BaseSchema

# File content travels verbatim in both directions. BaseSchema strips surrounding
# whitespace, which would drop the trailing newline every harness write appends
# and eat the indentation of a leading code block.
_VERBATIM_CONTENT = ConfigDict(str_strip_whitespace=False)


class MemoryFileEntry(BaseSchema):
    """One memory file as shown in listings (path is scope-relative)."""

    path: str
    size_chars: int
    version: str


class MemoryFileList(BaseSchema):
    """All of one user's memory files."""

    items: list[MemoryFileEntry]
    total: int
    truncated: bool = False
    """More files exist in the store than ``items`` carries."""


class MemoryFileRead(BaseSchema):
    """Full content of one memory file, with its CAS version."""

    model_config = _VERBATIM_CONTENT

    path: str
    content: str
    version: str
    truncated: bool


class MemoryFileWrite(BaseSchema):
    """Full-content write. ``version=None`` creates; a version updates via CAS."""

    model_config = _VERBATIM_CONTENT

    content: str = Field(max_length=MAX_MEMORY_FILE_CHARS)
    version: str | None = None
