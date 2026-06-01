{%- if cookiecutter.use_crewai %}
"""CrewAI Multi-Agent implementation.

A multi-agent orchestration framework using CrewAI.
Enables teams of AI agents to work together on complex tasks.
Uses CrewAI's event system for real-time streaming to WebSocket.
"""

import asyncio
import contextvars
import logging
import os
from queue import Empty, Queue
from threading import Thread
from typing import Any, TypedDict

# Disable CrewAI interactive prompts for server use
os.environ.setdefault("CREWAI_DISABLE_TRACES_PROMPT", "true")

from crewai import Agent, Crew, Process, Task
from crewai.events import (
    crewai_event_bus,
    CrewKickoffStartedEvent,
    CrewKickoffCompletedEvent,
    CrewKickoffFailedEvent,
    AgentExecutionStartedEvent,
    AgentExecutionCompletedEvent,
    TaskStartedEvent,
    TaskCompletedEvent,
    ToolUsageStartedEvent,
    ToolUsageFinishedEvent,
    LLMCallStartedEvent,
    LLMCallCompletedEvent,
)
from pydantic import BaseModel, Field
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
from app.agents.tools.rag_tool import SearchKnowledgeBase
{%- endif %}
from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    role: str = Field(..., description="Agent's role/title")
    goal: str = Field(..., description="Agent's primary goal")
    backstory: str = Field(..., description="Agent's background context")
    tools: list[str] = Field(default_factory=list)
    allow_delegation: bool = True
    verbose: bool = True


class TaskConfig(BaseModel):
    """Configuration for a single task."""

    description: str = Field(..., description="Task description")
    expected_output: str = Field(..., description="Expected output format")
    agent_role: str = Field(..., description="Role of agent to execute this")
    context_from: list[str] = Field(default_factory=list)


class CrewConfig(BaseModel):
    """Configuration for the entire crew."""

    name: str = "default_crew"
    process: str = "sequential"  # sequential, hierarchical
    memory: bool = True
    max_rpm: int = 10
    agents: list[AgentConfig] = Field(default_factory=list)
    tasks: list[TaskConfig] = Field(default_factory=list)


class CrewContext(TypedDict, total=False):
    """Runtime context for crew execution."""

    user_id: str | None
    user_name: str | None
    metadata: dict[str, Any]


