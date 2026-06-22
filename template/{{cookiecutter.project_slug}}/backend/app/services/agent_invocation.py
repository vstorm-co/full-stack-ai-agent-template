{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
"""Framework-agnostic agent invocation for channel messages (non-streaming)."""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories import conversation_repo
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
from app.repositories import knowledge_base_repo
{%- endif %}
{%- if cookiecutter.use_pydantic_ai %}
from app.agents.assistant import Deps, get_agent
from app.services.agent import build_message_history
{%- endif %}
{%- if cookiecutter.use_pydantic_deep %}
from app.agents.pydantic_deep_assistant import PydanticDeepAssistant, PydanticDeepContext
{%- endif %}
{%- if cookiecutter.use_langchain %}
from app.agents.langchain_assistant import get_agent
{%- endif %}
{%- if cookiecutter.use_langgraph %}
from app.agents.langgraph_assistant import get_agent
{%- endif %}
{%- if cookiecutter.use_deepagents %}
from app.agents.deepagents_assistant import get_agent
{%- endif %}
{%- if (cookiecutter.use_langchain or cookiecutter.use_langgraph or cookiecutter.use_deepagents) and cookiecutter.enable_teams and cookiecutter.enable_rag %}
from app.agents.tools.rag_tool import _active_kb_collections
{%- endif %}
{%- if cookiecutter.use_pydantic_ai and cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
from app.services.usage import UsageService
{%- endif %}


@dataclass
class ToolEvent:
    """A tool call + result pair collected during agent execution."""

    tool_name: str
    args: dict[str, Any] = field(default_factory=dict)
    result: str = ""


logger = logging.getLogger(__name__)


def _provider_from_model(model_name: str) -> str:
    name = (model_name or "").lower()
    if name.startswith(("gpt", "o1", "o3", "o4", "openai")):
        return "openai"
    if name.startswith(("claude", "anthropic")):
        return "anthropic"
    if name.startswith(("gemini", "google")):
        return "google"
    return "unknown"


class AgentInvocationService:
    """Invoke the configured AI agent and return the final text response.

    Used by channel adapters where streaming is not required. Both the user
    message and the assistant reply are persisted to the database.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def invoke(
        self,
        *,
        user_message: str,
        conversation_id: UUID,
        user_id: UUID | None = None,
        project_id: UUID | None = None,
        organization_id: UUID | None = None,
        system_prompt_override: str | None = None,
        model_override: str | None = None,
    ) -> tuple[str, list[ToolEvent]]:
        """Run the agent and return final text + tool events.

        Returns:
            Tuple of (response_text, tool_events).
        """
        await self._persist_user_message(conversation_id, user_message)

        history = await self._load_history(conversation_id)
        # Resolve active KB collections server-side — never trust the client
        kb_collection_names = await self._load_active_kb_collection_names(
            conversation_id=conversation_id,
            user_id=user_id,
            organization_id=organization_id,
        )

        tool_events: list[ToolEvent] = []
        response_text, tool_events = await self._call_agent(
            user_message=user_message,
            history=history,
            conversation_id=conversation_id,
            user_id=user_id,
            project_id=project_id,
            kb_collection_names=kb_collection_names,
            system_prompt_override=system_prompt_override,
            model_override=model_override,
        )

        await self._persist_assistant_message(conversation_id, response_text)

        return response_text, tool_events

    async def _call_agent(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, list[ToolEvent]]:
        """Dispatch to the framework-specific agent implementation."""
{%- if cookiecutter.use_pydantic_ai %}
        return await self._call_pydantic_ai(user_message=user_message, history=history, **kwargs)
{%- elif cookiecutter.use_pydantic_deep %}
        return await self._call_pydantic_deep(user_message=user_message, history=history, **kwargs)
{%- elif cookiecutter.use_langchain %}
        return await self._call_langchain(user_message=user_message, history=history, **kwargs)
{%- elif cookiecutter.use_langgraph %}
        return await self._call_langgraph(user_message=user_message, history=history, **kwargs)
{%- elif cookiecutter.use_deepagents %}
        return await self._call_deepagents(user_message=user_message, history=history, **kwargs)
{%- else %}
        return f"Echo: {user_message}", []
{%- endif %}

{%- if cookiecutter.use_pydantic_ai %}

    async def _call_pydantic_ai(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, list[ToolEvent]]:
        """Invoke PydanticAI agent and extract tool events from result messages."""

        model_name: str | None = kwargs.get("model_override")
        assistant = get_agent(model_name=model_name)

        model_history = build_message_history(history)
        deps = Deps(kb_collection_names=kwargs.get("kb_collection_names") or [])

        result = await assistant.agent.run(
            user_message,
            message_history=model_history,
            deps=deps,
        )

        tool_events = self._extract_tool_events(result.all_messages())
{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
        organization_id = kwargs.get("organization_id")
        if organization_id is not None:
            try:
                usage = result.usage()
                effective_model = assistant.model_name or model_name or "unknown"
                await UsageService(self.db).record(
                    organization_id=organization_id,
                    model=effective_model,
                    provider=_provider_from_model(effective_model),
                    input_tokens=getattr(usage, "input_tokens", 0) or 0,
                    output_tokens=getattr(usage, "output_tokens", 0) or 0,
                    cached_tokens=getattr(usage, "cache_read_tokens", 0) or 0,
                    ai_framework="pydantic_ai",
                    actor_user_id=kwargs.get("user_id"),
                    conversation_id=kwargs.get("conversation_id"),
                )
            except Exception:
                logger.exception(
                    "channel_usage_record_failed",
                    extra={"org_id": str(organization_id)},
                )
{%- endif %}

        return str(result.output), tool_events

    @staticmethod
    def _extract_tool_events(messages: list[Any]) -> list[ToolEvent]:
        """Extract tool call/result pairs from pydantic-ai message history."""
        from pydantic_ai.messages import ModelRequest, ModelResponse

        pending: dict[str, ToolEvent] = {}
        events: list[ToolEvent] = []

        for msg in messages:
            if isinstance(msg, ModelResponse):
                for part in msg.parts:
                    tool_name = getattr(part, "tool_name", None)
                    tool_call_id = getattr(part, "tool_call_id", None)
                    if tool_name and tool_call_id:
                        args = getattr(part, "args", None)
                        te = ToolEvent(
                            tool_name=tool_name,
                            args=args if isinstance(args, dict) else {},
                        )
                        pending[tool_call_id] = te
                        events.append(te)
            elif isinstance(msg, ModelRequest):
                for part in msg.parts:
                    tool_call_id = getattr(part, "tool_call_id", None)
                    content = getattr(part, "content", None)
                    if tool_call_id and tool_call_id in pending and content:
                        pending[tool_call_id].result = str(content)[:500]

        return events
{%- endif %}

{%- if cookiecutter.use_pydantic_deep %}

    async def _call_pydantic_deep(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, list[ToolEvent]]:
        """Invoke PydanticDeep agent (non-streaming).

        PydanticDeep manages its own conversation history via history_messages_path,
        so we pass the conversation_id for per-conversation persistence rather than
        replaying the DB message history.
        """

        conversation_id = str(kwargs.get("conversation_id") or "default")
        user_id = str(kwargs.get("user_id")) if kwargs.get("user_id") else None
        model_name: str | None = kwargs.get("model_override")

        assistant = PydanticDeepAssistant(
            model_name=model_name,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        context = PydanticDeepContext(user_id=user_id)
        text, _, _ = await assistant.run(user_message, context=context)
        return text, []
{%- endif %}

{%- if cookiecutter.use_langchain %}

    async def _call_langchain(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, list[ToolEvent]]:
        """Invoke LangChain agent (async)."""
        from langchain_core.messages import AIMessage, HumanMessage

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        _active_kb_collections.set(kwargs.get("kb_collection_names") or [])
{%- endif %}

        assistant = get_agent()
        lc_history = self._build_langchain_history(history)
        lc_history.append(HumanMessage(content=user_message))

        result = await assistant.agent.ainvoke({"messages": lc_history})

        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage):
                content = msg.content
                return (content if isinstance(content, str) else str(content)), []
        return "", []
{%- endif %}

{%- if cookiecutter.use_langgraph %}

    async def _call_langgraph(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, list[ToolEvent]]:
        """Invoke LangGraph agent (async)."""
        from langchain_core.messages import AIMessage, HumanMessage

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        _active_kb_collections.set(kwargs.get("kb_collection_names") or [])
{%- endif %}

        assistant = get_agent()
        lc_history = self._build_langchain_history(history)
        lc_history.append(HumanMessage(content=user_message))

        result = await assistant.graph.ainvoke({"messages": lc_history})

        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage):
                content = msg.content
                return (content if isinstance(content, str) else str(content)), []
        return "", []
{%- endif %}

{%- if cookiecutter.use_deepagents %}

    async def _call_deepagents(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, list[ToolEvent]]:
        """Invoke DeepAgents graph (async)."""
        from langchain_core.messages import AIMessage, HumanMessage

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        _active_kb_collections.set(kwargs.get("kb_collection_names") or [])
{%- endif %}

        assistant = get_agent()
        lc_history = self._build_langchain_history(history)
        lc_history.append(HumanMessage(content=user_message))

        result = await assistant.graph.ainvoke({"messages": lc_history})

        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage):
                content = msg.content
                return (content if isinstance(content, str) else str(content)), []
        return "", []
{%- endif %}

{%- if cookiecutter.use_langchain or cookiecutter.use_langgraph or cookiecutter.use_deepagents %}

    def _build_langchain_history(self, history: list[dict[str, str]]) -> list[Any]:
        """Convert conversation history to LangChain message format."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        lc_msgs: list[Any] = []
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                lc_msgs.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_msgs.append(AIMessage(content=content))
            elif role == "system":
                lc_msgs.append(SystemMessage(content=content))
        return lc_msgs
{%- endif %}

    async def _load_active_kb_collection_names(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID | None,
        organization_id: UUID | None,
    ) -> list[str]:
        """Return vector-store collection names for the active KBs of this conversation.

        Resolution is always server-side: we intersect the conversation's
        active_knowledge_base_ids with the KBs actually visible to the user,
        preventing any client-supplied KB IDs from leaking cross-org data.
        """
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        conv = await conversation_repo.get_conversation_by_id(self.db, conversation_id)
        if not conv:
            return []

        effective_org_id = organization_id or getattr(conv, "organization_id", None)

        active_ids: list[str] = conv.active_knowledge_base_ids or []
        if not active_ids:
            # Fall back to the org's default KB so the agent is never blind
            if effective_org_id is not None:
                default_kb = await knowledge_base_repo.get_default_for_org(self.db, effective_org_id)
                if default_kb:
                    return [default_kb.collection_name]
            return []

        # Security: only return collections the user is actually allowed to see
        accessible = await knowledge_base_repo.get_accessible(
            self.db,
            user_id=user_id,
            organization_id=effective_org_id,
        )
        active_set = {str(i) for i in active_ids}
        return [kb.collection_name for kb in accessible if str(kb.id) in active_set]
{%- else %}
        return []
{%- endif %}

    async def _persist_user_message(self, conversation_id: UUID, content: str) -> None:
        """Persist the user message directly via conversation repo."""
        await conversation_repo.create_message(
            self.db,
            conversation_id=conversation_id,
            role="user",
            content=content,
        )

    async def _persist_assistant_message(
        self, conversation_id: UUID, content: str
    ) -> None:
        """Persist the assistant reply directly via conversation repo."""
        await conversation_repo.create_message(
            self.db,
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            model_name=settings.AI_MODEL,
        )

    async def _load_history(
        self, conversation_id: UUID
    ) -> list[dict[str, str]]:
        """Load conversation message history ordered chronologically."""
        messages = await conversation_repo.get_messages_by_conversation(
            self.db,
            conversation_id=conversation_id,
            skip=0,
            limit=200,
        )
        return [{"role": m.role, "content": m.content} for m in messages]

{%- endif %}
