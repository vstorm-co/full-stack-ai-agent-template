"""Integration tests for project generation."""

import sys
from pathlib import Path

import pytest

from fastapi_gen.config import (
    AuthType,
    BackgroundTaskType,
    CIType,
    DatabaseType,
    ProjectConfig,
)
from fastapi_gen.generator import generate_project


class TestMinimalProjectGeneration:
    """Integration tests for minimal project generation."""

    @pytest.fixture
    def minimal_project(self, tmp_path: Path) -> Path:
        """Generate a minimal project."""
        config = ProjectConfig(
            project_name="minimal_project",
            database=DatabaseType.NONE,
            auth=AuthType.NONE,
            enable_logfire=False,
            enable_docker=False,
            enable_precommit=False,
            ci_type=CIType.NONE,
        )
        return generate_project(config, tmp_path)

    def test_project_directory_created(self, minimal_project: Path) -> None:
        """Test project directory is created."""
        assert minimal_project.exists()
        assert minimal_project.is_dir()

    def test_basic_structure_exists(self, minimal_project: Path) -> None:
        """Test basic project structure exists."""
        backend = minimal_project / "backend"
        assert backend.is_dir()
        assert (backend / "app").is_dir()
        assert (backend / "app" / "main.py").is_file()
        assert (backend / "app" / "core").is_dir()
        assert (backend / "app" / "core" / "config.py").is_file()
        assert (backend / "app" / "api").is_dir()
        assert (backend / "pyproject.toml").is_file()

    def test_pyproject_toml_exists(self, minimal_project: Path) -> None:
        """Test pyproject.toml exists."""
        assert (minimal_project / "backend" / "pyproject.toml").is_file()

    def test_main_py_exists(self, minimal_project: Path) -> None:
        """Test main.py exists."""
        assert (minimal_project / "backend" / "app" / "main.py").is_file()

    def test_tests_directory_exists(self, minimal_project: Path) -> None:
        """Test tests directory exists."""
        assert (minimal_project / "backend" / "tests").is_dir()


class TestPostgresqlProjectGeneration:
    """Integration tests for PostgreSQL project generation."""

    @pytest.fixture
    def postgresql_project(self, tmp_path: Path) -> Path:
        """Generate a PostgreSQL project."""
        config = ProjectConfig(
            project_name="pg_project",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            enable_logfire=True,
            enable_docker=True,
            ci_type=CIType.GITHUB,
        )
        return generate_project(config, tmp_path)

    def test_alembic_exists(self, postgresql_project: Path) -> None:
        """Test Alembic directory exists."""
        backend = postgresql_project / "backend"
        assert (backend / "alembic").is_dir()
        assert (backend / "alembic.ini").is_file()

    def test_database_session_exists(self, postgresql_project: Path) -> None:
        """Test database session module exists."""
        assert (postgresql_project / "backend" / "app" / "db" / "session.py").is_file()

    def test_docker_files_exist(self, postgresql_project: Path) -> None:
        """Test Docker files exist."""
        assert (postgresql_project / "backend" / "Dockerfile").is_file()
        assert (postgresql_project / "docker-compose.yml").is_file()

    def test_github_actions_exist(self, postgresql_project: Path) -> None:
        """Test GitHub Actions workflow exists."""
        workflows_dir = postgresql_project / ".github" / "workflows"
        assert workflows_dir.is_dir()

    def test_auth_files_exist(self, postgresql_project: Path) -> None:
        """Test auth-related files exist."""
        assert (postgresql_project / "backend" / "app" / "core" / "security.py").is_file()


class TestMongoDBProjectGeneration:
    """Integration tests for MongoDB project generation."""

    @pytest.fixture
    def mongodb_project(self, tmp_path: Path) -> Path:
        """Generate a MongoDB project."""
        config = ProjectConfig(
            project_name="mongo_project",
            database=DatabaseType.MONGODB,
            auth=AuthType.API_KEY,
        )
        return generate_project(config, tmp_path)

    def test_project_created(self, mongodb_project: Path) -> None:
        """Test MongoDB project is created."""
        assert mongodb_project.exists()
        assert mongodb_project.is_dir()

    def test_mongodb_session_exists(self, mongodb_project: Path) -> None:
        """Test MongoDB connection module exists."""
        assert (mongodb_project / "backend" / "app" / "db").is_dir()

    def test_api_key_auth_exists(self, mongodb_project: Path) -> None:
        """Test API key auth dependencies exist."""
        assert (mongodb_project / "backend" / "app" / "api" / "deps.py").is_file()


