{%- if cookiecutter.enable_ai_agent and cookiecutter.use_langgraph %}
"""LangGraph ReAct Agent implementation.

A simple ReAct (Reasoning + Acting) agent built with LangGraph.
Uses a graph-based architecture with conditional edges for tool execution.
"""

import logging
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
{%- if cookiecutter.use_openai %}
from langchain_openai import ChatOpenAI
{%- endif %}
{%- if cookiecutter.use_anthropic %}
from langchain_anthropic import ChatAnthropic
{%- endif %}

from app.agents.prompts import DEFAULT_SYSTEM_PROMPT
{%- if cookiecutter.enable_rag %}
from app.agents.prompts import get_system_prompt_with_rag
{%- endif %}
from app.agents.tools import get_current_datetime
{%- if cookiecutter.enable_rag %}
from app.agents.tools.rag_tool import search_knowledge_base_sync
{%- endif %}
from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentContext(TypedDict, total=False):
    """Runtime context for the agent.

    Passed via config parameter to the graph.
    """

    user_id: str | None
    user_name: str | None
    metadata: dict[str, Any]


class AgentState(TypedDict):
    """State for the LangGraph agent.

    This is what flows through the agent graph.
    The messages field uses add_messages reducer to properly
    append new messages to the conversation history.
    """

    messages: Annotated[list[BaseMessage], add_messages]


@tool
def current_datetime() -> str:
    """Get the current date and time.

    Use this tool when you need to know the current date or time.
    """
    return get_current_datetime()


{%- if cookiecutter.enable_rag %}
@tool
def search_documents(query: str, collection: str = "documents", top_k: int = 5) -> str:
    """Search the knowledge base for relevant documents.

    Use this tool to find information from uploaded documents before answering user queries.
    Cite sources by referring to the document filename from the search results.

    Args:
        query: The search query string.
        collection: Name of the collection to search (default: "documents").
        top_k: Number of top results to retrieve (default: 5).

    Returns:
        Formatted string with search results including content and scores.
    """
    return search_knowledge_base_sync(query=query, collection=collection, top_k=top_k)
{%- endif %}


# List of all available tools
ALL_TOOLS = [current_datetime]
{%- if cookiecutter.enable_rag %}
ALL_TOOLS.append(search_documents)
{%- endif %}

# Create a dictionary for quick tool lookup by name
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}


