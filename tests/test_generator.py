"""Tests for fastapi_gen.generator module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fastapi_gen.config import BackgroundTaskType, DatabaseType, FrontendType, ProjectConfig, RAGFeatures, VectorStoreType
from fastapi_gen.generator import (
    TEMPLATE_DIR,
    _find_template_dir,
    _get_database_setup_commands,
    generate_project,
    get_template_path,
    post_generation_tasks,
)


class TestFindTemplateDir:
    """Tests for _find_template_dir function."""

    def test_finds_dev_template(self) -> None:
        """Test dev template is found when it exists."""
        # The default behavior should find the dev template
        path = _find_template_dir()
        assert path.exists()
        assert (path / "cookiecutter.json").exists()

    def test_finds_installed_template_when_dev_not_exists(self, tmp_path: Path) -> None:
        """Test installed template is found when dev path doesn't exist."""
        # Create a fake installed template directory structure
        installed_template = tmp_path / "template"
        installed_template.mkdir(parents=True)
        (installed_template / "cookiecutter.json").write_text("{}")

        # Mock __file__ to point to a location where:
        # - dev path (parent.parent / "template") doesn't exist
        # - installed path (parent / "template") exists
        fake_generator_file = tmp_path / "generator.py"

        with patch("fastapi_gen.generator.__file__", str(fake_generator_file)):
            result = _find_template_dir()
            assert result == installed_template

    def test_raises_when_no_template_found(self, tmp_path: Path) -> None:
        """Test FileNotFoundError when no template found."""
        # Point to a location where neither dev nor installed template exists
        fake_generator_file = tmp_path / "nonexistent" / "generator.py"

        with (
            patch("fastapi_gen.generator.__file__", str(fake_generator_file)),
            pytest.raises(FileNotFoundError, match="Could not find cookiecutter"),
        ):
            _find_template_dir()


class TestGetDatabaseSetupCommands:
    """Tests for _get_database_setup_commands function."""

    def test_postgresql_commands(self) -> None:
        """Test PostgreSQL returns docker-db and migration commands."""
        commands = _get_database_setup_commands(DatabaseType.POSTGRESQL)

        assert len(commands) == 3
        # Commands are now tuples of (command, description)
        assert "docker-db" in commands[0][0]
        assert "PostgreSQL" in commands[0][1]
        assert "db-migrate" in commands[1][0]
        assert "db-upgrade" in commands[2][0]



class TestGetTemplatePath:
    """Tests for get_template_path function."""

    def test_returns_template_directory(self) -> None:
        """Test template path is returned."""
        path = get_template_path()
        assert isinstance(path, str)
        assert Path(path).exists()
        assert Path(path) == TEMPLATE_DIR

    def test_template_contains_cookiecutter_json(self) -> None:
        """Test template contains cookiecutter.json."""
        path = get_template_path()
        cookiecutter_json = Path(path) / "cookiecutter.json"
        assert cookiecutter_json.exists()


class TestGenerateProject:
    """Tests for generate_project function."""

    @patch("fastapi_gen.generator.cookiecutter")
    def test_generates_project_in_current_dir(
        self,
        mock_cookiecutter: MagicMock,
        minimal_config: ProjectConfig,
        temp_output_dir: Path,
    ) -> None:
        """Test project is generated in current directory when no output specified."""
        mock_cookiecutter.return_value = str(temp_output_dir / "test_project")

        with patch("fastapi_gen.generator.Path.cwd", return_value=temp_output_dir):
            result = generate_project(minimal_config)

        mock_cookiecutter.assert_called_once()
        call_kwargs = mock_cookiecutter.call_args
        assert call_kwargs[1]["no_input"] is True
        assert isinstance(result, Path)

    @patch("fastapi_gen.generator.cookiecutter")
    def test_generates_project_in_output_dir(
        self,
        mock_cookiecutter: MagicMock,
        minimal_config: ProjectConfig,
        temp_output_dir: Path,
    ) -> None:
        """Test project is generated in specified output directory."""
        mock_cookiecutter.return_value = str(temp_output_dir / "test_project")

        result = generate_project(minimal_config, temp_output_dir)

        mock_cookiecutter.assert_called_once()
        call_kwargs = mock_cookiecutter.call_args
        assert call_kwargs[1]["output_dir"] == str(temp_output_dir)
        assert isinstance(result, Path)

    @patch("fastapi_gen.generator.cookiecutter")
    def test_passes_config_context_to_cookiecutter(
        self,
        mock_cookiecutter: MagicMock,
        minimal_config: ProjectConfig,
        temp_output_dir: Path,
    ) -> None:
        """Test config context is passed to cookiecutter."""
        mock_cookiecutter.return_value = str(temp_output_dir / "test_project")

        generate_project(minimal_config, temp_output_dir)

        call_kwargs = mock_cookiecutter.call_args
        extra_context = call_kwargs[1]["extra_context"]
        assert extra_context["project_name"] == "test_project"

    def test_raises_if_directory_exists_and_not_empty(
        self,
        minimal_config: ProjectConfig,
        temp_output_dir: Path,
    ) -> None:
        """Test ValueError is raised if target directory exists and is not empty."""
        # Create target directory with a file
        target_dir = temp_output_dir / "test_project"
        target_dir.mkdir()
        (target_dir / "existing_file.txt").write_text("content")

        with pytest.raises(ValueError, match="already exists and is not empty"):
            generate_project(minimal_config, temp_output_dir)

    @patch("fastapi_gen.generator.cookiecutter")
    @patch("fastapi_gen.generator.shutil.rmtree")
    def test_cleans_up_on_failure(
        self,
        mock_rmtree: MagicMock,
        mock_cookiecutter: MagicMock,
        minimal_config: ProjectConfig,
        temp_output_dir: Path,
    ) -> None:
        """Test partial files are cleaned up on failure."""
        mock_cookiecutter.side_effect = Exception("Generation failed")
        target_dir = temp_output_dir / "test_project"
        target_dir.mkdir()  # Simulate partial creation

        with pytest.raises(Exception, match="Generation failed"):
            generate_project(minimal_config, temp_output_dir)

        mock_rmtree.assert_called_once_with(target_dir)


