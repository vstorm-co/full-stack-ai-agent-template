{%- if cookiecutter.use_pydantic_ai %}
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent{%- if cookiecutter.enable_rag %}, ModelRetry{%- endif %}, RunContext
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
    ToolCallPart,
    ToolReturnPart,
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
{%- if cookiecutter.enable_deep_research %}
from app.agents.prompts import get_research_prompt
{%- endif %}
{%- if cookiecutter.enable_todo %}
from pydantic_ai_todo import TodoCapability
{%- endif %}
{%- if cookiecutter.enable_subagents %}
from subagents_pydantic_ai import SubAgentCapability
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
from pydantic_ai_summarization import ContextManagerCapability
{%- endif %}
from app.agents.tools.ask_user_tool import MAX_QUESTIONS, QuestionItem, format_answers
from app.agents.utils import get_current_datetime
{%- if cookiecutter.enable_rag %}
from app.agents.tools.rag_tool import search_knowledge_base
{%- endif %}
{%- if cookiecutter.enable_charts %}
from app.agents.tools.chart_tool import ChartType, create_chart
{%- endif %}
{%- if cookiecutter.enable_code_execution %}
from app.agents.tools.code_execution import run_python as run_python_code
{%- endif %}
{%- if cookiecutter.enable_skills %}
from pathlib import Path

from pydantic_ai_skills import SkillsToolset
{%- endif %}
from app.core.config import settings

logger = logging.getLogger(__name__)

{%- if cookiecutter.use_all_providers %}


def _build_model(model_name: str) -> "OpenAIResponsesModel | AnthropicModel | GoogleModel | OpenRouterModel":
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


def _build_model(model_name: str) -> OpenAIResponsesModel:
    """OpenAI-only deployment."""
    return OpenAIResponsesModel(
        model_name or settings.AI_MODEL,
        provider=OpenAIProvider(api_key=settings.OPENAI_API_KEY),
    )
{%- elif cookiecutter.use_anthropic %}


def _build_model(model_name: str) -> AnthropicModel:
    return AnthropicModel(model_name or settings.AI_MODEL)
{%- elif cookiecutter.use_google %}


def _build_model(model_name: str) -> GoogleModel:
    return GoogleModel(
        model_name or settings.AI_MODEL,
        provider=GoogleProvider(api_key=settings.GOOGLE_API_KEY),
    )
{%- elif cookiecutter.use_openrouter %}


def _build_model(model_name: str) -> OpenRouterModel:
    return OpenRouterModel(
        model_name or settings.AI_MODEL,
        provider=OpenRouterProvider(api_key=settings.OPENROUTER_API_KEY),
    )
{%- endif %}


AskUserCallback = Callable[[list[dict[str, Any]]], Awaitable[list[dict[str, Any]]]]


@dataclass
class Deps:
    """Dependencies passed to tools via RunContext."""

    user_id: str | None = None
    user_name: str | None = None
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    # Resolved server-side from conversation.active_knowledge_base_ids — never from the LLM
    kb_collection_names: list[str] = field(default_factory=list)
{%- endif %}
    metadata: dict[str, Any] = field(default_factory=dict)
    ask_user: AskUserCallback | None = None
{%- if cookiecutter.enable_subagents %}
    # Required by SubAgentDepsProtocol; kept empty (capabilities carry the agents).
    subagents: dict[str, Any] = field(default_factory=dict)

    def clone_for_subagent(self, max_depth: int = 0) -> "Deps":
        """Create isolated deps for a delegated subagent (required by SubAgentDepsProtocol)."""
        return Deps(
            user_id=self.user_id,
            user_name=self.user_name,
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
            kb_collection_names=self.kb_collection_names,
{%- endif %}
            metadata=self.metadata,
            ask_user=None,
            subagents={} if max_depth <= 0 else self.subagents,
        )
{%- endif %}


