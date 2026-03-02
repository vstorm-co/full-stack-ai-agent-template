{%- if cookiecutter.enable_ai_agent and cookiecutter.use_pydantic_ai %}
"""Assistant agent with PydanticAI.

The main conversational agent that can be extended with custom tools.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
{%- if cookiecutter.use_openai %}
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
{%- endif %}
{%- if cookiecutter.use_anthropic %}
from pydantic_ai.models.anthropic import AnthropicModel
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
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Deps:
    """Dependencies for the assistant agent.

    These are passed to tools via RunContext.
    """

    user_id: str | None = None
    user_name: str | None = None
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
    ):
        self.model_name = model_name or settings.AI_MODEL
        self.temperature = temperature or settings.AI_TEMPERATURE
{%- if cookiecutter.enable_rag %}
        self.system_prompt = system_prompt or get_system_prompt_with_rag()
{%- else %}
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
{%- endif %}
        self._agent: Agent[Deps, str] | None = None

    def _create_agent(self) -> Agent[Deps, str]:
        """Create and configure the PydanticAI agent."""
{%- if cookiecutter.use_openai %}
        model = OpenAIChatModel(
            self.model_name,
            provider=OpenAIProvider(api_key=settings.OPENAI_API_KEY),
        )
{%- endif %}
{%- if cookiecutter.use_anthropic %}
        model = AnthropicModel(
            self.model_name,
            api_key=settings.ANTHROPIC_API_KEY,
        )
{%- endif %}
{%- if cookiecutter.use_openrouter %}
        model = OpenRouterModel(
            self.model_name,
            provider=OpenRouterProvider(api_key=settings.OPENROUTER_API_KEY),
        )
{%- endif %}

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
            """Get the current date and time.

            Use this tool when you need to know the current date or time.
            """
            return get_current_datetime()

{%- if cookiecutter.enable_rag %}
        @agent.tool
        async def search_documents(
            ctx: RunContext[Deps], query: str, collection: str = "default", top_k: int = 5
        ) -> str:
            """Search the knowledge base for relevant documents.

            Use this tool to find information from uploaded documents before answering user queries.
            Cite sources by referring to the document filename from the search results.

            Args:
                query: The search query string.
                collection: Name of the collection to search (default: "default").
                top_k: Number of top results to retrieve (default: 5).

            Returns:
                Formatted string with search results including content and scores.
            """
            return await search_knowledge_base(query=query, collection=collection, top_k=top_k)
{%- endif %}

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
        model_history: list[ModelRequest | ModelResponse] = []

        for msg in history or []:
            if msg["role"] == "user":
                model_history.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
            elif msg["role"] == "assistant":
                model_history.append(ModelResponse(parts=[TextPart(content=msg["content"])]))
            elif msg["role"] == "system":
                model_history.append(ModelRequest(parts=[SystemPromptPart(content=msg["content"])]))

        agent_deps = deps if deps is not None else Deps()

        logger.info(f"Running agent with user input: {user_input[:100]}...")
        result = await self.agent.run(user_input, deps=agent_deps, message_history=model_history)

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
    ):
        """Stream agent execution with full event access.

        Args:
            user_input: User's message.
            history: Conversation history.
            deps: Optional dependencies.

        Yields:
            Agent events for streaming responses.
        """
        model_history: list[ModelRequest | ModelResponse] = []

        for msg in history or []:
            if msg["role"] == "user":
                model_history.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
            elif msg["role"] == "assistant":
                model_history.append(ModelResponse(parts=[TextPart(content=msg["content"])]))
            elif msg["role"] == "system":
                model_history.append(ModelRequest(parts=[SystemPromptPart(content=msg["content"])]))

        agent_deps = deps if deps is not None else Deps()

        async with self.agent.iter(
            user_input,
            deps=agent_deps,
            message_history=model_history,
        ) as run:
            async for event in run:
                yield event


def get_agent() -> AssistantAgent:
    """Factory function to create an AssistantAgent.

    Returns:
        Configured AssistantAgent instance.
    """
    return AssistantAgent()


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