class TestFullFeaturedProjectGeneration:
    """Integration tests for fully-featured project generation."""

    @pytest.fixture
    def full_project(self, tmp_path: Path) -> Path:
        """Generate a fully-featured project."""
        config = ProjectConfig(
            project_name="full_project",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.BOTH,
            enable_logfire=True,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_caching=True,
            enable_rate_limiting=True,
            enable_pagination=True,
            enable_admin_panel=True,
            enable_websockets=True,
            enable_file_storage=True,
            enable_ai_agent=True,
            enable_cors=True,
            enable_docker=True,
            ci_type=CIType.GITHUB,
            enable_kubernetes=True,
        )
        return generate_project(config, tmp_path)

    def test_project_created(self, full_project: Path) -> None:
        """Test full project is created."""
        assert full_project.exists()
        assert full_project.is_dir()

    def test_core_directory_exists(self, full_project: Path) -> None:
        """Test core directory exists."""
        assert (full_project / "backend" / "app" / "core").is_dir()

    def test_api_routes_exist(self, full_project: Path) -> None:
        """Test API routes exist."""
        api_routes = full_project / "backend" / "app" / "api" / "routes"
        assert api_routes.is_dir()

    def test_services_directory_exists(self, full_project: Path) -> None:
        """Test services directory exists."""
        services_dir = full_project / "backend" / "app" / "services"
        assert services_dir.is_dir()

    def test_docker_files_exist(self, full_project: Path) -> None:
        """Test Docker files exist."""
        assert (full_project / "backend" / "Dockerfile").is_file()
        assert (full_project / "docker-compose.yml").is_file()


class TestGitLabCIProjectGeneration:
    """Integration tests for GitLab CI project generation."""

    @pytest.fixture
    def gitlab_project(self, tmp_path: Path) -> Path:
        """Generate a GitLab CI project."""
        config = ProjectConfig(
            project_name="gitlab_project",
            ci_type=CIType.GITLAB,
        )
        return generate_project(config, tmp_path)

    def test_project_created(self, gitlab_project: Path) -> None:
        """Test GitLab project is created."""
        assert gitlab_project.exists()
        assert gitlab_project.is_dir()

    def test_basic_structure_exists(self, gitlab_project: Path) -> None:
        """Test basic project structure exists."""
        backend = gitlab_project / "backend"
        assert backend.is_dir()
        assert (backend / "app").is_dir()
        assert (backend / "app" / "main.py").is_file()


class TestProjectContents:
    """Tests for generated project file contents."""

    @pytest.fixture
    def project_with_all_options(self, tmp_path: Path) -> Path:
        """Generate project with all options for content testing."""
        config = ProjectConfig(
            project_name="content_test",
            project_description="Test project for content verification",
            author_name="Test Author",
            author_email="test@example.com",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            enable_logfire=True,
        )
        return generate_project(config, tmp_path)

    def test_pyproject_contains_project_name(self, project_with_all_options: Path) -> None:
        """Test pyproject.toml contains project name."""
        pyproject = project_with_all_options / "backend" / "pyproject.toml"
        content = pyproject.read_text()
        assert 'name = "content_test"' in content or 'name = "content-test"' in content

    def test_config_contains_project_name(self, project_with_all_options: Path) -> None:
        """Test config.py contains project name."""
        config_file = project_with_all_options / "backend" / "app" / "core" / "config.py"
        content = config_file.read_text()
        assert "content_test" in content

    def test_env_example_exists(self, project_with_all_options: Path) -> None:
        """Test .env.example file exists in backend directory."""
        env_example = project_with_all_options / "backend" / ".env.example"
        assert env_example.is_file()
        content = env_example.read_text()
        assert "POSTGRES" in content  # PostgreSQL config should be present

    def test_main_py_has_fastapi_app(self, project_with_all_options: Path) -> None:
        """Test main.py has FastAPI app."""
        main_file = project_with_all_options / "backend" / "app" / "main.py"
        content = main_file.read_text()
        assert "FastAPI" in content
        assert "app = " in content or "app=" in content


