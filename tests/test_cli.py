"""Tests for fastapi_gen.cli module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from fastapi_gen.cli import cli, create, main, new, templates
from fastapi_gen.config import (
    BackgroundTaskType,
    CIType,
    DatabaseType,
    FrontendType,
    OAuthProvider,
    ProjectConfig,
)


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestCli:
    """Tests for main CLI group."""

    def test_cli_help(self, runner: CliRunner) -> None:
        """Test CLI help displays."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Full-Stack AI Agent Template Generator" in result.output

    def test_cli_version(self, runner: CliRunner) -> None:
        """Test CLI version displays."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "fastapi-fullstack" in result.output

    @patch("fastapi_gen.cli.run_interactive_prompts")
    @patch("fastapi_gen.cli.show_summary")
    @patch("fastapi_gen.cli.confirm_generation")
    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_cli_no_subcommand_invokes_new(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        mock_confirm: MagicMock,
        mock_summary: MagicMock,
        mock_prompts: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test that invoking cli without subcommand calls 'new'."""
        mock_prompts.return_value = ProjectConfig(
            project_name="testproject", background_tasks=BackgroundTaskType.NONE
        )
        mock_confirm.return_value = True
        mock_generate.return_value = tmp_path / "testproject"

        result = runner.invoke(cli, [])

        assert result.exit_code == 0
        mock_prompts.assert_called_once()


