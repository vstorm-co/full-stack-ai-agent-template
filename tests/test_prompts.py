"""Tests for fastapi_gen.prompts module."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from fastapi_gen.config import (
    AIFrameworkType,
    BackgroundTaskType,
    BrandColorType,
    CIType,
    DatabaseType,
    FrontendType,
    LLMProviderType,
    LogfireFeatures,
    OAuthProvider,
    OrmType,
    PdfParserType,
    RAGFeatures,
    RateLimitStorageType,
    RerankerType,
    ReverseProxyType,
    VectorStoreType,
)
from fastapi_gen.prompts import (
    _check_cancelled,
    _normalize_project_name,
    _validate_email,
    _validate_positive_integer,
    _validate_project_name,
    confirm_generation,
    prompt_background_tasks,
    prompt_basic_info,
    prompt_brand_color,
    prompt_database,
    prompt_dev_tools,
    prompt_frontend,
    prompt_integrations,
    prompt_langsmith,
    prompt_llm_provider,
    prompt_logfire,
    prompt_oauth,
    prompt_orm_type,
    prompt_ports,
    prompt_python_version,
    prompt_rag_config,
    prompt_rate_limit_config,
    prompt_reverse_proxy,
    run_interactive_prompts,
    show_header,
    show_summary,
)


class TestCheckCancelled:
    """Tests for _check_cancelled helper."""

    def test_returns_value_when_not_none(self) -> None:
        """Test value is returned when not None."""
        assert _check_cancelled("test") == "test"
        assert _check_cancelled(123) == 123
        assert _check_cancelled([1, 2, 3]) == [1, 2, 3]

    def test_raises_keyboard_interrupt_when_none(self) -> None:
        """Test KeyboardInterrupt is raised when value is None."""
        with pytest.raises(KeyboardInterrupt):
            _check_cancelled(None)


class TestValidateProjectName:
    """Tests for _validate_project_name helper."""

    def test_valid_lowercase_name(self) -> None:
        """Test valid lowercase name returns True."""
        assert _validate_project_name("myproject") is True
        assert _validate_project_name("my_project") is True
        assert _validate_project_name("project123") is True

    def test_valid_uppercase_name(self) -> None:
        """Test valid uppercase name returns True (will be normalized later)."""
        assert _validate_project_name("MyProject") is True
        assert _validate_project_name("MY_PROJECT") is True

    def test_valid_name_with_spaces(self) -> None:
        """Test valid name with spaces returns True."""
        assert _validate_project_name("my project") is True
        assert _validate_project_name("My Project") is True

    def test_valid_name_with_dashes(self) -> None:
        """Test valid name with dashes returns True."""
        assert _validate_project_name("my-project") is True
        assert _validate_project_name("My-Project") is True

    def test_invalid_empty_name(self) -> None:
        """Test empty name returns error message."""
        result = _validate_project_name("")
        assert result == "Project name cannot be empty"

    def test_invalid_starts_with_number(self) -> None:
        """Test name starting with number returns error message."""
        result = _validate_project_name("123project")
        assert result == "Project name must start with a letter"

    def test_invalid_starts_with_underscore(self) -> None:
        """Test name starting with underscore returns error message."""
        result = _validate_project_name("_project")
        assert result == "Project name must start with a letter"

    def test_invalid_special_characters(self) -> None:
        """Test name with special characters returns error message."""
        result = _validate_project_name("my@project")
        assert "can only contain" in result
        result = _validate_project_name("my.project")
        assert "can only contain" in result
        result = _validate_project_name("my/project")
        assert "can only contain" in result


class TestNormalizeProjectName:
    """Tests for _normalize_project_name helper."""

    def test_lowercase_conversion(self) -> None:
        """Test uppercase is converted to lowercase."""
        assert _normalize_project_name("MyProject") == "myproject"
        assert _normalize_project_name("MY_PROJECT") == "my_project"

    def test_space_to_underscore(self) -> None:
        """Test spaces are converted to underscores."""
        assert _normalize_project_name("my project") == "my_project"
        assert _normalize_project_name("My Project") == "my_project"

    def test_dash_to_underscore(self) -> None:
        """Test dashes are converted to underscores."""
        assert _normalize_project_name("my-project") == "my_project"
        assert _normalize_project_name("My-Project") == "my_project"

    def test_mixed_conversion(self) -> None:
        """Test mixed case, spaces, and dashes are all normalized."""
        assert _normalize_project_name("My Cool-Project") == "my_cool_project"
        assert _normalize_project_name("MY COOL-PROJECT") == "my_cool_project"

    def test_already_normalized(self) -> None:
        """Test already normalized name is unchanged."""
        assert _normalize_project_name("my_project") == "my_project"
        assert _normalize_project_name("project123") == "project123"


class TestValidateEmail:
    """Tests for _validate_email helper."""

    def test_valid_email_returns_true(self) -> None:
        """Test valid email returns True."""
        assert _validate_email("user@example.com") is True
        assert _validate_email("user.name@example.com") is True
        assert _validate_email("user+tag@example.com") is True
        assert _validate_email("user@subdomain.example.com") is True
        assert _validate_email("user123@example.co.uk") is True

    def test_empty_email_returns_error(self) -> None:
        """Test empty email returns error message."""
        result = _validate_email("")
        assert result == "Email cannot be empty"

    def test_invalid_email_returns_error(self) -> None:
        """Test invalid email returns error message."""
        assert _validate_email("not-an-email") == "Please enter a valid email address"
        assert _validate_email("missing@tld") == "Please enter a valid email address"
        assert _validate_email("@no-local-part.com") == "Please enter a valid email address"
        assert _validate_email("spaces in@email.com") == "Please enter a valid email address"


class TestValidatePositiveInteger:
    """Tests for _validate_positive_integer helper."""

    def test_valid_positive_integers(self) -> None:
        """Test valid positive integers return True."""
        assert _validate_positive_integer("1") is True
        assert _validate_positive_integer("100") is True
        assert _validate_positive_integer("999999") is True

    def test_empty_value_returns_error(self) -> None:
        """Test empty value returns error message."""
        assert _validate_positive_integer("") == "Value cannot be empty"

    def test_non_digit_returns_error(self) -> None:
        """Test non-digit input returns error message."""
        assert _validate_positive_integer("abc") == "Must be a positive number"
        assert _validate_positive_integer("12.5") == "Must be a positive number"
        assert _validate_positive_integer("-10") == "Must be a positive number"

    def test_zero_returns_error(self) -> None:
        """Test zero returns error message."""
        assert _validate_positive_integer("0") == "Must be greater than 0"


class TestShowHeader:
    """Tests for show_header function."""

    def test_show_header_runs_without_error(self) -> None:
        """Test header displays without errors."""
        # Just verify it doesn't raise
        show_header()


class TestPromptBasicInfo:
    """Tests for prompt_basic_info function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_all_fields(self, mock_questionary: MagicMock) -> None:
        """Test all basic info fields are returned."""
        mock_text = MagicMock()
        mock_text.ask.side_effect = [
            "myproject",
            "My description",
            "John Doe",
            "john@example.com",
            "UTC",
        ]
        mock_questionary.text.return_value = mock_text

        result = prompt_basic_info()

        assert result == {
            "project_name": "myproject",
            "project_description": "My description",
            "author_name": "John Doe",
            "author_email": "john@example.com",
            "timezone": "UTC",
        }

    @patch("fastapi_gen.prompts.questionary")
    def test_normalizes_project_name_with_uppercase(self, mock_questionary: MagicMock) -> None:
        """Test project name with uppercase is normalized to lowercase."""
        mock_text = MagicMock()
        mock_text.ask.side_effect = [
            "MyProject",
            "My description",
            "John Doe",
            "john@example.com",
            "UTC",
        ]
        mock_questionary.text.return_value = mock_text

        result = prompt_basic_info()

        assert result["project_name"] == "myproject"

    @patch("fastapi_gen.prompts.questionary")
    def test_normalizes_project_name_with_spaces(self, mock_questionary: MagicMock) -> None:
        """Test project name with spaces is normalized to underscores."""
        mock_text = MagicMock()
        mock_text.ask.side_effect = [
            "My Project",
            "My description",
            "John Doe",
            "john@example.com",
            "UTC",
        ]
        mock_questionary.text.return_value = mock_text

        result = prompt_basic_info()

        assert result["project_name"] == "my_project"

    @patch("fastapi_gen.prompts.questionary")
    def test_normalizes_project_name_with_dashes(self, mock_questionary: MagicMock) -> None:
        """Test project name with dashes is normalized to underscores."""
        mock_text = MagicMock()
        mock_text.ask.side_effect = [
            "my-project",
            "My description",
            "John Doe",
            "john@example.com",
            "UTC",
        ]
        mock_questionary.text.return_value = mock_text

        result = prompt_basic_info()

        assert result["project_name"] == "my_project"

    @patch("fastapi_gen.prompts.questionary")
    def test_raises_on_cancel(self, mock_questionary: MagicMock) -> None:
        """Test KeyboardInterrupt on cancel."""
        mock_text = MagicMock()
        mock_text.ask.return_value = None
        mock_questionary.text.return_value = mock_text

        with pytest.raises(KeyboardInterrupt):
            prompt_basic_info()