class CrewEventQueueListener:
    """Event listener that sends CrewAI events to a queue for WebSocket streaming.

    Registers handlers with the global crewai_event_bus to capture all events
    and forward them to a queue for async WebSocket streaming.
    """

    def __init__(self, event_queue: Queue):
        self._event_queue = event_queue
        self._handlers: list[Any] = []
        self._register_handlers()

    def _register_handlers(self):
        """Register all event handlers with the CrewAI event bus."""

        def on_crew_started(source, event: CrewKickoffStartedEvent):
            self._event_queue.put({
                "type": "crew_started",
                "crew_name": getattr(event, "crew_name", "crew"),
                "crew_id": str(getattr(event, "crew_id", "")),
            })

        def on_crew_completed(source, event: CrewKickoffCompletedEvent):
            output = getattr(event, "output", None)
            metrics = getattr(source, "usage_metrics", None)
            usage_payload = None
            if metrics is not None:
                usage_payload = {
                    "prompt_tokens": int(getattr(metrics, "prompt_tokens", 0) or 0),
                    "completion_tokens": int(getattr(metrics, "completion_tokens", 0) or 0),
                    "cached_prompt_tokens": int(getattr(metrics, "cached_prompt_tokens", 0) or 0),
                    "total_tokens": int(getattr(metrics, "total_tokens", 0) or 0),
                }
            self._event_queue.put({
                "type": "crew_complete",
                "result": str(output.raw if hasattr(output, "raw") else output) if output else "",
                "usage": usage_payload,
            })

        def on_crew_failed(source, event: CrewKickoffFailedEvent):
            self._event_queue.put({
                "type": "error",
                "error": str(getattr(event, "error", "Unknown error")),
            })

        def on_agent_started(source, event: AgentExecutionStartedEvent):
            agent = getattr(event, "agent", None)
            self._event_queue.put({
                "type": "agent_started",
                "agent": getattr(agent, "role", "Unknown") if agent else "Unknown",
                "task": str(getattr(event, "task", "")),
            })

        def on_agent_completed(source, event: AgentExecutionCompletedEvent):
            agent = getattr(event, "agent", None)
            output = getattr(event, "output", None)
            self._event_queue.put({
                "type": "agent_completed",
                "agent": getattr(agent, "role", "Unknown") if agent else "Unknown",
                "output": str(output) if output else "",
            })

        def on_task_started(source, event: TaskStartedEvent):
            task = getattr(event, "task", None)
            self._event_queue.put({
                "type": "task_started",
                "task_id": str(getattr(task, "id", "")) if task else "",
                "description": str(getattr(task, "description", "")) if task else "",
                "agent": getattr(getattr(task, "agent", None), "role", "Unknown") if task else "Unknown",
            })

        def on_task_completed(source, event: TaskCompletedEvent):
            task = getattr(event, "task", None)
            output = getattr(event, "output", None)
            self._event_queue.put({
                "type": "task_completed",
                "task_id": str(getattr(task, "id", "")) if task else "",
                "output": str(output.raw if hasattr(output, "raw") else output) if output else "",
                "agent": getattr(getattr(task, "agent", None), "role", "Unknown") if task else "Unknown",
            })

        def on_tool_started(source, event: ToolUsageStartedEvent):
            self._event_queue.put({
                "type": "tool_started",
                "tool_name": str(getattr(event, "tool_name", "Unknown")),
                "tool_args": str(getattr(event, "tool_args", {})),
                "agent": str(getattr(event, "agent", "Unknown")),
            })

        def on_tool_finished(source, event: ToolUsageFinishedEvent):
            self._event_queue.put({
                "type": "tool_finished",
                "tool_name": str(getattr(event, "tool_name", "Unknown")),
                "tool_result": str(getattr(event, "tool_result", "")),
                "agent": str(getattr(event, "agent", "Unknown")),
            })

        def on_llm_started(source, event: LLMCallStartedEvent):
            self._event_queue.put({
                "type": "llm_started",
                "agent": str(getattr(event, "agent", "Unknown")),
            })

        def on_llm_completed(source, event: LLMCallCompletedEvent):
            response = getattr(event, "response", None)
            self._event_queue.put({
                "type": "llm_completed",
                "agent": str(getattr(event, "agent", "Unknown")),
                "response": str(response) if response else "",
            })

        # Register handlers with the event bus
        crewai_event_bus.on(CrewKickoffStartedEvent)(on_crew_started)
        crewai_event_bus.on(CrewKickoffCompletedEvent)(on_crew_completed)
        crewai_event_bus.on(CrewKickoffFailedEvent)(on_crew_failed)
        crewai_event_bus.on(AgentExecutionStartedEvent)(on_agent_started)
        crewai_event_bus.on(AgentExecutionCompletedEvent)(on_agent_completed)
        crewai_event_bus.on(TaskStartedEvent)(on_task_started)
        crewai_event_bus.on(TaskCompletedEvent)(on_task_completed)
        crewai_event_bus.on(ToolUsageStartedEvent)(on_tool_started)
        crewai_event_bus.on(ToolUsageFinishedEvent)(on_tool_finished)
        crewai_event_bus.on(LLMCallStartedEvent)(on_llm_started)
        crewai_event_bus.on(LLMCallCompletedEvent)(on_llm_completed)

        # Store references to prevent garbage collection
        self._handlers = [
            on_crew_started, on_crew_completed, on_crew_failed,
            on_agent_started, on_agent_completed,
            on_task_started, on_task_completed,
            on_tool_started, on_tool_finished,
            on_llm_started, on_llm_completed,
        ]


{%- if cookiecutter.enable_rag %}
def _search_knowledge_base_sync(query: str, collection: str = "documents", top_k: int = 5) -> str:
    """Synchronous wrapper for RAG search tool.

    This sync function is used by CrewAI agents since they run in a
    synchronous context. Uses asyncio.run() to execute the async RAG search.

    Args:
        query: The search query string.
        collection: Name of the collection to search (default: "documents").
        top_k: Number of top results to retrieve (default: 5).

    Returns:
        Formatted string with search results.
    """
    from app.agents.tools.rag_tool import search_knowledge_base_sync
    return search_knowledge_base_sync(query=query, collection=collection, top_k=top_k)


