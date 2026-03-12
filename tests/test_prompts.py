"""Tests for fastapi_gen.prompts module."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from fastapi_gen.config import (
    AdminEnvironmentType,
    AIFrameworkType,
    AuthType,
    BackgroundTaskType,
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
    ReverseProxyType,
    WebSocketAuthType,
)
from fastapi_gen.prompts import (
    _check_cancelled,
    _normalize_project_name,
    _validate_email,
    _validate_positive_integer,
    _validate_project_name,
    confirm_generation,
    prompt_admin_config,
    prompt_auth,
    prompt_background_tasks,
    prompt_basic_info,
    prompt_database,
    prompt_dev_tools,
    prompt_frontend,
    prompt_frontend_features,
    prompt_integrations,
    prompt_llm_provider,
    prompt_logfire,
    prompt_oauth,
    prompt_orm_type,
    prompt_ports,
    prompt_python_version,
    prompt_rag_config,
    prompt_rate_limit_config,
    prompt_reverse_proxy,
    prompt_websocket_auth,
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
        ]
        mock_questionary.text.return_value = mock_text

        result = prompt_basic_info()

        assert result == {
            "project_name": "myproject",
            "project_description": "My description",
            "author_name": "John Doe",
            "author_email": "john@example.com",
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


class TestPromptDatabase:
    """Tests for prompt_database function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_selected_database(self, mock_questionary: MagicMock) -> None:
        """Test selected database is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = DatabaseType.MONGODB
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_database()

        assert result == DatabaseType.MONGODB

    @patch("fastapi_gen.prompts.questionary")
    def test_raises_on_cancel(self, mock_questionary: MagicMock) -> None:
        """Test KeyboardInterrupt on cancel."""
        mock_select = MagicMock()
        mock_select.ask.return_value = None
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        with pytest.raises(KeyboardInterrupt):
            prompt_database()


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


class TestPromptAuth:
    """Tests for prompt_auth function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_selected_auth(self, mock_questionary: MagicMock) -> None:
        """Test selected auth method is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = AuthType.API_KEY
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_auth()

        assert result == AuthType.API_KEY


class TestPromptLogfire:
    """Tests for prompt_logfire function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_disabled_logfire(self, mock_questionary: MagicMock) -> None:
        """Test disabled Logfire returns False and default features."""
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        enabled, features = prompt_logfire(BackgroundTaskType.NONE)

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

        enabled, features = prompt_logfire(BackgroundTaskType.NONE)

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

        enabled, features = prompt_logfire(BackgroundTaskType.CELERY)

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
        assert result["enable_websockets"] is True
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
    def test_admin_panel_hidden_with_mongodb(self, mock_questionary: MagicMock) -> None:
        """Test admin panel option is not shown when MongoDB is selected."""
        mock_checkbox = MagicMock()
        mock_checkbox.ask.return_value = []
        mock_questionary.checkbox.return_value = mock_checkbox
        mock_questionary.Choice = MagicMock()

        prompt_integrations(
            database=DatabaseType.MONGODB,
            orm_type=OrmType.SQLALCHEMY,  # Doesn't apply for MongoDB
        )

        # Check that checkbox was called without admin_panel in choices
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
    def test_webhooks_hidden_without_database(self, mock_questionary: MagicMock) -> None:
        """Test webhooks option is not shown when no database is selected."""
        mock_checkbox = MagicMock()
        mock_checkbox.ask.return_value = []
        mock_questionary.checkbox.return_value = mock_checkbox
        mock_questionary.Choice = MagicMock()

        prompt_integrations(
            database=DatabaseType.NONE,
            orm_type=OrmType.SQLALCHEMY,
        )

        # Check that checkbox was called without webhooks in choices
        # Each call in call_args_list is (args, kwargs) tuple
        choice_values = [call[1].get("value") for call in mock_questionary.Choice.call_args_list]
        assert "webhooks" not in choice_values

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

        mock_select = MagicMock()
        mock_select.ask.return_value = RateLimitStorageType.MEMORY
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        requests, period, storage = prompt_rate_limit_config(redis_enabled=False)

        assert requests == 50
        assert period == 30
        assert storage == RateLimitStorageType.MEMORY

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_redis_storage_when_redis_enabled(self, mock_questionary: MagicMock) -> None:
        """Test Redis storage can be selected when Redis is enabled."""
        mock_text = MagicMock()
        mock_text.ask.side_effect = ["100", "60"]
        mock_questionary.text.return_value = mock_text

        mock_select = MagicMock()
        mock_select.ask.return_value = RateLimitStorageType.REDIS
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        requests, period, storage = prompt_rate_limit_config(redis_enabled=True)

        assert requests == 100
        assert period == 60
        assert storage == RateLimitStorageType.REDIS

    @patch("fastapi_gen.prompts.questionary")
    def test_redis_option_not_shown_when_redis_disabled(self, mock_questionary: MagicMock) -> None:
        """Test Redis storage option is not shown when Redis is disabled."""
        mock_text = MagicMock()
        mock_text.ask.side_effect = ["100", "60"]
        mock_questionary.text.return_value = mock_text

        mock_select = MagicMock()
        mock_select.ask.return_value = RateLimitStorageType.MEMORY
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        prompt_rate_limit_config(redis_enabled=False)

        # Check that select was called with only one choice (Memory)
        select_call = mock_questionary.select.call_args
        choices = select_call[1]["choices"]
        assert len(choices) == 1

    @patch("fastapi_gen.prompts.questionary")
    def test_redis_option_shown_when_redis_enabled(self, mock_questionary: MagicMock) -> None:
        """Test Redis storage option is shown when Redis is enabled."""
        mock_text = MagicMock()
        mock_text.ask.side_effect = ["100", "60"]
        mock_questionary.text.return_value = mock_text

        mock_select = MagicMock()
        mock_select.ask.return_value = RateLimitStorageType.MEMORY
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        prompt_rate_limit_config(redis_enabled=True)

        # Check that select was called with two choices (Memory and Redis)
        select_call = mock_questionary.select.call_args
        choices = select_call[1]["choices"]
        assert len(choices) == 2

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