class TestGeneratedAppSmokeTest:
    """Smoke tests to verify generated FastAPI app can be imported and instantiated.

    These tests ensure the generated code is syntactically correct and
    can be imported without errors, verifying runnability not just file existence.

    Note: These tests require the generated project to have its dependencies installed.
    They will be skipped if FastAPI is not available in the generated project's context.
    """

    @pytest.fixture
    def minimal_project_for_import(self, tmp_path: Path) -> Path:
        """Generate a minimal project for import testing."""
        config = ProjectConfig(
            project_name="smoke_test_project",
            database=DatabaseType.NONE,
            auth=AuthType.NONE,
            enable_logfire=False,
            enable_docker=False,
            enable_precommit=False,
            ci_type=CIType.NONE,
        )
        return generate_project(config, tmp_path)

    def _can_import_fastapi(self, project_path: Path) -> bool:
        """Check if FastAPI can be imported in the project's context."""
        backend_path = project_path / "backend"
        original_path = sys.path.copy()
        sys.path.insert(0, str(backend_path))
        try:
            import fastapi  # noqa: F401

            return True
        except ImportError:
            return False
        finally:
            sys.path = original_path

    def test_main_py_syntax_is_valid(self, minimal_project_for_import: Path) -> None:
        """Test that main.py has valid Python syntax."""
        main_file = minimal_project_for_import / "backend" / "app" / "main.py"
        content = main_file.read_text()

        # Compile the Python code to check for syntax errors
        try:
            compile(content, str(main_file), "exec")
        except SyntaxError as e:
            pytest.fail(f"main.py has syntax error: {e}")

    @pytest.mark.skipif(
        not Path("tests/conftest.py").exists(), reason="Test requires full environment"
    )
    def test_fastapi_app_can_be_imported(self, minimal_project_for_import: Path) -> None:
        """Test that the generated FastAPI app module can be imported."""
        backend_path = minimal_project_for_import / "backend"

        if not self._can_import_fastapi(minimal_project_for_import):
            pytest.skip("FastAPI not available in generated project")

        # Add the backend directory to sys.path
        original_path = sys.path.copy()
        sys.path.insert(0, str(backend_path))

        try:
            # Try importing the app module
            import app.main as main_module

            # Verify the module was imported successfully
            assert main_module is not None
        finally:
            # Restore original sys.path
            sys.path = original_path

    @pytest.mark.skipif(
        not Path("tests/conftest.py").exists(), reason="Test requires full environment"
    )
    def test_fastapi_app_has_app_instance(self, minimal_project_for_import: Path) -> None:
        """Test that the generated main.py exports a FastAPI app instance."""
        backend_path = minimal_project_for_import / "backend"

        if not self._can_import_fastapi(minimal_project_for_import):
            pytest.skip("FastAPI not available in generated project")

        # Add the backend directory to sys.path
        original_path = sys.path.copy()
        sys.path.insert(0, str(backend_path))

        try:
            # Import the app module
            import app.main as main_module

            # Check for common FastAPI app variable names
            app_instance = (
                getattr(main_module, "app", None)
                or getattr(main_module, "application", None)
                or getattr(main_module, "fastapi_app", None)
            )
            assert app_instance is not None, "FastAPI app instance not found in main.py"

            # Verify it's a FastAPI instance
            assert type(app_instance).__name__ == "FastAPI", (
                f"Expected FastAPI instance, got {type(app_instance).__name__}"
            )
        finally:
            # Restore original sys.path
            sys.path = original_path

    def test_postgresql_main_py_syntax_is_valid(self, tmp_path: Path) -> None:
        """Test that PostgreSQL project main.py has valid Python syntax."""
        config = ProjectConfig(
            project_name="pg_smoke_test",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            enable_logfire=False,
            enable_docker=False,
            enable_precommit=False,
            ci_type=CIType.NONE,
        )
        project_path = generate_project(config, tmp_path)
        main_file = project_path / "backend" / "app" / "main.py"
        content = main_file.read_text()

        # Compile the Python code to check for syntax errors
        try:
            compile(content, str(main_file), "exec")
        except SyntaxError as e:
            pytest.fail(f"main.py has syntax error: {e}")
