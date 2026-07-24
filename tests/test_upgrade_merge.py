"""Tests for fastapi_gen.upgrade.merge — the 3-way merge engine."""

import subprocess
from pathlib import Path

import pytest

from fastapi_gen.upgrade.merge import (
    MergeResult,
    _tracked_files,
    apply_renames,
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
            ".DS_Store",
            ".claude/.DS_Store",
            "Thumbs.db",
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

    @pytest.mark.parametrize(
        "path",
        [
            "backend/.env.example",
            "frontend/.env.example",
            ".env.sample",
            "backend/.env.template",
        ],
    )
    def test_env_samples_are_merged(self, path: str) -> None:
        """`.env.example` is committed, secret-free, and the only place a release
        announces new settings — excluding it would drop them silently (classify_trees
        filters on this same predicate, so no report line would mention it either)."""
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
            "git checkout -f main && git branch -D template-upgrade/vY"
        )

    def test_preserves_submodule(
        self, tmp_path: Path, three_trees: tuple[Path, Path, Path]
    ) -> None:
        """A gitlink (mode 160000) is never materialized, so it must not be treated as a
        tracked file and deleted from the client's worktree."""
        base, ours, theirs = three_trees
        client = tmp_path / "client"
        client.mkdir()
        for p in ours.rglob("*"):
            if p.is_file():
                rel = p.relative_to(ours)
                (client / rel).parent.mkdir(parents=True, exist_ok=True)
                (client / rel).write_text(p.read_text(), encoding="utf-8")
        _init_client_repo(client)

        inner = tmp_path / "inner"
        inner.mkdir()
        _write(inner, "m.txt", "sub content\n")
        _init_client_repo(inner)
        subprocess.run(
            [
                "git",
                "-C",
                str(client),
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                str(inner),
                "vendor/sub",
            ],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(client), "commit", "-q", "-m", "add submodule"], check=True
        )

        # The merged tree (from the fixture trees) knows nothing about vendor/sub.
        result = merge_trees(base, ours, theirs)
        materialize(result, client, branch="template-upgrade/vY")

        assert (client / "vendor" / "sub").is_dir()
        assert (client / "vendor" / "sub" / "m.txt").exists()
        status = subprocess.run(
            ["git", "-C", str(client), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert "vendor/sub" not in status

    def test_global_export_ignore_does_not_drop_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`git archive` consults the *global* attributes file even for the throwaway
        store, so a developer with `export-ignore` set there would silently lose the
        file from the upgrade — a new file wouldn't even land on disk."""
        attributes = tmp_path / "global-attrs"
        attributes.write_text("new_feature.txt export-ignore\n", encoding="utf-8")
        global_config = tmp_path / "gitconfig"
        global_config.write_text(f"[core]\n\tattributesFile = {attributes}\n", encoding="utf-8")
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))

        base, theirs = tmp_path / "base", tmp_path / "theirs"
        client = tmp_path / "client"
        for t in (base, theirs, client):
            t.mkdir()
        _write(base, "keep.txt", "same\n")
        _write(client, "keep.txt", "same\n")
        _write(theirs, "keep.txt", "same\n")
        _write(theirs, "new_feature.txt", "shiny\n")
        _init_client_repo(client)

        result = merge_trees(base, client, theirs)
        materialize(result, client, branch="template-upgrade/vY")

        assert (client / "new_feature.txt").exists()

    def test_tracked_files_handles_unicode(self, tmp_path: Path) -> None:
        """ls-tree -z returns real paths — without it, non-ASCII names are C-quoted."""
        client = tmp_path / "client"
        client.mkdir()
        _write(client, "żółć.txt", "unicode\n")
        _init_client_repo(client)
        assert "żółć.txt" in _tracked_files(client, "HEAD")

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

    def test_missing_store_raises(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeError, match="Merge store not found"):
            materialize(MergeResult(merged_tree="deadbeef"), tmp_path, branch="template-upgrade/vX")

    def test_existing_branch_guard_and_force(self, tmp_path: Path) -> None:
        base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
        for t in (base, ours, theirs):
            t.mkdir()
        _write(base, "f.txt", "a\n")
        _write(ours, "f.txt", "a\n")
        _write(theirs, "f.txt", "b\n")
        result = merge_trees(base, ours, theirs)

        client = tmp_path / "client"
        client.mkdir()
        _write(client, "f.txt", "a\n")
        _init_client_repo(client)
        subprocess.run(["git", "-C", str(client), "branch", "template-upgrade/vY"], check=True)

        with pytest.raises(RuntimeError, match="already exists"):
            materialize(result, client, branch="template-upgrade/vY", force=False)

        assert materialize(result, client, branch="template-upgrade/vY", force=True) == "main"
        assert (client / "f.txt").read_text() == "b\n"

    def test_stages_a_merged_file_the_client_gitignores(
        self, tmp_path: Path, three_trees: tuple[Path, Path, Path]
    ) -> None:
        """A merged file covered by the client's .gitignore must not abort the upgrade.

        `git add` given an explicit pathspec for an ignored path fails the whole call
        with exit 1, so without --force a single ignored template file (the generated
        .gitignore covers .DS_Store, and clients add their own rules) kills materialize
        before anything is staged.
        """
        base, ours, theirs = three_trees
        client = tmp_path / "client"
        client.mkdir()
        _write(client, "upd.txt", "one\ntwo\nthree\n")
        _write(client, ".gitignore", "new_feature.txt\n")
        _init_client_repo(client)

        result = merge_trees(base, client, theirs)
        materialize(result, client, branch="template-upgrade/vY")

        staged = subprocess.run(
            ["git", "-C", str(client), "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        assert "new_feature.txt" in staged

    def test_rolls_back_on_materialize_failure(
        self, tmp_path: Path, three_trees: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        base, ours, theirs = three_trees
        client = tmp_path / "client"
        client.mkdir()
        _write(client, "upd.txt", "one\ntwo\nthree\n")
        _init_client_repo(client)
        result = merge_trees(base, client, theirs)

        def _boom(*_a: object, **_k: object) -> None:
            raise RuntimeError("write blew up")

        monkeypatch.setattr("fastapi_gen.upgrade.merge._materialize_onto_branch", _boom)
        with pytest.raises(RuntimeError, match="write blew up"):
            materialize(result, client, branch="template-upgrade/vY")

        head = subprocess.run(
            ["git", "-C", str(client), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert head == "main"
        branches = subprocess.run(
            ["git", "-C", str(client), "branch", "--list", "template-upgrade/vY"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert branches == ""


class TestApplyRenames:
    def test_moves_dir_and_file(self, tmp_path: Path) -> None:
        tree = tmp_path / "tree"
        (tree / "old_dir").mkdir(parents=True)
        (tree / "old_dir" / "a.py").write_text("A", encoding="utf-8")
        (tree / "single.py").write_text("S", encoding="utf-8")

        apply_renames(tree, [("old_dir/", "new_dir/"), ("single.py", "renamed.py")])

        assert (tree / "new_dir" / "a.py").read_text() == "A"
        assert not (tree / "old_dir").exists()
        assert (tree / "renamed.py").read_text() == "S"
        assert not (tree / "single.py").exists()
