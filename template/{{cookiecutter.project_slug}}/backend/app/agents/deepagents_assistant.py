{%- if cookiecutter.use_deepagents %}
"""DeepAgents implementation with middleware stacking and human-in-the-loop.

DeepAgents is a framework for building agentic coding assistants.
It uses LangGraph under the hood and comes with built-in tools for:
- File operations: ls, read_file, write_file, edit_file, glob, grep
- Task management: write_todos, task (subagent spawning)
- Shell execution: execute (when sandbox backend is enabled)

Human-in-the-loop (HITL) support:
- Configure tools requiring approval via DEEPAGENTS_INTERRUPT_TOOLS
- Allowed decisions: approve, edit, reject
- Interrupts are returned via stream/run and can be resumed with decisions

Backend types (DEEPAGENTS_BACKEND_TYPE):
- "state"  — in-memory, ephemeral per WebSocket connection (default)

Configuration via settings:
- DEEPAGENTS_BACKEND_TYPE: Backend type (state)
- DEEPAGENTS_MEMORY_PATHS: Comma-separated AGENTS.md memory file paths
- DEEPAGENTS_SKILLS_PATHS: Comma-separated skill paths
- DEEPAGENTS_ENABLE_EXECUTE: Enable shell execution (default: False)
- DEEPAGENTS_INTERRUPT_TOOLS: Tools requiring human approval
- DEEPAGENTS_ALLOWED_DECISIONS: Allowed decisions (approve,edit,reject)
"""

import logging
from typing import Annotated, Any, TypedDict

from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
{%- if cookiecutter.enable_rag %}
from langchain_core.tools import tool
{%- endif %}
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from langgraph.types import Command
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
{%- if cookiecutter.enable_rag %}
from app.agents.tools.rag_tool import search_knowledge_base
{%- endif %}
from app.core.config import settings

logger = logging.getLogger(__name__)


{%- if cookiecutter.enable_rag %}
@tool
async def search_documents(query: str, collection: str | None = None, top_k: int = 5) -> str:
    """Search the knowledge base for relevant documents.

    Use this tool to find information from uploaded documents before answering user queries.
    Searches across all available collections automatically.
    Cite sources by referring to the document filename from the search results.

    Args:
        query: The search query string.
        collection: Name of the collection to search (default: all collections).
        top_k: Number of top results to retrieve (default: 5).

    Returns:
        Formatted string with search results including content and scores.
    """
    return await search_knowledge_base(query=query, collection=collection, top_k=top_k)


# List of custom tools for DeepAgents when RAG is enabled
DEEPAGENTS_CUSTOM_TOOLS = [search_documents]
{%- else %}
DEEPAGENTS_CUSTOM_TOOLS = []
{%- endif %}


class AgentContext(TypedDict, total=False):
    """Runtime context for the agent.

    Passed via config parameter to the graph.
    """

    user_id: str | None
    user_name: str | None
    metadata: dict[str, Any]


class AgentState(TypedDict):
    """State for the DeepAgents agent.

    This is what flows through the agent graph.
    The messages field uses add_messages reducer to properly
    append new messages to the conversation history.
    """

    messages: Annotated[list[BaseMessage], add_messages]


class InterruptData(TypedDict):
    """Data structure for human-in-the-loop interrupts."""

    action_requests: list[dict[str, Any]]  # List of tool calls pending approval
    review_configs: list[dict[str, Any]]  # Config for each tool (allowed_decisions)


class Decision(TypedDict, total=False):
    """Human decision for a tool call."""

    type: str  # "approve", "edit", or "reject"
    edited_action: dict[str, Any] | None  # For "edit" type: modified tool call


def _parse_skills_paths() -> list[str] | None:
    """Parse skills paths from settings.

    Returns:
        List of skill paths or None if not configured.
    """
    if not settings.DEEPAGENTS_SKILLS_PATHS:
        return None

    paths = [p.strip() for p in settings.DEEPAGENTS_SKILLS_PATHS.split(",") if p.strip()]
    return paths if paths else None


def _parse_memory_paths() -> list[str] | None:
    """Parse memory (AGENTS.md) file paths from settings.

    Returns:
        List of memory file paths or None if not configured.
    """
    if not settings.DEEPAGENTS_MEMORY_PATHS:
        return None

    paths = [p.strip() for p in settings.DEEPAGENTS_MEMORY_PATHS.split(",") if p.strip()]
    return paths if paths else None


