{%- if cookiecutter.use_pydantic_deep %}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""PydanticDeep assistant — deep agentic coding assistant.

PydanticDeep is built on PydanticAI and provides:
- Filesystem tools: ls, read_file, write_file, edit_file, glob, grep
- Task management: write_todos, planning subagent
- Subagent delegation
- Skills system (SKILL.md files)
- Memory persistence (MEMORY.md across sessions)
- Context file discovery (AGENTS.md, SOUL.md from workspace root)
- Built-in web search and web fetch

Workspace types (set via PYDANTIC_DEEP_BACKEND_TYPE):
  "state"   — In-memory ``StateWorkspace`` (default, no persistence)
  "daytona" — ``DaytonaWorkspace``, a Daytona cloud sandbox (isolated, cloud-native)

Configuration via settings:
  PYDANTIC_DEEP_BACKEND_TYPE  : "state" | "daytona" (default: "state")
  PYDANTIC_DEEP_INCLUDE_SUBAGENTS : enable subagent delegation (default: True)
  PYDANTIC_DEEP_INCLUDE_SKILLS    : enable skills system (default: True)
  PYDANTIC_DEEP_INCLUDE_PLAN      : enable planner subagent (default: True)
  PYDANTIC_DEEP_INCLUDE_MEMORY    : enable persistent MEMORY.md (default: True)
  PYDANTIC_DEEP_INCLUDE_EXECUTE   : enable shell execution (default: False)
  PYDANTIC_DEEP_WEB_SEARCH        : enable built-in web search (default: True)