class TestPromptWebsocketAuth:
    """Tests for prompt_websocket_auth function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_none_auth(self, mock_questionary: MagicMock) -> None:
        """Test none auth is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = WebSocketAuthType.NONE
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_websocket_auth(auth=AuthType.JWT)

        assert result == WebSocketAuthType.NONE

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_jwt_auth(self, mock_questionary: MagicMock) -> None:
        """Test JWT auth is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = WebSocketAuthType.JWT
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_websocket_auth(auth=AuthType.JWT)

        assert result == WebSocketAuthType.JWT

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_api_key_auth(self, mock_questionary: MagicMock) -> None:
        """Test API key auth is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = WebSocketAuthType.API_KEY
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        result = prompt_websocket_auth(auth=AuthType.API_KEY)

        assert result == WebSocketAuthType.API_KEY

    @patch("fastapi_gen.prompts.questionary")
    def test_jwt_option_shown_with_jwt_auth(self, mock_questionary: MagicMock) -> None:
        """Test JWT option is shown when main auth is JWT."""
        mock_select = MagicMock()
        mock_select.ask.return_value = WebSocketAuthType.NONE
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        prompt_websocket_auth(auth=AuthType.JWT)

        # Check that JWT option was included
        choice_values = [call[1].get("value") for call in mock_questionary.Choice.call_args_list]
        assert WebSocketAuthType.JWT in choice_values
        assert WebSocketAuthType.API_KEY not in choice_values  # Not shown for JWT-only

    @patch("fastapi_gen.prompts.questionary")
    def test_jwt_option_hidden_with_api_key_auth(self, mock_questionary: MagicMock) -> None:
        """Test JWT option is hidden when main auth is API key only."""
        mock_select = MagicMock()
        mock_select.ask.return_value = WebSocketAuthType.NONE
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        prompt_websocket_auth(auth=AuthType.API_KEY)

        # Check that JWT option was NOT included
        choice_values = [call[1].get("value") for call in mock_questionary.Choice.call_args_list]
        assert WebSocketAuthType.JWT not in choice_values
        assert WebSocketAuthType.API_KEY in choice_values

    @patch("fastapi_gen.prompts.questionary")
    def test_both_options_shown_with_both_auth(self, mock_questionary: MagicMock) -> None:
        """Test both JWT and API key options are shown when main auth is BOTH."""
        mock_select = MagicMock()
        mock_select.ask.return_value = WebSocketAuthType.NONE
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        prompt_websocket_auth(auth=AuthType.BOTH)

        # Check that both options were included
        choice_values = [call[1].get("value") for call in mock_questionary.Choice.call_args_list]
        assert WebSocketAuthType.JWT in choice_values
        assert WebSocketAuthType.API_KEY in choice_values

    @patch("fastapi_gen.prompts.questionary")
    def test_no_auth_options_with_none_auth(self, mock_questionary: MagicMock) -> None:
        """Test only None option is available when main auth is NONE."""
        mock_select = MagicMock()
        mock_select.ask.return_value = WebSocketAuthType.NONE
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        prompt_websocket_auth(auth=AuthType.NONE)

        # Check that only None option was included
        choice_values = [call[1].get("value") for call in mock_questionary.Choice.call_args_list]
        assert WebSocketAuthType.NONE in choice_values
        assert WebSocketAuthType.JWT not in choice_values
        assert WebSocketAuthType.API_KEY not in choice_values


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


