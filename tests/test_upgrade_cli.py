"""Tests for the `upgrade` / `upgrade finalize` CLI wiring."""

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from fastapi_gen.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestUpgradeCliWiring:
    def test_upgrade_help_lists_options(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["upgrade", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--with-new-features" in result.output
        assert "--to" in result.output

    def test_finalize_subcommand_registered(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["upgrade", "finalize", "--help"])
        assert result.exit_code == 0

    def test_finalize_without_pending_reports_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        result = runner.invoke(cli, ["upgrade", "finalize", "--path", str(tmp_path)])
        assert result.exit_code != 0
        assert "pending" in result.output.lower()

    def test_recover_writes_candidate(self, runner: CliRunner, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("Generated v0.2.10\n", encoding="utf-8")
        result = runner.invoke(cli, ["upgrade", "recover", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / ".fastapi-fullstack.json.candidate").exists()

    @pytest.mark.parametrize(
        ("option", "value"),
        [
            ("--path", "."),
            ("--to", "9.9.9"),
            ("--dry-run", None),
            ("--with-new-features", None),
            ("--force", None),
        ],
    )
    def test_group_option_after_subcommand_is_rejected(
        self, runner: CliRunner, option: str, value: str | None
    ) -> None:
        """A group option typed after the subcommand silently applies to the group,
        not the subcommand — `upgrade --path X finalize` would finalize the current
        directory instead of X. Refuse rather than act on the wrong project."""
        typed = [option] if value is None else [option, value]
        result = runner.invoke(cli, ["upgrade", *typed, "finalize"])
        assert result.exit_code != 0
        assert option in result.output
        assert "finalize" in result.output

    def test_upgrade_without_manifest_reports_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
        (tmp_path / "README.md").write_text("x", encoding="utf-8")
        result = runner.invoke(cli, ["upgrade", "--path", str(tmp_path)])
        assert result.exit_code != 0
        assert "recovery" in result.output.lower() or "manifest" in result.output.lower()
