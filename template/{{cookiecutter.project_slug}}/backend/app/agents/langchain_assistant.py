{%- if cookiecutter.use_langchain %}
"""Assistant agent with LangChain.

The main conversational agent that can be extended with custom tools.
"""

import logging
from typing import Any, TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware, ToolCallLimitMiddleware, ToolRetryMiddleware
from langchain.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph.state import CompiledStateGraph
{%- if cookiecutter.use_openai %}
from langchain_openai import ChatOpenAI
{%- endif %}
{%- if cookiecutter.use_anthropic %}
from langchain_anthropic import ChatAnthropic
{%- endif %}
{%- if cookiecutter.use_google %}
from langchain_google_genai import ChatGoogleGenerativeAI
{%- endif %}

from app.agents.prompts import DEFAULT_SYSTEM_PROMPT
{%- if cookiecutter.enable_rag %}
from app.agents.prompts import get_system_prompt_with_rag
{%- endif %}
from app.agents.tools import get_current_datetime
{%- if cookiecutter.enable_web_search %}
from app.agents.tools.web_search import web_search
{%- endif %}
{%- if cookiecutter.web_fetch_tool %}
from app.agents.tools.fetch_url import fetch_url
{%- endif %}
{%- if cookiecutter.enable_rag %}
{%- if cookiecutter.enable_teams %}
from app.agents.tools.rag_tool import _active_kb_collections, search_knowledge_base
{%- else %}
from app.agents.tools.rag_tool import search_knowledge_base
{%- endif %}
{%- endif %}
{%- if cookiecutter.enable_charts %}
from app.agents.tools.chart_tool import create_chart
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
from app.agents.tools.antv_chart import get_antv_langchain_tools
from app.agents.tools.map_tool import MapMarker, create_map
{%- endif %}
from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentContext(TypedDict, total=False):
    """Runtime context for the agent.

    Passed via context parameter to agent.invoke()/stream().
    """

    user_id: str | None
    user_name: str | None
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    # Resolved server-side from conversation.active_knowledge_base_ids — never from the LLM
    kb_collection_names: list[str]
{%- endif %}
    metadata: dict[str, Any]



@tool
def current_datetime() -> dict[str, str]:
    """Get the current date and time.

    Use this tool when you need to know the current date or time.
    """
    return get_current_datetime()


{%- if cookiecutter.enable_web_search %}
@tool
async def web_search_tool(query: str, max_results: int = 5) -> str:
    """Search the web for current information.

    Use this tool to find up-to-date information about events, facts, or topics
    that may not be in the model's training data.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (1-10, default: 5).

    Returns:
        Formatted string with search results including titles, URLs, and content.
    """
    return await web_search(query, max_results)
{%- endif %}
{%- if cookiecutter.web_fetch_tool %}
@tool
async def fetch_url_tool(url: str) -> str:
    """Fetch a web page and return its readable text content.

    Use this to read a specific URL the user gave you (an article, doc, or
    page). Distinct from web search, which finds pages.

    Args:
        url: The absolute http(s) URL to fetch.

    Returns:
        The page title and main text with markup stripped.
    """
    return await fetch_url(url)
{%- endif %}


{%- if cookiecutter.enable_rag %}
{%- if cookiecutter.enable_teams %}
@tool
async def search_documents(query: str, top_k: int = 5) -> str:
    """Search the knowledge base for relevant documents.

    Use this tool to find information from uploaded documents before answering user queries.
    Searches across all knowledge bases active for this conversation.
    Cite sources by referring to the document filename from the search results.

    Args:
        query: The search query string.
        top_k: Number of top results to retrieve (default: 5).

    Returns:
        Formatted string with search results including content and scores.
    """
    return await search_knowledge_base(query=query, top_k=top_k)
{%- else %}
@tool
async def search_documents(query: str, top_k: int = 5) -> str:
    """Search the knowledge base for relevant documents.

    Use this tool to find information from uploaded documents before answering user queries.
    Cite sources by referring to the document filename from the search results.

    Args:
        query: The search query string.
        top_k: Number of top results to retrieve (default: 5).

    Returns:
        Formatted string with search results including content and scores.
    """
    return await search_knowledge_base(query=query, top_k=top_k)
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_charts %}


@tool
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