def _parse_interrupt_config() -> dict[str, bool | dict[str, list[str]]] | None:
    """Parse interrupt_on configuration from settings.

    Returns:
        Dict mapping tool names to interrupt configs, or None if not configured.
    """
    if not settings.DEEPAGENTS_INTERRUPT_TOOLS:
        return None

    tools = [t.strip() for t in settings.DEEPAGENTS_INTERRUPT_TOOLS.split(",") if t.strip()]
    if not tools:
        return None

    # Parse allowed decisions
    allowed = [d.strip() for d in settings.DEEPAGENTS_ALLOWED_DECISIONS.split(",") if d.strip()]
    if not allowed:
        allowed = ["approve", "edit", "reject"]

    # Build interrupt_on config
    interrupt_on: dict[str, bool | dict[str, list[str]]] = {}

    # Built-in DeepAgents tools
    builtin_tools = [
        "ls", "read_file", "write_file", "edit_file", "glob", "grep",
        "execute", "write_todos", "task"
    ]

    if "all" in tools:
        # Interrupt all tools
        for tool_name in builtin_tools:
            interrupt_on[tool_name] = {"allowed_decisions": allowed}
    else:
        for tool_name in tools:
            interrupt_on[tool_name] = {"allowed_decisions": allowed}

    return interrupt_on if interrupt_on else None


