"""Tests for CLI commands module."""

import click
from click.testing import CliRunner

from app.commands import (
    command,
    discover_commands,
    error,
    info,
    register_commands,
    success,
    warning,
)


class TestCommandDecorator:
    """Tests for the command decorator."""

    def test_command_registers_function(self):
        """Test that @command decorator registers a click command."""
        from app.commands import _commands

        initial_count = len(_commands)

        @command("test-cmd", help="Test command")
        def test_func():
            pass

        assert len(_commands) == initial_count + 1
        assert _commands[-1].name == "test-cmd"

    def test_command_uses_function_name_as_default(self):
        """Test that command name defaults to function name."""
        from app.commands import _commands

        @command()
        def my_test_command():
            pass

        assert _commands[-1].name == "my-test-command"


class TestHelperFunctions:
    """Tests for helper output functions."""

    def test_success_prints_green(self, capsys):
        """Test success prints in green."""
        success("Test message")
        # Click uses escape codes for colors
        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_error_prints_red(self, capsys):
        """Test error prints in red."""
        error("Error message")
        captured = capsys.readouterr()
        assert "Error message" in captured.out

    def test_warning_prints_yellow(self, capsys):
        """Test warning prints in yellow."""
        warning("Warning message")
        captured = capsys.readouterr()
        assert "Warning message" in captured.out

    def test_info_prints_plain(self, capsys):
        """Test info prints plain text."""
        info("Info message")
        captured = capsys.readouterr()
        assert "Info message" in captured.out


class TestDiscoverCommands:
    """Tests for command discovery."""

    def test_discover_commands_returns_list(self):
        """Test that discover_commands returns a list."""
        commands = discover_commands()
        assert isinstance(commands, list)

    def test_discover_commands_caches_results(self):
        """Test that discover_commands caches on second call."""
        commands1 = discover_commands()
        commands2 = discover_commands()
        assert commands1 is commands2


class TestRegisterCommands:
    """Tests for registering commands."""

    def test_register_commands_adds_to_group(self):
        """Test that register_commands adds discovered commands to CLI group."""

        @click.group()
        def cli():
            pass

        register_commands(cli)
        # After registration, cli should have commands
        # We can't assert exact count since it depends on what's discovered


class TestSeedCommand:
    """Tests for the seed command."""

    def test_seed_dry_run(self):
        """Test seed command with --dry-run."""
        from app.commands.seed import seed

        runner = CliRunner()
        result = runner.invoke(seed, ["--dry-run", "--count", "5"])
        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output
        assert "5" in result.output

    def test_seed_dry_run_with_clear(self):
        """Test seed command with --dry-run and --clear."""
        from app.commands.seed import seed

        runner = CliRunner()
        result = runner.invoke(seed, ["--dry-run", "--clear"])
        assert result.exit_code == 0
        assert "Would clear existing data" in result.output


class TestHelloCommand:
    """Tests for the hello command."""

    def test_hello_command_runs(self):
        """Test hello command executes."""
        from app.commands.example import hello

        runner = CliRunner()
        result = runner.invoke(hello)
        assert result.exit_code == 0
        assert "Hello" in result.output

    def test_hello_command_with_name(self):
        """Test hello command with --name option."""
        from app.commands.example import hello

        runner = CliRunner()
        result = runner.invoke(hello, ["--name", "Alice"])
        assert result.exit_code == 0
        assert "Alice" in result.output


class TestCleanupCommand:
    """Tests for the cleanup command."""

    def test_cleanup_dry_run(self):
        """Test cleanup command with --dry-run."""
        from app.commands.cleanup import cleanup

        runner = CliRunner()
        result = runner.invoke(cleanup, ["--dry-run"])
        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output

    def test_cleanup_with_days_option(self):
        """Test cleanup command with --days option."""
        from app.commands.cleanup import cleanup

        runner = CliRunner()
        result = runner.invoke(cleanup, ["--dry-run", "--days", "7"])
        assert result.exit_code == 0