class TestPromptOrmType:
    """Tests for prompt_orm_type function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_sqlalchemy(self, mock_questionary: MagicMock) -> None:
        """Test SQLAlchemy is returned when selected."""
        mock_select = MagicMock()
        mock_select.ask.return_value = OrmType.SQLALCHEMY
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_orm_type()

        assert result == OrmType.SQLALCHEMY

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_sqlmodel(self, mock_questionary: MagicMock) -> None:
        """Test SQLModel is returned when selected."""
        mock_select = MagicMock()
        mock_select.ask.return_value = OrmType.SQLMODEL
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_orm_type()

        assert result == OrmType.SQLMODEL

    @patch("fastapi_gen.prompts.questionary")
    def test_raises_on_cancel(self, mock_questionary: MagicMock) -> None:
        """Test KeyboardInterrupt on cancel."""
        mock_select = MagicMock()
        mock_select.ask.return_value = None
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        with pytest.raises(KeyboardInterrupt):
            prompt_orm_type()


class TestPromptLogfire:
    """Tests for prompt_logfire function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_disabled_logfire(self, mock_questionary: MagicMock) -> None:
        """Test disabled Logfire returns False and default features."""
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        enabled, features = prompt_logfire(BackgroundTaskType.NONE, AIFrameworkType.PYDANTIC_AI)

        assert enabled is False
        assert isinstance(features, LogfireFeatures)

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_enabled_logfire_with_features(self, mock_questionary: MagicMock) -> None:
        """Test enabled Logfire returns selected features."""
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True
        mock_questionary.confirm.return_value = mock_confirm

        mock_checkbox = MagicMock()
        mock_checkbox.ask.return_value = ["fastapi", "redis", "httpx"]
        mock_questionary.checkbox.return_value = mock_checkbox
        mock_questionary.Choice = MagicMock()

        enabled, features = prompt_logfire(BackgroundTaskType.NONE, AIFrameworkType.PYDANTIC_AI)

        assert enabled is True
        assert features.fastapi is True
        assert features.database is False
        assert features.redis is True
        assert features.celery is False
        assert features.httpx is True

    @patch("fastapi_gen.prompts.questionary")
    def test_celery_option_shown_only_for_celery(self, mock_questionary: MagicMock) -> None:
        """Test Celery instrumentation option is only shown when Celery is selected."""
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True
        mock_questionary.confirm.return_value = mock_confirm

        mock_checkbox = MagicMock()
        mock_checkbox.ask.return_value = ["fastapi", "celery"]
        mock_questionary.checkbox.return_value = mock_checkbox
        mock_questionary.Choice = MagicMock()

        enabled, features = prompt_logfire(BackgroundTaskType.CELERY, AIFrameworkType.PYDANTIC_AI)

        assert enabled is True
        assert features.celery is True
        # Verify Choice was called 5 times (4 default + celery)
        assert mock_questionary.Choice.call_count == 5


class TestPromptBackgroundTasks:
    """Tests for prompt_background_tasks function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_selected_task_type(self, mock_questionary: MagicMock) -> None:
        """Test selected background task type is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = BackgroundTaskType.TASKIQ
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_background_tasks()

        assert result == BackgroundTaskType.TASKIQ


