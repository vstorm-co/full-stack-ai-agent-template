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

    def test_upgrade_without_manifest_reports_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
        (tmp_path / "README.md").write_text("x", encoding="utf-8")
        result = runner.invoke(cli, ["upgrade", "--path", str(tmp_path)])
        assert result.exit_code != 0
        assert "recovery" in result.output.lower() or "manifest" in result.output.lower()