@tool
def create_map_tool(
    title: str,
    markers: list[MapMarker],
    center: list[float] | None = None,
    zoom: int | None = None,
) -> str:
    """Create an interactive map to show places geographically for the user.

    Use whenever the user asks to show, map, or locate places. Provide
    latitude/longitude for each marker from your own knowledge (e.g. Warsaw ≈
    52.23, 21.01). Do not repeat the returned JSON — just briefly describe the
    map you created.

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


class LangChainAssistant:
    """Assistant agent wrapper for conversational AI using LangChain.

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
        self.temperature = temperature or settings.AI_TEMPERATURE
        # Extended-thinking effort for reasoning-capable models. ``None`` keeps
        # the model in plain mode; "low"/"medium"/"high" enables provider-
        # specific reasoning (Claude extended thinking, OpenAI o-series, etc).
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
        self._agent: CompiledStateGraph | None = None
        self._tools = [current_datetime]
{%- if cookiecutter.enable_web_search %}
        self._tools.append(web_search_tool)
{%- endif %}
{%- if cookiecutter.web_fetch_tool %}
        self._tools.append(fetch_url_tool)
{%- endif %}
{%- if cookiecutter.enable_rag %}
        self._tools.append(search_documents)
{%- endif %}
{%- if cookiecutter.enable_charts %}
        self._tools.append(create_chart_tool)
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
        self._tools.append(create_map_tool)
        self._tools.extend(get_antv_langchain_tools())
{%- endif %}

    def _create_agent(self) -> CompiledStateGraph:
        """Create and configure the LangChain agent."""
{%- if cookiecutter.use_all_providers %}
        lowered = self.model_name.lower()
        if lowered.startswith(("claude-", "claude/")):
            anthropic_kwargs: dict[str, Any] = {}
            if self.thinking_effort:
                budget = {"low": 1024, "medium": 4096, "high": 16384}.get(self.thinking_effort, 4096)
                anthropic_kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
                anthropic_kwargs["max_tokens"] = budget + 4096
                anthropic_kwargs["temperature"] = 1.0
            model = ChatAnthropic(
                model=self.model_name,
                temperature=anthropic_kwargs.pop("temperature", self.temperature),
                api_key=settings.ANTHROPIC_API_KEY,
                **anthropic_kwargs,
            )
        elif lowered.startswith("gemini"):
            model = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=self.temperature,
                google_api_key=settings.GOOGLE_API_KEY,
            )
        else:
            openai_kwargs: dict[str, Any] = {}
            if self.thinking_effort:
                openai_kwargs["reasoning"] = {"effort": self.thinking_effort, "summary": "auto"}
                openai_kwargs["use_responses_api"] = True
                openai_kwargs["output_version"] = "responses/v1"
            model = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=settings.OPENAI_API_KEY,
                **openai_kwargs,
            )
{%- elif cookiecutter.use_openai %}
        # OpenAI: ``reasoning`` is honored only by the Responses API.
        openai_kwargs: dict[str, Any] = {}
        if self.thinking_effort:
            openai_kwargs["reasoning"] = {
                "effort": self.thinking_effort,
                "summary": "auto",
            }
            openai_kwargs["use_responses_api"] = True
            openai_kwargs["output_version"] = "responses/v1"
        model = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            api_key=settings.OPENAI_API_KEY,
            **openai_kwargs,
        )
{%- elif cookiecutter.use_anthropic %}
        # Claude: extended thinking needs an explicit token budget.
        anthropic_kwargs: dict[str, Any] = {}
        if self.thinking_effort:
            budget = {"low": 1024, "medium": 4096, "high": 16384}.get(
                self.thinking_effort, 4096
            )
            anthropic_kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": budget,
            }
            anthropic_kwargs["max_tokens"] = budget + 4096
            anthropic_kwargs["temperature"] = 1.0
        model = ChatAnthropic(
            model=self.model_name,
            temperature=anthropic_kwargs.pop("temperature", self.temperature),
            api_key=settings.ANTHROPIC_API_KEY,
            **anthropic_kwargs,
        )
{%- elif cookiecutter.use_google %}
        model = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            google_api_key=settings.GOOGLE_API_KEY,
        )
{%- endif %}

        return create_agent(
            model=model,
            tools=self._tools,
            system_prompt=self.system_prompt,
            context_schema=AgentContext,
            middleware=[
                ModelRetryMiddleware(max_retries=2),
                ToolRetryMiddleware(max_retries=1),
                ToolCallLimitMiddleware(run_limit=15),
            ],
        )

    @property
    def agent(self) -> CompiledStateGraph:
        """Get or create the agent instance."""
        if self._agent is None:
            self._agent = self._create_agent()
        return self._agent

    @staticmethod
    def _convert_history(
        history: list[dict[str, str]] | None,
    ) -> list[HumanMessage | AIMessage | SystemMessage]:
        """Convert conversation history to LangChain message format."""
        messages: list[HumanMessage | AIMessage | SystemMessage] = []

        for msg in history or []:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
            elif msg["role"] == "system":
                messages.append(SystemMessage(content=msg["content"]))

        return messages

    async def run(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        context: AgentContext | None = None,
    ) -> tuple[str, list[Any], AgentContext]:
        """Run agent and return the output along with tool call events.

        Args:
            user_input: User's message.
            history: Conversation history as list of {"role": "...", "content": "..."}.
            context: Optional runtime context with user info.

        Returns:
            Tuple of (output_text, tool_events, context).
        """
        messages = self._convert_history(history)
        messages.append(HumanMessage(content=user_input))

        agent_context: AgentContext = context if context is not None else {}

        logger.info(f"Running agent with user input: {user_input[:100]}...")

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        token = _active_kb_collections.set(agent_context.get("kb_collection_names") or [])
        try:
            result = await self.agent.ainvoke(
                {"messages": messages},
                config={"configurable": agent_context} if agent_context else None,
            )
        finally:
            _active_kb_collections.reset(token)
{%- else %}
        result = await self.agent.ainvoke(
            {"messages": messages},
            config={"configurable": agent_context} if agent_context else None,
        )
{%- endif %}

        # Extract the final response
        output = ""
        tool_events: list[Any] = []

        for message in result.get("messages", []):
            if hasattr(message, "content") and isinstance(message, AIMessage):
                output = message.content
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_events.extend(message.tool_calls)

        logger.info(f"Agent run complete. Output length: {len(output)} chars")

        return output, tool_events, agent_context

    async def stream(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        context: AgentContext | None = None,
    ):
        """Stream agent execution with token-level streaming.

        Args:
            user_input: User's message.
            history: Conversation history.
            context: Optional runtime context.

        Yields:
            Tuples of (stream_mode, data) for streaming responses.
            - stream_mode="messages": (token, metadata) for LLM tokens
            - stream_mode="updates": state updates after each step
        """
        messages = self._convert_history(history)
        messages.append(HumanMessage(content=user_input))

        agent_context: AgentContext = context if context is not None else {}

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        token = _active_kb_collections.set(agent_context.get("kb_collection_names") or [])
        try:
            async for event in self.agent.astream(
                {"messages": messages},
                stream_mode=["messages", "updates"],
                config={"configurable": agent_context} if agent_context else None,
            ):
                yield event
        finally:
            _active_kb_collections.reset(token)
{%- else %}
        async for event in self.agent.astream(
            {"messages": messages},
            stream_mode=["messages", "updates"],
            config={"configurable": agent_context} if agent_context else None,
        ):
            yield event
{%- endif %}


def get_agent(
    model_name: str | None = None,
    thinking_effort: str | None = None,
) -> LangChainAssistant:
    """Factory function to create a LangChainAssistant.

    Args:
        model_name: Override the default AI model.
        thinking_effort: Extended-thinking effort ("low"/"medium"/"high") or
            ``None`` to disable. Wired to ``thinking={...}`` for Anthropic and
            ``reasoning={...}`` for OpenAI Responses-API models.

    Returns:
        Configured LangChainAssistant instance.
    """
    return LangChainAssistant(model_name=model_name, thinking_effort=thinking_effort)


async def run_agent(
    user_input: str,
    history: list[dict[str, str]],
    context: AgentContext | None = None,
) -> tuple[str, list[Any], AgentContext]:
    """Run agent and return the output along with tool call events.

    This is a convenience function for backwards compatibility.

    Args:
        user_input: User's message.
        history: Conversation history.
        context: Optional runtime context.

    Returns:
        Tuple of (output_text, tool_events, context).
    """
    agent = get_agent()
    return await agent.run(user_input, history, context)
{%- else %}
"""LangChain Assistant agent - not configured."""
{%- endif %}