class DeepAgentsAssistant:
    """Wrapper for DeepAgents with run() and stream() methods.

    DeepAgents creates a LangGraph-based agent with built-in tools for
    filesystem operations, task management, and code execution.

    Backend: StateBackend (in-memory file state, no external deps).
    Skills can be configured via DEEPAGENTS_SKILLS_PATHS setting.
    Human-in-the-loop via DEEPAGENTS_INTERRUPT_TOOLS setting.
    """

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
        skills: list[str] | None = None,
        memory: list[str] | None = None,
        interrupt_on: dict[str, bool | dict[str, list[str]]] | None = None,
        conversation_id: str | None = None,
    ):
        """Initialize DeepAgentsAssistant.

        Args:
            model_name: LLM model name (default from settings.AI_MODEL)
            temperature: LLM temperature (default from settings.AI_TEMPERATURE)
            system_prompt: System prompt (default from DEFAULT_SYSTEM_PROMPT)
            skills: List of skill paths (default from settings.DEEPAGENTS_SKILLS_PATHS)
            memory: List of AGENTS.md memory paths (default from settings.DEEPAGENTS_MEMORY_PATHS)
            interrupt_on: Dict of tool names to interrupt configs (default from settings)
            conversation_id: Unique ID for the conversation.
        """
        self.model_name = model_name or settings.AI_MODEL
        self.temperature = temperature or settings.AI_TEMPERATURE
{%- if cookiecutter.enable_rag %}
        self.system_prompt = system_prompt or get_system_prompt_with_rag()
{%- else %}
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
{%- endif %}
        self.skills = skills if skills is not None else _parse_skills_paths()
        self.memory = memory if memory is not None else _parse_memory_paths()
        self.interrupt_on = interrupt_on if interrupt_on is not None else _parse_interrupt_config()
        self.conversation_id = conversation_id
        self._graph = None
        self._checkpointer = MemorySaver()

    def _create_backend(self):
        """Create the file-storage backend.

        Returns:
            BackendFactory (callable) for StateBackend (in-memory, ephemeral).
        """
        return lambda rt: StateBackend(rt)

    def _create_model(self):
        """Create the LLM model for DeepAgents."""
{%- if cookiecutter.use_openai %}
        return ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            api_key=settings.OPENAI_API_KEY,
            streaming=True,
        )
{%- endif %}
{%- if cookiecutter.use_anthropic %}
        return ChatAnthropic(
            model=self.model_name,
            temperature=self.temperature,
            api_key=settings.ANTHROPIC_API_KEY,
            streaming=True,
        )
{%- endif %}
{%- if cookiecutter.use_google %}
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            google_api_key=settings.GOOGLE_API_KEY,
        )
{%- endif %}

    @property
    def graph(self):
        """Get or create the compiled graph instance.

        The agent is created with:
        - Backend: StateBackend (in-memory)
        - TodoListMiddleware: For task tracking
        - FilesystemMiddleware: For file operations
        - SubAgentMiddleware: For spawning subagents
        - MemoryMiddleware: For AGENTS.md memory (if DEEPAGENTS_MEMORY_PATHS set)
        - Skills: Loaded from configured paths (if any)
        - interrupt_on: Human-in-the-loop config (if any)
        """
        if self._graph is None:
            model = self._create_model()
            backend = self._create_backend()

            self._graph = create_deep_agent(
                model=model,
                system_prompt=self.system_prompt,
                checkpointer=self._checkpointer,
                backend=backend,
                skills=self.skills,
                memory=self.memory,
                interrupt_on=self.interrupt_on,
                tools=DEEPAGENTS_CUSTOM_TOOLS,
            )

            logger.info(
                "DeepAgents initialized: model=%s backend=%s skills=%s memory=%s "
                "interrupt_on=%s execute=%s",
                self.model_name,
                settings.DEEPAGENTS_BACKEND_TYPE,
                self.skills,
                self.memory,
                list(self.interrupt_on.keys()) if self.interrupt_on else None,
                settings.DEEPAGENTS_ENABLE_EXECUTE,
            )

        return self._graph

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

    @staticmethod
    def extract_interrupt(result: dict[str, Any]) -> InterruptData | None:
        """Extract interrupt data from agent result if present.

        Args:
            result: The result from agent.invoke() or final state from stream.

        Returns:
            InterruptData if interrupted, None otherwise.
        """
        if not result.get("__interrupt__"):
            return None

        interrupt_value = result["__interrupt__"][0].value
        return InterruptData(
            action_requests=interrupt_value.get("action_requests", []),
            review_configs=interrupt_value.get("review_configs", []),
        )

    async def run(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        context: AgentContext | None = None,
        thread_id: str = "default",
        files: dict[str, str] | None = None,
    ) -> tuple[str, list[Any], AgentContext, InterruptData | None]:
        """Run agent and return the output along with tool call events.

        Args:
            user_input: User's message.
            history: Conversation history as list of {"role": "...", "content": "..."}.
            context: Optional runtime context with user info.
            thread_id: Thread ID for conversation continuity.
            files: Optional dict of {path: content} to provide to StateBackend.

        Returns:
            Tuple of (output_text, tool_events, context, interrupt_data).
            interrupt_data is None if not interrupted, otherwise contains pending approvals.
        """
        messages = self._convert_history(history)
        messages.append(HumanMessage(content=user_input))

        agent_context: AgentContext = context if context is not None else {}

        logger.info(f"Running DeepAgents with user input: {user_input[:100]}...")

        config = {
            "configurable": {
                "thread_id": thread_id,
                **agent_context,
            }
        }

        # Prepare input with optional files for StateBackend
        input_data: dict[str, Any] = {"messages": messages}
        if files:
            input_data["files"] = files

        result = await self.graph.ainvoke(input_data, config=config)

        # Check for interrupt
        interrupt_data = self.extract_interrupt(result)
        if interrupt_data:
            logger.info(f"Agent interrupted with {len(interrupt_data['action_requests'])} pending approvals")
            return "", [], agent_context, interrupt_data

        # Extract the final response and tool events
        output = ""
        tool_events: list[Any] = []

        for message in result.get("messages", []):
            if isinstance(message, AIMessage):
                if message.content:
                    output = message.content if isinstance(message.content, str) else str(message.content)
                if hasattr(message, "tool_calls") and message.tool_calls:
                    tool_events.extend(message.tool_calls)

        logger.info(f"DeepAgents run complete. Output length: {len(output)} chars")

        return output, tool_events, agent_context, None

    async def resume(
        self,
        decisions: list[Decision],
        thread_id: str = "default",
        context: AgentContext | None = None,
    ) -> tuple[str, list[Any], AgentContext, InterruptData | None]:
        """Resume agent execution after human-in-the-loop interrupt.

        Args:
            decisions: List of decisions for each pending tool call.
            thread_id: Thread ID (must match the interrupted session).
            context: Optional runtime context.

        Returns:
            Tuple of (output_text, tool_events, context, interrupt_data).
        """
        agent_context: AgentContext = context if context is not None else {}

        config = {
            "configurable": {
                "thread_id": thread_id,
                **agent_context,
            }
        }

        logger.info(f"Resuming DeepAgents with {len(decisions)} decisions")

        # Resume with Command
        result = await self.graph.ainvoke(
            Command(resume={"decisions": decisions}),
            config=config
        )

        # Check for another interrupt
        interrupt_data = self.extract_interrupt(result)
        if interrupt_data:
            logger.info(f"Agent interrupted again with {len(interrupt_data['action_requests'])} pending approvals")
            return "", [], agent_context, interrupt_data

        # Extract the final response and tool events
        output = ""
        tool_events: list[Any] = []

        for message in result.get("messages", []):
            if isinstance(message, AIMessage):
                if message.content:
                    output = message.content if isinstance(message.content, str) else str(message.content)
                if hasattr(message, "tool_calls") and message.tool_calls:
                    tool_events.extend(message.tool_calls)

        logger.info(f"DeepAgents resume complete. Output length: {len(output)} chars")

        return output, tool_events, agent_context, None

    async def stream(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        context: AgentContext | None = None,
        thread_id: str = "default",
        files: dict[str, str] | None = None,
    ):
        """Stream agent execution with message and state update streaming.

        Args:
            user_input: User's message.
            history: Conversation history.
            context: Optional runtime context.
            thread_id: Thread ID for conversation continuity.
            files: Optional dict of {path: content} to provide to StateBackend.

        Yields:
            Tuples of (stream_mode, data) for streaming responses.
            - stream_mode="messages": (chunk, metadata) for LLM tokens
            - stream_mode="updates": state updates after each node
            - stream_mode="interrupt": InterruptData when human approval needed
        """
        messages = self._convert_history(history)
        messages.append(HumanMessage(content=user_input))

        agent_context: AgentContext = context if context is not None else {}

        config = {
            "configurable": {
                "thread_id": thread_id,
                **agent_context,
            }
        }

        # Prepare input with optional files for StateBackend
        input_data: dict[str, Any] = {"messages": messages}
        if files:
            input_data["files"] = files

        logger.info(f"Starting DeepAgents stream for user input: {user_input[:100]}...")

        final_state: dict[str, Any] = {}

        async for stream_mode, data in self.graph.astream(
            input_data,
            config=config,
            stream_mode=["messages", "updates"],
        ):
            final_state = data if stream_mode == "updates" else final_state
            yield stream_mode, data

        # Check for interrupt after stream completes by reading checkpoint state
        state = await self.graph.aget_state(config)
        if state.next and state.tasks:
            interrupts = state.tasks[0].interrupts if state.tasks[0].interrupts else []
            if interrupts:
                interrupt_value = interrupts[0].value
                interrupt_data = InterruptData(
                    action_requests=interrupt_value.get("action_requests", []),
                    review_configs=interrupt_value.get("review_configs", []),
                )
                yield "interrupt", interrupt_data

    async def stream_resume(
        self,
        decisions: list[Decision],
        thread_id: str = "default",
        context: AgentContext | None = None,
    ):
        """Stream agent execution after resuming from interrupt.

        Args:
            decisions: List of decisions for each pending tool call.
            thread_id: Thread ID (must match the interrupted session).
            context: Optional runtime context.

        Yields:
            Tuples of (stream_mode, data) for streaming responses.
        """
        agent_context: AgentContext = context if context is not None else {}

        config = {
            "configurable": {
                "thread_id": thread_id,
                **agent_context,
            }
        }

        logger.info(f"Streaming resume with {len(decisions)} decisions")

        async for stream_mode, data in self.graph.astream(
            Command(resume={"decisions": decisions}),
            config=config,
            stream_mode=["messages", "updates"],
        ):
            yield stream_mode, data

        # Check for another interrupt by reading checkpoint state
        state = await self.graph.aget_state(config)
        if state.next and state.tasks:
            interrupts = state.tasks[0].interrupts if state.tasks[0].interrupts else []
            if interrupts:
                interrupt_value = interrupts[0].value
                interrupt_data = InterruptData(
                    action_requests=interrupt_value.get("action_requests", []),
                    review_configs=interrupt_value.get("review_configs", []),
                )
                yield "interrupt", interrupt_data