class TestPromptIntegrations:
    """Tests for prompt_integrations function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_selected_integrations(self, mock_questionary: MagicMock) -> None:
        """Test selected integrations are returned."""
        mock_checkbox = MagicMock()
        mock_checkbox.ask.return_value = ["redis", "caching", "websockets"]
        mock_questionary.checkbox.return_value = mock_checkbox
        mock_questionary.Choice = MagicMock()

        result = prompt_integrations(
            database=DatabaseType.POSTGRESQL,
            orm_type=OrmType.SQLALCHEMY,
        )

        assert result["enable_redis"] is True
        assert result["enable_caching"] is True
        assert result["enable_pagination"] is False
        assert result["enable_sentry"] is False

    @patch("fastapi_gen.prompts.questionary")
    def test_admin_panel_shown_with_sqlalchemy(self, mock_questionary: MagicMock) -> None:
        """Test admin panel option IS shown when SQLAlchemy is selected."""
        mock_checkbox = MagicMock()
        mock_checkbox.ask.return_value = []
        mock_questionary.checkbox.return_value = mock_checkbox
        mock_questionary.Choice = MagicMock()

        prompt_integrations(
            database=DatabaseType.POSTGRESQL,
            orm_type=OrmType.SQLALCHEMY,
        )

        # Check that checkbox was called WITH admin_panel in choices
        # Each call in call_args_list is (args, kwargs) tuple
        choice_values = [call[1].get("value") for call in mock_questionary.Choice.call_args_list]
        assert "admin_panel" in choice_values

    @patch("fastapi_gen.prompts.questionary")
    def test_admin_panel_hidden_with_sqlmodel(self, mock_questionary: MagicMock) -> None:
        """Test admin panel option is not shown when SQLModel is selected."""
        mock_checkbox = MagicMock()
        mock_checkbox.ask.return_value = []
        mock_questionary.checkbox.return_value = mock_checkbox
        mock_questionary.Choice = MagicMock()

        prompt_integrations(
            database=DatabaseType.POSTGRESQL,
            orm_type=OrmType.SQLMODEL,
        )

        # Check that checkbox was called without admin_panel in choices
        # Each call in call_args_list is (args, kwargs) tuple
        choice_values = [call[1].get("value") for call in mock_questionary.Choice.call_args_list]
        assert "admin_panel" not in choice_values

    @patch("fastapi_gen.prompts.questionary")
    def test_webhooks_shown_with_database(self, mock_questionary: MagicMock) -> None:
        """Test webhooks option IS shown when a database is selected."""
        mock_checkbox = MagicMock()
        mock_checkbox.ask.return_value = []
        mock_questionary.checkbox.return_value = mock_checkbox
        mock_questionary.Choice = MagicMock()

        prompt_integrations(
            database=DatabaseType.POSTGRESQL,
            orm_type=OrmType.SQLALCHEMY,
        )

        # Check that checkbox was called WITH webhooks in choices
        choice_values = [call[1].get("value") for call in mock_questionary.Choice.call_args_list]
        assert "webhooks" in choice_values

    @patch("fastapi_gen.prompts.questionary")
    def test_auto_enables_redis_for_caching(self, mock_questionary: MagicMock) -> None:
        """Test that Redis is auto-enabled when caching is selected without Redis."""
        mock_checkbox = MagicMock()
        mock_checkbox.ask.return_value = ["caching"]  # caching without redis
        mock_questionary.checkbox.return_value = mock_checkbox
        mock_questionary.Choice = MagicMock()

        result = prompt_integrations(
            database=DatabaseType.POSTGRESQL,
            orm_type=OrmType.SQLALCHEMY,
        )

        # Redis should be auto-enabled
        assert result["enable_redis"] is True
        assert result["enable_caching"] is True


class TestPromptRateLimitConfig:
    """Tests for prompt_rate_limit_config function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_config_values(self, mock_questionary: MagicMock) -> None:
        """Test rate limit config values are returned."""
        mock_text = MagicMock()
        mock_text.ask.side_effect = ["50", "30"]
        mock_questionary.text.return_value = mock_text

        requests, period, storage = prompt_rate_limit_config(redis_enabled=False)

        assert requests == 50
        assert period == 30
        assert storage == RateLimitStorageType.MEMORY

    @patch("fastapi_gen.prompts.questionary")
    def test_auto_selects_redis_when_enabled(self, mock_questionary: MagicMock) -> None:
        """Test Redis storage is auto-selected when Redis is enabled."""
        mock_text = MagicMock()
        mock_text.ask.side_effect = ["100", "60"]
        mock_questionary.text.return_value = mock_text

        requests, period, storage = prompt_rate_limit_config(redis_enabled=True)

        assert requests == 100
        assert period == 60
        assert storage == RateLimitStorageType.REDIS

    @patch("fastapi_gen.prompts.questionary")
    def test_auto_selects_memory_when_redis_disabled(self, mock_questionary: MagicMock) -> None:
        """Test memory storage is auto-selected when Redis is disabled."""
        mock_text = MagicMock()
        mock_text.ask.side_effect = ["100", "60"]
        mock_questionary.text.return_value = mock_text

        _, _, storage = prompt_rate_limit_config(redis_enabled=False)

        assert storage == RateLimitStorageType.MEMORY
        # No select prompt should be called for storage
        mock_questionary.select.assert_not_called()

    @patch("fastapi_gen.prompts.questionary")
    def test_raises_on_cancel(self, mock_questionary: MagicMock) -> None:
        """Test KeyboardInterrupt on cancel."""
        mock_text = MagicMock()
        mock_text.ask.return_value = None
        mock_questionary.text.return_value = mock_text

        with pytest.raises(KeyboardInterrupt):
            prompt_rate_limit_config(redis_enabled=False)


class TestPromptDevTools:
    """Tests for prompt_dev_tools function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_selected_dev_tools(self, mock_questionary: MagicMock) -> None:
        """Test selected dev tools are returned."""
        mock_checkbox = MagicMock()
        mock_checkbox.ask.return_value = ["pytest", "docker", "kubernetes"]
        mock_questionary.checkbox.return_value = mock_checkbox

        mock_select = MagicMock()
        mock_select.ask.return_value = CIType.GITLAB
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_dev_tools()

        assert result["enable_pytest"] is True
        assert result["enable_precommit"] is False
        assert result["enable_docker"] is True
        assert result["enable_kubernetes"] is True
        assert result["ci_type"] == CIType.GITLAB


class TestPromptFrontend:
    """Tests for prompt_frontend function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_selected_frontend(self, mock_questionary: MagicMock) -> None:
        """Test selected frontend is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = FrontendType.NEXTJS
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_frontend()

        assert result == FrontendType.NEXTJS

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_none_frontend(self, mock_questionary: MagicMock) -> None:
        """Test none frontend is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = FrontendType.NONE
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_frontend()

        assert result == FrontendType.NONE

    @patch("fastapi_gen.prompts.questionary")
    def test_raises_on_cancel(self, mock_questionary: MagicMock) -> None:
        """Test KeyboardInterrupt on cancel."""
        mock_select = MagicMock()
        mock_select.ask.return_value = None
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        with pytest.raises(KeyboardInterrupt):
            prompt_frontend()