class AssistantAgent:
    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
        thinking_effort: str | None = None,
{%- if cookiecutter.enable_deep_research %}
        deep_research: bool = False,
{%- endif %}
{%- if cookiecutter.enable_todo %}
        todo_capability: "TodoCapability | None" = None,
{%- endif %}
{%- if cookiecutter.enable_subagents %}
        subagent_capability: "SubAgentCapability | None" = None,
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
        context_manager_capability: "ContextManagerCapability | None" = None,
{%- endif %}
    ):
{%- if cookiecutter.enable_deep_research %}
        self.deep_research = deep_research
{%- endif %}
{%- if cookiecutter.enable_todo %}
        self.todo_capability = todo_capability
{%- endif %}
{%- if cookiecutter.enable_subagents %}
        self.subagent_capability = subagent_capability
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
        self.context_manager_capability = context_manager_capability
{%- endif %}
        self.model_name = model_name or settings.AI_MODEL
        # ``temperature`` stays ``None`` when caller didn't set it — don't fall
        # back to settings.AI_TEMPERATURE here. Reasoning/o-series models
        # (gpt-5.5, o1, …) reject the parameter entirely, so we only forward
        # it to the model when explicitly requested.
        self.temperature = temperature
        self.thinking_effort = (
            thinking_effort
            if thinking_effort is not None
            else (settings.AI_THINKING_EFFORT if settings.AI_THINKING_ENABLED else None)
        )
{%- if cookiecutter.enable_rag %}
        self.system_prompt = system_prompt or get_system_prompt_with_rag()
{%- else %}
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
        if deep_research:
            self.system_prompt = system_prompt or get_research_prompt()
{%- endif %}
        self._agent: Agent[Deps, str] | None = None

    def _create_agent(self) -> Agent[Deps, str]:
        model = _build_model(self.model_name)

        capabilities: list[Any] = [ReinjectSystemPrompt()]
        if self.thinking_effort:
            capabilities.append(Thinking(effort=self.thinking_effort))  # ty: ignore[invalid-argument-type]
{%- if cookiecutter.enable_web_search or cookiecutter.enable_web_fetch %}
        # Local DuckDuckGo / fetch (the installed extras) — works uniformly across
        # all providers, unlike provider-native web search.
{%- if cookiecutter.enable_deep_research %}
        if not self.deep_research:
{%- if cookiecutter.enable_web_search %}
            capabilities.append(WebSearch(native=False, local="duckduckgo"))
{%- endif %}
{%- if cookiecutter.enable_web_fetch %}
            capabilities.append(WebFetch(native=False, local=True))
{%- endif %}
{%- else %}
{%- if cookiecutter.enable_web_search %}
        capabilities.append(WebSearch(native=False, local="duckduckgo"))
{%- endif %}
{%- if cookiecutter.enable_web_fetch %}
        capabilities.append(WebFetch(native=False, local=True))
{%- endif %}
{%- endif %}
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

{%- if cookiecutter.enable_skills %}
        toolsets: list[Any] = []
{%- endif %}
{%- if cookiecutter.enable_skills %}

        skills_dir = Path(__file__).parent.parent.parent / "skills"
        if skills_dir.exists():
            toolsets.append(SkillsToolset(directories=[str(skills_dir)]))
{%- endif %}
{%- if cookiecutter.enable_todo %}

        if self.todo_capability is not None:
            capabilities.append(self.todo_capability)
{%- endif %}
{%- if cookiecutter.enable_subagents %}
        if self.subagent_capability is not None:
            capabilities.append(self.subagent_capability)
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
        # Context manager must be last — summarization-pydantic-ai requires it.
        if self.context_manager_capability is not None:
            capabilities.append(self.context_manager_capability)
{%- endif %}

        agent = Agent[Deps, str](
            model=model,
            model_settings=model_settings,
            system_prompt=self.system_prompt,
            capabilities=capabilities,
{%- if cookiecutter.enable_skills %}
            toolsets=toolsets,
{%- endif %}
        )

        self._register_tools(agent)

        return agent

    def _register_tools(self, agent: Agent[Deps, str]) -> None:
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
            try:
{%- if cookiecutter.enable_teams %}
                return await search_knowledge_base(
                    query=query,
                    kb_collection_names=ctx.deps.kb_collection_names,
                    top_k=top_k,
                )
{%- else %}
                return await search_knowledge_base(query=query, top_k=top_k)
{%- endif %}
            except Exception as e:
                raise ModelRetry("Knowledge base temporarily unavailable, please try again.") from e
{%- endif %}

