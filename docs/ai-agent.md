# AI Agent Documentation

This document describes the AI agent integrations available in the template.

## Overview

The template supports multiple AI frameworks for building intelligent agents:

| Framework | Description | Best For |
|-----------|-------------|----------|
| **PydanticAI** | Type-safe AI with Pydantic integration | Simple agents, type safety |
| **LangChain** | Comprehensive AI tooling ecosystem | Complex chains, many integrations |
| **LangGraph** | Graph-based ReAct agents | Multi-step reasoning, tool loops |
| **CrewAI** | Multi-agent orchestration | Agent teams, complex workflows |
| **RAG** | Document retrieval & knowledge base | Building AI assistants with context |

Select your framework during project creation:

```bash
fastapi-fullstack create my_project --ai-framework pydanticai  # default
fastapi-fullstack create my_project --ai-framework langchain
fastapi-fullstack create my_project --ai-framework langgraph
fastapi-fullstack create my_project --ai-framework crewai
```

---

## PydanticAI Agent

The default agent is powered by [PydanticAI](https://ai.pydantic.dev), providing:

- Type-safe AI interactions
- Tool/function calling support
- WebSocket streaming responses
- Conversation history persistence
- Logfire observability integration

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      WebSocket Client                        │
│                (Frontend / External Client)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket Endpoint                        │
│                  /api/v1/agent/ws                           │
│         Authentication, Message Routing, Streaming           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AssistantAgent                            │
│              PydanticAI Agent Wrapper                        │
│         Model Config, Tools, Streaming via iter()            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      LLM Provider                            │
│                  OpenAI / Anthropic / etc.                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional
AI_MODEL=gpt-4o-mini        # Default model
AI_TEMPERATURE=0.7          # Response creativity (0.0-1.0)
```

### Settings

```python
# app/core/config.py
class Settings(BaseSettings):
    # AI Agent
    OPENAI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4o-mini"
    AI_TEMPERATURE: float = 0.7
```

---

## Agent Implementation

### AssistantAgent Class

```python
# app/agents/assistant.py
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from app.core.config import settings


@dataclass
class Deps:
    """Dependencies for the agent.

    Passed to tools via RunContext.
    """
    user_id: str | None = None
    user_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AssistantAgent:
    """Wrapper for PydanticAI agent with tool support."""

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
        system_prompt: str = "You are a helpful assistant.",
    ):
        self.model_name = model_name or settings.AI_MODEL
        self.temperature = temperature or settings.AI_TEMPERATURE
        self.system_prompt = system_prompt
        self._agent: Agent[Deps, str] | None = None

    def _create_agent(self) -> Agent[Deps, str]:
        """Create and configure the PydanticAI agent."""
        model = OpenAIChatModel(
            self.model_name,
            provider=OpenAIProvider(api_key=settings.OPENAI_API_KEY),
        )

        agent = Agent[Deps, str](
            model=model,
            model_settings=ModelSettings(temperature=self.temperature),
            system_prompt=self.system_prompt,
        )

        self._register_tools(agent)
        return agent

    def _register_tools(self, agent: Agent[Deps, str]) -> None:
        """Register all tools on the agent."""

        @agent.tool
        async def current_datetime(ctx: RunContext[Deps]) -> str:
            """Get the current date and time."""
            from app.agents.tools import get_current_datetime
            return get_current_datetime()

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
        """Run agent and return output with tool events."""
        # Convert history to PydanticAI format
        model_history = self._convert_history(history or [])
        agent_deps = deps or Deps()

        result = await self.agent.run(
            user_input,
            deps=agent_deps,
            message_history=model_history,
        )

        # Extract tool call events
        tool_events = []
        for message in result.all_messages():
            if hasattr(message, "parts"):
                for part in message.parts:
                    if hasattr(part, "tool_name"):
                        tool_events.append(part)

        return result.output, tool_events, agent_deps

    async def iter(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        deps: Deps | None = None,
    ):
        """Stream agent execution with full event access."""
        model_history = self._convert_history(history or [])
        agent_deps = deps or Deps()

        async with self.agent.iter(
            user_input,
            deps=agent_deps,
            message_history=model_history,
        ) as run:
            async for event in run:
                yield event
```

---

## Adding Custom Tools

### Creating a Tool

```python
# app/agents/tools/weather.py
import httpx