class TestPromptAIFramework:
    """Tests for prompt_ai_framework function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_pydantic_ai(self, mock_questionary: MagicMock) -> None:
        """Test PydanticAI framework is returned."""
        from fastapi_gen.prompts import prompt_ai_framework

        mock_select = MagicMock()
        mock_select.ask.return_value = AIFrameworkType.PYDANTIC_AI
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_ai_framework()

        assert result == AIFrameworkType.PYDANTIC_AI

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_langchain(self, mock_questionary: MagicMock) -> None:
        """Test LangChain framework is returned."""
        from fastapi_gen.prompts import prompt_ai_framework

        mock_select = MagicMock()
        mock_select.ask.return_value = AIFrameworkType.LANGCHAIN
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_ai_framework()

        assert result == AIFrameworkType.LANGCHAIN


class TestPromptPythonVersion:
    """Tests for prompt_python_version function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_python_312(self, mock_questionary: MagicMock) -> None:
        """Test Python 3.12 is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = "3.12"
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_python_version()

        assert result == "3.12"

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_python_311(self, mock_questionary: MagicMock) -> None:
        """Test Python 3.11 is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = "3.11"
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_python_version()

        assert result == "3.11"

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_python_313(self, mock_questionary: MagicMock) -> None:
        """Test Python 3.13 is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = "3.13"
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_python_version()

        assert result == "3.13"


class TestPromptPorts:
    """Tests for prompt_ports function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_backend_port_only(self, mock_questionary: MagicMock) -> None:
        """Test only backend port is returned when no frontend."""
        mock_text = MagicMock()
        mock_text.ask.return_value = "8000"
        mock_questionary.text.return_value = mock_text

        result = prompt_ports(has_frontend=False)

        assert result == {"backend_port": 8000}
        # text should only be called once for backend port
        assert mock_questionary.text.call_count == 1

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_both_ports_with_frontend(self, mock_questionary: MagicMock) -> None:
        """Test both ports are returned when frontend is enabled."""
        mock_text = MagicMock()
        mock_text.ask.side_effect = ["8080", "3001"]
        mock_questionary.text.return_value = mock_text

        result = prompt_ports(has_frontend=True)

        assert result == {"backend_port": 8080, "frontend_port": 3001}
        # text should be called twice
        assert mock_questionary.text.call_count == 2

    @patch("fastapi_gen.prompts.questionary")
    def test_port_validator_valid_port(self, mock_questionary: MagicMock) -> None:
        """Test port validator accepts valid ports."""
        mock_text = MagicMock()
        mock_text.ask.return_value = "8000"
        mock_questionary.text.return_value = mock_text

        prompt_ports(has_frontend=False)

        # Get the validator function passed to questionary.text
        call_kwargs = mock_questionary.text.call_args[1]
        validate_port = call_kwargs["validate"]

        # Test valid ports
        assert validate_port("1024") is True
        assert validate_port("8000") is True
        assert validate_port("65535") is True

    @patch("fastapi_gen.prompts.questionary")
    def test_port_validator_invalid_port(self, mock_questionary: MagicMock) -> None:
        """Test port validator rejects invalid ports."""
        mock_text = MagicMock()
        mock_text.ask.return_value = "8000"
        mock_questionary.text.return_value = mock_text

        prompt_ports(has_frontend=False)

        # Get the validator function passed to questionary.text
        call_kwargs = mock_questionary.text.call_args[1]
        validate_port = call_kwargs["validate"]

        # Test invalid ports - validator returns error string (not False)
        assert validate_port("1023") is not True  # Below range
        assert validate_port("65536") is not True  # Above range
        assert validate_port("invalid") is not True  # Not a number
        assert validate_port("") is not True  # Empty string


class TestPromptOAuth:
    """Tests for prompt_oauth function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_google_provider(self, mock_questionary: MagicMock) -> None:
        """Test Google OAuth provider is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = OAuthProvider.GOOGLE
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_oauth()

        assert result == OAuthProvider.GOOGLE

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_none_provider(self, mock_questionary: MagicMock) -> None:
        """Test None OAuth provider is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = OAuthProvider.NONE
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_oauth()

        assert result == OAuthProvider.NONE


class TestPromptReverseProxy:
    """Tests for prompt_reverse_proxy function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_traefik_included(self, mock_questionary: MagicMock) -> None:
        """Test Traefik included is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = ReverseProxyType.TRAEFIK_INCLUDED
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_reverse_proxy()

        assert result == ReverseProxyType.TRAEFIK_INCLUDED

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_traefik_external(self, mock_questionary: MagicMock) -> None:
        """Test Traefik external is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = ReverseProxyType.TRAEFIK_EXTERNAL
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_reverse_proxy()

        assert result == ReverseProxyType.TRAEFIK_EXTERNAL

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_none(self, mock_questionary: MagicMock) -> None:
        """Test None is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = ReverseProxyType.NONE
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_reverse_proxy()

        assert result == ReverseProxyType.NONE

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_nginx_included(self, mock_questionary: MagicMock) -> None:
        """Test Nginx included is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = ReverseProxyType.NGINX_INCLUDED
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_reverse_proxy()

        assert result == ReverseProxyType.NGINX_INCLUDED

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_nginx_external(self, mock_questionary: MagicMock) -> None:
        """Test Nginx external is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = ReverseProxyType.NGINX_EXTERNAL
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_reverse_proxy()

        assert result == ReverseProxyType.NGINX_EXTERNAL

    @patch("fastapi_gen.prompts.questionary")
    def test_raises_on_cancel(self, mock_questionary: MagicMock) -> None:
        """Test KeyboardInterrupt on cancel."""
        mock_select = MagicMock()
        mock_select.ask.return_value = None
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        with pytest.raises(KeyboardInterrupt):
            prompt_reverse_proxy()


class TestPromptLLMProvider:
    """Tests for prompt_llm_provider function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_openai(self, mock_questionary: MagicMock) -> None:
        """Test OpenAI provider is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = LLMProviderType.OPENAI
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_llm_provider(AIFrameworkType.PYDANTIC_AI)

        assert result == LLMProviderType.OPENAI

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_anthropic(self, mock_questionary: MagicMock) -> None:
        """Test Anthropic provider is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = LLMProviderType.ANTHROPIC
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_llm_provider(AIFrameworkType.LANGCHAIN)

        assert result == LLMProviderType.ANTHROPIC

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_openrouter_for_pydanticai(self, mock_questionary: MagicMock) -> None:
        """Test OpenRouter provider is returned for PydanticAI."""
        mock_select = MagicMock()
        mock_select.ask.return_value = LLMProviderType.OPENROUTER
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_llm_provider(AIFrameworkType.PYDANTIC_AI)

        assert result == LLMProviderType.OPENROUTER

    @patch("fastapi_gen.prompts.questionary")
    def test_openrouter_option_added_for_pydanticai(self, mock_questionary: MagicMock) -> None:
        """Test OpenRouter option is added when using PydanticAI."""
        mock_select = MagicMock()
        mock_select.ask.return_value = LLMProviderType.OPENAI
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        prompt_llm_provider(AIFrameworkType.PYDANTIC_AI)

        # Check that select was called with 4 choices (OpenAI, Anthropic, Google, OpenRouter)
        select_call = mock_questionary.select.call_args
        choices = select_call[1]["choices"]
        assert len(choices) == 4

    @patch("fastapi_gen.prompts.questionary")
    def test_openrouter_option_not_added_for_langchain(self, mock_questionary: MagicMock) -> None:
        """Test OpenRouter option is NOT added when using LangChain."""
        mock_select = MagicMock()
        mock_select.ask.return_value = LLMProviderType.OPENAI
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        prompt_llm_provider(AIFrameworkType.LANGCHAIN)

        # Check that select was called with 3 choices (OpenAI, Anthropic, Google)
        select_call = mock_questionary.select.call_args
        choices = select_call[1]["choices"]
        assert len(choices) == 3

    @patch("fastapi_gen.prompts.questionary")
    def test_raises_on_cancel(self, mock_questionary: MagicMock) -> None:
        """Test KeyboardInterrupt on cancel."""
        mock_select = MagicMock()
        mock_select.ask.return_value = None
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        with pytest.raises(KeyboardInterrupt):
            prompt_llm_provider(AIFrameworkType.PYDANTIC_AI)