class TestNewCommand:
    """Tests for 'new' command."""

    def test_new_help(self, runner: CliRunner) -> None:
        """Test new command help displays."""
        result = runner.invoke(new, ["--help"])
        assert result.exit_code == 0
        assert "Create a new FastAPI project interactively" in result.output

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_new_with_no_input(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test new command with --no-input flag."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(new, ["--no-input", "--name", "myproject"])

        assert result.exit_code == 0
        mock_generate.assert_called_once()
        mock_post_gen.assert_called_once()

    def test_new_no_input_requires_name(self, runner: CliRunner) -> None:
        """Test --no-input requires --name."""
        result = runner.invoke(new, ["--no-input"])
        assert result.exit_code == 1
        assert "--name is required" in result.output

    @patch("fastapi_gen.cli.run_interactive_prompts")
    @patch("fastapi_gen.cli.show_summary")
    @patch("fastapi_gen.cli.confirm_generation")
    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_new_interactive(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        mock_confirm: MagicMock,
        mock_summary: MagicMock,
        mock_prompts: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test new command in interactive mode."""
        mock_prompts.return_value = ProjectConfig(project_name="testproject", background_tasks=BackgroundTaskType.NONE)
        mock_confirm.return_value = True
        mock_generate.return_value = tmp_path / "testproject"

        result = runner.invoke(new, [])

        assert result.exit_code == 0
        mock_prompts.assert_called_once()
        mock_summary.assert_called_once()
        mock_confirm.assert_called_once()
        mock_generate.assert_called_once()

    @patch("fastapi_gen.cli.run_interactive_prompts")
    @patch("fastapi_gen.cli.show_summary")
    @patch("fastapi_gen.cli.confirm_generation")
    def test_new_cancelled(
        self,
        mock_confirm: MagicMock,
        mock_summary: MagicMock,
        mock_prompts: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test new command cancelled by user."""
        mock_prompts.return_value = ProjectConfig(project_name="testproject", background_tasks=BackgroundTaskType.NONE)
        mock_confirm.return_value = False

        result = runner.invoke(new, [])

        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()

    @patch("fastapi_gen.cli.run_interactive_prompts")
    def test_new_keyboard_interrupt(
        self,
        mock_prompts: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test new command handles keyboard interrupt."""
        mock_prompts.side_effect = KeyboardInterrupt()

        result = runner.invoke(new, [])

        assert result.exit_code == 0
        assert "Cancelled" in result.output

    @patch("fastapi_gen.cli.run_interactive_prompts")
    def test_new_generic_exception(
        self,
        mock_prompts: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test new command handles generic exceptions."""
        mock_prompts.side_effect = RuntimeError("Something went wrong")

        result = runner.invoke(new, [])

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Something went wrong" in result.output

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_new_with_output_dir(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test new command accepts --output option."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(new, ["--no-input", "--name", "myproject", "-o", str(tmp_path)])

        assert result.exit_code == 0
        mock_generate.assert_called_once()
        # Verify output path was passed to generate_project
        call_args = mock_generate.call_args
        assert call_args[0][1] == tmp_path

    def test_new_output_dir_must_exist(self, runner: CliRunner) -> None:
        """Test that non-existent output dir fails validation."""
        result = runner.invoke(
            new, ["--no-input", "--name", "myproject", "-o", "/nonexistent/path"]
        )
        assert result.exit_code != 0

    @patch("fastapi_gen.cli.run_interactive_prompts")
    @patch("fastapi_gen.cli.show_summary")
    @patch("fastapi_gen.cli.confirm_generation")
    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_new_interactive_with_output_dir(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        mock_confirm: MagicMock,
        mock_summary: MagicMock,
        mock_prompts: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test new command in interactive mode with output dir."""
        mock_prompts.return_value = ProjectConfig(project_name="testproject", background_tasks=BackgroundTaskType.NONE)
        mock_confirm.return_value = True
        mock_generate.return_value = tmp_path / "testproject"

        result = runner.invoke(new, ["--output", str(tmp_path)])

        assert result.exit_code == 0
        mock_generate.assert_called_once()
        # Verify output path was passed
        call_args = mock_generate.call_args
        assert call_args[0][1] == tmp_path


class TestCreateCommand:
    """Tests for 'create' command."""

    def test_create_help(self, runner: CliRunner) -> None:
        """Test create command help displays."""
        result = runner.invoke(create, ["--help"])
        assert result.exit_code == 0
        assert "Create a new FastAPI project" in result.output

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_defaults(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with default options."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject"])

        assert result.exit_code == 0
        mock_generate.assert_called_once()
        config = mock_generate.call_args[0][0]
        assert config.project_name == "myproject"
        assert config.database == DatabaseType.POSTGRESQL

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_no_logfire(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with Logfire disabled."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--no-logfire"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.enable_logfire is False

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_no_docker(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with Docker disabled."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--no-docker"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.enable_docker is False

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_minimal(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with --minimal flag."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--minimal"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.database == DatabaseType.POSTGRESQL
        assert config.enable_logfire is False
        assert config.enable_docker is False
        assert config.ci_type == CIType.NONE

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_nextjs_frontend(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with Next.js frontend."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--frontend", "nextjs"])

        assert result.exit_code == 0
        assert "Frontend: nextjs" in result.output
        config = mock_generate.call_args[0][0]
        assert config.frontend == FrontendType.NEXTJS

    def test_create_invalid_project_name(self, runner: CliRunner) -> None:
        """Test create with invalid project name."""
        result = runner.invoke(create, ["Invalid-Name"])
        assert result.exit_code == 1
        assert "Invalid configuration" in result.output or "Error" in result.output

    @patch("fastapi_gen.cli.generate_project")
    def test_create_generic_exception(
        self,
        mock_generate: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test create command handles generic exceptions."""
        mock_generate.side_effect = RuntimeError("Generation failed")

        result = runner.invoke(create, ["myproject"])

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Generation failed" in result.output

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_ai_framework_pydantic_ai(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with AI framework (PydanticAI)."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--ai-framework", "pydantic_ai"])

        assert result.exit_code == 0
        assert "AI Agent: pydantic_ai" in result.output
        config = mock_generate.call_args[0][0]
        assert config.ai_framework.value == "pydantic_ai"

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_ai_framework_langchain(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with AI framework (LangChain)."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--ai-framework", "langchain"])

        assert result.exit_code == 0
        assert "AI Agent: langchain" in result.output
        config = mock_generate.call_args[0][0]
        assert config.ai_framework.value == "langchain"

    # Tests for new CLI options

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_preset_production(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with production preset."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--preset", "production"])

        assert result.exit_code == 0
        assert "Preset: production" in result.output
        config = mock_generate.call_args[0][0]
        assert config.database == DatabaseType.POSTGRESQL
        assert config.enable_redis is True
        assert config.enable_caching is True
        assert config.enable_rate_limiting is True
        assert config.enable_sentry is True
        assert config.enable_prometheus is True
        assert config.enable_kubernetes is True

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_preset_ai_agent(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with ai-agent preset."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--preset", "ai-agent"])

        assert result.exit_code == 0
        assert "Preset: ai-agent" in result.output
        config = mock_generate.call_args[0][0]
        assert config.enable_websockets is True
        assert config.enable_redis is True

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_redis(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with Redis enabled."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--redis"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.enable_redis is True

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_caching(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with caching enabled (requires Redis)."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--redis", "--caching"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.enable_redis is True
        assert config.enable_caching is True

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_rate_limiting(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with rate limiting enabled."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--rate-limiting"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.enable_rate_limiting is True

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_admin_panel(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with admin panel enabled."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--admin-panel"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.enable_admin_panel is True

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_task_queue_celery(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with Celery task queue."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--task-queue", "celery", "--redis"])

        assert result.exit_code == 0
        assert "Task Queue: celery" in result.output
        config = mock_generate.call_args[0][0]
        assert config.background_tasks == BackgroundTaskType.CELERY

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_task_queue_taskiq(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with Taskiq task queue."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--task-queue", "taskiq", "--redis"])

        assert result.exit_code == 0
        assert "Task Queue: taskiq" in result.output
        config = mock_generate.call_args[0][0]
        assert config.background_tasks == BackgroundTaskType.TASKIQ

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_oauth_google(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with Google OAuth."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--oauth-google", "--frontend", "nextjs"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.oauth_provider == OAuthProvider.GOOGLE

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_session_management(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with session management."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--session-management"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.enable_session_management is True

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_kubernetes(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with Kubernetes manifests."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--kubernetes"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.enable_kubernetes is True

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_ci_gitlab(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with GitLab CI."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--ci", "gitlab"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.ci_type == CIType.GITLAB

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_sentry(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with Sentry enabled."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--sentry"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.enable_sentry is True

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_prometheus(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with Prometheus enabled."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--prometheus"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.enable_prometheus is True

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_file_storage(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with file storage enabled."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--file-storage"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.enable_file_storage is True

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_webhooks(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with webhooks enabled."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--webhooks"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.enable_webhooks is True

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_python_version(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with specific Python version."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(create, ["myproject", "--python-version", "3.13"])

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.python_version == "3.13"

    @patch("fastapi_gen.cli.generate_project")
    @patch("fastapi_gen.cli.post_generation_tasks")
    def test_create_with_multiple_options(
        self,
        mock_post_gen: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test create with multiple options combined."""
        mock_generate.return_value = tmp_path / "myproject"

        result = runner.invoke(
            create,
            [
                "myproject",
                "--redis",
                "--caching",
                "--rate-limiting",
                "--admin-panel",
                "--task-queue",
                "taskiq",
                "--sentry",
                "--prometheus",
            ],
        )

        assert result.exit_code == 0
        config = mock_generate.call_args[0][0]
        assert config.enable_redis is True
        assert config.enable_caching is True
        assert config.enable_rate_limiting is True
        assert config.enable_admin_panel is True
        assert config.background_tasks == BackgroundTaskType.TASKIQ
        assert config.enable_sentry is True
        assert config.enable_prometheus is True


class TestTemplatesCommand:
    """Tests for 'templates' command."""

    def test_templates_displays_options(self, runner: CliRunner) -> None:
        """Test templates command displays available options."""
        result = runner.invoke(templates, [])

        assert result.exit_code == 0
        # Presets
        assert "Presets" in result.output
        assert "--preset production" in result.output
        assert "--preset ai-agent" in result.output
        assert "--minimal" in result.output
        # Database
        assert "Database" in result.output
        assert "postgresql" in result.output
        # Authentication
        assert "Authentication" in result.output
        assert "JWT" in result.output
        assert "API Key" in result.output
        assert "--oauth-google" in result.output
        assert "--session-management" in result.output
        # Background Tasks
        assert "Background Tasks" in result.output
        assert "celery" in result.output
        assert "taskiq" in result.output
        # Integrations
        assert "Integrations" in result.output
        assert "--redis" in result.output
        assert "--caching" in result.output
        assert "--rate-limiting" in result.output
        assert "--admin-panel" in result.output
        # Observability
        assert "Observability" in result.output
        assert "--sentry" in result.output
        assert "--prometheus" in result.output
        # DevOps
        assert "DevOps" in result.output
        assert "--kubernetes" in result.output
        assert "--ci github" in result.output
        assert "--ci gitlab" in result.output


class TestMainEntrypoint:
    """Tests for main entrypoint."""

    def test_main_calls_cli(self) -> None:
        """Test main function calls cli."""
        with patch("fastapi_gen.cli.cli") as mock_cli:
            main()
            mock_cli.assert_called_once()
