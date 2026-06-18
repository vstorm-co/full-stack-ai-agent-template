"""Assistant agent with PydanticAI.

The main conversational agent that can be extended with custom tools.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.capabilities import (
    ReinjectSystemPrompt,
    Thinking,
    WebFetch,
    WebSearch,
)
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.settings import ModelSettings
from pydantic_ai_skills import SkillsToolset

from app.agents.prompts import (
    get_research_prompt,
    get_system_prompt_with_rag,
)
from app.agents.tools import get_current_datetime
from app.agents.tools.antv_chart import get_antv_toolset
from app.agents.tools.ask_user_tool import MAX_QUESTIONS, QuestionItem, format_answers
from app.agents.tools.chart_tool import create_chart
from app.agents.tools.code_execution import EmitToolEvent
from app.agents.tools.code_execution import run_python as run_python_code
from app.agents.tools.map_tool import MapMarker, create_map
from app.agents.tools.rag_tool import search_knowledge_base
from app.core.config import settings

logger = logging.getLogger(__name__)


def _build_model(model_name: str):
    return OpenRouterModel(
        model_name or settings.AI_MODEL,
        provider=OpenRouterProvider(api_key=settings.OPENROUTER_API_KEY),
    )


AskUserCallback = Callable[[list[dict[str, Any]]], Awaitable[list[dict[str, Any]]]]


@dataclass
class Deps:
    """Dependencies for the assistant agent.

    These are passed to tools via RunContext.
    """

    user_id: str | None = None
    user_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    ask_user: AskUserCallback | None = None
    emit_tool_event: EmitToolEvent | None = None
    # Required by SubAgentDepsProtocol; kept empty (capabilities carry the agents).
    subagents: dict[str, Any] = field(default_factory=dict)

    def clone_for_subagent(self, max_depth: int = 0) -> "Deps":
        """Create isolated deps for a delegated subagent.

        Required by ``subagents-pydantic-ai`` (``SubAgentDepsProtocol``). Shares
        the lightweight context but drops the interactive hooks and hands over an
        empty ``subagents`` dict when ``max_depth <= 0`` so a subagent cannot
        recurse.
        """
        return Deps(
            user_id=self.user_id,
            user_name=self.user_name,
            metadata=self.metadata,
            ask_user=None,
            emit_tool_event=None,
            subagents={} if max_depth <= 0 else self.subagents,
        )


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
        deep_research: bool = False,
        research_capabilities: list[Any] | None = None,
    ):
        self.deep_research = deep_research
        self.research_capabilities = research_capabilities or []
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
        if deep_research:
            self.system_prompt = system_prompt or get_research_prompt()
        else:
            self.system_prompt = system_prompt or get_system_prompt_with_rag()
        self._agent: Agent[Deps, str] | None = None

    def _create_agent(self) -> Agent[Deps, str]:
        """Create and configure the PydanticAI agent."""
        model = _build_model(self.model_name)

        capabilities: list[Any] = [ReinjectSystemPrompt()]
        if self.thinking_effort:
            capabilities.append(Thinking(effort=self.thinking_effort))  # ty: ignore[invalid-argument-type]
        # Local DuckDuckGo / fetch (the installed extras) — works uniformly across
        # all providers, unlike provider-native web search.
        if not self.deep_research:
            capabilities.append(WebSearch(native=False, local="duckduckgo"))
            capabilities.append(WebFetch(native=False, local=True))

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

        # None when AntV is disabled or the sidecar is unavailable.
        antv_toolset = get_antv_toolset()
        toolsets = [antv_toolset] if antv_toolset is not None else []

        skills_dir = Path(__file__).parent.parent.parent / "skills"
        if skills_dir.exists():
            toolsets.append(SkillsToolset(directories=[str(skills_dir)]))

        capabilities.extend(self.research_capabilities)

        agent = Agent[Deps, str](
            model=model,
            model_settings=model_settings,
            system_prompt=self.system_prompt,
            capabilities=capabilities,
            toolsets=toolsets,
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

        @agent.tool
        async def search_documents(ctx: RunContext[Deps], query: str, top_k: int = 5) -> str:
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
                return await search_knowledge_base(query=query, top_k=top_k)
            except Exception as e:
                raise ModelRetry("Knowledge base temporarily unavailable, please try again.") from e

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

        if settings.ENABLE_CODE_EXECUTION:

            @agent.tool
            async def run_python(ctx: RunContext[Deps], code: str) -> str:
                """Run Python in a sandbox to compute and to build visualizations.

                Use this for multi-step number-crunching (projections, aggregations,
                simulations) and whenever you want to produce several charts at once.
                Inside the code you can call:
                  - ``create_chart(chart_type, title, data, series=None, x_key="x", style=None)``
                  - ``create_map(title, markers, center=None, zoom=None)``
                  - ``current_datetime()``
                ``create_chart``/``create_map`` are async — call them with ``await``,
                and run several in parallel with ``await asyncio.gather(...)``. Each one
                renders to the user immediately as an interactive chart/map.
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

                Print intermediate values you want to keep; don't paste the returned
                chart JSON back to the user.

                Args:
                    code: The Python source to execute.

                Returns:
                    The captured stdout plus the final expression value, or an error
                    message you can read and fix.
                """
                return await run_python_code(code, emit=ctx.deps.emit_tool_event)

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
    deep_research: bool = False,
    research_capabilities: list[Any] | None = None,
) -> AssistantAgent:
    """Factory function to create an AssistantAgent.

    Args:
        model_name: Override the default AI model.
        thinking_effort: Override thinking effort ("low", "medium", "high", or None to disable).
        temperature: Sampling temperature (typically 0.0-2.0). ``None`` falls back to
            ``settings.AI_TEMPERATURE``.
        deep_research: Build the planner persona and drop the planner's own web
            tools so it delegates to subagents.
        research_capabilities: Pre-built deep-research capabilities (
            subagents, context manager), already ordered with the context manager last.

    Returns:
        Configured AssistantAgent instance.
    """
    return AssistantAgent(
        model_name=model_name,
        thinking_effort=thinking_effort,
        temperature=temperature,
        deep_research=deep_research,
        research_capabilities=research_capabilities,
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