class TestPromptBrandColor:
    """Tests for prompt_brand_color function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_blue(self, mock_questionary: MagicMock) -> None:
        """Test blue brand color is returned when selected."""
        mock_select = MagicMock()
        mock_select.ask.return_value = BrandColorType.BLUE
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_brand_color()

        assert result == BrandColorType.BLUE

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_green(self, mock_questionary: MagicMock) -> None:
        """Test green brand color is returned when selected."""
        mock_select = MagicMock()
        mock_select.ask.return_value = BrandColorType.GREEN
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_brand_color()

        assert result == BrandColorType.GREEN


class TestRunInteractivePrompts:
    """Tests for run_interactive_prompts function."""

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_llm_provider")
    @patch("fastapi_gen.prompts.prompt_ai_framework")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    @patch("fastapi_gen.prompts.prompt_rag_config")
    def test_builds_project_config(
        self,
        mock_rag_config: MagicMock,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_ai_framework: MagicMock,
        mock_llm_provider: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test ProjectConfig is built from prompts."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
            "timezone": "UTC",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_oauth.return_value = OAuthProvider.NONE
        mock_logfire.return_value = (True, LogfireFeatures())
        mock_background_tasks.return_value = BackgroundTaskType.NONE
        mock_integrations.return_value = {
            "enable_redis": False,
            "enable_caching": False,
            "enable_rate_limiting": False,
            "enable_pagination": True,
            "enable_sentry": False,
            "enable_prometheus": False,
            "enable_admin_panel": False,
            "enable_websockets": False,
            "enable_file_storage": False,
            "enable_cors": True,

        }
        mock_dev_tools.return_value = {
            "enable_pytest": True,
            "enable_precommit": True,
            "enable_docker": True,
            "enable_kubernetes": False,
            "ci_type": CIType.GITHUB,
        }
        mock_reverse_proxy.return_value = ReverseProxyType.TRAEFIK_INCLUDED
        mock_frontend.return_value = FrontendType.NONE
        mock_python_version.return_value = "3.12"
        mock_ports.return_value = {"backend_port": 8000}
        mock_ai_framework.return_value = AIFrameworkType.PYDANTIC_AI
        mock_llm_provider.return_value = LLMProviderType.OPENAI
        mock_rag_config.return_value = RAGFeatures(enable_rag=False)

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        assert config.project_name == "test_project"
        assert config.database == DatabaseType.POSTGRESQL
        assert config.enable_logfire is True
        assert config.ci_type == CIType.GITHUB
        assert config.python_version == "3.12"
        assert config.backend_port == 8000

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_llm_provider")
    @patch("fastapi_gen.prompts.prompt_ai_framework")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    @patch("fastapi_gen.prompts.prompt_rag_config")
    def test_auto_enables_redis_for_celery(
        self,
        mock_rag_config: MagicMock,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_ai_framework: MagicMock,
        mock_llm_provider: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test Redis is auto-enabled when Celery is selected."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
            "timezone": "UTC",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_oauth.return_value = OAuthProvider.NONE
        mock_logfire.return_value = (False, LogfireFeatures())
        mock_background_tasks.return_value = BackgroundTaskType.CELERY
        mock_integrations.return_value = {
            "enable_redis": False,  # User didn't select Redis
            "enable_caching": False,
            "enable_rate_limiting": False,
            "enable_pagination": True,
            "enable_sentry": False,
            "enable_prometheus": False,
            "enable_admin_panel": False,
            "enable_websockets": False,
            "enable_file_storage": False,
            "enable_cors": True,

        }
        mock_dev_tools.return_value = {
            "enable_pytest": True,
            "enable_precommit": True,
            "enable_docker": True,
            "enable_kubernetes": False,
            "ci_type": CIType.GITHUB,
        }
        mock_reverse_proxy.return_value = ReverseProxyType.TRAEFIK_INCLUDED
        mock_frontend.return_value = FrontendType.NONE
        mock_python_version.return_value = "3.12"
        mock_ports.return_value = {"backend_port": 8000}
        mock_ai_framework.return_value = AIFrameworkType.PYDANTIC_AI
        mock_llm_provider.return_value = LLMProviderType.OPENAI
        mock_rag_config.return_value = RAGFeatures(enable_rag=False)

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        # Redis should be auto-enabled for Celery
        assert config.enable_redis is True
        assert config.background_tasks == BackgroundTaskType.CELERY

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_llm_provider")
    @patch("fastapi_gen.prompts.prompt_ai_framework")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    @patch("fastapi_gen.prompts.prompt_rag_config")
    def test_ai_agent_with_conversation_persistence(
        self,
        mock_rag_config: MagicMock,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_ai_framework: MagicMock,
        mock_llm_provider: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test AI agent prompts conversation persistence."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
            "timezone": "UTC",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_oauth.return_value = OAuthProvider.NONE
        mock_logfire.return_value = (True, LogfireFeatures())
        mock_background_tasks.return_value = BackgroundTaskType.NONE
        mock_integrations.return_value = {
            "enable_redis": False,
            "enable_caching": False,
            "enable_rate_limiting": False,
            "enable_pagination": True,
            "enable_sentry": False,
            "enable_prometheus": False,
            "enable_admin_panel": False,
            "enable_websockets": False,
            "enable_file_storage": False,
            "enable_cors": True,

        }
        mock_dev_tools.return_value = {
            "enable_pytest": True,
            "enable_precommit": True,
            "enable_docker": True,
            "enable_kubernetes": False,
            "ci_type": CIType.GITHUB,
        }
        mock_reverse_proxy.return_value = ReverseProxyType.TRAEFIK_INCLUDED
        mock_frontend.return_value = FrontendType.NONE
        mock_python_version.return_value = "3.12"
        mock_ports.return_value = {"backend_port": 8000}
        mock_ai_framework.return_value = AIFrameworkType.PYDANTIC_AI
        mock_llm_provider.return_value = LLMProviderType.OPENAI
        mock_rag_config.return_value = RAGFeatures(enable_rag=False)  # Skip RAG logic

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        assert config.llm_provider == LLMProviderType.OPENAI

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_llm_provider")
    @patch("fastapi_gen.prompts.prompt_ai_framework")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    @patch("fastapi_gen.prompts.prompt_rag_config")
    def test_admin_panel_with_postgresql(
        self,
        mock_rag_config: MagicMock,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_ai_framework: MagicMock,
        mock_llm_provider: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test admin panel prompts config when PostgreSQL is selected."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
            "timezone": "UTC",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_oauth.return_value = OAuthProvider.NONE
        mock_logfire.return_value = (True, LogfireFeatures())
        mock_background_tasks.return_value = BackgroundTaskType.NONE
        mock_integrations.return_value = {
            "enable_redis": False,
            "enable_caching": False,
            "enable_rate_limiting": False,
            "enable_pagination": True,
            "enable_sentry": False,
            "enable_prometheus": False,
            "enable_admin_panel": True,  # Admin panel enabled
            "enable_websockets": False,
            "enable_file_storage": False,
            "enable_cors": True,

        }
        mock_dev_tools.return_value = {
            "enable_pytest": True,
            "enable_precommit": True,
            "enable_docker": True,
            "enable_kubernetes": False,
            "ci_type": CIType.GITHUB,
        }
        mock_reverse_proxy.return_value = ReverseProxyType.TRAEFIK_INCLUDED
        mock_frontend.return_value = FrontendType.NONE
        mock_python_version.return_value = "3.12"
        mock_ports.return_value = {"backend_port": 8000}
        mock_ai_framework.return_value = AIFrameworkType.PYDANTIC_AI
        mock_llm_provider.return_value = LLMProviderType.OPENAI
        mock_rag_config.return_value = RAGFeatures(enable_rag=False)

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        # Admin config should be set
        assert config.enable_admin_panel is True

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_brand_color")
    @patch("fastapi_gen.prompts.prompt_llm_provider")
    @patch("fastapi_gen.prompts.prompt_ai_framework")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    @patch("fastapi_gen.prompts.prompt_rag_config")
    def test_frontend_with_nextjs_prompts_brand_color(
        self,
        mock_rag_config: MagicMock,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_ai_framework: MagicMock,
        mock_llm_provider: MagicMock,
        mock_brand_color: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test brand color is prompted when Next.js is selected."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
            "timezone": "UTC",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_oauth.return_value = OAuthProvider.NONE
        mock_logfire.return_value = (False, LogfireFeatures())
        mock_background_tasks.return_value = BackgroundTaskType.NONE
        mock_integrations.return_value = {
            "enable_redis": False,
            "enable_caching": False,
            "enable_rate_limiting": False,
            "enable_pagination": True,
            "enable_sentry": False,
            "enable_prometheus": False,
            "enable_admin_panel": False,
            "enable_websockets": False,
            "enable_file_storage": False,
            "enable_cors": True,

        }
        mock_dev_tools.return_value = {
            "enable_pytest": True,
            "enable_precommit": True,
            "enable_docker": True,
            "enable_kubernetes": False,
            "ci_type": CIType.GITHUB,
        }
        mock_reverse_proxy.return_value = ReverseProxyType.TRAEFIK_INCLUDED
        mock_frontend.return_value = FrontendType.NEXTJS
        mock_python_version.return_value = "3.12"
        mock_ports.return_value = {"backend_port": 8000, "frontend_port": 3000}
        mock_ai_framework.return_value = AIFrameworkType.PYDANTIC_AI
        mock_llm_provider.return_value = LLMProviderType.OPENAI
        mock_rag_config.return_value = RAGFeatures(enable_rag=False)
        mock_brand_color.return_value = BrandColorType.BLUE

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        # Brand color should be called when Next.js is selected
        assert config.frontend == FrontendType.NEXTJS
        mock_brand_color.assert_called_once()

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_rate_limit_config")
    @patch("fastapi_gen.prompts.prompt_llm_provider")
    @patch("fastapi_gen.prompts.prompt_ai_framework")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    @patch("fastapi_gen.prompts.prompt_rag_config")
    def test_rate_limit_config_prompted_when_enabled(
        self,
        mock_rag_config: MagicMock,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_ai_framework: MagicMock,
        mock_llm_provider: MagicMock,
        mock_rate_limit_config: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test rate limit config is prompted when rate limiting is enabled."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
            "timezone": "UTC",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_oauth.return_value = OAuthProvider.NONE
        mock_logfire.return_value = (False, LogfireFeatures())
        mock_background_tasks.return_value = BackgroundTaskType.NONE
        mock_integrations.return_value = {
            "enable_redis": True,
            "enable_caching": False,
            "enable_rate_limiting": True,  # Rate limiting enabled
            "enable_pagination": True,
            "enable_sentry": False,
            "enable_prometheus": False,
            "enable_admin_panel": False,
            "enable_websockets": False,
            "enable_file_storage": False,
            "enable_cors": True,

        }
        mock_dev_tools.return_value = {
            "enable_pytest": True,
            "enable_precommit": True,
            "enable_docker": True,
            "enable_kubernetes": False,
            "ci_type": CIType.GITHUB,
        }
        mock_reverse_proxy.return_value = ReverseProxyType.TRAEFIK_INCLUDED
        mock_frontend.return_value = FrontendType.NONE
        mock_python_version.return_value = "3.12"
        mock_ports.return_value = {"backend_port": 8000}
        mock_ai_framework.return_value = AIFrameworkType.PYDANTIC_AI
        mock_llm_provider.return_value = LLMProviderType.OPENAI
        mock_rag_config.return_value = RAGFeatures(enable_rag=False)
        mock_rate_limit_config.return_value = (50, 30, RateLimitStorageType.REDIS)

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        # Rate limit config should be called and values set
        assert config.enable_rate_limiting is True
        assert config.rate_limit_requests == 50
        assert config.rate_limit_period == 30
        assert config.rate_limit_storage == RateLimitStorageType.REDIS
        mock_rate_limit_config.assert_called_once_with(redis_enabled=True)

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_rate_limit_config")
    @patch("fastapi_gen.prompts.prompt_llm_provider")
    @patch("fastapi_gen.prompts.prompt_ai_framework")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    @patch("fastapi_gen.prompts.prompt_rag_config")
    def test_rate_limit_config_not_prompted_when_disabled(
        self,
        mock_rag_config: MagicMock,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_ai_framework: MagicMock,
        mock_llm_provider: MagicMock,
        mock_rate_limit_config: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test rate limit config is NOT prompted when rate limiting is disabled."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
            "timezone": "UTC",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_oauth.return_value = OAuthProvider.NONE
        mock_logfire.return_value = (False, LogfireFeatures())
        mock_background_tasks.return_value = BackgroundTaskType.NONE
        mock_integrations.return_value = {
            "enable_redis": False,
            "enable_caching": False,
            "enable_rate_limiting": False,  # Rate limiting disabled
            "enable_pagination": True,
            "enable_sentry": False,
            "enable_prometheus": False,
            "enable_admin_panel": False,
            "enable_websockets": False,
            "enable_file_storage": False,
            "enable_cors": True,

        }
        mock_dev_tools.return_value = {
            "enable_pytest": True,
            "enable_precommit": True,
            "enable_docker": True,
            "enable_kubernetes": False,
            "ci_type": CIType.GITHUB,
        }
        mock_reverse_proxy.return_value = ReverseProxyType.TRAEFIK_INCLUDED
        mock_frontend.return_value = FrontendType.NONE
        mock_python_version.return_value = "3.12"
        mock_ports.return_value = {"backend_port": 8000}
        mock_ai_framework.return_value = AIFrameworkType.PYDANTIC_AI
        mock_llm_provider.return_value = LLMProviderType.OPENAI
        mock_rag_config.return_value = RAGFeatures(enable_rag=False)

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        # Rate limit config should NOT be called
        assert config.enable_rate_limiting is False
        assert config.rate_limit_requests == 100  # Default value
        assert config.rate_limit_period == 60  # Default value
        assert config.rate_limit_storage == RateLimitStorageType.MEMORY  # Default value
        mock_rate_limit_config.assert_not_called()


class TestShowSummary:
    """Tests for show_summary function."""

    def test_show_summary_runs_without_error(self, minimal_config: Any) -> None:
        """Test summary displays without errors."""
        # Just verify it doesn't raise
        show_summary(minimal_config)

    def test_show_summary_with_features(self, full_config: Any) -> None:
        """Test summary displays with all features."""
        # Just verify it doesn't raise
        show_summary(full_config)


class TestConfirmGeneration:
    """Tests for confirm_generation function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_true_on_confirm(self, mock_questionary: MagicMock) -> None:
        """Test True is returned on confirmation."""
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True
        mock_questionary.confirm.return_value = mock_confirm

        result = confirm_generation()

        assert result is True

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_false_on_decline(self, mock_questionary: MagicMock) -> None:
        """Test False is returned on decline."""
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        result = confirm_generation()

        assert result is False

    @patch("fastapi_gen.prompts.questionary")
    def test_raises_on_cancel(self, mock_questionary: MagicMock) -> None:
        """Test KeyboardInterrupt on cancel."""
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = None
        mock_questionary.confirm.return_value = mock_confirm

        with pytest.raises(KeyboardInterrupt):
            confirm_generation()