async def get_weather(city: str) -> dict:
    """Get current weather for a city.

    Args:
        city: City name (e.g., "London", "New York")

    Returns:
        Weather data including temperature and conditions.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.weatherapi.com/v1/current.json",
            params={"key": "YOUR_API_KEY", "q": city},
        )
        data = response.json()

    return {
        "city": city,
        "temperature": data["current"]["temp_c"],
        "condition": data["current"]["condition"]["text"],
        "humidity": data["current"]["humidity"],
    }
```

### Registering the Tool

```python
# app/agents/assistant.py

def _register_tools(self, agent: Agent[Deps, str]) -> None:
    """Register all tools on the agent."""

    @agent.tool
    async def current_datetime(ctx: RunContext[Deps]) -> str:
        """Get the current date and time."""
        from app.agents.tools import get_current_datetime
        return get_current_datetime()

    @agent.tool
    async def get_weather(ctx: RunContext[Deps], city: str) -> dict:
        """Get current weather for a city.

        Args:
            city: City name (e.g., "London", "New York")
        """
        from app.agents.tools.weather import get_weather as fetch_weather
        return await fetch_weather(city)

    @agent.tool
    async def search_database(ctx: RunContext[Deps], query: str) -> list[dict]:
        """Search the database for items.

        Args:
            query: Search query string
        """
        # Access dependencies via ctx.deps
        user_id = ctx.deps.user_id
        # Perform search...
        return results
```

### Tool Best Practices

1. **Clear docstrings** - The LLM uses these to understand when to call tools
2. **Type hints** - Required for argument validation
3. **Error handling** - Return meaningful error messages

---

## RAG Tool Integration

When RAG is enabled, agents can search a knowledge base for relevant documents.

### Enabling RAG with AI Agent

```bash
fastapi-fullstack create my_project --enable-rag --enable-ai-agent
```

### Using the RAG Tool

```python
# app/agents/assistant.py
from app.agents.tools.rag_tool import search_knowledge_base

def _register_tools(self, agent: Agent[Deps, str]) -> None:
    """Register all tools on the agent."""

    @agent.tool
    async def search_knowledge(ctx: RunContext[Deps], query: str) -> str:
        """Search the knowledge base for relevant documents.
        
        Args:
            query: The search query string
        """
        return await search_knowledge_base(
            query=query,
            collection="documents",
            top_k=5
        )
```

### RAG Tool Function Signature

```python
async def search_knowledge_base(
    query: str,
    collection: str = "documents",
    top_k: int = 5,
) -> str:
    """Search the knowledge base and return formatted results.
    
    Args:
        query: The search query string.
        collection: Name of the collection to search (default: "documents").
        top_k: Number of top results to retrieve (default: 5).
    
    Returns:
        Formatted string with search results, including content and scores.
    """
```

### CrewAI Integration

For CrewAI agents, use the synchronous wrapper:

```python
# app/agents/crewai_assistant.py
from app.agents.tools.rag_tool import search_knowledge_base_sync

class MyCrewAgent:
    def __init__(self):
        self.tools = [
            Tool.from_function(
                func=search_knowledge_base_sync,
                name="search_knowledge_base",
                description="Search the knowledge base for relevant documents"
            )
        ]
```

See also: [RAG Documentation](rag.md) for detailed configuration.
3. **Async** - Use async functions for I/O operations
4. **Error handling** - Return user-friendly error messages
5. **Context access** - Use `ctx.deps` for user-specific data

---

## WebSocket Endpoint

### Basic Endpoint

```python
# app/api/routes/v1/agent.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic_ai.messages import PartDeltaEvent

from app.agents.assistant import AssistantAgent, Deps

router = APIRouter(prefix="/agent", tags=["agent"])


@router.websocket("/ws")
async def agent_websocket(websocket: WebSocket):
    """WebSocket endpoint for AI agent streaming."""
    await websocket.accept()

    agent = AssistantAgent()
    history: list[dict[str, str]] = []

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            user_input = data.get("content", "")
            history = data.get("history", history)

            # Send start event
            await websocket.send_json({"type": "start"})

            # Stream response
            full_response = ""
            async for event in agent.iter(user_input, history):
                if isinstance(event, PartDeltaEvent):
                    if hasattr(event.delta, "content"):
                        token = event.delta.content
                        full_response += token
                        await websocket.send_json({
                            "type": "token",
                            "content": token,
                        })

                # Handle tool calls
                if hasattr(event, "tool_name"):
                    await websocket.send_json({
                        "type": "tool_call",
                        "tool": {
                            "name": event.tool_name,
                            "args": event.args,
                        },
                    })

            # Update history
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": full_response})

            # Send end event
            await websocket.send_json({"type": "end"})

    except WebSocketDisconnect:
        pass
```

### With Authentication

```python
# app/api/routes/v1/agent.py
from fastapi import WebSocket, WebSocketDisconnect, Query, HTTPException

from app.core.security import verify_token
from app.services.user import UserService


@router.websocket("/ws")
async def agent_websocket(
    websocket: WebSocket,
    token: str | None = Query(None),
):
    """WebSocket endpoint with JWT authentication."""
    # Verify token
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    payload = verify_token(token)
    if payload is None:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()

    # Create agent with user context
    deps = Deps(
        user_id=payload["sub"],
        user_name=payload.get("name"),
    )
    agent = AssistantAgent()

    # ... rest of the handler
```

---

## Conversation Persistence

### Database Models

```python
# app/db/models/conversation.py
from uuid import uuid4
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Conversation(Base):
    """Conversation (chat session) model."""

    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation")


class Message(Base):
    """Chat message model."""

    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
```

### Conversation Service

```python
# app/services/conversation.py
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation, Message
from app.repositories.conversation import conversation_repo


class ConversationService:
    """Service for managing conversations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: UUID, title: str | None = None) -> Conversation:
        """Create a new conversation."""
        return await conversation_repo.create(self.db, user_id=user_id, title=title)

    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        tool_calls: dict | None = None,
    ) -> Message:
        """Add a message to a conversation."""
        return await conversation_repo.add_message(
            self.db,
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
        )

    async def get_messages(self, conversation_id: UUID) -> list[Message]:
        """Get all messages in a conversation."""
        return await conversation_repo.get_messages(self.db, conversation_id)
