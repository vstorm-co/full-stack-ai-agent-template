"""Tests for fastapi_gen.config module."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from fastapi_gen.config import (
    AIFrameworkType,
    AuthType,
    BackgroundTaskType,
    CIType,
    DatabaseType,
    LLMProviderType,
    LogfireFeatures,
    OrmType,
    ProjectConfig,
    RateLimitStorageType,
    ReverseProxyType,
    WebSocketAuthType,
    get_generator_version,
)


class TestGetGeneratorVersion:
    """Tests for get_generator_version function."""

    def test_returns_version_when_package_exists(self) -> None:
        """Test version is returned when package is installed."""
        # The package should be installed in the test environment
        version = get_generator_version()
        # Should return either a real version or fallback
        assert version is not None
        assert isinstance(version, str)

    def test_returns_fallback_when_package_not_found(self) -> None:
        """Test fallback version is returned when package is not found."""
        with patch("fastapi_gen.config.version", side_effect=Exception("Package not found")):
            version = get_generator_version()
            assert version == "0.0.0"


class TestEnums:
    """Tests for configuration enums."""

    def test_database_type_values(self) -> None:
        """Test DatabaseType enum values."""
        assert DatabaseType.POSTGRESQL.value == "postgresql"
        assert DatabaseType.MONGODB.value == "mongodb"
        assert DatabaseType.SQLITE.value == "sqlite"
        assert DatabaseType.NONE.value == "none"

    def test_auth_type_values(self) -> None:
        """Test AuthType enum values."""
        assert AuthType.JWT.value == "jwt"
        assert AuthType.API_KEY.value == "api_key"
        assert AuthType.BOTH.value == "both"
        assert AuthType.NONE.value == "none"

    def test_background_task_type_values(self) -> None:
        """Test BackgroundTaskType enum values."""
        assert BackgroundTaskType.NONE.value == "none"
        assert BackgroundTaskType.CELERY.value == "celery"
        assert BackgroundTaskType.TASKIQ.value == "taskiq"
        assert BackgroundTaskType.ARQ.value == "arq"

    def test_ci_type_values(self) -> None:
        """Test CIType enum values."""
        assert CIType.GITHUB.value == "github"
        assert CIType.GITLAB.value == "gitlab"
        assert CIType.NONE.value == "none"

    def test_rate_limit_storage_type_values(self) -> None:
        """Test RateLimitStorageType enum values."""
        assert RateLimitStorageType.MEMORY.value == "memory"
        assert RateLimitStorageType.REDIS.value == "redis"

    def test_orm_type_values(self) -> None:
        """Test OrmType enum values."""
        assert OrmType.SQLALCHEMY.value == "sqlalchemy"
        assert OrmType.SQLMODEL.value == "sqlmodel"


class TestLogfireFeatures:
    """Tests for LogfireFeatures model."""

    def test_default_values(self) -> None:
        """Test default LogfireFeatures values."""
        features = LogfireFeatures()
        assert features.fastapi is True
        assert features.database is True
        assert features.redis is False
        assert features.celery is False
        assert features.httpx is False

    def test_custom_values(self) -> None:
        """Test LogfireFeatures with custom values."""
        features = LogfireFeatures(
            fastapi=False,
            database=False,
            redis=True,
            celery=True,
            httpx=True,
        )
        assert features.fastapi is False
        assert features.database is False
        assert features.redis is True
        assert features.celery is True
        assert features.httpx is True


class TestProjectConfig:
    """Tests for ProjectConfig model."""

    def test_minimal_config(self) -> None:
        """Test minimal valid configuration."""
        config = ProjectConfig(project_name="myproject")
        assert config.project_name == "myproject"
        assert config.database == DatabaseType.POSTGRESQL
        assert config.auth == AuthType.JWT

    def test_valid_project_names(self) -> None:
        """Test valid project name patterns."""
        valid_names = [
            "myproject",
            "my_project",
            "project123",
            "a",
            "abc_def_123",
        ]
        for name in valid_names:
            config = ProjectConfig(project_name=name)
            assert config.project_name == name

    def test_invalid_project_names(self) -> None:
        """Test invalid project name patterns."""
        invalid_names = [
            "123project",  # starts with number
            "my-project",  # contains hyphen
            "My_Project",  # contains uppercase
            "_project",  # starts with underscore
            "",  # empty
        ]
        for name in invalid_names:
            with pytest.raises(ValidationError):
                ProjectConfig(project_name=name)

    def test_project_slug_conversion(self) -> None:
        """Test project_slug is derived from project_name."""
        config = ProjectConfig(project_name="my_project")
        context = config.to_cookiecutter_context()
        assert context["project_slug"] == "my_project"

    def test_all_fields_present_in_context(self) -> None:
        """Test all expected fields are in cookiecutter context."""
        config = ProjectConfig(project_name="test")
        context = config.to_cookiecutter_context()

        expected_keys = [
            "project_name",
            "project_slug",
            "project_description",
            "author_name",
            "author_email",
            "database",
            "use_postgresql",
            "use_mongodb",
            "use_sqlite",
            "use_database",
            "auth",
            "use_jwt",
            "use_api_key",
            "use_auth",
            "enable_logfire",
            "logfire_fastapi",
            "logfire_database",
            "logfire_redis",
            "logfire_celery",
            "logfire_httpx",
            "background_tasks",
            "use_celery",
            "use_taskiq",
            "use_arq",
            "enable_redis",
            "enable_caching",
            "enable_rate_limiting",
            "enable_pagination",
            "enable_sentry",
            "enable_prometheus",
            "enable_admin_panel",
            "enable_websockets",
            "enable_file_storage",
            "enable_ai_agent",
            "enable_cors",
            "enable_orjson",
            "enable_pytest",
            "enable_precommit",
            "enable_makefile",
            "enable_docker",
            "ci_type",
            "use_github_actions",
            "use_gitlab_ci",
            "enable_kubernetes",
        ]

        for key in expected_keys:
            assert key in context, f"Missing key: {key}"


class TestCookiecutterContext:
    """Tests for to_cookiecutter_context conversion."""

    def test_postgresql_database_flags(self) -> None:
        """Test PostgreSQL sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
        )
        context = config.to_cookiecutter_context()

        assert context["database"] == "postgresql"
        assert context["use_postgresql"] is True
        assert context["use_mongodb"] is False
        assert context["use_sqlite"] is False
        assert context["use_database"] is True

    def test_mongodb_database_flags(self) -> None:
        """Test MongoDB sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.MONGODB,
        )
        context = config.to_cookiecutter_context()

        assert context["database"] == "mongodb"
        assert context["use_postgresql"] is False
        assert context["use_mongodb"] is True
        assert context["use_sqlite"] is False
        assert context["use_database"] is True

    def test_sqlite_database_flags(self) -> None:
        """Test SQLite sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.SQLITE,
        )
        context = config.to_cookiecutter_context()

        assert context["database"] == "sqlite"
        assert context["use_postgresql"] is False
        assert context["use_mongodb"] is False
        assert context["use_sqlite"] is True
        assert context["use_database"] is True

    def test_no_database_flags(self) -> None:
        """Test no database sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.NONE,
            logfire_features=LogfireFeatures(database=False),  # Must disable logfire DB
        )
        context = config.to_cookiecutter_context()

        assert context["database"] == "none"
        assert context["use_postgresql"] is False
        assert context["use_mongodb"] is False
        assert context["use_sqlite"] is False
        assert context["use_database"] is False

    def test_jwt_auth_flags(self) -> None:
        """Test JWT auth sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            auth=AuthType.JWT,
        )
        context = config.to_cookiecutter_context()

        assert context["auth"] == "jwt"
        assert context["use_jwt"] is True
        assert context["use_api_key"] is False
        assert context["use_auth"] is True

    def test_api_key_auth_flags(self) -> None:
        """Test API key auth sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            auth=AuthType.API_KEY,
        )
        context = config.to_cookiecutter_context()

        assert context["auth"] == "api_key"
        assert context["use_jwt"] is False
        assert context["use_api_key"] is True
        assert context["use_auth"] is True

    def test_both_auth_flags(self) -> None:
        """Test both auth sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            auth=AuthType.BOTH,
        )
        context = config.to_cookiecutter_context()

        assert context["auth"] == "both"
        assert context["use_jwt"] is True
        assert context["use_api_key"] is True
        assert context["use_auth"] is True

    def test_no_auth_flags(self) -> None:
        """Test no auth sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            auth=AuthType.NONE,
        )
        context = config.to_cookiecutter_context()

        assert context["auth"] == "none"
        assert context["use_jwt"] is False
        assert context["use_api_key"] is False
        assert context["use_auth"] is False

    def test_celery_background_task_flags(self) -> None:
        """Test Celery sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,  # Required for Celery
        )
        context = config.to_cookiecutter_context()

        assert context["background_tasks"] == "celery"
        assert context["use_celery"] is True
        assert context["use_taskiq"] is False
        assert context["use_arq"] is False

    def test_taskiq_background_task_flags(self) -> None:
        """Test Taskiq sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            background_tasks=BackgroundTaskType.TASKIQ,
            enable_redis=True,  # Required for Taskiq
        )
        context = config.to_cookiecutter_context()

        assert context["background_tasks"] == "taskiq"
        assert context["use_celery"] is False
        assert context["use_taskiq"] is True
        assert context["use_arq"] is False

    def test_arq_background_task_flags(self) -> None:
        """Test ARQ sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            background_tasks=BackgroundTaskType.ARQ,
            enable_redis=True,  # Required for ARQ
        )
        context = config.to_cookiecutter_context()

        assert context["background_tasks"] == "arq"
        assert context["use_celery"] is False
        assert context["use_taskiq"] is False
        assert context["use_arq"] is True

    def test_github_ci_flags(self) -> None:
        """Test GitHub CI sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            ci_type=CIType.GITHUB,
        )
        context = config.to_cookiecutter_context()

        assert context["ci_type"] == "github"
        assert context["use_github_actions"] is True
        assert context["use_gitlab_ci"] is False

    def test_gitlab_ci_flags(self) -> None:
        """Test GitLab CI sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            ci_type=CIType.GITLAB,
        )
        context = config.to_cookiecutter_context()

        assert context["ci_type"] == "gitlab"
        assert context["use_github_actions"] is False
        assert context["use_gitlab_ci"] is True

    def test_traefik_included_flags(self) -> None:
        """Test Traefik included sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            reverse_proxy=ReverseProxyType.TRAEFIK_INCLUDED,
        )
        context = config.to_cookiecutter_context()

        assert context["reverse_proxy"] == "traefik_included"
        assert context["include_traefik_service"] is True
        assert context["include_traefik_labels"] is True
        assert context["use_traefik"] is True
        assert context["include_nginx_service"] is False
        assert context["include_nginx_config"] is False
        assert context["use_nginx"] is False

    def test_traefik_external_flags(self) -> None:
        """Test Traefik external sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            reverse_proxy=ReverseProxyType.TRAEFIK_EXTERNAL,
        )
        context = config.to_cookiecutter_context()

        assert context["reverse_proxy"] == "traefik_external"
        assert context["include_traefik_service"] is False
        assert context["include_traefik_labels"] is True
        assert context["use_traefik"] is True
        assert context["include_nginx_service"] is False
        assert context["include_nginx_config"] is False
        assert context["use_nginx"] is False

    def test_nginx_included_flags(self) -> None:
        """Test Nginx included sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            reverse_proxy=ReverseProxyType.NGINX_INCLUDED,
        )
        context = config.to_cookiecutter_context()

        assert context["reverse_proxy"] == "nginx_included"
        assert context["include_traefik_service"] is False
        assert context["include_traefik_labels"] is False
        assert context["use_traefik"] is False
        assert context["include_nginx_service"] is True
        assert context["include_nginx_config"] is True
        assert context["use_nginx"] is True

    def test_nginx_external_flags(self) -> None:
        """Test Nginx external sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            reverse_proxy=ReverseProxyType.NGINX_EXTERNAL,
        )
        context = config.to_cookiecutter_context()

        assert context["reverse_proxy"] == "nginx_external"
        assert context["include_traefik_service"] is False
        assert context["include_traefik_labels"] is False
        assert context["use_traefik"] is False
        assert context["include_nginx_service"] is False
        assert context["include_nginx_config"] is True
        assert context["use_nginx"] is True

    def test_no_reverse_proxy_flags(self) -> None:
        """Test no reverse proxy sets correct flags."""
        config = ProjectConfig(
            project_name="test",
            reverse_proxy=ReverseProxyType.NONE,
        )
        context = config.to_cookiecutter_context()

        assert context["reverse_proxy"] == "none"
        assert context["include_traefik_service"] is False
        assert context["include_traefik_labels"] is False
        assert context["use_traefik"] is False
        assert context["include_nginx_service"] is False
        assert context["include_nginx_config"] is False
        assert context["use_nginx"] is False

    def test_logfire_features_in_context(self) -> None:
        """Test Logfire features are correctly mapped."""
        config = ProjectConfig(
            project_name="test",
            enable_logfire=True,
            enable_redis=True,  # Required for logfire redis feature
            logfire_features=LogfireFeatures(
                fastapi=True,
                database=False,
                redis=True,
                celery=False,
                httpx=True,
            ),
        )
        context = config.to_cookiecutter_context()

        assert context["enable_logfire"] is True
        assert context["logfire_fastapi"] is True
        assert context["logfire_database"] is False
        assert context["logfire_redis"] is True
        assert context["logfire_celery"] is False
        assert context["logfire_httpx"] is True