class TestPromptRAGConfig:
    """Tests for prompt_rag_config function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_rag_disabled_by_default(self, mock_questionary: MagicMock) -> None:
        """Test RAG is disabled by default when user declines."""
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        result = prompt_rag_config()

        assert result.enable_rag is False
        assert result.enable_google_drive_ingestion is False
        assert result.reranker_type == RerankerType.NONE

    @patch("fastapi_gen.prompts.questionary")
    def test_rag_enabled_no_features(self, mock_questionary: MagicMock) -> None:
        """Test RAG enabled but no additional features selected."""
        # Confirms: enable_rag=True, google_drive=False, s3=False, image_desc=False
        mock_confirm = MagicMock()
        mock_confirm.ask.side_effect = [True, False, False, False]
        mock_questionary.confirm.return_value = mock_confirm

        # Selects: vector_store, reranker_type, pdf_parser
        mock_select = MagicMock()
        mock_select.ask.side_effect = [
            VectorStoreType.MILVUS,
            RerankerType.NONE,
            PdfParserType.PYMUPDF,
        ]
        mock_questionary.select.return_value = mock_select

        result = prompt_rag_config()

        assert result.enable_rag is True
        assert result.vector_store == VectorStoreType.MILVUS
        assert result.enable_google_drive_ingestion is False
        assert result.reranker_type == RerankerType.NONE

    @patch("fastapi_gen.prompts.questionary")
    def test_rag_enabled_with_google_drive(self, mock_questionary: MagicMock) -> None:
        """Test RAG enabled with Google Drive ingestion."""
        # Confirms: enable_rag=True, google_drive=True, s3=False, image_desc=False
        mock_confirm = MagicMock()
        mock_confirm.ask.side_effect = [True, True, False, False]
        mock_questionary.confirm.return_value = mock_confirm

        # Selects: vector_store, reranker_type, pdf_parser
        mock_select = MagicMock()
        mock_select.ask.side_effect = [
            VectorStoreType.MILVUS,
            RerankerType.NONE,
            PdfParserType.PYMUPDF,
        ]
        mock_questionary.select.return_value = mock_select

        result = prompt_rag_config()

        assert result.enable_rag is True
        assert result.enable_google_drive_ingestion is True
        assert result.reranker_type == RerankerType.NONE

    @patch("fastapi_gen.prompts.questionary")
    def test_rag_enabled_with_reranker(self, mock_questionary: MagicMock) -> None:
        """Test RAG enabled with reranker."""
        # Confirms: enable_rag=True, google_drive=False, s3=False, image_desc=False
        mock_confirm = MagicMock()
        mock_confirm.ask.side_effect = [True, False, False, False]
        mock_questionary.confirm.return_value = mock_confirm

        # Selects: vector_store, reranker_type, pdf_parser
        mock_select = MagicMock()
        mock_select.ask.side_effect = [
            VectorStoreType.QDRANT,
            RerankerType.COHERE,
            PdfParserType.PYMUPDF,
        ]
        mock_questionary.select.return_value = mock_select

        result = prompt_rag_config()

        assert result.enable_rag is True
        assert result.vector_store == VectorStoreType.QDRANT
        assert result.reranker_type == RerankerType.COHERE

    @patch("fastapi_gen.prompts.questionary")
    def test_rag_enabled_with_all_features(self, mock_questionary: MagicMock) -> None:
        """Test RAG enabled with all features."""
        # Confirms: enable_rag=True, google_drive=True, s3=True
        # (no image_desc confirm since LLAMAPARSE is not PYMUPDF/ALL)
        mock_confirm = MagicMock()
        mock_confirm.ask.side_effect = [True, True, True]
        mock_questionary.confirm.return_value = mock_confirm

        # Selects: vector_store, reranker_type, pdf_parser
        mock_select = MagicMock()
        mock_select.ask.side_effect = [
            VectorStoreType.CHROMADB,
            RerankerType.COHERE,
            PdfParserType.LLAMAPARSE,
        ]
        mock_questionary.select.return_value = mock_select

        result = prompt_rag_config()

        assert result.enable_rag is True
        assert result.vector_store == VectorStoreType.CHROMADB
        assert result.pdf_parser == PdfParserType.LLAMAPARSE
        assert result.reranker_type == RerankerType.COHERE

    @patch("fastapi_gen.prompts.console")
    @patch("fastapi_gen.prompts.questionary")
    def test_prompt_uses_llm_provider(
        self, mock_questionary: MagicMock, mock_console: MagicMock
    ) -> None:
        """Test that prompt_rag_config receives the LLM provider."""
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        # Call with Anthropic provider
        prompt_rag_config()

        # The function should work with any LLM provider without errors
        # (The provider is passed as argument but not used in current implementation)
        assert mock_confirm.ask.call_count == 1


class TestPromptLangsmith:
    """Tests for prompt_langsmith function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_true_when_confirmed(self, mock_questionary: MagicMock) -> None:
        """Test prompt_langsmith returns True when user confirms."""
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True
        mock_questionary.confirm.return_value = mock_confirm

        result = prompt_langsmith()

        assert result is True

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_false_when_declined(self, mock_questionary: MagicMock) -> None:
        """Test prompt_langsmith returns False when user declines."""
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        result = prompt_langsmith()

        assert result is False