{%- if cookiecutter.enable_charts %}
        @agent.tool_plain
        def create_chart_tool(
            chart_type: ChartType,
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
                chart_type=chart_type,
                title=title,
                data=data,
                series=series,
                x_key=x_key,
                style=style,
            )
{%- endif %}

        @agent.tool
        async def ask_user(ctx: RunContext[Deps], questions: list[QuestionItem]) -> str:
            """Ask the user one or more questions and wait for their answers.

            Use this when a decision or missing detail would materially change what
            you do next and you can't reasonably assume it. You may pass several
            questions at once — the user answers them one after another and you get
            all the answers back together (good for an intake/setup flow). You can
            also call this again later to follow up on what they said. Prefer
            answering directly when the request is already clear.

            Args:
                questions: The questions to ask. Each has the question text, optional
                    suggested `options`, and `allow_custom` (whether a free-form
                    answer is allowed, default True).

            Returns:
                The user's answers as a Q/A transcript, with skipped questions marked.
            """
            if ctx.deps.ask_user is None:
                return (
                    "User interaction is unavailable here; proceed with a reasonable "
                    "assumption and state it briefly."
                )
            if not questions:
                return "No questions were provided."
            payload = [q.model_dump() for q in questions[:MAX_QUESTIONS]]
            answers = await ctx.deps.ask_user(payload)
            return format_answers(payload, answers)

{%- if cookiecutter.enable_code_execution %}

        @agent.tool
        async def run_python(ctx: RunContext[Deps], code: str) -> str:
            """Run Python in a sandbox and return its output.

            Use for multi-step number-crunching (projections, aggregations, simulations).
            SANDBOX LIMITATIONS — violating these causes "Execution failed" errors:
              - NO comma thousands separator in f-strings: ``{x:,}`` or ``{x:,.2f}``
                CRASHES. Use ``f"${int(x)}"`` or ``f"{x:.2f}"`` instead.
              - NO ``statistics``, ``random``, ``itertools``, ``collections``,
                numpy, pandas — compute stats manually with loops/math.
              - NO file I/O, network calls, or OS access.
              - NO ``import`` of any module not in: math, asyncio, json, datetime, re.
              - Walrus operator ``:=`` is unsupported.
              - f-string expressions must be simple: no ``!r``, no ``=`` suffix
                (``{x=}`` debug format crashes). Use ``print(f"x = {x}")``.

            Args:
                code: The Python source to execute.

            Returns:
                The captured stdout plus the final expression value, or an error
                message you can read and fix.
            """
            return await run_python_code(code)
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
        if self._agent is None:
            self._agent = self._create_agent()
        return self._agent

    async def run(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        deps: Deps | None = None,
    ) -> tuple[str, list[ToolCallPart | ToolReturnPart], Deps]:
        agent_deps = deps if deps is not None else Deps()

        logger.info("Running agent with user input: %s...", user_input[:100])
        result = await self.agent.run(
            user_input,
            deps=agent_deps,
            message_history=self._build_model_history(history),
        )

        tool_events: list[ToolCallPart | ToolReturnPart] = []
        for message in result.all_messages():
            if hasattr(message, "parts"):
                for part in message.parts:
                    if isinstance(part, (ToolCallPart, ToolReturnPart)):
                        tool_events.append(part)

        logger.info("Agent run complete. Output length: %s chars", len(result.output))

        return result.output, tool_events, agent_deps

    async def iter(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        deps: Deps | None = None,
    ) -> AsyncGenerator[Any, None]:
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
{%- if cookiecutter.enable_deep_research %}
    deep_research: bool = False,
{%- endif %}
{%- if cookiecutter.enable_todo %}
    todo_capability: "TodoCapability | None" = None,
{%- endif %}
{%- if cookiecutter.enable_subagents %}
    subagent_capability: "SubAgentCapability | None" = None,
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
    context_manager_capability: "ContextManagerCapability | None" = None,
{%- endif %}
) -> AssistantAgent:
    return AssistantAgent(
        model_name=model_name,
        thinking_effort=thinking_effort,
        temperature=temperature,
{%- if cookiecutter.enable_deep_research %}
        deep_research=deep_research,
{%- endif %}
{%- if cookiecutter.enable_todo %}
        todo_capability=todo_capability,
{%- endif %}
{%- if cookiecutter.enable_subagents %}
        subagent_capability=subagent_capability,
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
        context_manager_capability=context_manager_capability,
{%- endif %}
    )


async def run_agent(
    user_input: str,
    history: list[dict[str, str]],
    deps: Deps | None = None,
) -> tuple[str, list[ToolCallPart | ToolReturnPart], Deps]:
    agent = get_agent()
    return await agent.run(user_input, history, deps)
{%- else %}
"""PydanticAI Assistant agent - not configured."""
{%- endif %}