```

### Persisting Messages

```python
# In WebSocket handler
async for event in agent.iter(user_input, history):
    # ... stream tokens ...

# Save to database
await conversation_service.add_message(
    conversation_id=conversation_id,
    role="user",
    content=user_input,
)
await conversation_service.add_message(
    conversation_id=conversation_id,
    role="assistant",
    content=full_response,
    tool_calls=tool_events if tool_events else None,
)
```

---

## Logfire Integration

The agent is automatically instrumented with Logfire:

```python
# app/core/logfire_setup.py
import logfire


def instrument_pydantic_ai() -> None:
    """Instrument PydanticAI for Logfire tracing."""
    logfire.instrument_pydantic_ai()
```

This provides:

- **Traces** for each agent run
- **Token usage** tracking
- **Tool call** visibility
- **Latency** metrics
- **Error** tracking

View traces in the [Logfire dashboard](https://logfire.pydantic.dev).

---

## Frontend Integration

### WebSocket Hook

```typescript
// src/hooks/use-websocket.ts
export function useAgentWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback((token?: string) => {
    const url = token
      ? `${WS_URL}?token=${token}`
      : WS_URL;

    const ws = new WebSocket(url);

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleMessage(data);
    };

    wsRef.current = ws;
  }, []);

  const send = useCallback((content: string, history: Message[]) => {
    wsRef.current?.send(JSON.stringify({
      type: 'message',
      content,
      history: history.map(m => ({
        role: m.role,
        content: m.content,
      })),
    }));
  }, []);

  return { isConnected, isStreaming, connect, send };
}
```

### Message Types

```typescript
// src/types/chat.ts
interface StreamEvent {
  type: 'start' | 'token' | 'tool_call' | 'end' | 'error';
  content?: string;
  tool?: {
    name: string;
    args: Record<string, unknown>;
  };
  error?: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  tool_name?: string;
  created_at: Date;
}
```

---

## Best Practices

1. **System prompts** - Be specific about the agent's role and capabilities
2. **Tool design** - Keep tools focused and well-documented
3. **Error handling** - Return graceful error messages to users
4. **Rate limiting** - Protect against abuse with request limits
5. **Context management** - Limit history length to control token usage
6. **Observability** - Use Logfire to monitor agent behavior
7. **Testing** - Mock LLM responses for deterministic tests

---

## Troubleshooting

### Common Issues

**"Invalid API key"**

- Check `OPENAI_API_KEY` is set correctly
- Verify the key has sufficient credits

**"Model not found"**

- Check `AI_MODEL` is a valid model name
- Ensure you have access to the specified model

**"WebSocket connection failed"**

- Verify the backend is running
- Check CORS settings for WebSocket connections
- Ensure the token is valid (if using auth)

**"Tool not found"**

- Verify the tool is registered in `_register_tools()`
- Check the tool's docstring is descriptive enough

---

## CrewAI Multi-Agent Framework

[CrewAI](https://crewai.com) enables multi-agent orchestration where specialized agents collaborate on complex tasks.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      WebSocket Client                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket Endpoint                        │
│                  /api/v1/agent/ws                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CrewAIAssistant                           │
│              Multi-Agent Crew Orchestrator                   │
│         Agents, Tasks, Process (sequential/hierarchical)    │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐
        │ Agent 1 │     │ Agent 2 │     │ Agent N │
        │Researcher│    │ Writer  │     │   ...   │
        └─────────┘     └─────────┘     └─────────┘
```

### Configuration

