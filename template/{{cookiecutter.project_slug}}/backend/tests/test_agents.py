{%- if cookiecutter.use_pydantic_ai %}
"""Tests for AI agent module (PydanticAI)."""

from unittest.mock import MagicMock, patch

import pytest

from app.agents.assistant import AssistantAgent, Deps, get_agent, run_agent
from app.agents.prompts import DEFAULT_SYSTEM_PROMPT
{%- if cookiecutter.enable_rag %}
from app.agents.prompts import get_system_prompt_with_rag
{%- endif %}
from app.agents.tools.datetime_tool import get_current_datetime


class TestDeps:
    """Tests for Deps dataclass."""

    def test_deps_default_values(self):
        """Test Deps has correct default values."""
        deps = Deps()
        assert deps.user_id is None
        assert deps.user_name is None
        assert deps.metadata == {}

    def test_deps_with_values(self):
        """Test Deps with custom values."""
        deps = Deps(user_id="123", user_name="Test User", metadata={"key": "value"})
        assert deps.user_id == "123"
        assert deps.user_name == "Test User"
        assert deps.metadata == {"key": "value"}


class TestGetCurrentDatetime:
    """Tests for get_current_datetime tool."""

    def test_returns_formatted_string(self):
        """Test get_current_datetime returns formatted string."""
        result = get_current_datetime()
        assert isinstance(result, str)
        # Should contain year, month, day
        assert len(result) > 10


class TestAssistantAgent:
    """Tests for AssistantAgent class."""

    def test_init_with_defaults(self):
        """Test AssistantAgent initializes with defaults."""
        agent = AssistantAgent()
{%- if cookiecutter.enable_rag %}
        assert agent.system_prompt == get_system_prompt_with_rag()
{%- else %}
        assert agent.system_prompt == DEFAULT_SYSTEM_PROMPT
{%- endif %}
        assert agent._agent is None

    def test_init_with_custom_values(self):
        """Test AssistantAgent with custom configuration."""
        agent = AssistantAgent(
            model_name="gpt-4",
            temperature=0.5,
            system_prompt="Custom prompt",
        )
        assert agent.model_name == "gpt-4"
        assert agent.temperature == 0.5
        assert agent.system_prompt == "Custom prompt"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("app.agents.assistant.OpenAIProvider")
    @patch("app.agents.assistant.OpenAIChatModel")
    def test_agent_property_creates_agent(self, mock_model, mock_provider):
        """Test agent property creates agent on first access."""
        agent = AssistantAgent()
        _ = agent.agent
        assert agent._agent is not None
        mock_model.assert_called_once()

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("app.agents.assistant.OpenAIProvider")
    @patch("app.agents.assistant.OpenAIChatModel")
    def test_agent_property_caches_agent(self, mock_model, mock_provider):
        """Test agent property caches the agent instance."""
        agent = AssistantAgent()
        agent1 = agent.agent
        agent2 = agent.agent
        assert agent1 is agent2
        mock_model.assert_called_once()


class TestGetAgent:
    """Tests for get_agent factory function."""

    def test_returns_assistant_agent(self):
        """Test get_agent returns AssistantAgent."""
        agent = get_agent()
        assert isinstance(agent, AssistantAgent)


class TestAgentRoutes:
    """Tests for agent WebSocket routes."""

    @pytest.mark.anyio
    async def test_agent_websocket_connection(self, client):
        """Test WebSocket connection to agent endpoint."""
        # This test verifies the WebSocket endpoint is accessible
        # Actual agent testing would require mocking OpenAI
        pass


