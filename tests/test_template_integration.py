"""Integration tests for generated template code quality.

These tests generate actual projects and run linting/type checking on them.
They are slower but ensure the template produces valid, well-formatted code.
"""

import subprocess
from pathlib import Path

import pytest

from fastapi_gen.config import (
    AIFrameworkType,
    BackgroundTaskType,
    CIType,
    DatabaseType,
    FrontendType,
    LLMProviderType,
    LogfireFeatures,
    OAuthProvider,
    OrmType,
    ProjectConfig,
    RAGFeatures,
    VectorStoreType,
)
from fastapi_gen.generator import generate_project


@pytest.fixture
def generated_project_minimal(tmp_path: Path) -> Path:
    """Generate a minimal project for testing."""
    config = ProjectConfig(
        project_name="test_minimal",
        database=DatabaseType.SQLITE,
        enable_logfire=False,
        enable_docker=False,
        ci_type=CIType.NONE,
        background_tasks=BackgroundTaskType.NONE,
    )
    return generate_project(config, tmp_path)


@pytest.fixture
def generated_project_full(tmp_path: Path) -> Path:
    """Generate a full-featured project for testing."""
    config = ProjectConfig(
        project_name="test_full",
        project_description="A fully featured test project",
        author_name="Test Author",
        author_email="test@example.com",
        database=DatabaseType.POSTGRESQL,
        oauth_provider=OAuthProvider.GOOGLE,
        enable_session_management=True,
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
        enable_webhooks=True,
        enable_cors=True,
        enable_pytest=True,
        enable_precommit=True,
        enable_makefile=True,
        enable_docker=True,
        ci_type=CIType.GITHUB,
        enable_kubernetes=True,
        frontend=FrontendType.NEXTJS,
    )
    return generate_project(config, tmp_path)


class TestGeneratedTemplateRuff:
    """Test that generated code passes ruff linting."""

    @pytest.mark.slow
    def test_minimal_project_passes_ruff(self, generated_project_minimal: Path) -> None:
        """Test minimal project passes ruff check."""
        backend_path = generated_project_minimal / "backend"
        result = subprocess.run(
            ["uvx", "ruff", "check", str(backend_path)],
            capture_output=True,
            text=True,
            cwd=backend_path,
        )
        assert result.returncode == 0, f"Ruff failed:\n{result.stdout}\n{result.stderr}"

    @pytest.mark.slow
    def test_full_project_passes_ruff(self, generated_project_full: Path) -> None:
        """Test full project passes ruff check."""
        backend_path = generated_project_full / "backend"
        result = subprocess.run(
            ["uvx", "ruff", "check", str(backend_path)],
            capture_output=True,
            text=True,
            cwd=backend_path,
        )
        assert result.returncode == 0, f"Ruff failed:\n{result.stdout}\n{result.stderr}"


class TestGeneratedTemplateTy:
    """Test that generated code passes ty type checking."""

    @pytest.mark.slow
    def test_minimal_project_passes_ty(self, generated_project_minimal: Path) -> None:
        """Test minimal project passes ty check."""
        backend_path = generated_project_minimal / "backend"
        result = subprocess.run(
            ["uv", "run", "ty", "check"],
            capture_output=True,
            text=True,
            cwd=backend_path,
        )
        assert result.returncode == 0, f"ty failed:\n{result.stdout}\n{result.stderr}"

    @pytest.mark.slow
    def test_full_project_passes_ty(self, generated_project_full: Path) -> None:
        """Test full project passes ty check."""
        backend_path = generated_project_full / "backend"
        result = subprocess.run(
            ["uv", "run", "ty", "check"],
            capture_output=True,
            text=True,
            cwd=backend_path,
        )
        assert result.returncode == 0, f"ty failed:\n{result.stdout}\n{result.stderr}"


class TestGeneratedTemplateAgentsFolder:
    """Test that agents folder is always created since AI agent is always enabled."""

    @pytest.mark.slow
    def test_agents_folder_created_in_minimal(self, generated_project_minimal: Path) -> None:
        """Test that agents folder exists in minimal project (AI agent is always enabled)."""
        agents_path = generated_project_minimal / "backend" / "app" / "agents"
        assert agents_path.exists(), "agents/ folder should exist since AI agent is always enabled"

    @pytest.mark.slow
    def test_agents_folder_created_when_enabled(self, generated_project_full: Path) -> None:
        """Test that agents folder exists when AI agent is enabled."""
        agents_path = generated_project_full / "backend" / "app" / "agents"
        assert agents_path.exists(), "agents/ folder should exist when AI is enabled"
        assert (agents_path / "__init__.py").exists()
        assert (agents_path / "assistant.py").exists()