def get_agent(
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    interrupt_on: dict[str, bool | dict[str, list[str]]] | None = None,
    conversation_id: str | None = None,
) -> DeepAgentsAssistant:
    """Factory function to create a DeepAgentsAssistant.

    Args:
        skills: Optional list of skill paths to override settings.
        memory: Optional list of AGENTS.md memory paths to override settings.
        interrupt_on: Optional interrupt config to override settings.
        conversation_id: Unique conversation ID for workspace/container scoping.

    Returns:
        Configured DeepAgentsAssistant instance.
    """
    return DeepAgentsAssistant(
        skills=skills,
        memory=memory,
        interrupt_on=interrupt_on,
        conversation_id=conversation_id,
    )


async def run_agent(
    user_input: str,
    history: list[dict[str, str]],
    context: AgentContext | None = None,
    thread_id: str = "default",
    files: dict[str, str] | None = None,
) -> tuple[str, list[Any], AgentContext, InterruptData | None]:
    """Run agent and return the output along with tool call events.

    This is a convenience function for backwards compatibility.

    Args:
        user_input: User's message.
        history: Conversation history.
        context: Optional runtime context.
        thread_id: Thread ID for conversation continuity.
        files: Optional dict of {path: content} to provide to StateBackend.

    Returns:
        Tuple of (output_text, tool_events, context, interrupt_data).
    """
    agent = get_agent()
    return await agent.run(user_input, history, context, thread_id, files)
{%- else %}
"""DeepAgents Assistant agent - not configured."""
{%- endif %}