class LangGraphAssistant:
    """ReAct agent wrapper using LangGraph.

    Implements a graph-based agent with:
    - An agent node that processes messages and decides actions
    - A tools node that executes tool calls
    - Conditional edges that loop back for tool execution or end

    The ReAct pattern:
    1. Agent receives input and reasons about it
    2. If tool calls are needed, execute them
    3. Tool results are added to messages
    4. Agent reasons again with new information
    5. Repeat until agent provides final response
    """

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
    ):
        self.model_name = model_name or settings.AI_MODEL
        self.temperature = temperature or settings.AI_TEMPERATURE
{%- if cookiecutter.enable_rag %}
        self.system_prompt = system_prompt or get_system_prompt_with_rag()
{%- else %}
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
{%- endif %}
        self._graph = None
        self._checkpointer = MemorySaver()

    def _create_model(self):
        """Create the LLM model with tools bound."""
{%- if cookiecutter.use_openai %}
        model = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            api_key=settings.OPENAI_API_KEY,
            streaming=True,
        )
{%- endif %}
{%- if cookiecutter.use_anthropic %}
        model = ChatAnthropic(
            model=self.model_name,
            temperature=self.temperature,
            api_key=settings.ANTHROPIC_API_KEY,
            streaming=True,
        )
{%- endif %}

        return model.bind_tools(ALL_TOOLS)

    def _agent_node(self, state: AgentState) -> dict[str, list[BaseMessage]]:
        """Agent node that processes messages and decides whether to call tools.

        This is the main reasoning node in the ReAct pattern.
        """
        model = self._create_model()

        # Prepend system message to the conversation
        messages = [SystemMessage(content=self.system_prompt), *state["messages"]]

        response = model.invoke(messages)

        logger.info(
            f"Agent processed message - Tool calls: {len(response.tool_calls) if hasattr(response, 'tool_calls') else 0}"
        )

        return {"messages": [response]}

    def _tools_node(self, state: AgentState) -> dict[str, list[ToolMessage]]:
        """Tools node that executes tool calls from the agent.

        Processes each tool call and returns results as ToolMessages.
        """
        messages = state["messages"]
        last_message = messages[-1]

        tool_results = []

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                try:
                    tool_fn = TOOLS_BY_NAME.get(tool_name)
                    if tool_fn:
                        result = tool_fn.invoke(tool_args)
                        tool_results.append(
                            ToolMessage(
                                content=str(result),
                                tool_call_id=tool_id,
                                name=tool_name,
                            )
                        )
                        logger.info(f"Tool {tool_name} completed successfully")
                    else:
                        error_msg = f"Unknown tool: {tool_name}"
                        logger.error(error_msg)
                        tool_results.append(
                            ToolMessage(
                                content=error_msg,
                                tool_call_id=tool_id,
                                name=tool_name,
                            )
                        )
                except Exception as e:
                    error_msg = f"Error executing {tool_name}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    tool_results.append(
                        ToolMessage(
                            content=error_msg,
                            tool_call_id=tool_id,
                            name=tool_name,
                        )
                    )

        return {"messages": tool_results}

    def _should_continue(self, state: AgentState) -> Literal["tools", "__end__"]:
        """Conditional edge that decides whether to continue to tools or end.

        Returns:
            - "tools" if the agent made tool calls (needs to execute tools)
            - "__end__" if the agent provided a final response (no tool calls)
        """
        messages = state["messages"]
        last_message = messages[-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            logger.info(f"Continuing to tools - {len(last_message.tool_calls)} tool(s) to execute")
            return "tools"

        logger.info("No tool calls - ending conversation")
        return "__end__"

    def _build_graph(self) -> StateGraph:
        """Build and compile the LangGraph state graph."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tools_node)

        # Add edges
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {"tools": "tools", "__end__": END},
        )
        workflow.add_edge("tools", "agent")

        return workflow.compile(checkpointer=self._checkpointer)

    @property
    def graph(self):
        """Get or create the compiled graph instance."""
        if self._graph is None:
            self._graph = self._build_graph()
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

    async def run(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        context: AgentContext | None = None,
        thread_id: str = "default",
    ) -> tuple[str, list[Any], AgentContext]:
        """Run agent and return the output along with tool call events.

        Args:
            user_input: User's message.
            history: Conversation history as list of {"role": "...", "content": "..."}.
            context: Optional runtime context with user info.
            thread_id: Thread ID for conversation continuity.

        Returns:
            Tuple of (output_text, tool_events, context).
        """
        messages = self._convert_history(history)
        messages.append(HumanMessage(content=user_input))

        agent_context: AgentContext = context if context is not None else {}

        logger.info(f"Running agent with user input: {user_input[:100]}...")

        config = {
            "configurable": {
                "thread_id": thread_id,
                **agent_context,
            }
        }

        result = await self.graph.ainvoke({"messages": messages}, config=config)

        # Extract the final response and tool events
        output = ""
        tool_events: list[Any] = []

        for message in result.get("messages", []):
            if isinstance(message, AIMessage):
                if message.content:
                    output = message.content if isinstance(message.content, str) else str(message.content)
                if hasattr(message, "tool_calls") and message.tool_calls:
                    tool_events.extend(message.tool_calls)

        logger.info(f"Agent run complete. Output length: {len(output)} chars")

        return output, tool_events, agent_context

    async def stream(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        context: AgentContext | None = None,
        thread_id: str = "default",
    ):
        """Stream agent execution with message and state update streaming.

        Args:
            user_input: User's message.
            history: Conversation history.
            context: Optional runtime context.
            thread_id: Thread ID for conversation continuity.

        Yields:
            Tuples of (stream_mode, data) for streaming responses.
            - stream_mode="messages": (chunk, metadata) for LLM tokens
            - stream_mode="updates": state updates after each node
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

        logger.info(f"Starting stream for user input: {user_input[:100]}...")

        async for stream_mode, data in self.graph.astream(
            {"messages": messages},
            config=config,
            stream_mode=["messages", "updates"],
        ):
            yield stream_mode, data


def get_agent() -> LangGraphAssistant:
    """Factory function to create a LangGraphAssistant.

    Returns:
        Configured LangGraphAssistant instance.
    """
    return LangGraphAssistant()


async def run_agent(
    user_input: str,
    history: list[dict[str, str]],
    context: AgentContext | None = None,
    thread_id: str = "default",
) -> tuple[str, list[Any], AgentContext]:
    """Run agent and return the output along with tool call events.

    This is a convenience function for backwards compatibility.

    Args:
        user_input: User's message.
        history: Conversation history.
        context: Optional runtime context.
        thread_id: Thread ID for conversation continuity.

    Returns:
        Tuple of (output_text, tool_events, context).
    """
    agent = get_agent()
    return await agent.run(user_input, history, context, thread_id)
{%- else %}
"""LangGraph Assistant agent - not configured."""
{%- endif %}
