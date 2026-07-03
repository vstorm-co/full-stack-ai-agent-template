"""Tests for fastapi_gen.upgrade.merge — the 3-way merge engine."""

import subprocess
from pathlib import Path

import pytest

from fastapi_gen.upgrade.merge import (
    is_excluded,
    materialize,
    merge_trees,
    undo_command,
)


class TestIsExcluded:
    @pytest.mark.parametrize(
        "path",
        [
            ".env",
            ".env.local",
            "backend/uv.lock",
            "frontend/bun.lockb",
            "frontend/bun.lock",
            ".fastapi-fullstack.json",
            ".gitattributes",
            ".git/config",
            "frontend/node_modules/x/index.js",
            "backend/__pycache__/m.pyc",
        ],
    )
    def test_excluded(self, path: str) -> None:
        assert is_excluded(path)

    @pytest.mark.parametrize(
        "path",
        ["backend/app/main.py", "frontend/src/page.tsx", "README.md", "pyproject.toml"],
    )
    def test_not_excluded(self, path: str) -> None:
        assert not is_excluded(path)


def _write(tree: Path, rel: str, content: str) -> None:
    p = tree / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


@pytest.fixture
def three_trees(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Trees exercising the §6 classification matrix rows."""
    base, ours, theirs = tmp_path / "base", tmp_path / "ours", tmp_path / "theirs"
    for t in (base, ours, theirs):
        t.mkdir()

    _write(base, "upd.txt", "one\ntwo\nthree\n")
    _write(ours, "upd.txt", "one\ntwo\nthree\n")
    _write(theirs, "upd.txt", "one\nTWO-NEW\nthree\n")

    _write(base, "cust.txt", "alpha\nbeta\n")
    _write(ours, "cust.txt", "alpha\nBETA-EDIT\n")
    _write(theirs, "cust.txt", "alpha\nbeta\n")

    _write(ours, "client_only.txt", "mine\n")

    _write(theirs, "new_feature.txt", "shiny\n")

    _write(base, "conflict.txt", "x\ny\nz\n")
    _write(ours, "conflict.txt", "x\nOURS\nz\n")
    _write(theirs, "conflict.txt", "x\nTHEIRS\nz\n")

    _write(base, "gone.txt", "obsolete\n")
    _write(ours, "gone.txt", "obsolete\n")

    return base, ours, theirs


class TestMergeTrees:
    def test_classifies_matrix(self, three_trees: tuple[Path, Path, Path]) -> None:
        base, ours, theirs = three_trees
        result = merge_trees(base, ours, theirs)

        assert not result.clean
        assert result.conflicted_paths == ["conflict.txt"]

    def test_clean_merge_reports_clean(self, tmp_path: Path) -> None:
        base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
        for t in (base, ours, theirs):
            t.mkdir()
        _write(base, "f.txt", "a\n")
        _write(ours, "f.txt", "a\n")
        _write(theirs, "f.txt", "b\n")
        result = merge_trees(base, ours, theirs)
        assert result.clean
        assert result.conflicted_paths == []


def _init_client_repo(worktree: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(worktree)], check=True)
    subprocess.run(["git", "-C", str(worktree), "config", "user.email", "t@t.co"], check=True)
    subprocess.run(["git", "-C", str(worktree), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(worktree), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(worktree), "commit", "-q", "-m", "init"], check=True)


class TestMaterialize:
    def test_full_back_map(self, tmp_path: Path, three_trees: tuple[Path, Path, Path]) -> None:
        base, ours, theirs = three_trees

        client = tmp_path / "client"
        client.mkdir()
        for p in ours.rglob("*"):
            if p.is_file():
                rel = p.relative_to(ours)
                (client / rel).parent.mkdir(parents=True, exist_ok=True)
                (client / rel).write_text(p.read_text(), encoding="utf-8")
        (client / ".env").write_text("SECRET=xyz\n", encoding="utf-8")
        _init_client_repo(client)

        result = merge_trees(base, client, theirs)
        orig = materialize(result, client, branch="template-upgrade/vY")

        assert (
            subprocess.run(
                ["git", "-C", str(client), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            == "template-upgrade/vY"
        )
        assert orig == "main"

        assert "TWO-NEW" in (client / "upd.txt").read_text()
        assert "BETA-EDIT" in (client / "cust.txt").read_text()
        assert (client / "new_feature.txt").exists()
        assert (client / "client_only.txt").exists()
        assert not (client / "gone.txt").exists()

        conflict_text = (client / "conflict.txt").read_text()
        assert "<<<<<<<" in conflict_text and ">>>>>>>" in conflict_text

        status = subprocess.run(
            ["git", "-C", str(client), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert any(line.startswith("UU") and "conflict.txt" in line for line in status.splitlines())

        assert (client / ".env").read_text() == "SECRET=xyz\n"

        assert undo_command("template-upgrade/vY", orig) == (
            "git checkout main && git branch -D template-upgrade/vY"
        )

    def test_refuses_dirty_worktree(
        self, tmp_path: Path, three_trees: tuple[Path, Path, Path]
    ) -> None:
        base, ours, theirs = three_trees
        client = tmp_path / "client"
        client.mkdir()
        _write(client, "upd.txt", "one\ntwo\nthree\n")
        _init_client_repo(client)
        _write(client, "upd.txt", "dirty edit\n")

        result = merge_trees(base, client, theirs)
        with pytest.raises(RuntimeError, match="uncommitted changes"):
            materialize(result, client, branch="template-upgrade/vY")
