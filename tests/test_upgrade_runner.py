"""Tests for fastapi_gen.upgrade.runner — orchestration + finalize."""

import subprocess
from pathlib import Path

import pytest

from fastapi_gen.config import (
    BackgroundTaskType,
    CIType,
    DatabaseType,
    ProjectConfig,
    get_generator_version,
)
from fastapi_gen.upgrade.fetch import TemplateFetchError, fetch_template
from fastapi_gen.upgrade.manifest import MANIFEST_FILENAME, write_manifest
from fastapi_gen.upgrade.render import render_template
from fastapi_gen.upgrade.runner import UpgradeError, run_finalize, run_upgrade


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _commit_all(repo: Path, message: str = "init") -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    _git(repo, "config", "user.email", "t@t.co")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


class TestGuards:
    def test_missing_manifest_raises(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("x", encoding="utf-8")
        _commit_all(tmp_path)
        with pytest.raises(FileNotFoundError):
            run_upgrade(tmp_path)

    def test_already_up_to_date_is_noop(self, tmp_path: Path) -> None:
        write_manifest(tmp_path, {"project_name": "x"}, package_version=get_generator_version())
        _commit_all(tmp_path)
        outcome = run_upgrade(tmp_path)
        assert outcome.applied is False
        assert outcome.merge is None

    def test_finalize_without_pending_raises(self, tmp_path: Path) -> None:
        write_manifest(tmp_path, {"project_name": "x"}, package_version="0.1.0")
        _commit_all(tmp_path)
        with pytest.raises(UpgradeError, match="No pending upgrade"):
            run_finalize(tmp_path)

    def test_downgrade_is_rejected(self, tmp_path: Path) -> None:
        write_manifest(tmp_path, {"project_name": "x"}, package_version="99.0.0")
        _commit_all(tmp_path)
        with pytest.raises(UpgradeError, match="Downgrades are not supported"):
            run_upgrade(tmp_path, to_version=get_generator_version())

    def test_dirty_worktree_rejected_before_expensive_work(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("x", encoding="utf-8")
        write_manifest(tmp_path, {"project_name": "x"}, package_version="0.1.0")
        _commit_all(tmp_path)
        (tmp_path / "README.md").write_text("dirty change", encoding="utf-8")
        with pytest.raises(RuntimeError, match="uncommitted changes"):
            run_upgrade(tmp_path, dry_run=False)

    def test_run_recover_writes_candidate(self, tmp_path: Path) -> None:
        from fastapi_gen.upgrade.runner import run_recover

        (tmp_path / "README.md").write_text("Generated v0.2.10\n", encoding="utf-8")
        (tmp_path / "frontend").mkdir()
        candidate = run_recover(tmp_path)
        assert candidate.exists()
        assert candidate.name == MANIFEST_FILENAME + ".candidate"

    def test_finalize_blocked_by_unmerged_conflicts(self, tmp_path: Path) -> None:
        write_manifest(tmp_path, {"project_name": "x"}, package_version="0.1.0")
        _commit_all(tmp_path)
        (tmp_path / "c.txt").write_text("base\n", encoding="utf-8")
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-q", "-m", "base")
        _git(tmp_path, "checkout", "-q", "-b", "other")
        (tmp_path / "c.txt").write_text("other\n", encoding="utf-8")
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-q", "-m", "other")
        _git(tmp_path, "checkout", "-q", "main")
        (tmp_path / "c.txt").write_text("main\n", encoding="utf-8")
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-q", "-m", "main")
        subprocess.run(["git", "-C", str(tmp_path), "merge", "other"], capture_output=True)
        (tmp_path / (MANIFEST_FILENAME + ".pending")).write_text("{}", encoding="utf-8")
        with pytest.raises(UpgradeError, match="Unresolved merge conflicts"):
            run_finalize(tmp_path)


@pytest.mark.slow
class TestSelfUpgradeEndToEnd:
    """Real 0.2.13 → running-version upgrade of a simulated client project."""

    def _make_client(self, work: Path) -> tuple[Path, str]:
        cfg = ProjectConfig(
            project_name="e2e_app",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.NONE,
            enable_docker=False,
            enable_logfire=False,
            ci_type=CIType.NONE,
        )
        ctx = cfg.to_cookiecutter_context()
        try:
            old_template = fetch_template("0.2.13")
        except TemplateFetchError as exc:
            pytest.skip(f"PyPI unreachable: {exc}")
        client = render_template(old_template, ctx, work / "client_parent")
        write_manifest(client, ctx, package_version="0.2.13")
        main = client / "backend" / "app" / "main.py"
        main.write_text("# CLIENT CUSTOM COMMENT\n" + main.read_text(), encoding="utf-8")
        _commit_all(client)
        return client, "# CLIENT CUSTOM COMMENT"

    def test_upgrade_preserves_edits_and_applies_updates(self, tmp_path: Path) -> None:
        client, marker = self._make_client(tmp_path)
        outcome = run_upgrade(client, to_version=None, dry_run=False)

        assert outcome.applied is True
        assert outcome.branch == f"template-upgrade/v{get_generator_version()}"
        assert outcome.classification.auto_updated, "expected real template updates"
        assert "backend/app/main.py" in outcome.classification.client_kept
        assert outcome.classification.conflicts == []
        assert marker in (client / "backend" / "app" / "main.py").read_text()
        assert (client / (MANIFEST_FILENAME + ".pending")).exists()

        _git(client, "add", "-A")
        run_finalize(client)
        import json

        manifest = json.loads((client / MANIFEST_FILENAME).read_text())
        assert manifest["package_version"] == get_generator_version()
        assert not (client / (MANIFEST_FILENAME + ".pending")).exists()

    def test_dry_run_changes_nothing(self, tmp_path: Path) -> None:
        client, _marker = self._make_client(tmp_path)
        head_before = subprocess.run(
            ["git", "-C", str(client), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        outcome = run_upgrade(client, dry_run=True)
        assert outcome.applied is False
        branch = subprocess.run(
            ["git", "-C", str(client), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert branch == "main"
        head_after = subprocess.run(
            ["git", "-C", str(client), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert head_before == head_after
        assert not (client / (MANIFEST_FILENAME + ".pending")).exists()