{%- endif %}
class CrewAIAssistant:
    """Multi-agent crew orchestration using CrewAI.

    Supports:
    - Multiple specialized agents with different roles
    - Sequential or hierarchical task execution
    - Agent delegation and collaboration
    - Real-time event streaming via WebSocket

    CrewAI Pattern:
    1. Define agents with roles, goals, and backstories
    2. Define tasks assigned to specific agents
    3. Crew executes tasks in order (sequential/hierarchical)
    4. Events are streamed in real-time to connected clients
    5. Final output aggregated from all task results
    """

    def __init__(
        self,
        config: CrewConfig | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
    ):
        self.config = config or self._default_config()
        self.model_name = model_name or settings.AI_MODEL
        self.temperature = temperature or settings.AI_TEMPERATURE
{%- if cookiecutter.enable_rag %}
        self.system_prompt = system_prompt or get_system_prompt_with_rag()
{%- else %}
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
{%- endif %}
        self._crew: Crew | None = None
        self._agents: dict[str, Agent] = {}

    def _default_config(self) -> CrewConfig:
        """Default crew configuration for general assistance."""
{%- if cookiecutter.enable_rag %}
        research_tools = ["search_documents"]
        task_description_suffix = " Use search_documents to find information from uploaded documents before answering, and cite sources by referring to the document filename."
{%- else %}
        research_tools = []
        task_description_suffix = ""
{%- endif %}
{%- if cookiecutter.enable_web_search %}
        research_tools.append("search_web")
{%- endif %}
{%- if cookiecutter.web_fetch_tool %}
        research_tools.append("fetch_url")
{%- endif %}
{%- if cookiecutter.enable_charts %}
        writer_tools = ["create_chart"]
{%- else %}
        writer_tools = []
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
        writer_tools.append("create_map")
{%- endif %}
        return CrewConfig(
            name="assistant_crew",
            process="sequential",
            memory=False,  # Disable memory for simpler setup
            agents=[
                AgentConfig(
                    role="Research Analyst",
                    goal="Gather and analyze information accurately to help the user",
                    backstory="You are an expert research analyst skilled at finding and synthesizing information. You always provide accurate, well-researched answers.",
                    tools=research_tools,
                    allow_delegation=False,  # Simpler without delegation
                ),
                AgentConfig(
                    role="Content Writer",
                    goal="Create clear, well-structured responses for the user",
                    backstory="You are a skilled writer who produces high-quality, readable content. You take research findings and transform them into helpful responses.",
                    tools=writer_tools,
                    allow_delegation=False,
                ),
            ],
            tasks=[
                TaskConfig(
                    description=f"Research and analyze the user's query: {{ "{{user_input}}" }}. Gather all relevant information needed to provide a comprehensive answer.{task_description_suffix}",
                    expected_output="Comprehensive research findings with key facts and insights",
                    agent_role="Research Analyst",
                ),
                TaskConfig(
                    description="Based on the research findings, write a clear, helpful response to the user's original query.",
                    expected_output="A well-written, user-friendly response that addresses the query",
                    agent_role="Content Writer",
                    context_from=["Research Analyst"],
                ),
            ],
        )

    def _get_llm(self):
        """Get LLM instance based on settings."""
{%- if cookiecutter.use_all_providers %}
        lowered = self.model_name.lower()
        if lowered.startswith(("claude-", "claude/")):
            return ChatAnthropic(
                model=self.model_name,
                temperature=self.temperature,
                api_key=settings.ANTHROPIC_API_KEY,
            )
        if lowered.startswith("gemini"):
            return ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=self.temperature,
                google_api_key=settings.GOOGLE_API_KEY,
            )
        return ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            api_key=settings.OPENAI_API_KEY,
        )
{%- elif cookiecutter.use_openai %}
        return ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            api_key=settings.OPENAI_API_KEY,
        )
{%- elif cookiecutter.use_anthropic %}
        return ChatAnthropic(
            model=self.model_name,
            temperature=self.temperature,
            api_key=settings.ANTHROPIC_API_KEY,
        )
{%- elif cookiecutter.use_google %}
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            google_api_key=settings.GOOGLE_API_KEY,
        )
{%- endif %}

    def _build_agents(self) -> dict[str, Agent]:
        """Build Agent instances from config."""
        agents = {}
        llm = self._get_llm()

        def get_tools_for_agent(agent_tools: list[str]) -> list:
            """Get tool functions for an agent based on tool names."""
            tool_map = {}
{%- if cookiecutter.enable_rag %}
            tool_map["search_documents"] = SearchKnowledgeBase()
{%- endif %}
{%- if cookiecutter.enable_web_search %}
            from app.agents.tools.web_search import web_search_sync
            from langchain_core.tools import tool as lc_tool
            @lc_tool
            def search_web(query: str) -> str:
                """Search the web for current information."""
                return web_search_sync(query=query)
            tool_map["search_web"] = search_web
{%- endif %}
{%- if cookiecutter.web_fetch_tool %}
            from app.agents.tools.fetch_url import fetch_url_sync
            from langchain_core.tools import tool as lc_tool_fetch

            @lc_tool_fetch
            def fetch_url(url: str) -> str:
                """Fetch a web page and return its readable text content."""
                return fetch_url_sync(url=url)

            tool_map["fetch_url"] = fetch_url
{%- endif %}
{%- if cookiecutter.enable_charts %}
            from app.agents.tools.chart_tool import create_chart
            from langchain_core.tools import tool as lc_tool_charts

            @lc_tool_charts
            def create_chart_tool(
                chart_type: str,
                title: str,
                data: list[dict[str, Any]],
                series: list[dict[str, Any]] | None = None,
                x_key: str = "x",
                style: dict[str, Any] | None = None,
            ) -> str:
                """Create a chart (line/bar/pie/area/scatter) to visualize data.

                Use whenever the user asks to plot/chart/graph/visualize numbers.
                Do not repeat the returned JSON back — just describe the chart.

                Args:
                    chart_type: "line", "bar", "pie", "area", or "scatter".
                    title: Short chart title.
                    data: Row dicts, e.g. [{"x": "Jan", "revenue": 120}].
                    series: Optional [{"key", "label"?, "color"?}].
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

            tool_map["create_chart"] = create_chart_tool
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
            from app.agents.tools.antv_chart import get_antv_crewai_tools
            from app.agents.tools.map_tool import MapMarker, create_map
            from langchain_core.tools import tool as lc_tool_map

            @lc_tool_map
            def create_map_tool(
                title: str,
                markers: list[MapMarker],
                center: list[float] | None = None,
                zoom: int | None = None,
            ) -> str:
                """Create an interactive map to show places geographically.

                Use whenever the user asks to show, map, or locate places.
                Provide lat/lng for each marker from your own knowledge (e.g.
                Warsaw ≈ 52.23, 21.01). Do not repeat the returned JSON — just
                describe the map.

                Args:
                    title: Short map title.
                    markers: One entry per place, each with lat, lng and a short
                        label (plus optional description and color). Non-empty.
                    center: Optional [lat, lng] center (auto-fit if omitted).
                    zoom: Optional zoom level 1-18 (useful for a single marker).
                """
                return create_map(
                    title=title,
                    markers=[m.model_dump() for m in markers],
                    center=center,
                    zoom=zoom,
                )

            tool_map["create_map"] = create_map_tool
{%- endif %}
            resolved = [tool_map[name] for name in agent_tools if name in tool_map]
{%- if cookiecutter.enable_antv_charts %}
            # AntV diagram tools from the MCP sidecar go to the visual agent
            # (the writer, which also carries create_map/create_chart).
            if "create_map" in agent_tools or "create_chart" in agent_tools:
                resolved.extend(get_antv_crewai_tools())
{%- endif %}
            return resolved

        for agent_config in self.config.agents:
            agent = Agent(
                role=agent_config.role,
                goal=agent_config.goal,
                backstory=agent_config.backstory,
                tools=get_tools_for_agent(agent_config.tools),
                allow_delegation=agent_config.allow_delegation,
                verbose=agent_config.verbose,
                llm=llm,
            )
            agents[agent_config.role] = agent

        return agents

    def _build_tasks(self, agents: dict[str, Agent]) -> list[Task]:
        """Build Task instances from config."""
        tasks = []
        task_by_agent: dict[str, Task] = {}

        for task_config in self.config.tasks:
            agent = agents.get(task_config.agent_role)
            if not agent:
                raise ValueError(f"Agent '{task_config.agent_role}' not found")

            context = [
                task_by_agent[role] for role in task_config.context_from if role in task_by_agent
            ]

            task = Task(
                description=task_config.description,
                expected_output=task_config.expected_output,
                agent=agent,
                context=context if context else None,
            )
            tasks.append(task)
            task_by_agent[task_config.agent_role] = task

        return tasks

    def _build_crew(self) -> Crew:
        """Build and return the Crew instance."""
        self._agents = self._build_agents()
        tasks = self._build_tasks(self._agents)

        process = (
            Process.hierarchical
            if self.config.process == "hierarchical"
            else Process.sequential
        )

        return Crew(
            agents=list(self._agents.values()),
            tasks=tasks,
            process=process,
            memory=self.config.memory,
            verbose=False,  # Disable console output for server use
        )

    @property
    def crew(self) -> Crew:
        """Get or create the Crew instance."""
        if self._crew is None:
            self._crew = self._build_crew()
        return self._crew

    async def run(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        context: CrewContext | None = None,
        thread_id: str = "default",
    ) -> tuple[str, list[dict[str, Any]], CrewContext]:
        """Run the crew and return results.

        Args:
            user_input: User's message/request.
            history: Conversation history (for context).
            context: Runtime context.
            thread_id: Thread ID for conversation continuity.

        Returns:
            Tuple of (output_text, task_results, context).
        """
        crew_context: CrewContext = context if context is not None else {}

        inputs = {
            "user_input": user_input,
            "history": self._format_history(history),
            **crew_context.get("metadata", {}),
        }

        logger.info(f"Starting CrewAI execution: {user_input[:100]}...")

        # Reset crew for fresh execution
        self._crew = None

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.crew.kickoff(inputs=inputs)
        )

        task_results = []
        for task in self.crew.tasks:
            if task.output:
                task_results.append({
                    "agent": task.agent.role if task.agent else "Unknown",
                    "description": task.description[:100],
                    "output": str(task.output.raw if hasattr(task.output, "raw") else task.output),
                })

        output = str(result.raw if hasattr(result, "raw") else result) if result else ""
        logger.info(f"CrewAI execution complete. Output length: {len(output)}")

        return output, task_results, crew_context

    async def stream(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        context: CrewContext | None = None,
        thread_id: str = "default",
    ):
        """Stream crew execution with real-time event updates.

        Uses CrewAI's event system to capture and stream:
        - crew_started: Crew execution begins
        - agent_started/completed: Agent lifecycle events
        - task_started/completed: Task lifecycle events
        - tool_started/finished: Tool usage events
        - llm_started/completed: LLM call events
        - crew_complete: Final result
        - error: Error occurred

        Args:
            user_input: User's message.
            history: Conversation history.
            context: Optional runtime context.
            thread_id: Thread ID for conversation continuity.

        Yields:
            Dict events with type and data.
        """
        event_queue: Queue = Queue()

        inputs = {
            "user_input": user_input,
            "history": self._format_history(history),
        }

        # Reset crew for fresh execution
        self._crew = None

        # Create event listener BEFORE starting thread (keeps reference alive)
        listener = CrewEventQueueListener(event_queue)

        def run_with_events():
            """Run crew with event listener."""
            nonlocal listener  # Keep reference to prevent GC
            try:
                # Build and run crew
                crew = self.crew
                result = crew.kickoff(inputs=inputs)

                # Ensure final result is sent (event bus may have already sent it)
                if result:
                    event_queue.put({
                        "type": "crew_complete",
                        "result": str(result.raw if hasattr(result, "raw") else result),
                    })

            except Exception as e:
                logger.error(f"CrewAI execution error: {e}", exc_info=True)
                event_queue.put({
                    "type": "error",
                    "error": str(e),
                })
            finally:
                event_queue.put(None)  # Signal completion

        # Start crew in background thread, propagating ContextVars (e.g. _active_kb_collections)
        _ctx = contextvars.copy_context()
        thread = Thread(target=lambda: _ctx.run(run_with_events), daemon=True)
        thread.start()

        # Yield events as they arrive
        while True:
            await asyncio.sleep(0.05)

            while True:
                try:
                    event = event_queue.get_nowait()
                    if event is None:
                        thread.join(timeout=2.0)
                        _ = listener  # Keep reference until done
                        return
                    yield event
                except Empty:
                    break

            # Check if thread is still alive
            if not thread.is_alive():
                # Drain remaining events
                while True:
                    try:
                        event = event_queue.get_nowait()
                        if event is None:
                            _ = listener  # Keep reference until done
                            return
                        yield event
                    except Empty:
                        break
                _ = listener  # Keep reference until done
                return

    def _format_history(self, history: list[dict[str, str]] | None) -> str:
        """Format conversation history as context string."""
        if not history:
            return ""

        formatted = []
        for msg in history[-5:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted.append(f"{role.upper()}: {content}")

        return "\n".join(formatted)


def get_crew() -> CrewAIAssistant:
    """Factory function to create a CrewAIAssistant.

    Returns:
        Configured CrewAIAssistant instance.
    """
    return CrewAIAssistant()


async def run_crew(
    user_input: str,
    history: list[dict[str, str]],
    context: CrewContext | None = None,
    thread_id: str = "default",
) -> tuple[str, list[dict[str, Any]], CrewContext]:
    """Run crew and return the output along with task results.

    This is a convenience function for backwards compatibility.

    Args:
        user_input: User's message.
        history: Conversation history.
        context: Optional runtime context.
        thread_id: Thread ID for conversation continuity.

    Returns:
        Tuple of (output_text, task_results, context).
    """
    crew = get_crew()
    return await crew.run(user_input, history, context, thread_id)
{%- else %}
"""CrewAI Assistant agent - not configured."""
{%- endif %}