```python
# app/agents/crewai_assistant.py
from pydantic import BaseModel

class AgentConfig(BaseModel):
    role: str           # Agent's role (e.g., "Research Analyst")
    goal: str           # What the agent aims to achieve
    backstory: str      # Agent's background/personality
    tools: list[str] = []
    allow_delegation: bool = True
    verbose: bool = True

class TaskConfig(BaseModel):
    description: str    # Task description
    expected_output: str
    agent_role: str     # Which agent handles this task
    context_from: list[str] = []  # Dependencies on other tasks

class CrewConfig(BaseModel):
    name: str = "default_crew"
    process: str = "sequential"  # or "hierarchical"
    memory: bool = True
    max_rpm: int = 10
    agents: list[AgentConfig] = []
    tasks: list[TaskConfig] = []
```

### Event Streaming

CrewAI streams real-time events via WebSocket:

| Event Type | Description |
|------------|-------------|
| `crew_started` | Crew execution begins |
| `crew_complete` | Final result ready |
| `agent_started` | Agent begins working on task |
| `agent_completed` | Agent finishes task |
| `task_started` | Task execution begins |
| `task_completed` | Task result available |
| `tool_started` | Tool is being called |
| `tool_finished` | Tool returns result |
| `llm_started` | LLM request begins |
| `llm_completed` | LLM response received |
| `error` | Error occurred |

### Example Usage

```python
# Create a research crew
crew = CrewAIAssistant(config=CrewConfig(
    name="research_crew",
    process="sequential",
    agents=[
        AgentConfig(
            role="Research Analyst",
            goal="Find accurate information",
            backstory="Expert researcher with attention to detail",
        ),
        AgentConfig(
            role="Content Writer",
            goal="Create clear, engaging content",
            backstory="Skilled writer who simplifies complex topics",
        ),
    ],
    tasks=[
        TaskConfig(
            description="Research the topic: {user_prompt}",
            expected_output="Comprehensive research summary",
            agent_role="Research Analyst",
        ),
        TaskConfig(
            description="Write an article based on the research",
            expected_output="Well-structured article",
            agent_role="Content Writer",
            context_from=["Research Analyst"],
        ),
    ],
))

# Stream events
async for event in crew.stream("Explain quantum computing"):
    print(event)
```

---

## LangGraph ReAct Agent

[LangGraph](https://langchain-ai.github.io/langgraph/) provides graph-based agent orchestration with the ReAct pattern.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      WebSocket Client                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket Endpoint                        │
│                  /api/v1/agent/ws                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   LangGraphAssistant                         │
│               Graph-based ReAct Agent                        │
│         Agent Node ←→ Tools Node (conditional loop)         │
└─────────────────────────────────────────────────────────────┘
```

### ReAct Pattern

The agent follows the Reasoning + Acting pattern:

1. **Reason** - Analyze the input and decide on action
2. **Act** - Execute tools if needed
3. **Observe** - Process tool results
4. **Repeat** - Continue until task is complete

### Configuration

```python
# app/agents/langgraph_assistant.py
from langgraph.graph import StateGraph, MessagesState

class LangGraphAssistant:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model = ChatOpenAI(model=model_name)
        self.tools = [get_current_datetime]
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(MessagesState)
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", self._tools_node)
        graph.add_conditional_edges(
            "agent",
            self._should_continue,
            {"continue": "tools", "end": END}
        )
        graph.add_edge("tools", "agent")
        graph.set_entry_point("agent")
        return graph.compile(checkpointer=MemorySaver())
```

### Streaming Modes

LangGraph supports two streaming modes:

```python
# Token streaming (for LLM output)
async for event in assistant.stream(prompt, mode="messages"):
    if event["type"] == "token":
        print(event["content"], end="")

# State updates (for tool calls)
async for event in assistant.stream(prompt, mode="updates"):
    if event["type"] == "tool_call":
        print(f"Calling: {event['tool_name']}")
```

---

## Framework Comparison

| Feature | PydanticAI | LangChain | LangGraph | CrewAI |
|---------|------------|-----------|-----------|--------|
| Type Safety | ✅ Native | ⚠️ Manual | ⚠️ Manual | ⚠️ Manual |
| Multi-Agent | ❌ | ⚠️ Complex | ⚠️ Complex | ✅ Native |
| Tool Calling | ✅ | ✅ | ✅ | ✅ |
| Streaming | ✅ iter() | ✅ astream | ✅ astream | ✅ Events |
| Memory | ✅ Built-in | ✅ Chains | ✅ Checkpointer | ✅ Built-in |
| Complexity | Low | Medium | Medium | High |
| Dependencies | Few | Many | Medium | Many |

### When to Use Each

- **PydanticAI**: Simple assistants, chatbots, type-safe applications
- **LangChain**: Complex chains, many third-party integrations needed
- **LangGraph**: Multi-step reasoning, tool loops, state machines
- **CrewAI**: Agent teams, role-based collaboration, complex workflows