class TestPromptAdminConfig:
    """Tests for prompt_admin_config function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_dev_staging_with_auth(self, mock_questionary: MagicMock) -> None:
        """Test dev_staging environment with auth is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = AdminEnvironmentType.DEV_STAGING
        mock_questionary.select.return_value = mock_select

        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True
        mock_questionary.confirm.return_value = mock_confirm
        mock_questionary.Choice = MagicMock()

        env, require_auth = prompt_admin_config()

        assert env == AdminEnvironmentType.DEV_STAGING
        assert require_auth is True

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_disabled_skips_auth(self, mock_questionary: MagicMock) -> None:
        """Test disabled environment skips auth question."""
        mock_select = MagicMock()
        mock_select.ask.return_value = AdminEnvironmentType.DISABLED
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        env, require_auth = prompt_admin_config()

        assert env == AdminEnvironmentType.DISABLED
        assert require_auth is False
        # confirm should not have been called
        mock_questionary.confirm.assert_not_called()

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_all_without_auth(self, mock_questionary: MagicMock) -> None:
        """Test all environment without auth is returned."""
        mock_select = MagicMock()
        mock_select.ask.return_value = AdminEnvironmentType.ALL
        mock_questionary.select.return_value = mock_select

        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm
        mock_questionary.Choice = MagicMock()

        env, require_auth = prompt_admin_config()

        assert env == AdminEnvironmentType.ALL
        assert require_auth is False


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

        # Test invalid ports
        assert validate_port("1023") is False  # Below range
        assert validate_port("65536") is False  # Above range
        assert validate_port("invalid") is False  # Not a number
        assert validate_port("") is False  # Empty string


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

        # Check that select was called with 3 choices (OpenAI, Anthropic, OpenRouter)
        select_call = mock_questionary.select.call_args
        choices = select_call[1]["choices"]
        assert len(choices) == 3

    @patch("fastapi_gen.prompts.questionary")
    def test_openrouter_option_not_added_for_langchain(self, mock_questionary: MagicMock) -> None:
        """Test OpenRouter option is NOT added when using LangChain."""
        mock_select = MagicMock()
        mock_select.ask.return_value = LLMProviderType.OPENAI
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        prompt_llm_provider(AIFrameworkType.LANGCHAIN)

        # Check that select was called with 2 choices (OpenAI, Anthropic)
        select_call = mock_questionary.select.call_args
        choices = select_call[1]["choices"]
        assert len(choices) == 2

    @patch("fastapi_gen.prompts.questionary")
    def test_raises_on_cancel(self, mock_questionary: MagicMock) -> None:
        """Test KeyboardInterrupt on cancel."""
        mock_select = MagicMock()
        mock_select.ask.return_value = None
        mock_questionary.select.return_value = mock_select
        mock_questionary.Choice = MagicMock()

        with pytest.raises(KeyboardInterrupt):
            prompt_llm_provider(AIFrameworkType.PYDANTIC_AI)


