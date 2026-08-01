"""Per-user persistent memory for the assistant.

Builds the pydantic-ai-harness ``Memory`` capability over the process-wide
Postgres store (see ``app.db.memory_pool``). Each user gets an isolated
namespace — store paths look like ``user-<uuid>/main/MEMORY.md`` — resolved
from the authenticated user here, never from model-controlled input.
"""

import logging
from typing import TYPE_CHECKING

from pydantic_ai import ModelRetry
from pydantic_ai_harness.memory import Memory
from pydantic_ai_harness.memory._capability import _DEFAULT_GUIDANCE
from pydantic_ai_harness.memory._toolset import normalize_filename

from app.core.config import settings
from app.db.memory_pool import get_memory_store

if TYPE_CHECKING:
    from app.agents.assistant import Deps

logger = logging.getLogger(__name__)

# The tools the harness Memory capability registers. Mirrors the frontend
# ``MEMORY_TOOLS`` in ``lib/agent-tools.ts``; the names are owned by the
# harness, so ``test_tool_names_match_harness_toolset`` pins them.
MEMORY_TOOL_NAMES = frozenset({"write_memory", "read_memory", "delete_memory", "search_memory"})
MAX_MEMORY_FILE_CHARS = 65_536
MEMORY_AGENT_NAME = "main"

# The injected notebook makes recall invisible: asked "what do you remember about
# me?", the model would answer straight from the injected context with no tool
# call, so the user never sees where the answer came from. Route such questions
# through the tools — every call renders as a memory card in the chat.
MEMORY_GUIDANCE = (
    _DEFAULT_GUIDANCE
    + " Exception: whenever the user asks about your memory or notes themselves"
    " -- what you remember, what you know about them, what you have written"
    " down -- you MUST call `read_memory` (or `search_memory` for a specific"
    " topic) before answering, and answer from the tool result. For such"
    " questions, answering from the injected context without the tool call is"
    " an error: the user is auditing their memory and must see the actual read."
    " Never guess dates in notes: only date an entry with a date you actually"
    " know from the conversation or a tool, otherwise write the fact undated."
)


def memory_namespace(user_id: str) -> str:
    """Store namespace for one user's memory."""
    return f"user-{user_id}"


def memory_scope_prefix(user_id: str) -> str:
    """Store-path prefix all of one user's memory files live under."""
    return f"{memory_namespace(user_id)}/{MEMORY_AGENT_NAME}/"


def canonical_memory_filename(path: str) -> str:
    """Return *path* as the flat ``<name>.md`` filename the agent's tools accept.

    The toolset lists, reads and searches only flat ``*.md`` names of at most 80
    characters starting with a letter or digit. A nested or differently-shaped
    name is invisible to the agent and makes ``search_memory`` raise, so every
    write goes through here first. Raises ``ValueError`` for a name that cannot
    be represented.
    """
    try:
        return normalize_filename(path)
    except ModelRetry as e:
        raise ValueError(str(e)) from e


async def build_memory_capability(user_id: str) -> "Memory[Deps] | None":
    """Build the per-user Memory capability, or ``None`` when unavailable.

    A static namespace (rather than a ``ctx.deps`` callable) keeps CLI and
    other user-less agent paths from silently writing to a ``user-None`` scope.
    """
    if not settings.ENABLE_MEMORY:
        return None
    store = await get_memory_store()
    if store is None:
        logger.warning("Agent memory enabled but store unavailable; running without memory")
        return None
    return Memory(
        store=store,
        namespace=memory_namespace(user_id),
        agent_name=MEMORY_AGENT_NAME,
        max_memory_size=MAX_MEMORY_FILE_CHARS,
        guidance=MEMORY_GUIDANCE,
    )
