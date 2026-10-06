"""Per-user persistent memory for the assistant.

Builds the pydantic-ai-harness ``Memory`` capability over the process-wide
Postgres store (see ``app.db.memory_pool``). Each user gets an isolated
namespace, resolved from the authenticated user here, never from
model-controlled input:
{%- if cookiecutter.enable_teams %}
``user-<uuid>/org-<uuid>/main/MEMORY.md`` — one notebook per organisation the
user works in, so what the agent learns in one organisation's conversations is
never injected into another's.
{%- else %}
``user-<uuid>/main/MEMORY.md``.
{%- endif %}
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

# The tools the harness Memory capability registers. Mirrors ``isMemoryTool`` in
# the frontend's ``components/chat/tool-results/memory.tsx``; the names are owned
# by the harness, so ``test_tool_names_match_harness_toolset`` pins them.
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


def memory_user_prefix(user_id: str) -> str:
    """Store-path prefix of everything one user has remembered, in any scope."""
    return f"user-{user_id}/"


{%- if cookiecutter.enable_teams %}


def memory_namespace(user_id: str, organization_id: str) -> str:
    """Store namespace for one user's memory within one organisation."""
    return f"{memory_user_prefix(user_id)}org-{organization_id}"


def memory_scope_prefix(user_id: str, organization_id: str) -> str:
    """Store-path prefix of one user's memory files within one organisation."""
    return f"{memory_namespace(user_id, organization_id)}/{MEMORY_AGENT_NAME}/"
{%- else %}


def memory_namespace(user_id: str) -> str:
    """Store namespace for one user's memory."""
    return memory_user_prefix(user_id).rstrip("/")


def memory_scope_prefix(user_id: str) -> str:
    """Store-path prefix all of one user's memory files live under."""
    return f"{memory_namespace(user_id)}/{MEMORY_AGENT_NAME}/"
{%- endif %}


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


{%- if cookiecutter.enable_teams %}
async def build_memory_capability(
    user_id: str, organization_id: str | None
) -> "Memory[Deps] | None":
    """Build the user's Memory capability for one organisation, or ``None``.

    A static namespace (rather than a ``ctx.deps`` callable) keeps CLI and
    other user-less agent paths from silently writing to a ``user-None`` scope.
    Without an organisation there is no memory at all, rather than one shared
    across every organisation the user belongs to.
    """
    if not settings.ENABLE_MEMORY:
        return None
    if organization_id is None:
        logger.warning("No organisation for this turn; running without memory")
        return None
    namespace = memory_namespace(user_id, organization_id)
{%- else %}
async def build_memory_capability(user_id: str) -> "Memory[Deps] | None":
    """Build the per-user Memory capability, or ``None`` when unavailable.

    A static namespace (rather than a ``ctx.deps`` callable) keeps CLI and
    other user-less agent paths from silently writing to a ``user-None`` scope.
    """
    if not settings.ENABLE_MEMORY:
        return None
    namespace = memory_namespace(user_id)
{%- endif %}
    store = await get_memory_store()
    if store is None:
        logger.warning("Agent memory enabled but store unavailable; running without memory")
        return None
    return Memory(
        store=store,
        namespace=namespace,
        agent_name=MEMORY_AGENT_NAME,
        max_memory_size=MAX_MEMORY_FILE_CHARS,
        guidance=MEMORY_GUIDANCE,
    )