"""

import logging
from typing import Any, TypedDict

from pydantic_ai import Agent
{%- if cookiecutter.enable_rag or cookiecutter.enable_charts %}
from pydantic_ai import Tool as PAITool
{%- endif %}
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai_backends import StateWorkspace
from pydantic_deep import DeepAgentDeps, create_deep_agent

from app.agents.prompts import DEFAULT_SYSTEM_PROMPT
{%- if cookiecutter.enable_rag %}
from app.agents.prompts import get_system_prompt_with_rag
{%- if cookiecutter.enable_teams %}
from app.agents.tools.rag_tool import _active_kb_collections, search_knowledge_base
{%- else %}
from app.agents.tools.rag_tool import search_knowledge_base
{%- endif %}
{%- endif %}
{%- if cookiecutter.enable_charts %}
from app.agents.tools.chart_tool import create_chart_tool
{%- endif %}
from app.core.config import settings

logger = logging.getLogger(__name__)

_PROVIDER_PREFIXES: dict[str, str] = {
    "openai": "openai-responses",
    "anthropic": "anthropic",
    "google": "google-gla",  # Google AI (Gemini) via GOOGLE_API_KEY
    "openrouter": "openrouter",
}


class PydanticDeepContext(TypedDict, total=False):
    """Runtime context passed through the agent run."""

    user_id: str | None
    user_name: str | None
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    # Resolved server-side from conversation.active_knowledge_base_ids — never from the LLM
    kb_collection_names: list[str]
{%- endif %}
    metadata: dict[str, Any]


{%- if cookiecutter.enable_rag %}


async def _rag_search(query: str, top_k: int = 5) -> str:
    """Search the knowledge base for relevant documents.

    Use this tool to find information from uploaded documents before answering
    user queries. Searches across all available collections automatically.
    Cite sources by referring to the document filename from the search results.

    Args:
        query: The search query string.
        top_k: Number of top results to retrieve (default: 5).

    Returns:
        Formatted string with search results including content and scores.
    """
    return await search_knowledge_base(query=query, top_k=top_k)


{%- endif %}




class PydanticDeepAssistant:
    """Deep agentic assistant powered by pydantic-deep.

    Wraps create_deep_agent() with web-app friendly defaults:
    - StateWorkspace by default (in-memory, ephemeral)
    - Optional DaytonaWorkspace for cloud-native sandboxes
    - Conversation scoped by conversation_id (history_messages_path)
    - Non-interactive mode (no human-in-the-loop approval prompts)
    """

    def __init__(
        self,
        model_name: str | None = None,
        thinking_effort: str | None = None,
        conversation_id: str = "default",
        user_id: str | None = None,
        user_name: str | None = None,
        history_messages_path: str | None = None,
    ):
        self.model_name = model_name or settings.AI_MODEL
        self.thinking_effort = thinking_effort
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.user_name = user_name
        # Lets the project-scoped WS endpoint keep one history file per chat
        self._history_messages_path = history_messages_path
        self._agent: Agent | None = None
        self._deps: DeepAgentDeps | None = None

    def _get_model_string(self) -> str:
        """Build pydantic-ai model string with provider prefix.

        If the model name already contains ':', it is used as-is — except a bare
        ``openai:`` prefix, which is rewritten to ``openai-responses:`` so it hits
        the Responses API (tools + reasoning models). Otherwise the prefix from the
        LLM_PROVIDER setting is prepended.

        Examples:
            "gpt-5.5"             → "openai-responses:gpt-5.5"
            "claude-opus-4-7"     → "anthropic:claude-opus-4-7"
            "gemini-2.5-flash"    → "google-gla:gemini-2.5-flash"
            "openai:gpt-5.5"      → "openai-responses:gpt-5.5"  (rewritten)
            "openai-responses:gpt-5.5" → "openai-responses:gpt-5.5"  (unchanged)
        """
        if ":" in self.model_name:
            if self.model_name.startswith("openai:"):
                return f"openai-responses:{self.model_name.removeprefix('openai:')}"
            return self.model_name
        prefix = _PROVIDER_PREFIXES.get(settings.LLM_PROVIDER, settings.LLM_PROVIDER)
        return f"{prefix}:{self.model_name}"

    @property
    def uses_sandbox(self) -> bool:
        """Whether runs work in a sandbox the agent can read uploaded files from."""
        return settings.PYDANTIC_DEEP_BACKEND_TYPE == "daytona"

    def _create_workspace(self) -> AbstractCapability[Any]:
        """Create the workspace capability based on PYDANTIC_DEEP_BACKEND_TYPE."""
        if self.uses_sandbox:
            # Needs the `daytona` extra of pydantic-ai-backend, which the project
            # depends on when generated with the Daytona sandbox.
            from pydantic_ai_backends import DaytonaWorkspace

            return DaytonaWorkspace(sandbox_name=f"pd-{self.conversation_id}")

        # Default: in-memory, no cross-connection persistence
        return StateWorkspace()

    def _get_system_prompt(self) -> str:
        """Return the base system prompt."""
{%- if cookiecutter.enable_rag %}
        return get_system_prompt_with_rag()
{%- else %}
        return DEFAULT_SYSTEM_PROMPT
{%- endif %}

    def _build_agent_and_deps(self) -> tuple[Agent[DeepAgentDeps, str], DeepAgentDeps]:
        """Instantiate the pydantic-deep agent and its dependencies."""
        workspace = self._create_workspace()
        model_str = self._get_model_string()
        history_path = (
            self._history_messages_path
            if self._history_messages_path is not None
            else f".pydantic-deep/sessions/{self.conversation_id}/messages.json"
        )

        logger.info(
            "Creating PydanticDeep agent — model=%s workspace=%s conversation=%s",
            model_str,
            type(workspace).__name__,
            self.conversation_id,
        )

{%- if cookiecutter.enable_rag or cookiecutter.enable_charts %}
        extra_tools: list[Any] = []
{%- if cookiecutter.enable_rag %}
        extra_tools.append(PAITool(_rag_search))
{%- endif %}
{%- if cookiecutter.enable_charts %}
        extra_tools.append(PAITool(create_chart_tool))
{%- endif %}
{%- else %}
        extra_tools: list[Any] = []
{%- endif %}

        agent = create_deep_agent(
            model=model_str,
            workspace=workspace,
            instructions=self._get_system_prompt(),
            # Per-conversation history persistence
            history_messages_path=history_path,
            # Built-in tool groups
            include_filesystem=True,
            include_execute=settings.PYDANTIC_DEEP_INCLUDE_EXECUTE,
            include_todo=True,
            include_subagents=settings.PYDANTIC_DEEP_INCLUDE_SUBAGENTS,
            include_builtin_subagents=settings.PYDANTIC_DEEP_INCLUDE_SUBAGENTS,
            include_skills=settings.PYDANTIC_DEEP_INCLUDE_SKILLS,
            include_plan=settings.PYDANTIC_DEEP_INCLUDE_PLAN,
            # Memory: shared MEMORY.md across all conversations in the workspace
            include_memory=settings.PYDANTIC_DEEP_INCLUDE_MEMORY,
            memory_dir=".pydantic-deep",
            # Context discovery: reads AGENTS.md, SOUL.md from workspace root
            context_discovery=True,
            # Web tools (built-in pydantic-ai WebSearch / WebFetch)
            web_search=settings.PYDANTIC_DEEP_WEB_SEARCH,
            web_fetch=True,
            # Context management: auto-compress history at token budget
            context_manager=True,
            # Cost tracking
            cost_tracking=True,
            # Thinking effort — "auto" lets pydantic-ai resolve per-provider
            thinking=self.thinking_effort or "auto",
            # Extra tools (e.g. RAG search)
            **({"tools": extra_tools} if extra_tools else {}),
        )

        deps = DeepAgentDeps()
        return agent, deps

    async def upload_file(self, filename: str, content: bytes | str) -> str:
        """Make a file available in the workspace of the next run.

        pydantic-deep writes it into the run's workspace when the run starts.

        Args:
            filename: The file's name; it lands under ``uploads/``.
            content: File content (bytes or str).

        Returns:
            The workspace-relative path, e.g. ``uploads/report.pdf``.
        """
        data = content if isinstance(content, bytes) else content.encode("utf-8")
        return await self.deps.upload_file(filename, data)

    @property
    def agent(self) -> Agent:
        """Get or create the underlying pydantic-ai Agent."""
        if self._agent is None:
            self._agent, self._deps = self._build_agent_and_deps()
        return self._agent

    @property
    def deps(self) -> DeepAgentDeps:
        """Get or create the DeepAgentDeps for this assistant."""
        if self._deps is None:
            self._agent, self._deps = self._build_agent_and_deps()
        return self._deps

    async def run(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,  # noqa: ARG002 — managed internally via history_messages_path
        context: PydanticDeepContext | None = None,
    ) -> tuple[str, list[Any], PydanticDeepContext]:
        """Run the agent and return the full response.

        Note: pydantic-deep manages conversation history internally via the
        workspace (history_messages_path). The ``history`` parameter is accepted
        for API parity with other agent wrappers but is not used.

        Args:
            user_input: User's message.
            history: Ignored — pydantic-deep persists history internally.
            context: Optional runtime context (user_id, user_name, metadata).

        Returns:
            Tuple of (output_text, tool_events, context).
        """
        agent_context: PydanticDeepContext = context if context is not None else {}
        logger.info("Running PydanticDeep agent: %s…", user_input[:100])

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        token = _active_kb_collections.set(agent_context.get("kb_collection_names") or [])
        try:
            result = await self.agent.run(user_input, deps=self.deps)
        finally:
            _active_kb_collections.reset(token)
{%- else %}
        result = await self.agent.run(user_input, deps=self.deps)
{%- endif %}

        tool_events: list[Any] = []
        for message in result.all_messages():
            if hasattr(message, "parts"):
                for part in message.parts:
                    if hasattr(part, "tool_name"):
                        tool_events.append(part)

        logger.info("PydanticDeep run complete. Output: %d chars", len(result.output))
        return result.output, tool_events, agent_context

    async def stream(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,  # noqa: ARG002 — managed internally via history_messages_path
        context: PydanticDeepContext | None = None,
    ):
        """Stream agent execution token by token.

        Note: pydantic-deep manages conversation history internally via the
        workspace (history_messages_path). The ``history`` parameter is accepted
        for API parity with other agent wrappers but is not used.

        Args:
            user_input: User's message.
            history: Ignored — pydantic-deep persists history internally.
            context: Optional runtime context.

        Yields:
            Tuples of ("messages", (chunk, metadata)) for LLM tokens.
        """
        logger.info("Streaming PydanticDeep agent: %s…", user_input[:100])

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        agent_context: PydanticDeepContext = context if context is not None else {}
        token = _active_kb_collections.set(agent_context.get("kb_collection_names") or [])
        try:
            async with self.agent.run_stream(user_input, deps=self.deps) as response:
                async for text in response.stream_text(delta=True):
                    yield "messages", (text, {})
        finally:
            _active_kb_collections.reset(token)
{%- else %}
        async with self.agent.run_stream(user_input, deps=self.deps) as response:
            async for text in response.stream_text(delta=True):
                yield "messages", (text, {})
{%- endif %}


def get_agent(
    model_name: str | None = None,
    thinking_effort: str | None = None,
    conversation_id: str = "default",
    user_id: str | None = None,
    user_name: str | None = None,
    history_messages_path: str | None = None,
) -> PydanticDeepAssistant:
    """Create a PydanticDeepAssistant instance.

    Args:
        model_name: Override AI_MODEL from settings.
        thinking_effort: Extended thinking effort level (e.g. "low", "medium", "high").
        conversation_id: Scope history to this conversation (default: "default").
        user_id: Optional user identifier for context.
        user_name: Optional user display name for context.
        history_messages_path: Override the history file path inside the workspace.
            Useful for project-scoped chats where each chat has its own path.

    Returns:
        Configured PydanticDeepAssistant.
    """
    return PydanticDeepAssistant(
        model_name=model_name,
        thinking_effort=thinking_effort,
        conversation_id=conversation_id,
        user_id=user_id,
        user_name=user_name,
        history_messages_path=history_messages_path,
    )


async def run_agent(
    user_input: str,
    conversation_id: str = "default",
    context: PydanticDeepContext | None = None,
) -> tuple[str, list[Any], PydanticDeepContext]:
    """One-shot convenience wrapper for running the agent.

    Args:
        user_input: User's message.
        conversation_id: Conversation scope for history.
        context: Optional runtime context.

    Returns:
        Tuple of (output_text, tool_events, context).
    """
    assistant = get_agent(conversation_id=conversation_id)
    return await assistant.run(user_input, context)
{%- else %}
"""PydanticDeep Assistant agent — not configured."""
{%- endif %}