class TestGeneratedTemplateSyntax:
    """Test that generated Python files have valid syntax."""

    @pytest.mark.slow
    def test_minimal_project_valid_python_syntax(self, generated_project_minimal: Path) -> None:
        """Test all Python files in minimal project have valid syntax."""
        backend_path = generated_project_minimal / "backend"
        python_files = list(backend_path.rglob("*.py"))

        for py_file in python_files:
            result = subprocess.run(
                ["python3", "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Syntax error in {py_file}:\n{result.stderr}"

    @pytest.mark.slow
    def test_full_project_valid_python_syntax(self, generated_project_full: Path) -> None:
        """Test all Python files in full project have valid syntax."""
        backend_path = generated_project_full / "backend"
        python_files = list(backend_path.rglob("*.py"))

        for py_file in python_files:
            result = subprocess.run(
                ["python3", "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Syntax error in {py_file}:\n{result.stderr}"


# ---------------------------------------------------------------------------
# Configuration matrix
# ---------------------------------------------------------------------------
#
# These tests generate projects across the meaningful axes of the template
# (AI framework, database, ORM, integrations) and run ruff + ty against each.
# Without this matrix, framework-specific bugs (e.g. an undefined `file_ids`
# in the DeepAgents WebSocket handler) only surface when a user picks that
# combination. Keep the list small but representative — one entry per branch
# of significant Jinja conditionals.

MATRIX_CONFIGS: dict[str, dict] = {
    # --- AI frameworks ----------------------------------------------------
    "langchain_pg_celery": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.LANGCHAIN,
        enable_redis=True,
        background_tasks=BackgroundTaskType.CELERY,
        enable_langsmith=True,
    ),
    "langgraph_pg": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.LANGGRAPH,
        enable_redis=True,
        background_tasks=BackgroundTaskType.NONE,
    ),
    # CrewAI 1.13.x pins pydantic<2.12 + opentelemetry<1.35 which conflicts with
    # both pydantic 2.12+ and logfire 4.30+. Until CrewAI catches up, the matrix
    # test runs the framework in isolation (no logfire, pinned older pydantic).
    # See ProjectConfig validator that blocks crewai+logfire.
    # NOTE: we only run ruff/syntax checks on this config — full ty + pip resolve
    # against Python 3.14 fails because pydantic<2.12 needs older pyo3 (no 3.14
    # support yet). Track upstream: crewai/crewai#3xxx
    "crewai_pg": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.CREWAI,
        enable_redis=True,
        background_tasks=BackgroundTaskType.NONE,
        enable_logfire=False,
    ),
    "deepagents_pg": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.DEEPAGENTS,
        enable_redis=True,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "deepagents_sqlite": dict(
        database=DatabaseType.SQLITE,
        ai_framework=AIFrameworkType.DEEPAGENTS,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "pydantic_deep_pg": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.PYDANTIC_DEEP,
        enable_redis=True,
        background_tasks=BackgroundTaskType.NONE,
    ),
    # --- LLM providers ----------------------------------------------------
    "openrouter": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        llm_provider=LLMProviderType.OPENROUTER,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "anthropic": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        llm_provider=LLMProviderType.ANTHROPIC,
        background_tasks=BackgroundTaskType.NONE,
    ),
    # --- Databases / ORM --------------------------------------------------
    "mongo": dict(
        database=DatabaseType.MONGODB,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "sqlmodel_pg": dict(
        database=DatabaseType.POSTGRESQL,
        orm_type=OrmType.SQLMODEL,
        background_tasks=BackgroundTaskType.NONE,
    ),
    # --- Optional integrations -------------------------------------------
    "channels_pg": dict(
        database=DatabaseType.POSTGRESQL,
        background_tasks=BackgroundTaskType.NONE,
        use_telegram=True,
        use_slack=True,
    ),
    # --- Charts / AntV maps -----------------------------------------------
    # Three separate entries because each AI framework generates a different
    "pydantic_ai_antv_charts": dict(
        database=DatabaseType.SQLITE,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        enable_logfire=False,
        enable_antv_charts=True,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "langchain_antv_charts": dict(
        database=DatabaseType.SQLITE,
        ai_framework=AIFrameworkType.LANGCHAIN,
        enable_logfire=False,
        enable_antv_charts=True,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "crewai_antv_charts": dict(
        database=DatabaseType.SQLITE,
        ai_framework=AIFrameworkType.CREWAI,
        enable_logfire=False,
        enable_antv_charts=True,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "pydantic_ai_charts": dict(
        database=DatabaseType.SQLITE,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        enable_logfire=False,
        enable_charts=True,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "pydantic_ai_code_execution": dict(
        database=DatabaseType.SQLITE,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        enable_logfire=False,
        enable_code_execution=True,
        enable_charts=True,
        enable_antv_charts=True,
        background_tasks=BackgroundTaskType.NONE,
    ),
    # SkillsToolset wiring: enable_skills attaches the toolset (no bundled
    # skills here, so it no-ops at runtime) — generated together with code
    # execution to confirm the two coexist and lint/type-check cleanly.
    "pydantic_ai_skills": dict(
        database=DatabaseType.SQLITE,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        enable_logfire=False,
        enable_skills=True,
        enable_code_execution=True,
        enable_charts=True,
        background_tasks=BackgroundTaskType.NONE,
    ),
    # Deep research: PG path (asyncpg TODO pool + persistence) with the frontend
    # panel, plus a sqlite path that exercises the in-memory TODO fallback.
    "pydantic_ai_deep_research_pg": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        enable_logfire=False,
        enable_deep_research=True,
        enable_charts=True,
        frontend=FrontendType.NEXTJS,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "pydantic_ai_deep_research_sqlite": dict(
        database=DatabaseType.SQLITE,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        enable_logfire=False,
        enable_deep_research=True,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "rag_pgvector": dict(
        database=DatabaseType.POSTGRESQL,
        background_tasks=BackgroundTaskType.NONE,
        rag_features=RAGFeatures(
            enable_rag=True,
            vector_store=VectorStoreType.PGVECTOR,
        ),
    ),
    "rag_qdrant_mongo": dict(
        database=DatabaseType.MONGODB,
        background_tasks=BackgroundTaskType.NONE,
        rag_features=RAGFeatures(
            enable_rag=True,
            vector_store=VectorStoreType.QDRANT,
        ),
    ),
    "frontend_oauth_pg": dict(
        database=DatabaseType.POSTGRESQL,
        background_tasks=BackgroundTaskType.NONE,
        frontend=FrontendType.NEXTJS,
        oauth_provider=OAuthProvider.GOOGLE,
    ),
}


@pytest.fixture(params=sorted(MATRIX_CONFIGS), scope="module")
def matrix_project(
    tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest
) -> Path:
    """Generate a project for a single matrix entry, shared across checks."""
    name: str = request.param
    out_dir = tmp_path_factory.mktemp(f"matrix_{name}")
    config = ProjectConfig(project_name=f"matrix_{name}", **MATRIX_CONFIGS[name])
    return generate_project(config, out_dir)


class TestGeneratedTemplateMatrix:
    """Regression matrix across AI frameworks, databases, and integrations.

    Locks in working configurations so framework-specific bugs (e.g. raw
    queries in a single agent path) cannot slip through CI.
    """

    @pytest.mark.slow
    def test_passes_ruff(self, matrix_project: Path) -> None:
        backend_path = matrix_project / "backend"
        result = subprocess.run(
            ["uvx", "ruff", "check", str(backend_path)],
            capture_output=True,
            text=True,
            cwd=backend_path,
        )
        assert result.returncode == 0, f"Ruff failed:\n{result.stdout}\n{result.stderr}"

    @pytest.mark.slow
    def test_passes_ty(self, matrix_project: Path, request: pytest.FixtureRequest) -> None:
        # CrewAI's pinned pydantic<2.12 forces a build of pydantic-core from source
        # which needs an older PyO3 that doesn't support Python 3.14 yet. Skip ty
        # (which depends on `uv sync`) — ruff still runs.
        if "crewai" in request.node.callspec.id:
            pytest.skip("CrewAI dependency tree broken on Python 3.14 (pydantic-core/pyo3)")

        backend_path = matrix_project / "backend"
        result = subprocess.run(
            ["uv", "run", "ty", "check"],
            capture_output=True,
            text=True,
            cwd=backend_path,
        )
        assert result.returncode == 0, f"ty failed:\n{result.stdout}\n{result.stderr}"


# ---------------------------------------------------------------------------
# AntV charts / Leaflet maps — generated-content checks
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def generated_project_antv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a pydantic_ai + sqlite + antv_charts project for content checks."""
    config = ProjectConfig(
        project_name="test_antv",
        database=DatabaseType.SQLITE,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        enable_logfire=False,
        enable_antv_charts=True,
        background_tasks=BackgroundTaskType.NONE,
    )
    return generate_project(config, tmp_path_factory.mktemp("antv"))


@pytest.fixture(scope="module")
def generated_project_antv_langchain(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a langchain + sqlite + antv_charts project for cache-code checks."""
    config = ProjectConfig(
        project_name="test_antv_lc",
        database=DatabaseType.SQLITE,
        ai_framework=AIFrameworkType.LANGCHAIN,
        enable_logfire=False,
        enable_antv_charts=True,
        background_tasks=BackgroundTaskType.NONE,
    )
    return generate_project(config, tmp_path_factory.mktemp("antv_lc"))


class TestGeneratedTemplateAntvCharts:
    """Verify that the AntV-charts / Leaflet-map feature renders correctly.

    These tests check specific implementation details that are easy to break
    via a bad Jinja merge: the MCP cache variables, the typed-marker signature,
    coordinate bounds validation, and the absence of removed dead code.
    """

    @pytest.mark.slow
    def test_map_tool_has_typed_marker_import(self, generated_project_antv: Path) -> None:
        """MapMarker must be defined in map_tool.py (typed schema for schema fidelity)."""
        map_tool = generated_project_antv / "backend" / "app" / "agents" / "tools" / "map_tool.py"
        assert map_tool.exists()
        content = map_tool.read_text()
        assert "class MapMarker" in content

    @pytest.mark.slow
    def test_map_tool_has_center_bounds_check(self, generated_project_antv: Path) -> None:
        """_validate_center must range-check coordinates, not just length."""
        content = (
            generated_project_antv / "backend" / "app" / "agents" / "tools" / "map_tool.py"
        ).read_text()
        assert "-90 <= lat <= 90" in content
        assert "-180 <= lng <= 180" in content

    @pytest.mark.slow
    def test_map_tool_no_parse_map_spec(self, generated_project_antv: Path) -> None:
        """parse_map_spec was removed (dead export); must not appear in generated code."""
        tools_dir = generated_project_antv / "backend" / "app" / "agents" / "tools"
        for f in tools_dir.rglob("*.py"):
            assert "parse_map_spec" not in f.read_text(), (
                f"{f.name} still references parse_map_spec"
            )

    @pytest.mark.slow
    def test_assistant_uses_typed_markers(self, generated_project_antv: Path) -> None:
        """The pydantic_ai assistant must use list[MapMarker] in its create_map wrapper."""
        assistant = generated_project_antv / "backend" / "app" / "agents" / "assistant.py"
        content = assistant.read_text()
        assert "list[MapMarker]" in content

    @pytest.mark.slow
    def test_antv_chart_langchain_has_module_cache(
        self, generated_project_antv_langchain: Path
    ) -> None:
        """get_antv_langchain_tools must use a module-level cache to avoid per-request MCP work."""
        antv = (
            generated_project_antv_langchain
            / "backend"
            / "app"
            / "agents"
            / "tools"
            / "antv_chart.py"
        )
        content = antv.read_text()
        assert "_antv_langchain_tools" in content
        assert "if _antv_langchain_tools is not None" in content


# ---------------------------------------------------------------------------
# Deep research — generated-content checks
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def generated_project_deep_research(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a pydantic_ai + PG + deep_research + frontend project for content checks."""
    config = ProjectConfig(
        project_name="test_deep_research",
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        enable_logfire=False,
        enable_deep_research=True,
        enable_charts=True,
        frontend=FrontendType.NEXTJS,
        background_tasks=BackgroundTaskType.NONE,
    )
    return generate_project(config, tmp_path_factory.mktemp("deep_research"))


@pytest.fixture(scope="module")
def generated_project_deep_research_off(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate the same project with deep research OFF to assert cleanup."""
    config = ProjectConfig(
        project_name="test_no_deep_research",
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        enable_logfire=False,
        enable_deep_research=False,
        frontend=FrontendType.NEXTJS,
        background_tasks=BackgroundTaskType.NONE,
    )
    return generate_project(config, tmp_path_factory.mktemp("no_deep_research"))


class TestGeneratedDeepResearch:
    """Verify the deep-research feature renders correctly and is fully gated.

    Guards the production-readiness fixes: the interstitial-tool gate (so a final
    report carrying a chart still streams), the no-conversation_id fallback, the
    shared RESEARCH_TOOL_NAMES set, and the post_gen cleanup when the flag is off.
    """

    @pytest.mark.slow
    def test_research_module_defines_shared_tool_names(
        self, generated_project_deep_research: Path
    ) -> None:
        """research.py owns the canonical interstitial-tool set and a telemetry flush."""
        research = generated_project_deep_research / "backend" / "app" / "services" / "research.py"
        assert research.exists()
        content = research.read_text()
        assert "RESEARCH_TOOL_NAMES = frozenset(" in content
        assert "async def flush(self)" in content

    @pytest.mark.slow
    def test_session_gates_buffer_on_research_tools(
        self, generated_project_deep_research: Path
    ) -> None:
        """The buffer drops text only for research-tool steps, not content tools (charts)."""
        session = (
            generated_project_deep_research / "backend" / "app" / "services" / "agent_session.py"
        )
        content = session.read_text()
        assert "from app.services.research import RESEARCH_TOOL_NAMES, ResearchToolkit" in content
        assert "made_research_call = any(name in RESEARCH_TOOL_NAMES" in content
        # The old indiscriminate drop must be gone.
        assert "made_tool_call" not in content

    @pytest.mark.slow
    def test_session_falls_back_without_conversation_id(
        self, generated_project_deep_research: Path
    ) -> None:
        """Without a conversation_id, deep_research is disabled rather than left tool-less."""
        session = (
            generated_project_deep_research / "backend" / "app" / "services" / "agent_session.py"
        )
        content = session.read_text()
        assert "if deep_research and self.current_conversation_id:" in content
        assert "deep_research = False" in content

    @pytest.mark.slow
    def test_frontend_panel_mirrors_backend(self, generated_project_deep_research: Path) -> None:
        """The frontend tool-name set is generated and documents the backend mirror."""
        panel = (
            generated_project_deep_research
            / "frontend"
            / "src"
            / "components"
            / "chat"
            / "research-panel.tsx"
        )
        assert panel.exists()
        content = panel.read_text()
        assert "RESEARCH_TOOL_NAMES" in content
        assert "app/services/research.py" in content

    @pytest.mark.slow
    def test_no_jinja_leftovers(self, generated_project_deep_research: Path) -> None:
        """No unrendered Jinja markers in the deep-research files."""
        files = [
            generated_project_deep_research / "backend" / "app" / "services" / "research.py",
            generated_project_deep_research / "backend" / "app" / "db" / "todo_pool.py",
            generated_project_deep_research / "backend" / "app" / "services" / "agent_session.py",
            generated_project_deep_research
            / "frontend"
            / "src"
            / "components"
            / "chat"
            / "research-panel.tsx",
        ]
        for f in files:
            content = f.read_text()
            assert "{%" not in content and "{{" not in content, f"Jinja leftover in {f.name}"

    @pytest.mark.slow
    def test_files_removed_when_disabled(self, generated_project_deep_research_off: Path) -> None:
        """post_gen removes every deep-research file when the flag is off."""
        root = generated_project_deep_research_off
        removed = [
            root / "backend" / "app" / "services" / "research.py",
            root / "backend" / "app" / "db" / "todo_pool.py",
            root / "frontend" / "src" / "components" / "chat" / "research-panel.tsx",
            root / "frontend" / "src" / "stores" / "research-store.ts",
            root / "frontend" / "src" / "stores" / "chat-mode-store.ts",
        ]
        for f in removed:
            assert not f.exists(), f"{f} should be removed when deep research is off"

    @pytest.mark.slow
    def test_disabled_session_keeps_original_streaming(
        self, generated_project_deep_research_off: Path
    ) -> None:
        """With the flag off, the session has no research buffering."""
        session = (
            generated_project_deep_research_off
            / "backend"
            / "app"
            / "services"
            / "agent_session.py"
        )
        content = session.read_text()
        assert "RESEARCH_TOOL_NAMES" not in content
        assert "made_research_call" not in content