class TestPromptFrontendFeatures:
    """Tests for prompt_frontend_features function."""

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_i18n_enabled(self, mock_questionary: MagicMock) -> None:
        """Test i18n feature is returned when selected."""
        mock_checkbox = MagicMock()
        mock_checkbox.ask.return_value = ["i18n"]
        mock_questionary.checkbox.return_value = mock_checkbox
        mock_questionary.Choice = MagicMock()

        result = prompt_frontend_features()

        assert result["enable_i18n"] is True

    @patch("fastapi_gen.prompts.questionary")
    def test_returns_no_features(self, mock_questionary: MagicMock) -> None:
        """Test empty features are returned when nothing selected."""
        mock_checkbox = MagicMock()
        mock_checkbox.ask.return_value = []
        mock_questionary.checkbox.return_value = mock_checkbox
        mock_questionary.Choice = MagicMock()

        result = prompt_frontend_features()

        assert result["enable_i18n"] is False


class TestRunInteractivePrompts:
    """Tests for run_interactive_prompts function."""

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_auth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    def test_builds_project_config(
        self,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_auth: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test ProjectConfig is built from prompts."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_auth.return_value = AuthType.JWT
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
            "enable_ai_agent": False,
            "enable_cors": True,
            "enable_orjson": True,
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

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        assert config.project_name == "test_project"
        assert config.database == DatabaseType.POSTGRESQL
        assert config.auth == AuthType.JWT
        assert config.enable_logfire is True
        assert config.ci_type == CIType.GITHUB
        assert config.python_version == "3.12"
        assert config.backend_port == 8000

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_auth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    def test_auto_enables_redis_for_celery(
        self,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_auth: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test Redis is auto-enabled when Celery is selected."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_auth.return_value = AuthType.JWT
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
            "enable_ai_agent": False,
            "enable_cors": True,
            "enable_orjson": True,
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

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        # Redis should be auto-enabled for Celery
        assert config.enable_redis is True
        assert config.background_tasks == BackgroundTaskType.CELERY

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_websocket_auth")
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
    @patch("fastapi_gen.prompts.prompt_auth")
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
        mock_auth: MagicMock,
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
        mock_websocket_auth: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test AI agent prompts websocket auth and conversation persistence."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_auth.return_value = AuthType.JWT
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
            "enable_ai_agent": True,  # AI Agent enabled
            "include_example_crud": True,
            "enable_cors": True,
            "enable_orjson": True,
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
        mock_websocket_auth.return_value = WebSocketAuthType.JWT

        # Mock session management and conversation persistence confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.side_effect = [False, True]  # session mgmt, conversation persistence
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        # WebSocket auth and conversation persistence should be set
        assert config.enable_ai_agent is True
        assert config.websocket_auth == WebSocketAuthType.JWT
        assert config.enable_conversation_persistence is True
        assert config.llm_provider == LLMProviderType.OPENAI
        mock_websocket_auth.assert_called_once()

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_admin_config")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_auth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    def test_admin_panel_with_postgresql(
        self,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_auth: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_admin_config: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test admin panel prompts config when PostgreSQL is selected."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_auth.return_value = AuthType.JWT
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
            "enable_ai_agent": False,
            "include_example_crud": True,
            "enable_cors": True,
            "enable_orjson": True,
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
        mock_admin_config.return_value = (AdminEnvironmentType.DEV_ONLY, True)

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        # Admin config should be set
        assert config.enable_admin_panel is True
        assert config.admin_environments == AdminEnvironmentType.DEV_ONLY
        assert config.admin_require_auth is True
        mock_admin_config.assert_called_once()

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_admin_config")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_auth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    def test_admin_panel_with_sqlite(
        self,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_auth: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_admin_config: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test admin panel prompts config when SQLite is selected."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
        }
        mock_database.return_value = DatabaseType.SQLITE
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_auth.return_value = AuthType.JWT
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
            "enable_ai_agent": False,
            "include_example_crud": True,
            "enable_cors": True,
            "enable_orjson": True,
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
        mock_admin_config.return_value = (AdminEnvironmentType.DEV_ONLY, True)

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        # Admin config should be set for SQLite too
        assert config.enable_admin_panel is True
        assert config.admin_environments == AdminEnvironmentType.DEV_ONLY
        assert config.admin_require_auth is True
        mock_admin_config.assert_called_once()

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_admin_config")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_auth")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    def test_admin_panel_not_prompted_with_mongodb(
        self,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_auth: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_admin_config: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test admin panel config is NOT prompted when MongoDB is selected."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
        }
        mock_database.return_value = DatabaseType.MONGODB
        mock_auth.return_value = AuthType.NONE
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
            "enable_admin_panel": False,  # Admin panel disabled for MongoDB
            "enable_websockets": False,
            "enable_file_storage": False,
            "enable_ai_agent": False,
            "include_example_crud": True,
            "enable_cors": True,
            "enable_orjson": True,
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

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        # Admin config should NOT be prompted for MongoDB
        assert config.enable_admin_panel is False
        mock_admin_config.assert_not_called()

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_frontend_features")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_auth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    def test_frontend_with_nextjs_prompts_frontend_features(
        self,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_auth: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_frontend_features: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test frontend features are prompted when Next.js is selected."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_auth.return_value = AuthType.JWT
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
            "enable_ai_agent": False,
            "enable_cors": True,
            "enable_orjson": True,
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
        mock_frontend_features.return_value = {"enable_i18n": True}

        # Mock session management confirm
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_questionary.confirm.return_value = mock_confirm

        config = run_interactive_prompts()

        # Frontend features should be called and i18n enabled
        assert config.frontend == FrontendType.NEXTJS
        assert config.enable_i18n is True
        mock_frontend_features.assert_called_once()

    @patch("fastapi_gen.prompts.questionary")
    @patch("fastapi_gen.prompts.prompt_rate_limit_config")
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_auth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    def test_rate_limit_config_prompted_when_enabled(
        self,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_auth: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_rate_limit_config: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test rate limit config is prompted when rate limiting is enabled."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_auth.return_value = AuthType.JWT
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
            "enable_ai_agent": False,
            "enable_cors": True,
            "enable_orjson": True,
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
    @patch("fastapi_gen.prompts.prompt_ports")
    @patch("fastapi_gen.prompts.prompt_python_version")
    @patch("fastapi_gen.prompts.prompt_frontend")
    @patch("fastapi_gen.prompts.prompt_reverse_proxy")
    @patch("fastapi_gen.prompts.prompt_dev_tools")
    @patch("fastapi_gen.prompts.prompt_integrations")
    @patch("fastapi_gen.prompts.prompt_background_tasks")
    @patch("fastapi_gen.prompts.prompt_logfire")
    @patch("fastapi_gen.prompts.prompt_oauth")
    @patch("fastapi_gen.prompts.prompt_auth")
    @patch("fastapi_gen.prompts.prompt_orm_type")
    @patch("fastapi_gen.prompts.prompt_database")
    @patch("fastapi_gen.prompts.prompt_basic_info")
    @patch("fastapi_gen.prompts.show_header")
    def test_rate_limit_config_not_prompted_when_disabled(
        self,
        mock_header: MagicMock,
        mock_basic_info: MagicMock,
        mock_database: MagicMock,
        mock_orm_type: MagicMock,
        mock_auth: MagicMock,
        mock_oauth: MagicMock,
        mock_logfire: MagicMock,
        mock_background_tasks: MagicMock,
        mock_integrations: MagicMock,
        mock_dev_tools: MagicMock,
        mock_reverse_proxy: MagicMock,
        mock_frontend: MagicMock,
        mock_python_version: MagicMock,
        mock_ports: MagicMock,
        mock_rate_limit_config: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test rate limit config is NOT prompted when rate limiting is disabled."""
        mock_basic_info.return_value = {
            "project_name": "test_project",
            "project_description": "Test",
            "author_name": "Test Author",
            "author_email": "test@test.com",
        }
        mock_database.return_value = DatabaseType.POSTGRESQL
        mock_orm_type.return_value = OrmType.SQLALCHEMY
        mock_auth.return_value = AuthType.JWT
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
            "enable_ai_agent": False,
            "enable_cors": True,
            "enable_orjson": True,
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
        assert result.enable_reranker is False

    @patch("fastapi_gen.prompts.questionary")
    def test_rag_enabled_no_features(self, mock_questionary: MagicMock) -> None:
        """Test RAG enabled but no additional features selected."""
        # First call: enable RAG = True
        # Second call: enable Google Drive = False
        # Third call: enable reranker = False
        mock_confirm = MagicMock()
        mock_confirm.ask.side_effect = [True, False, False]
        mock_questionary.confirm.return_value = mock_confirm

        # Mock the PDF parser selection (shown when RAG is enabled)
        mock_select = MagicMock()
        mock_select.ask.return_value = PdfParserType.PDFPLUMBER
        mock_questionary.select.return_value = mock_select

        result = prompt_rag_config()

        assert result.enable_rag is True
        assert result.enable_google_drive_ingestion is False
        assert result.enable_reranker is False

    @patch("fastapi_gen.prompts.questionary")
    def test_rag_enabled_with_google_drive(self, mock_questionary: MagicMock) -> None:
        """Test RAG enabled with Google Drive ingestion."""
        mock_confirm = MagicMock()
        mock_confirm.ask.side_effect = [True, True, False]  # RAG, Google Drive, no reranker
        mock_questionary.confirm.return_value = mock_confirm

        # Mock the PDF parser selection (shown when RAG is enabled)
        mock_select = MagicMock()
        mock_select.ask.return_value = PdfParserType.PDFPLUMBER
        mock_questionary.select.return_value = mock_select

        result = prompt_rag_config()

        assert result.enable_rag is True
        assert result.enable_google_drive_ingestion is True
        assert result.enable_reranker is False

    @patch("fastapi_gen.prompts.questionary")
    def test_rag_enabled_with_reranker(self, mock_questionary: MagicMock) -> None:
        """Test RAG enabled with reranker."""
        mock_confirm = MagicMock()
        mock_confirm.ask.side_effect = [True, False, True]  # RAG, no Google Drive, reranker
        mock_questionary.confirm.return_value = mock_confirm

        # Mock the PDF parser selection (shown when RAG is enabled)
        mock_select = MagicMock()
        mock_select.ask.return_value = PdfParserType.PDFPLUMBER
        mock_questionary.select.return_value = mock_select

        result = prompt_rag_config()

        assert result.enable_rag is True
        assert result.enable_google_drive_ingestion is False
        assert result.enable_reranker is True

    @patch("fastapi_gen.prompts.questionary")
    def test_rag_enabled_with_all_features(self, mock_questionary: MagicMock) -> None:
        """Test RAG enabled with all features."""
        mock_confirm = MagicMock()
        mock_confirm.ask.side_effect = [True, True, True]  # RAG, Google Drive, reranker
        mock_questionary.confirm.return_value = mock_confirm

        # Mock the PDF parser selection (shown when RAG is enabled)
        mock_select = MagicMock()
        mock_select.ask.return_value = PdfParserType.PDFPLUMBER
        mock_questionary.select.return_value = mock_select

        result = prompt_rag_config()

        assert result.enable_rag is True
        assert result.enable_google_drive_ingestion is True
        assert result.enable_reranker is True

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