class TestOptionCombinationValidation:
    """Tests for invalid option combination validation."""

    def test_admin_panel_requires_database(self) -> None:
        """Test that admin panel cannot be enabled without a database."""
        with pytest.raises(ValidationError, match="Admin panel requires a database"):
            ProjectConfig(
                project_name="test",
                database=DatabaseType.NONE,
                enable_admin_panel=True,
            )

    def test_admin_panel_not_supported_with_mongodb(self) -> None:
        """Test that admin panel (SQLAdmin) does not support MongoDB."""
        with pytest.raises(
            ValidationError,
            match="Admin panel \\(SQLAdmin\\) requires PostgreSQL, SQLite, or MS SQL Server",
        ):
            ProjectConfig(
                project_name="test",
                database=DatabaseType.MONGODB,
                enable_admin_panel=True,
            )

    def test_sqlmodel_requires_sql_database(self) -> None:
        """Test that SQLModel requires PostgreSQL, SQLite, or MS SQL Server database."""
        with pytest.raises(
            ValidationError,
            match="SQLModel requires PostgreSQL, SQLite, or MS SQL Server database",
        ):
            ProjectConfig(
                project_name="test",
                database=DatabaseType.MONGODB,
                orm_type=OrmType.SQLMODEL,
            )

    def test_sqlmodel_not_supported_with_no_database(self) -> None:
        """Test that SQLModel cannot be used without a database."""
        with pytest.raises(
            ValidationError,
            match="SQLModel requires PostgreSQL, SQLite, or MS SQL Server database",
        ):
            ProjectConfig(
                project_name="test",
                database=DatabaseType.NONE,
                orm_type=OrmType.SQLMODEL,
            )

    def test_sqlmodel_with_postgresql_is_valid(self) -> None:
        """Test that SQLModel with PostgreSQL is valid."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            orm_type=OrmType.SQLMODEL,
        )
        assert config.use_sqlmodel is True
        assert config.use_sqlalchemy is False

    def test_sqlmodel_with_sqlite_is_valid(self) -> None:
        """Test that SQLModel with SQLite is valid."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.SQLITE,
            orm_type=OrmType.SQLMODEL,
        )
        assert config.use_sqlmodel is True
        assert config.use_sqlalchemy is False

    def test_caching_requires_redis(self) -> None:
        """Test that caching requires Redis to be enabled."""
        with pytest.raises(ValidationError, match="Caching requires Redis to be enabled"):
            ProjectConfig(
                project_name="test",
                enable_caching=True,
                enable_redis=False,
            )

    def test_session_management_requires_database(self) -> None:
        """Test that session management requires a database."""
        with pytest.raises(ValidationError, match="Session management requires a database"):
            ProjectConfig(
                project_name="test",
                database=DatabaseType.NONE,
                enable_session_management=True,
            )

    def test_conversation_persistence_requires_database(self) -> None:
        """Test that conversation persistence requires a database."""
        with pytest.raises(ValidationError, match="Conversation persistence requires a database"):
            ProjectConfig(
                project_name="test",
                database=DatabaseType.NONE,
                enable_conversation_persistence=True,
            )

    def test_admin_panel_with_postgresql_is_valid(self) -> None:
        """Test that admin panel with PostgreSQL is valid."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            enable_admin_panel=True,
        )
        assert config.enable_admin_panel is True
        assert config.database == DatabaseType.POSTGRESQL

    def test_admin_panel_with_sqlite_is_valid(self) -> None:
        """Test that admin panel with SQLite is valid."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.SQLITE,
            enable_admin_panel=True,
        )
        assert config.enable_admin_panel is True
        assert config.database == DatabaseType.SQLITE

    def test_caching_with_redis_is_valid(self) -> None:
        """Test that caching with Redis enabled is valid."""
        config = ProjectConfig(
            project_name="test",
            enable_caching=True,
            enable_redis=True,
        )
        assert config.enable_caching is True
        assert config.enable_redis is True

    def test_session_management_with_database_is_valid(self) -> None:
        """Test that session management with a database is valid."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            enable_session_management=True,
        )
        assert config.enable_session_management is True

    def test_conversation_persistence_with_database_is_valid(self) -> None:
        """Test that conversation persistence with a database is valid."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            enable_conversation_persistence=True,
        )
        assert config.enable_conversation_persistence is True

    def test_openrouter_with_langchain_raises_validation_error(self) -> None:
        """Test that OpenRouter + LangChain combination is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig(
                project_name="test",
                enable_ai_agent=True,
                llm_provider=LLMProviderType.OPENROUTER,
                ai_framework=AIFrameworkType.LANGCHAIN,
            )
        assert "OpenRouter is not supported with LangChain" in str(exc_info.value)

    def test_openrouter_with_langgraph_raises_validation_error(self) -> None:
        """Test that OpenRouter + LangGraph combination is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig(
                project_name="test",
                enable_ai_agent=True,
                llm_provider=LLMProviderType.OPENROUTER,
                ai_framework=AIFrameworkType.LANGGRAPH,
            )
        assert "OpenRouter is not supported with LangGraph" in str(exc_info.value)

    def test_openrouter_with_crewai_raises_validation_error(self) -> None:
        """Test that OpenRouter + CrewAI combination is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig(
                project_name="test",
                enable_ai_agent=True,
                llm_provider=LLMProviderType.OPENROUTER,
                ai_framework=AIFrameworkType.CREWAI,
            )
        assert "OpenRouter is not supported with CrewAI" in str(exc_info.value)

    def test_openrouter_with_pydanticai_is_valid(self) -> None:
        """Test that OpenRouter + PydanticAI combination is accepted."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            llm_provider=LLMProviderType.OPENROUTER,
            ai_framework=AIFrameworkType.PYDANTIC_AI,
        )
        assert config.llm_provider == LLMProviderType.OPENROUTER
        assert config.ai_framework == AIFrameworkType.PYDANTIC_AI

    def test_crewai_framework_context_flags(self) -> None:
        """Test that CrewAI framework sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            ai_framework=AIFrameworkType.CREWAI,
        )
        context = config.to_cookiecutter_context()

        assert context["use_crewai"] is True
        assert context["use_pydantic_ai"] is False
        assert context["use_langchain"] is False
        assert context["use_langgraph"] is False

    def test_openrouter_with_deepagents_raises_validation_error(self) -> None:
        """Test that OpenRouter + DeepAgents combination is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig(
                project_name="test",
                enable_ai_agent=True,
                llm_provider=LLMProviderType.OPENROUTER,
                ai_framework=AIFrameworkType.DEEPAGENTS,
            )
        assert "DeepAgents does not support OpenRouter" in str(exc_info.value)

    def test_deepagents_with_openai_is_valid(self) -> None:
        """Test that DeepAgents + OpenAI combination is accepted."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            llm_provider=LLMProviderType.OPENAI,
            ai_framework=AIFrameworkType.DEEPAGENTS,
        )
        assert config.ai_framework == AIFrameworkType.DEEPAGENTS
        assert config.llm_provider == LLMProviderType.OPENAI

    def test_deepagents_with_anthropic_is_valid(self) -> None:
        """Test that DeepAgents + Anthropic combination is accepted."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            llm_provider=LLMProviderType.ANTHROPIC,
            ai_framework=AIFrameworkType.DEEPAGENTS,
        )
        assert config.ai_framework == AIFrameworkType.DEEPAGENTS
        assert config.llm_provider == LLMProviderType.ANTHROPIC

    def test_deepagents_framework_context_flags(self) -> None:
        """Test that DeepAgents framework sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            ai_framework=AIFrameworkType.DEEPAGENTS,
        )
        context = config.to_cookiecutter_context()

        assert context["use_deepagents"] is True
        assert context["use_pydantic_ai"] is False
        assert context["use_langchain"] is False
        assert context["use_langgraph"] is False
        assert context["use_crewai"] is False


class TestEmailValidation:
    """Tests for author_email validation."""

    def test_valid_email_accepted(self) -> None:
        """Test valid email addresses are accepted."""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user@subdomain.example.com",
            "user123@example.co.uk",
        ]
        for email in valid_emails:
            config = ProjectConfig(project_name="test", author_email=email)
            assert config.author_email == email

    def test_invalid_email_raises_error(self) -> None:
        """Test invalid email addresses raise ValidationError."""
        invalid_emails = [
            "not-an-email",
            "missing@tld",
            "@no-local-part.com",
            "spaces in@email.com",
            "",
        ]
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                ProjectConfig(project_name="test", author_email=email)


class TestRateLimitConfig:
    """Tests for rate limit configuration."""

    def test_default_rate_limit_values(self) -> None:
        """Test default rate limit configuration values."""
        config = ProjectConfig(project_name="test")
        assert config.rate_limit_requests == 100
        assert config.rate_limit_period == 60
        assert config.rate_limit_storage == RateLimitStorageType.MEMORY

    def test_custom_rate_limit_values(self) -> None:
        """Test custom rate limit configuration values."""
        config = ProjectConfig(
            project_name="test",
            enable_rate_limiting=True,
            rate_limit_requests=50,
            rate_limit_period=30,
            rate_limit_storage=RateLimitStorageType.MEMORY,
        )
        assert config.rate_limit_requests == 50
        assert config.rate_limit_period == 30
        assert config.rate_limit_storage == RateLimitStorageType.MEMORY

    def test_rate_limit_memory_storage_context_flags(self) -> None:
        """Test rate limit memory storage sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_rate_limiting=True,
            rate_limit_storage=RateLimitStorageType.MEMORY,
        )
        context = config.to_cookiecutter_context()

        assert context["rate_limit_storage"] == "memory"
        assert context["rate_limit_storage_memory"] is True
        assert context["rate_limit_storage_redis"] is False

    def test_rate_limit_redis_storage_context_flags(self) -> None:
        """Test rate limit Redis storage sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_rate_limiting=True,
            enable_redis=True,
            rate_limit_storage=RateLimitStorageType.REDIS,
        )
        context = config.to_cookiecutter_context()

        assert context["rate_limit_storage"] == "redis"
        assert context["rate_limit_storage_memory"] is False
        assert context["rate_limit_storage_redis"] is True

    def test_rate_limit_redis_storage_requires_redis(self) -> None:
        """Test that Redis storage for rate limiting requires Redis to be enabled."""
        with pytest.raises(
            ValidationError, match="Rate limiting with Redis storage requires Redis to be enabled"
        ):
            ProjectConfig(
                project_name="test",
                enable_rate_limiting=True,
                enable_redis=False,
                rate_limit_storage=RateLimitStorageType.REDIS,
            )

    def test_rate_limit_redis_storage_with_redis_is_valid(self) -> None:
        """Test that Redis storage with Redis enabled is valid."""
        config = ProjectConfig(
            project_name="test",
            enable_rate_limiting=True,
            enable_redis=True,
            rate_limit_storage=RateLimitStorageType.REDIS,
        )
        assert config.rate_limit_storage == RateLimitStorageType.REDIS
        assert config.enable_redis is True


class TestNewDependencyValidations:
    """Tests for new dependency validation rules."""

    def test_websocket_jwt_auth_requires_jwt_auth(self) -> None:
        """Test that WebSocket JWT auth requires main JWT auth to be enabled."""
        with pytest.raises(ValidationError, match="WebSocket JWT authentication requires JWT auth"):
            ProjectConfig(
                project_name="test",
                auth=AuthType.API_KEY,
                enable_ai_agent=True,
                websocket_auth=WebSocketAuthType.JWT,
            )

    def test_websocket_jwt_auth_with_jwt_is_valid(self) -> None:
        """Test that WebSocket JWT auth with main JWT auth is valid."""
        config = ProjectConfig(
            project_name="test",
            auth=AuthType.JWT,
            enable_ai_agent=True,
            websocket_auth=WebSocketAuthType.JWT,
        )
        assert config.websocket_auth == WebSocketAuthType.JWT

    def test_websocket_jwt_auth_with_both_auth_is_valid(self) -> None:
        """Test that WebSocket JWT auth with both auth types is valid."""
        config = ProjectConfig(
            project_name="test",
            auth=AuthType.BOTH,
            enable_ai_agent=True,
            websocket_auth=WebSocketAuthType.JWT,
        )
        assert config.websocket_auth == WebSocketAuthType.JWT

    def test_websocket_api_key_auth_requires_api_key_auth(self) -> None:
        """Test that WebSocket API key auth requires main API key auth to be enabled."""
        with pytest.raises(
            ValidationError, match="WebSocket API key authentication requires API key auth"
        ):
            ProjectConfig(
                project_name="test",
                auth=AuthType.JWT,
                enable_ai_agent=True,
                websocket_auth=WebSocketAuthType.API_KEY,
            )

    def test_websocket_api_key_auth_with_api_key_is_valid(self) -> None:
        """Test that WebSocket API key auth with main API key auth is valid."""
        config = ProjectConfig(
            project_name="test",
            auth=AuthType.API_KEY,
            enable_ai_agent=True,
            websocket_auth=WebSocketAuthType.API_KEY,
        )
        assert config.websocket_auth == WebSocketAuthType.API_KEY

    def test_admin_require_auth_requires_jwt(self) -> None:
        """Test that admin panel with authentication requires JWT auth."""
        with pytest.raises(ValidationError, match="Admin panel authentication requires JWT auth"):
            ProjectConfig(
                project_name="test",
                database=DatabaseType.POSTGRESQL,
                auth=AuthType.API_KEY,
                enable_admin_panel=True,
                admin_require_auth=True,
            )

    def test_admin_require_auth_with_jwt_is_valid(self) -> None:
        """Test that admin panel with authentication and JWT is valid."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            enable_admin_panel=True,
            admin_require_auth=True,
        )
        assert config.enable_admin_panel is True
        assert config.admin_require_auth is True

    def test_admin_without_auth_works_without_jwt(self) -> None:
        """Test that admin panel without authentication works without JWT."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.API_KEY,
            enable_admin_panel=True,
            admin_require_auth=False,
        )
        assert config.enable_admin_panel is True
        assert config.admin_require_auth is False

    def test_admin_with_no_auth_at_all_works(self) -> None:
        """Test that admin panel without auth works when no auth is configured."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.NONE,
            enable_admin_panel=True,
            admin_require_auth=False,
        )
        assert config.enable_admin_panel is True
        assert config.admin_require_auth is False

    def test_conversation_persistence_requires_ai_agent(self) -> None:
        """Test that conversation persistence requires AI agent to be enabled."""
        with pytest.raises(ValidationError, match="Conversation persistence requires AI agent"):
            ProjectConfig(
                project_name="test",
                database=DatabaseType.POSTGRESQL,
                enable_ai_agent=False,
                enable_conversation_persistence=True,
            )

    def test_conversation_persistence_with_ai_agent_is_valid(self) -> None:
        """Test that conversation persistence with AI agent is valid."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            enable_ai_agent=True,
            enable_conversation_persistence=True,
        )
        assert config.enable_conversation_persistence is True
        assert config.enable_ai_agent is True

    def test_admin_panel_requires_sqlalchemy(self) -> None:
        """Test that admin panel requires SQLAlchemy (not SQLModel)."""
        with pytest.raises(ValidationError, match="Admin panel.*requires SQLAlchemy ORM"):
            ProjectConfig(
                project_name="test",
                database=DatabaseType.POSTGRESQL,
                orm_type=OrmType.SQLMODEL,
                enable_admin_panel=True,
            )

    def test_admin_panel_with_sqlalchemy_is_valid(self) -> None:
        """Test that admin panel with SQLAlchemy is valid."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            orm_type=OrmType.SQLALCHEMY,
            enable_admin_panel=True,
        )
        assert config.enable_admin_panel is True
        assert config.use_sqlalchemy is True

    def test_session_management_requires_jwt(self) -> None:
        """Test that session management requires JWT auth to be enabled."""
        with pytest.raises(ValidationError, match="Session management requires JWT auth"):
            ProjectConfig(
                project_name="test",
                database=DatabaseType.POSTGRESQL,
                auth=AuthType.API_KEY,
                enable_session_management=True,
            )

    def test_session_management_with_jwt_is_valid(self) -> None:
        """Test that session management with JWT auth is valid."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            enable_session_management=True,
        )
        assert config.enable_session_management is True

    def test_webhooks_requires_database(self) -> None:
        """Test that webhooks require a database to be enabled."""
        with pytest.raises(ValidationError, match="Webhooks require a database"):
            ProjectConfig(
                project_name="test",
                database=DatabaseType.NONE,
                enable_webhooks=True,
                logfire_features=LogfireFeatures(database=False),  # Disable logfire DB
            )

    def test_webhooks_with_database_is_valid(self) -> None:
        """Test that webhooks with a database is valid."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            enable_webhooks=True,
        )
        assert config.enable_webhooks is True

    def test_logfire_database_requires_database(self) -> None:
        """Test that Logfire database instrumentation requires a database."""
        with pytest.raises(
            ValidationError, match="Logfire database instrumentation requires a database"
        ):
            ProjectConfig(
                project_name="test",
                database=DatabaseType.NONE,
                enable_logfire=True,
                logfire_features=LogfireFeatures(database=True),
            )

    def test_logfire_database_with_database_is_valid(self) -> None:
        """Test that Logfire database instrumentation with database is valid."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            enable_logfire=True,
            logfire_features=LogfireFeatures(database=True),
        )
        assert config.logfire_features.database is True

    def test_logfire_redis_requires_redis(self) -> None:
        """Test that Logfire Redis instrumentation requires Redis to be enabled."""
        with pytest.raises(ValidationError, match="Logfire Redis instrumentation requires Redis"):
            ProjectConfig(
                project_name="test",
                enable_logfire=True,
                enable_redis=False,
                logfire_features=LogfireFeatures(redis=True),
            )

    def test_logfire_redis_with_redis_is_valid(self) -> None:
        """Test that Logfire Redis instrumentation with Redis is valid."""
        config = ProjectConfig(
            project_name="test",
            enable_logfire=True,
            enable_redis=True,
            logfire_features=LogfireFeatures(redis=True),
        )
        assert config.logfire_features.redis is True

    def test_logfire_celery_requires_celery(self) -> None:
        """Test that Logfire Celery instrumentation requires Celery as background task system."""
        with pytest.raises(ValidationError, match="Logfire Celery instrumentation requires Celery"):
            ProjectConfig(
                project_name="test",
                enable_logfire=True,
                enable_redis=True,  # Required for Taskiq
                background_tasks=BackgroundTaskType.TASKIQ,
                logfire_features=LogfireFeatures(celery=True),
            )

    def test_logfire_celery_with_celery_is_valid(self) -> None:
        """Test that Logfire Celery instrumentation with Celery is valid."""
        config = ProjectConfig(
            project_name="test",
            enable_logfire=True,
            enable_redis=True,  # Required for Celery
            background_tasks=BackgroundTaskType.CELERY,
            logfire_features=LogfireFeatures(celery=True),
        )
        assert config.logfire_features.celery is True

    def test_celery_requires_redis(self) -> None:
        """Test that Celery requires Redis to be enabled."""
        with pytest.raises(ValidationError, match="Celery requires Redis"):
            ProjectConfig(
                project_name="test",
                background_tasks=BackgroundTaskType.CELERY,
                enable_redis=False,
            )

    def test_celery_with_redis_is_valid(self) -> None:
        """Test that Celery with Redis is valid."""
        config = ProjectConfig(
            project_name="test",
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
        )
        assert config.background_tasks == BackgroundTaskType.CELERY

    def test_taskiq_requires_redis(self) -> None:
        """Test that Taskiq requires Redis to be enabled."""
        with pytest.raises(ValidationError, match="Taskiq requires Redis"):
            ProjectConfig(
                project_name="test",
                background_tasks=BackgroundTaskType.TASKIQ,
                enable_redis=False,
            )

    def test_arq_requires_redis(self) -> None:
        """Test that ARQ requires Redis to be enabled."""
        with pytest.raises(ValidationError, match="Arq requires Redis"):
            ProjectConfig(
                project_name="test",
                background_tasks=BackgroundTaskType.ARQ,
                enable_redis=False,
            )