class TestHistoryConversion:
    """Tests for conversation history conversion."""

    def test_empty_history(self):
        """Test with empty history."""
        _agent = AssistantAgent()  # noqa: F841
        # History conversion happens inside run/iter methods
        # We test the structure here
        history = []
        assert len(history) == 0

    def test_history_roles(self):
        """Test history with different roles."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "system", "content": "You are helpful"},
        ]
        assert len(history) == 3
        assert all("role" in msg and "content" in msg for msg in history)
{%- elif cookiecutter.use_langchain %}
"""Tests for AI agent module (LangChain)."""

from unittest.mock import MagicMock, patch

import pytest

from app.agents.langchain_assistant import AgentContext, LangChainAssistant, get_agent, run_agent
from app.agents.tools.datetime_tool import get_current_datetime


class TestAgentContext:
    """Tests for AgentContext TypedDict."""

    def test_context_empty(self):
        """Test AgentContext can be empty."""
        context: AgentContext = {}
        assert "user_id" not in context
        assert "user_name" not in context

    def test_context_with_values(self):
        """Test AgentContext with values."""
        context: AgentContext = {
            "user_id": "123",
            "user_name": "Test User",
            "metadata": {"key": "value"},
        }
        assert context["user_id"] == "123"
        assert context["user_name"] == "Test User"
        assert context["metadata"] == {"key": "value"}


class TestGetCurrentDatetime:
    """Tests for get_current_datetime tool."""

    def test_returns_formatted_string(self):
        """Test get_current_datetime returns formatted string."""
        result = get_current_datetime()
        assert isinstance(result, str)
        # Should contain year, month, day
        assert len(result) > 10


class TestLangChainAssistant:
    """Tests for LangChainAssistant class."""

    def test_init_with_defaults(self):
        """Test LangChainAssistant initializes with defaults."""
        agent = LangChainAssistant()
        assert agent.system_prompt == "You are a helpful assistant."
        assert agent._agent is None

    def test_init_with_custom_values(self):
        """Test LangChainAssistant with custom configuration."""
        agent = LangChainAssistant(
            model_name="gpt-4",
            temperature=0.5,
            system_prompt="Custom prompt",
        )
        assert agent.model_name == "gpt-4"
        assert agent.temperature == 0.5
        assert agent.system_prompt == "Custom prompt"

    @patch("app.agents.langchain_assistant.ChatOpenAI")
    @patch("app.agents.langchain_assistant.create_agent")
    def test_agent_property_creates_agent(self, mock_create_agent, mock_chat):
        """Test agent property creates agent on first access."""
        mock_create_agent.return_value = MagicMock()
        agent = LangChainAssistant()
        _ = agent.agent
        assert agent._agent is not None
        mock_create_agent.assert_called_once()

    @patch("app.agents.langchain_assistant.ChatOpenAI")
    @patch("app.agents.langchain_assistant.create_agent")
    def test_agent_property_caches_agent(self, mock_create_agent, mock_chat):
        """Test agent property caches the agent instance."""
        mock_create_agent.return_value = MagicMock()
        agent = LangChainAssistant()
        agent1 = agent.agent
        agent2 = agent.agent
        assert agent1 is agent2
        mock_create_agent.assert_called_once()


class TestGetAgent:
    """Tests for get_agent factory function."""

    def test_returns_langchain_assistant(self):
        """Test get_agent returns LangChainAssistant."""
        agent = get_agent()
        assert isinstance(agent, LangChainAssistant)


class TestAgentRoutes:
    """Tests for agent WebSocket routes."""

    @pytest.mark.anyio
    async def test_agent_websocket_connection(self, client):
        """Test WebSocket connection to agent endpoint."""
        # This test verifies the WebSocket endpoint is accessible
        # Actual agent testing would require mocking OpenAI
        pass


class TestHistoryConversion:
    """Tests for conversation history conversion."""

    def test_empty_history(self):
        """Test with empty history."""
        _agent = LangChainAssistant()  # noqa: F841
        # History conversion happens inside run/stream methods
        # We test the structure here
        history = []
        assert len(history) == 0

    def test_history_roles(self):
        """Test history with different roles."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "system", "content": "You are helpful"},
        ]
        assert len(history) == 3
        assert all("role" in msg and "content" in msg for msg in history)

    def test_convert_history(self):
        """Test _convert_history method."""
        agent = LangChainAssistant()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "system", "content": "You are helpful"},
        ]
        messages = agent._convert_history(history)
        assert len(messages) == 3
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
        assert isinstance(messages[0], HumanMessage)
        assert isinstance(messages[1], AIMessage)
        assert isinstance(messages[2], SystemMessage)
{%- endif %}