class TestPostGenerationTasks:
    """Tests for post_generation_tasks function."""

    def test_displays_next_steps(
        self, minimal_config: ProjectConfig, temp_output_dir: Path
    ) -> None:
        """Test next steps are displayed."""
        project_path = temp_output_dir / "test_project"
        project_path.mkdir()

        # Should not raise
        post_generation_tasks(project_path, minimal_config)

    def test_displays_precommit_step_when_enabled(self, temp_output_dir: Path) -> None:
        """Test pre-commit step is displayed when enabled."""
        config = ProjectConfig(
            project_name="test",
            enable_precommit=True,
            background_tasks=BackgroundTaskType.NONE,
        )
        project_path = temp_output_dir / "test"
        project_path.mkdir()

        # Should not raise
        post_generation_tasks(project_path, config)

    def test_displays_db_step_when_database_enabled(self, temp_output_dir: Path) -> None:
        """Test database step is displayed when database enabled."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.NONE,
        )
        project_path = temp_output_dir / "test"
        project_path.mkdir()

        # Should not raise
        post_generation_tasks(project_path, config)

    def test_displays_logfire_info_when_enabled(self, temp_output_dir: Path) -> None:
        """Test Logfire info is displayed when enabled."""
        config = ProjectConfig(
            project_name="test",
            enable_logfire=True,
            background_tasks=BackgroundTaskType.NONE,
        )
        project_path = temp_output_dir / "test"
        project_path.mkdir()

        # Should not raise
        post_generation_tasks(project_path, config)

    def test_displays_frontend_steps_when_nextjs_enabled(self, temp_output_dir: Path) -> None:
        """Test frontend steps are displayed when Next.js is enabled."""
        config = ProjectConfig(
            project_name="test",
            frontend=FrontendType.NEXTJS,
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.NONE,
        )
        project_path = temp_output_dir / "test"
        project_path.mkdir()

        # Should not raise
        post_generation_tasks(project_path, config)

    def test_displays_env_copy_steps_when_generate_env_false_with_frontend(
        self, temp_output_dir: Path
    ) -> None:
        """Test env copy steps are displayed when generate_env=False with frontend."""
        config = ProjectConfig(
            project_name="test",
            frontend=FrontendType.NEXTJS,
            generate_env=False,
            background_tasks=BackgroundTaskType.NONE,
        )
        project_path = temp_output_dir / "test"
        project_path.mkdir()

        # Should not raise - tests lines 116-119
        post_generation_tasks(project_path, config)

    def test_displays_env_copy_steps_when_generate_env_false_backend_only(
        self, temp_output_dir: Path
    ) -> None:
        """Test env copy steps are displayed when generate_env=False backend only."""
        config = ProjectConfig(
            project_name="test",
            frontend=FrontendType.NONE,
            generate_env=False,
            background_tasks=BackgroundTaskType.NONE,
        )
        project_path = temp_output_dir / "test"
        project_path.mkdir()

        # Should not raise - tests lines 149-151
        post_generation_tasks(project_path, config)

    def test_displays_env_preconfigured_when_generate_env_true_backend_only(
        self, temp_output_dir: Path
    ) -> None:
        """Test env pre-configured message is displayed when generate_env=True backend only."""
        config = ProjectConfig(
            project_name="test",
            frontend=FrontendType.NONE,
            generate_env=True,
            background_tasks=BackgroundTaskType.NONE,
        )
        project_path = temp_output_dir / "test"
        project_path.mkdir()

        # Should not raise - tests lines 172-174
        post_generation_tasks(project_path, config)

    def test_displays_rag_messages_when_rag_enabled(
        self, temp_output_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test RAG post-generation messages are displayed (lines 226-232)."""
        config = ProjectConfig(
            project_name="test",
            database=DatabaseType.POSTGRESQL,
            rag_features=RAGFeatures(
                enable_rag=True,
                vector_store=VectorStoreType.MILVUS,
            ),
            background_tasks=BackgroundTaskType.NONE,
        )
        project_path = temp_output_dir / "test"
        project_path.mkdir()

        # Should not raise - exercises lines 226-232 (RAG messages)
        post_generation_tasks(project_path, config)

    def test_displays_web_search_env_message(
        self, temp_output_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test web search env message is displayed (line 235)."""
        config = ProjectConfig(
            project_name="test",
            enable_web_search=True,
            background_tasks=BackgroundTaskType.NONE,
        )
        project_path = temp_output_dir / "test"
        project_path.mkdir()

        # Should not raise - exercises line 235 (TAVILY_API_KEY message)
        post_generation_tasks(project_path, config)
