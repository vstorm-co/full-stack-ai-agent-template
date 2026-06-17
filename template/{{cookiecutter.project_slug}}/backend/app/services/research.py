"""Deep-research toolkit — builds the planner's capabilities for one turn.

The deep-research assistant is the normal assistant plus three composable
capabilities:

  - **todo planner** (``pydantic-ai-todo``) — a shared plan whose async storage
    event emitter streams each change to the client as a live checklist.
  - **subagents** (``subagents-pydantic-ai``) — parallel researcher/analyst/writer
    delegates, polled for live status cards.
  - **context manager** (``summarization-pydantic-ai``) — keeps the planner's
    context bounded, surfacing a usage meter and a "compacted" badge.

These can only be built where the live ``WebSocket`` and ``conversation_id`` are
known — inside :class:`~app.services.agent_session.AgentSession` — so this module
exposes a builder the session owns for the duration of a turn. The returned
capabilities are ordered with the context manager last, which
``summarization-pydantic-ai`` requires.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic_ai.capabilities import WebFetch, WebSearch
from pydantic_ai.usage import UsageLimits
from pydantic_ai_summarization import ContextManagerCapability
from pydantic_ai_todo import (
    AsyncMemoryStorage,
{%- if cookiecutter.use_postgresql %}
    AsyncPostgresStorage,
{%- endif %}
    TodoCapability,
    TodoEvent,
    TodoEventEmitter,
)
from subagents_pydantic_ai import SubAgentCapability, SubAgentConfig

from app.agents.assistant import _build_model
from app.core.config import settings
{%- if cookiecutter.use_postgresql %}
from app.db.todo_pool import get_todo_pool
{%- endif %}

logger = logging.getLogger(__name__)

# Planning/delegation tools the planner narrates around. A model step that calls
# one of these is interstitial (its text is dropped); content tools (charts, RAG)
# are not, so a final report carrying a chart still streams. Mirrors the frontend
# ``RESEARCH_TOOL_NAMES`` in ``components/chat/research-panel.tsx``.
RESEARCH_TOOL_NAMES = frozenset(
    {
        "add_todo",
        "update_todo_status",
        "write_todos",
        "remove_todo",
        "add_subtask",
        "set_dependency",
        "read_todos",
        "get_available_tasks",
        "task",
        "wait_tasks",
        "check_task",
        "list_active_tasks",
        "send_message_to_subagent",
        "answer_subagent",
    }
)


def _subagent_configs() -> list[SubAgentConfig]:
    """Return the three research specialists.

    Only the researcher gets web tools (via ``agent_kwargs`` capabilities); the
    analyst and writer are text-only. ``preferred_mode="async"`` nudges the
    delegation tool toward concurrent, pollable execution.
    """
    return [
        SubAgentConfig(
            name="researcher",
            description=(
                "Gathers facts from the web for one research sub-question. Returns "
                "concrete findings, each tied to a source title + URL."
            ),
            instructions=(
                "You are a research specialist. Given one focused sub-question, search "
                "the web and read the most relevant sources, then return a compact set "
                "of findings. For every factual claim include the source title and URL "
                "you got it from. Prefer primary/authoritative sources and recent data. "
                "Do not editorialize — just report what you found and where. If sources "
                "conflict, note the disagreement."
            ),
            agent_kwargs={
                "capabilities": [
                    WebSearch(native=False, local="duckduckgo"),
                    WebFetch(native=False, local=True),
                ]
            },
            preferred_mode="async",
        ),
        SubAgentConfig(
            name="analyst",
            description=(
                "Reasons over already-gathered findings: compares, computes, ranks, and "
                "surfaces trends or contradictions. No web access."
            ),
            instructions=(
                "You are a data analyst. You are given findings collected by researchers. "
                "Compare and synthesize them: compute totals/trends, rank options, and "
                "call out contradictions or gaps. Be precise with numbers and keep the "
                "source attribution from the findings intact so the writer can cite them. "
                "Do not invent data you weren't given."
            ),
            preferred_mode="async",
        ),
        SubAgentConfig(
            name="writer",
            description=(
                "Composes a structured, cited report section from findings + analysis. "
                "No web access."
            ),
            instructions=(
                "You are a report writer. Given findings and analysis, write a clear, "
                "well-structured section. Attach numbered citations [1], [2] to specific "
                "claims and list the corresponding sources (title + URL) at the end, using "
                "only sources that appear in the input. Lead with the conclusion, then the "
                "supporting detail. Never fabricate a source or figure."
            ),
            preferred_mode="async",
        ),
    ]


_TODO_DESCRIPTIONS = {
    "write_todos": (
        "(discouraged) Replaces the entire todo list at once and is NOT shown to "
        "the user live. Prefer calling add_todo once per planned step, then "
        "update_todo_status to advance each step."
    ),
}

EmitEvent = Callable[[str, Any], Awaitable[bool]]


def _todo_event_payload(event: TodoEvent) -> dict[str, Any]:
    """Serialize a ``TodoEvent`` to a JSON-safe ``todo_event`` frame payload."""
    return {
        "event_type": event.event_type.value,
        "todo": event.todo.model_dump(mode="json"),
        "previous": event.previous_state.model_dump(mode="json") if event.previous_state else None,
        "ts": event.timestamp.isoformat() if event.timestamp else None,
    }


class ResearchToolkit:
    """Builds and owns the deep-research capabilities for a single turn.

    One instance per turn. :meth:`build` wires the capabilities to the session's
    WebSocket emitter and returns them to hand to the agent.
    """

    def __init__(self, emit: EmitEvent, model_name: str | None = None) -> None:
        self._emit = emit
        self._model_name = model_name or settings.AI_MODEL
        self._storage: Any = None
        self.subagent_capability: SubAgentCapability | None = None
        self.context_manager: ContextManagerCapability | None = None
        self._bg_tasks: set[asyncio.Task[Any]] = set()

    async def build(self, conversation_id: str) -> list[Any]:
        """Build the ordered capability list for this turn.

        ``conversation_id`` scopes the TODO storage. The context manager is kept
        last, as ``summarization-pydantic-ai`` requires.
        """
        capabilities: list[Any] = []

        todo_cap = await self._build_todo_capability(conversation_id)
        if todo_cap is not None:
            capabilities.append(todo_cap)

        capabilities.append(self._build_subagent_capability())
        capabilities.append(self._build_context_manager())

        return capabilities

    def _emit_soon(self, event_type: str, payload: dict[str, Any]) -> None:
        """Schedule an emit from a synchronous callback as a tracked task."""
        try:
            task = asyncio.ensure_future(self._emit(event_type, payload))
        except RuntimeError:
            return
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def flush(self) -> None:
        """Await the fire-and-forget telemetry emits so the last usage/compaction
        frame lands before the turn's terminal ``complete``."""
        if self._bg_tasks:
            await asyncio.gather(*self._bg_tasks, return_exceptions=True)

    def _build_context_manager(self) -> ContextManagerCapability:
        """Build the bounded-context capability with usage + compaction telemetry.

        Emits ``context_usage`` every request and ``context_compacted`` when a
        compression pass runs.
        """

        def on_usage_update(pct: float, current: int, max_tokens: int) -> None:
            self._emit_soon("context_usage", {"pct": pct, "current": current, "max": max_tokens})

        def on_before_compress(messages: list[Any], cutoff_index: int) -> None:
            self._emit_soon("context_compacted", {"cutoff_index": cutoff_index})

        cap = ContextManagerCapability(
            max_tokens=settings.DEEP_RESEARCH_MAX_TOKENS,
            compress_threshold=settings.DEEP_RESEARCH_COMPRESS_THRESHOLD,
            summarization_model=_build_model(self._model_name),
            on_usage_update=on_usage_update,
            on_before_compress=on_before_compress,
            include_compact_tool=True,
        )
        self.context_manager = cap
        return cap

    def _build_subagent_capability(self) -> SubAgentCapability:
        """Build the researcher/analyst/writer delegation capability.

        Subagents share the turn's model and a usage cap so parallel delegation
        cannot run away on cost.
        """
        cap = SubAgentCapability(
            subagents=_subagent_configs(),
            default_model=_build_model(self._model_name),
            include_general_purpose=False,
            max_nesting_depth=0,
            usage_limits=UsageLimits(request_limit=25),
        )
        self.subagent_capability = cap
        return cap

    async def _build_todo_capability(self, conversation_id: str) -> TodoCapability | None:
        """Build the TODO planner capability and stream its events to the client.

        Use the shared asyncpg pool when available (events + persistence), else an
        in-memory backend (events still fire, no persistence).
        """
        emitter = TodoEventEmitter()

        async def _on_event(event: TodoEvent) -> None:
            await self._emit("todo_event", _todo_event_payload(event))

        for subscribe in (
            emitter.on_created,
            emitter.on_updated,
            emitter.on_status_changed,
            emitter.on_completed,
            emitter.on_deleted,
        ):
            subscribe(_on_event)

{%- if cookiecutter.use_postgresql %}
        pool = get_todo_pool()
        try:
            if pool is not None:
                storage: AsyncPostgresStorage | AsyncMemoryStorage = AsyncPostgresStorage(
                    pool=pool, session_id=conversation_id, event_emitter=emitter
                )
                await storage.initialize()
            else:
                storage = AsyncMemoryStorage(event_emitter=emitter)
        except Exception as e:
            logger.warning("TODO storage init failed, falling back to memory: %s", e)
            storage = AsyncMemoryStorage(event_emitter=emitter)
{%- else %}
        storage = AsyncMemoryStorage(event_emitter=emitter)
{%- endif %}

        self._storage = storage
        return TodoCapability(
            async_storage=storage,
            enable_subtasks=True,
            descriptions=_TODO_DESCRIPTIONS,
        )
