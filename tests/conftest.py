"""Shared fixtures for tests."""

from pathlib import Path
from typing import Any

import pytest

from fastapi_gen.config import (
    AuthType,
    BackgroundTaskType,
    CIType,
    DatabaseType,
    FrontendType,
    LogfireFeatures,
    OAuthProvider,
    ProjectConfig,
    RAGFeatures,
)


@pytest.fixture
def minimal_config() -> ProjectConfig:
    """Minimal project configuration."""
    return ProjectConfig(
        project_name="test_project",
        database=DatabaseType.NONE,
        auth=AuthType.NONE,
        enable_logfire=False,
        enable_docker=False,
        ci_type=CIType.NONE,
    )


@pytest.fixture
def full_config() -> ProjectConfig:
    """Full project configuration with all features enabled."""
    return ProjectConfig(
        project_name="full_project",
        project_description="A fully featured project",
        author_name="Test Author",
        author_email="test@example.com",
        database=DatabaseType.POSTGRESQL,
        auth=AuthType.JWT,
        oauth_provider=OAuthProvider.GOOGLE,
        enable_logfire=True,
        logfire_features=LogfireFeatures(
            fastapi=True,
            database=True,
            redis=True,
            celery=True,
            httpx=True,
        ),
        background_tasks=BackgroundTaskType.CELERY,
        enable_redis=True,
        enable_caching=True,
        enable_rate_limiting=True,
        enable_pagination=True,
        enable_sentry=True,
        enable_prometheus=True,
        enable_admin_panel=True,
        enable_websockets=True,
        enable_file_storage=True,
        enable_ai_agent=True,
        enable_webhooks=True,
        enable_cors=True,
        enable_orjson=True,
        enable_pytest=True,
        enable_precommit=True,
        enable_makefile=True,
        enable_docker=True,
        ci_type=CIType.GITHUB,
        enable_kubernetes=True,
        frontend=FrontendType.NEXTJS,
        enable_i18n=True,
    )


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Temporary directory for generated projects."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_questionary_responses() -> dict[str, Any]:
    """Standard mock responses for questionary prompts."""
    return {
        "project_name": "test_project",
        "project_description": "Test description",
        "author_name": "Test Author",
        "author_email": "test@example.com",
        "database": DatabaseType.POSTGRESQL,
        "auth": AuthType.JWT,
        "enable_logfire": True,
        "logfire_features": ["fastapi", "database"],
        "background_tasks": BackgroundTaskType.NONE,
        "integrations": ["pagination", "cors", "orjson"],
        "dev_tools": ["pytest", "precommit", "makefile", "docker"],
        "ci_type": CIType.GITHUB,
        "confirm": True,
    }


@pytest.fixture
def rag_base_config() -> ProjectConfig:
    """Base RAG project configuration with required dependencies.

    This fixture provides a minimal valid RAG configuration that can be
    extended in individual tests for specific RAG scenarios.
    """
    return ProjectConfig(
        project_name="rag_project",
        database=DatabaseType.POSTGRESQL,
        auth=AuthType.JWT,
        enable_ai_agent=True,
        rag_features=RAGFeatures(enable_rag=True),
        background_tasks=BackgroundTaskType.CELERY,
        enable_redis=True,
        enable_docker=True,
    )


@pytest.fixture
def rag_with_celery_config(rag_base_config: ProjectConfig) -> ProjectConfig:
    """RAG configuration with Celery background tasks."""
    return rag_base_config


@pytest.fixture
def rag_with_taskiq_config() -> ProjectConfig:
    """RAG configuration with Taskiq background tasks."""
    return ProjectConfig(
        project_name="rag_taskiq_project",
        database=DatabaseType.POSTGRESQL,
        auth=AuthType.JWT,
        enable_ai_agent=True,
        rag_features=RAGFeatures(enable_rag=True),
        background_tasks=BackgroundTaskType.TASKIQ,
        enable_redis=True,
        enable_docker=True,
    )


@pytest.fixture
def rag_with_arq_config() -> ProjectConfig:
    """RAG configuration with ARQ background tasks."""
    return ProjectConfig(
        project_name="rag_arq_project",
        database=DatabaseType.POSTGRESQL,
        auth=AuthType.JWT,
        enable_ai_agent=True,
        rag_features=RAGFeatures(enable_rag=True),
        background_tasks=BackgroundTaskType.ARQ,
        enable_redis=True,
        enable_docker=True,
    )