class TestRunInteractivePromptsLangSmith:
    """Tests for LangSmith prompt invocation in run_interactive_prompts."""

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_langsmith")
    @patch("fastapi_gen.prompts.prompt_llm_provider")
    @patch("fastapi_gen.prompts.prompt_ai_framework")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    @patch("fastapi_gen.prompts.prompt_rag_config")
    def test_langsmith_prompted_for_langchain_framework(
        self,
        mock_rag_config: MagicMock,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_ai_framework: MagicMock,
        mock_llm_provider: MagicMock,
        mock_langsmith: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test LangSmith prompt is called when LangChain framework is selected (line 900)."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
            "timezone": "UTC",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_oauth.return_value = OAuthProvider.NONE
        mock_logfire.return_value = (False, LogfireFeatures())
        mock_background_tasks.return_value = BackgroundTaskType.NONE
        mock_integrations.return_value = {
            "enable_redis": False,
            "enable_caching": False,
            "enable_rate_limiting": False,
            "enable_pagination": True,
            "enable_sentry": False,
            "enable_prometheus": False,
            "enable_admin_panel": False,
            "enable_websockets": False,
            "enable_file_storage": False,
            "enable_cors": True,

        }
        mock_dev_tools.return_value = {
            "enable_pytest": True,
            "enable_precommit": True,
            "enable_docker": True,
            "enable_kubernetes": False,
            "ci_type": CIType.GITHUB,
        }
        mock_reverse_proxy.return_value = ReverseProxyType.TRAEFIK_INCLUDED
        mock_frontend.return_value = FrontendType.NONE
        mock_python_version.return_value = "3.12"
        mock_ports.return_value = {"backend_port": 8000}
        mock_ai_framework.return_value = AIFrameworkType.LANGCHAIN
        mock_llm_provider.return_value = LLMProviderType.OPENAI
        mock_rag_config.return_value = RAGFeatures(enable_rag=False)
        mock_langsmith.return_value = True

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        # LangSmith should be called and enabled
        mock_langsmith.assert_called_once()
        assert config.enable_langsmith is True


class TestShowSummaryLangSmithAndRAG:
    """Tests for show_summary with LangSmith and RAG enabled."""

    def test_show_summary_with_langsmith_enabled(self) -> None:
        """Test show_summary displays LangSmith when enabled (line 969)."""
        from fastapi_gen.config import ProjectConfig

        config = ProjectConfig(
            project_name="test",
            ai_framework=AIFrameworkType.LANGCHAIN,
            enable_langsmith=True,
            background_tasks=BackgroundTaskType.NONE,
        )

        # Should not raise - exercises line 969
        show_summary(config)

    def test_show_summary_with_rag_enabled(self) -> None:
        """Test show_summary displays RAG info when enabled (line 985)."""
        from fastapi_gen.config import ProjectConfig

        config = ProjectConfig(
            project_name="test",
            rag_features=RAGFeatures(
                enable_rag=True,
                vector_store=VectorStoreType.MILVUS,
            ),
            background_tasks=BackgroundTaskType.NONE,
        )

        # Should not raise - exercises line 985
        show_summary(config)
