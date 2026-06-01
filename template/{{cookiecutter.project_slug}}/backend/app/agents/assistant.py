{%- if cookiecutter.use_pydantic_ai %}
"""Assistant agent with PydanticAI.

The main conversational agent that can be extended with custom tools.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent, ModelRetry{%- if cookiecutter.enable_rag %}, RunContext{%- endif %}
from pydantic_ai.capabilities import (
    ReinjectSystemPrompt,
    Thinking,
{%- if cookiecutter.enable_web_fetch %}
    WebFetch,
{%- endif %}
{%- if cookiecutter.enable_web_search %}
    WebSearch,
{%- endif %}
)
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
{%- if cookiecutter.use_openai %}
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
{%- endif %}
{%- if cookiecutter.use_anthropic %}
from pydantic_ai.models.anthropic import AnthropicModel
{%- endif %}
{%- if cookiecutter.use_google %}
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
{%- endif %}
{%- if cookiecutter.use_openrouter %}
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
{%- endif %}
from pydantic_ai.settings import ModelSettings

from app.agents.prompts import DEFAULT_SYSTEM_PROMPT
{%- if cookiecutter.enable_rag %}
from app.agents.prompts import get_system_prompt_with_rag
{%- endif %}
from app.agents.tools import get_current_datetime
{%- if cookiecutter.enable_rag %}
from app.agents.tools.rag_tool import search_knowledge_base
{%- endif %}
{%- if cookiecutter.enable_charts %}
from app.agents.tools.chart_tool import create_chart
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
from app.agents.tools.antv_chart import get_antv_toolset
from app.agents.tools.map_tool import MapMarker, create_map
{%- endif %}
from app.core.config import settings

logger = logging.getLogger(__name__)

{%- if cookiecutter.use_all_providers %}


def _build_model(model_name: str):
    """Dispatch to the right pydantic-ai Model for ``model_name``.

    Multi-provider deployments accept any model name from any installed SDK.
    Routing is done by name prefix:
      - openai/gpt-*, openai/o*, openai/text-* → OpenAI
      - anthropic/claude-*                      → Anthropic
      - google/gemini-*                         → Google
      - openrouter/<provider>/<model>           → OpenRouter
      - bare names (no slash) → fall back to OpenAI for backwards compat.
    """
    name = model_name or settings.AI_MODEL
    lowered = name.lower()
    if "/" in lowered:
        prefix, _, rest = lowered.partition("/")
        if prefix == "openai":
            return OpenAIResponsesModel(
                rest, provider=OpenAIProvider(api_key=settings.OPENAI_API_KEY)
            )
        if prefix == "anthropic":
            return AnthropicModel(rest)
        if prefix == "google":
            return GoogleModel(
                rest, provider=GoogleProvider(api_key=settings.GOOGLE_API_KEY)
            )
        if prefix == "openrouter":
            return OpenRouterModel(
                rest, provider=OpenRouterProvider(api_key=settings.OPENROUTER_API_KEY)
            )
    # Bare model name — best-effort sniff by family.
    if lowered.startswith(("claude-", "claude/")):
        return AnthropicModel(name.removeprefix("claude/"))
    if lowered.startswith("gemini"):
        return GoogleModel(name, provider=GoogleProvider(api_key=settings.GOOGLE_API_KEY))
    return OpenAIResponsesModel(
        name, provider=OpenAIProvider(api_key=settings.OPENAI_API_KEY)
    )
{%- elif cookiecutter.use_openai %}


def _build_model(model_name: str):
    """OpenAI-only deployment."""
    return OpenAIResponsesModel(
        model_name or settings.AI_MODEL,
        provider=OpenAIProvider(api_key=settings.OPENAI_API_KEY),
    )
{%- elif cookiecutter.use_anthropic %}


def _build_model(model_name: str):
    return AnthropicModel(model_name or settings.AI_MODEL)
{%- elif cookiecutter.use_google %}


def _build_model(model_name: str):
    return GoogleModel(
        model_name or settings.AI_MODEL,
        provider=GoogleProvider(api_key=settings.GOOGLE_API_KEY),
    )
{%- elif cookiecutter.use_openrouter %}


def _build_model(model_name: str):
    return OpenRouterModel(
        model_name or settings.AI_MODEL,
        provider=OpenRouterProvider(api_key=settings.OPENROUTER_API_KEY),
    )
{%- endif %}


@dataclass
class Deps:
    """Dependencies for the assistant agent.

    These are passed to tools via RunContext.
    """

    user_id: str | None = None
    user_name: str | None = None
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    # Resolved server-side from conversation.active_knowledge_base_ids — never from the LLM
    kb_collection_names: list[str] = field(default_factory=list)
{%- endif %}
    metadata: dict[str, Any] = field(default_factory=dict)


class AssistantAgent:
    """Assistant agent wrapper for conversational AI.

    Encapsulates agent creation and execution with tool support.
    """

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
        thinking_effort: str | None = None,
    ):
        self.model_name = model_name or settings.AI_MODEL
        # ``temperature`` stays ``None`` when caller didn't set it — don't fall
        # back to settings.AI_TEMPERATURE here. Reasoning/o-series models
        # (gpt-5.5, o1, …) reject the parameter entirely, so we only forward
        # it to the model when explicitly requested.
        self.temperature = temperature
        self.thinking_effort = thinking_effort if thinking_effort is not None else (
            settings.AI_THINKING_EFFORT if settings.AI_THINKING_ENABLED else None
        )
{%- if cookiecutter.enable_rag %}
        self.system_prompt = system_prompt or get_system_prompt_with_rag()
{%- else %}
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
{%- endif %}
        self._agent: Agent[Deps, str] | None = None

    def _create_agent(self) -> Agent[Deps, str]:
        """Create and configure the PydanticAI agent."""
        model = _build_model(self.model_name)

        capabilities = [ReinjectSystemPrompt()]
        if self.thinking_effort:
            capabilities.append(Thinking(effort=self.thinking_effort))
{%- if cookiecutter.enable_web_search %}
        capabilities.append(WebSearch())
{%- endif %}
{%- if cookiecutter.enable_web_fetch %}
        capabilities.append(WebFetch())
{%- endif %}

        # The unified ``Thinking()`` capability enables reasoning, but for the
        # OpenAI Responses API it sets only the effort — not the *summary*
        # field that controls whether the model streams reasoning summaries
        # back to the client. Without ``openai_reasoning_summary`` set, the
        # model reasons internally and we never see ThinkingPart events.
        # ``openai_*``-prefixed fields on TypedDict settings are silently
        # ignored by other providers, so this is safe to apply unconditionally.
        model_settings: ModelSettings = ModelSettings()
        if self.temperature is not None:
            model_settings["temperature"] = self.temperature
        if self.thinking_effort:
            model_settings["openai_reasoning_summary"] = "auto"  # type: ignore[typeddict-unknown-key]  # ty: ignore[invalid-key]

{%- if cookiecutter.enable_antv_charts %}

        # None when AntV is disabled or the sidecar is unavailable.
        antv_toolset = get_antv_toolset()
        toolsets = [antv_toolset] if antv_toolset is not None else []
{%- endif %}

        agent = Agent[Deps, str](
            model=model,
            model_settings=model_settings,
            system_prompt=self.system_prompt,
            capabilities=capabilities,
{%- if cookiecutter.enable_antv_charts %}
            toolsets=toolsets,
{%- endif %}
        )

        self._register_tools(agent)

        return agent

    def _register_tools(self, agent: Agent[Deps, str]) -> None:
        """Register all tools on the agent."""

        @agent.tool_plain
        def current_datetime() -> dict[str, str]:
            """Get the current date and time.

            Use this tool when you need to know the current date or time.
            """
            return get_current_datetime()

{%- if cookiecutter.enable_rag %}
        @agent.tool
        async def search_documents(
            ctx: RunContext[Deps], query: str, top_k: int = 5
        ) -> str:
            """Search the knowledge base for relevant documents.

            Use this tool to find information from uploaded documents before answering user queries.
            Cite sources by referring to the document filename from the search results.

            Args:
                query: The search query string.
                top_k: Number of top results to retrieve (default: 5).

            Returns:
                Formatted string with search results including content and scores.
            """
{%- if cookiecutter.enable_teams %}
            try:
                return await search_knowledge_base(
                    query=query,
                    kb_collection_names=ctx.deps.kb_collection_names,
                    top_k=top_k,
                )
            except Exception as e:
                raise ModelRetry("Knowledge base temporarily unavailable, please try again.") from e
{%- else %}
            try:
                return await search_knowledge_base(query=query, top_k=top_k)
            except Exception as e:
                raise ModelRetry("Knowledge base temporarily unavailable, please try again.") from e
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_charts %}
        @agent.tool_plain
        def create_chart_tool(
            chart_type: str,
            title: str,
            data: list[dict[str, Any]],
            series: list[dict[str, Any]] | None = None,
            x_key: str = "x",
            style: dict[str, Any] | None = None,
        ) -> str:
            """Create a chart (line/bar/pie/area/scatter) to visualize data for the user.

            Use whenever the user asks to plot, chart, graph, or visualize numbers,
            trends, comparisons, or distributions. Do not repeat the returned JSON
            back to the user — just briefly describe the chart you created.

            Args:
                chart_type: One of "line", "bar", "pie", "area", "scatter".
                title: Short chart title.
                data: Row dicts, e.g. [{"x": "Jan", "revenue": 120}]. For pie:
                    [{"x": "Chrome", "value": 64}, ...].
                series: Optional [{"key", "label"?, "color"?}] selecting fields to plot.
                x_key: Row field for the x-axis / pie label (default "x").
                style: Optional {"palette", "grid", "legend", "x_label", "y_label", "stacked"}.
            """
            return create_chart(
                chart_type=chart_type,  # type: ignore[arg-type]
                title=title,
                data=data,
                series=series,
                x_key=x_key,
                style=style,
            )
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
        @agent.tool_plain
        def create_map_tool(
            title: str,
            markers: list[MapMarker],
            center: list[float] | None = None,
            zoom: int | None = None,
        ) -> str:
            """Create an interactive map to show places geographically for the user.

            Use whenever the user asks to show, map, or locate places. Provide
            latitude/longitude for each marker from your own knowledge (e.g.
            Warsaw ≈ 52.23, 21.01). Do not repeat the returned JSON — just briefly
            describe the map you created.

            Args:
                title: Short map title.
                markers: One entry per place, each with lat, lng and a short label
                    (plus optional description and color). Must not be empty.
                center: Optional [lat, lng] center (auto-fit to markers if omitted).
                zoom: Optional zoom level 1-18 (mainly useful for a single marker).
            """
            return create_map(
                title=title,
                markers=[m.model_dump() for m in markers],
                center=center,
                zoom=zoom,
            )
{%- endif %}


    @staticmethod
    def _build_model_history(
        history: list[dict[str, str]] | None,
    ) -> list[ModelRequest | ModelResponse]:
        model_history: list[ModelRequest | ModelResponse] = []
        for msg in history or []:
            if msg["role"] == "user":
                model_history.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
            elif msg["role"] == "assistant":
                model_history.append(ModelResponse(parts=[TextPart(content=msg["content"])]))
            elif msg["role"] == "system":
                model_history.append(ModelRequest(parts=[SystemPromptPart(content=msg["content"])]))
        return model_history

    @property
    def agent(self) -> Agent[Deps, str]:
        """Get or create the agent instance."""
        if self._agent is None:
            self._agent = self._create_agent()
        return self._agent

    async def run(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        deps: Deps | None = None,
    ) -> tuple[str, list[Any], Deps]:
        """Run agent and return the output along with tool call events.

        Args:
            user_input: User's message.
            history: Conversation history as list of {"role": "...", "content": "..."}.
            deps: Optional dependencies. If not provided, a new Deps will be created.

        Returns:
            Tuple of (output_text, tool_events, deps).
        """
        agent_deps = deps if deps is not None else Deps()

        logger.info(f"Running agent with user input: {user_input[:100]}...")
        result = await self.agent.run(
            user_input,
            deps=agent_deps,
            message_history=self._build_model_history(history),
        )

        tool_events: list[Any] = []
        for message in result.all_messages():
            if hasattr(message, "parts"):
                for part in message.parts:
                    if hasattr(part, "tool_name"):
                        tool_events.append(part)

        logger.info(f"Agent run complete. Output length: {len(result.output)} chars")

        return result.output, tool_events, agent_deps

    async def iter(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        deps: Deps | None = None,
    ) -> Any:
        """Stream agent execution with full event access.

        Args:
            user_input: User's message.
            history: Conversation history.
            deps: Optional dependencies.

        Yields:
            Agent events for streaming responses.
        """
        agent_deps = deps if deps is not None else Deps()

        async with self.agent.iter(
            user_input,
            deps=agent_deps,
            message_history=self._build_model_history(history),
        ) as run:
            async for event in run:
                yield event


def get_agent(
    model_name: str | None = None,
    thinking_effort: str | None = None,
    temperature: float | None = None,
) -> AssistantAgent:
    """Factory function to create an AssistantAgent.

    Args:
        model_name: Override the default AI model.
        thinking_effort: Override thinking effort ("low", "medium", "high", or None to disable).
        temperature: Sampling temperature (typically 0.0-2.0). ``None`` falls back to
            ``settings.AI_TEMPERATURE``.

    Returns:
        Configured AssistantAgent instance.
    """
    return AssistantAgent(
        model_name=model_name,
        thinking_effort=thinking_effort,
        temperature=temperature,
    )


async def run_agent(
    user_input: str,
    history: list[dict[str, str]],
    deps: Deps | None = None,
) -> tuple[str, list[Any], Deps]:
    """Run agent and return the output along with tool call events.

    This is a convenience function for backwards compatibility.

    Args:
        user_input: User's message.
        history: Conversation history.
        deps: Optional dependencies.

    Returns:
        Tuple of (output_text, tool_events, deps).
    """
    agent = get_agent()
    return await agent.run(user_input, history, deps)
{%- else %}
"""PydanticAI Assistant agent - not configured."""
{%- endif %}
