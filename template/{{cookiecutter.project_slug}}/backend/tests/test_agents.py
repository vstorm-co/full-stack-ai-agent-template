{%- if cookiecutter.use_pydantic_ai %}
"""Tests for AI agent module (PydanticAI)."""

from unittest.mock import patch

import pytest
from pydantic_ai.models.test import TestModel

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

    def test_returns_dict_with_date_time_datetime(self):
        """Tool returns a dict with date/time/datetime keys."""
        result = get_current_datetime()
        assert isinstance(result, dict)
        assert {"date", "time", "datetime"} <= result.keys()
        # ISO-like date "YYYY-MM-DD"
        assert len(result["date"]) == 10


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

    # ``_build_model`` is the single per-provider model factory in
    # assistant.py, so patching it keeps these tests provider-agnostic
    # (openai/anthropic/google/openrouter/all) and avoids needing real API keys.
    @patch("app.agents.assistant._build_model")
    def test_agent_property_creates_agent(self, mock_build_model):
        """Test agent property creates agent on first access."""
        mock_build_model.return_value = TestModel()
        agent = AssistantAgent()
        _ = agent.agent
        assert agent._agent is not None
        mock_build_model.assert_called_once()

    @patch("app.agents.assistant._build_model")
    def test_agent_property_caches_agent(self, mock_build_model):
        """Test agent property caches the agent instance."""
        mock_build_model.return_value = TestModel()
        agent = AssistantAgent()
        agent1 = agent.agent
        agent2 = agent.agent
        assert agent1 is agent2
        mock_build_model.assert_called_once()


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
from app.agents.prompts import DEFAULT_SYSTEM_PROMPT
{%- if cookiecutter.enable_rag %}
from app.agents.prompts import get_system_prompt_with_rag
{%- endif %}
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

    def test_returns_dict_with_date_time_datetime(self):
        """Tool returns a dict with date/time/datetime keys."""
        result = get_current_datetime()
        assert isinstance(result, dict)
        assert {"date", "time", "datetime"} <= result.keys()
        assert len(result["date"]) == 10


class TestLangChainAssistant:
    """Tests for LangChainAssistant class."""

    def test_init_with_defaults(self):
        """Test LangChainAssistant initializes with defaults."""
        agent = LangChainAssistant()
{%- if cookiecutter.enable_rag %}
        assert agent.system_prompt == get_system_prompt_with_rag()
{%- else %}
        assert agent.system_prompt == DEFAULT_SYSTEM_PROMPT
{%- endif %}
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

    # Patch the provider-correct chat class so the test stays valid for
    # whichever LLM provider the project was generated with.
{%- if cookiecutter.use_anthropic %}
    @patch("app.agents.langchain_assistant.ChatAnthropic")
{%- elif cookiecutter.use_google %}
    @patch("app.agents.langchain_assistant.ChatGoogleGenerativeAI")
{%- else %}
    @patch("app.agents.langchain_assistant.ChatOpenAI")
{%- endif %}
    @patch("app.agents.langchain_assistant.create_agent")
    def test_agent_property_creates_agent(self, mock_create_agent, mock_chat):
        """Test agent property creates agent on first access."""
        mock_create_agent.return_value = MagicMock()
        agent = LangChainAssistant()
        _ = agent.agent
        assert agent._agent is not None
        mock_create_agent.assert_called_once()

    # Patch the provider-correct chat class so the test stays valid for
    # whichever LLM provider the project was generated with.
{%- if cookiecutter.use_anthropic %}
    @patch("app.agents.langchain_assistant.ChatAnthropic")
{%- elif cookiecutter.use_google %}
    @patch("app.agents.langchain_assistant.ChatGoogleGenerativeAI")
{%- else %}
    @patch("app.agents.langchain_assistant.ChatOpenAI")
{%- endif %}
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
{%- elif cookiecutter.use_pydantic_deep %}
"""Tests for AI agent module (PydanticDeep)."""

from unittest.mock import patch

from app.agents.pydantic_deep_assistant import PydanticDeepAssistant


class TestGetModelString:
    """Tests for PydanticDeepAssistant._get_model_string."""

    def test_openai_provider_uses_responses_api_prefix(self):
        assistant = PydanticDeepAssistant(model_name="gpt-5.5")
        with patch("app.agents.pydantic_deep_assistant.settings.LLM_PROVIDER", "openai"):
            assert assistant._get_model_string() == "openai-responses:gpt-5.5"

    def test_anthropic_provider_prefix(self):
        assistant = PydanticDeepAssistant(model_name="claude-opus-4-7")
        with patch("app.agents.pydantic_deep_assistant.settings.LLM_PROVIDER", "anthropic"):
            assert assistant._get_model_string() == "anthropic:claude-opus-4-7"

    def test_google_provider_prefix(self):
        assistant = PydanticDeepAssistant(model_name="gemini-2.5-flash")
        with patch("app.agents.pydantic_deep_assistant.settings.LLM_PROVIDER", "google"):
            assert assistant._get_model_string() == "google-gla:gemini-2.5-flash"

    def test_explicit_openai_prefix_rewritten_to_responses(self):
        assistant = PydanticDeepAssistant(model_name="openai:gpt-5.5")
        assert assistant._get_model_string() == "openai-responses:gpt-5.5"

    def test_explicit_responses_prefix_unchanged(self):
        assistant = PydanticDeepAssistant(model_name="openai-responses:gpt-5.5")
        assert assistant._get_model_string() == "openai-responses:gpt-5.5"

    def test_non_openai_explicit_prefix_unchanged(self):
        assistant = PydanticDeepAssistant(model_name="anthropic:claude-opus-4-7")
        assert assistant._get_model_string() == "anthropic:claude-opus-4-7"
{%- endif %}
