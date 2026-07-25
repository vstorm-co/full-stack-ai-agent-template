"""Tests for fastapi_gen.upgrade.normalize — formatter availability + tree passes."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from fastapi_gen.upgrade import normalize as normalize_mod
from fastapi_gen.upgrade.normalize import (
    _GENERATED_AT_PLACEHOLDER,
    _ruff_cmd,
    format_frontend,
    format_python,
    normalize_tree,
    normalize_whitespace,
    restore_generated_at,
)


def _fake_node_modules(root: Path, script: str) -> Path:
    nm = root / "nm"
    bindir = nm / ".bin"
    bindir.mkdir(parents=True)
    prettier = bindir / "prettier"
    prettier.write_text(script, encoding="utf-8")
    prettier.chmod(0o755)
    return nm


def test_ruff_available_at_runtime() -> None:
    """ruff must be a runtime dependency — the merge's correctness relies on it.

    If this fails, BASE/THEIRS render unformatted while OURS is formatted, producing
    spurious diffs and false conflicts under `uvx fastapi-fullstack upgrade`.
    """
    assert _ruff_cmd() is not None, (
        "ruff not found at runtime — it must be in [project.dependencies], not just dev."
    )


def test_format_python_runs_when_ruff_present(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("x=1\n", encoding="utf-8")
    assert format_python(tmp_path) is True
    assert (tmp_path / "m.py").read_text(encoding="utf-8") == "x = 1\n"


def test_format_python_leaves_autofixes_alone_by_default(tmp_path: Path) -> None:
    """OURS must never be autofixed: that would rewrite the client's own code into the
    merged tree and materialize onto the upgrade branch as edits they never made."""
    (tmp_path / "m.py").write_text("import os\nx=1\n", encoding="utf-8")
    assert format_python(tmp_path) is True
    assert (tmp_path / "m.py").read_text(encoding="utf-8") == "import os\n\nx = 1\n"


def test_format_python_autofix_matches_the_post_gen_hook(tmp_path: Path) -> None:
    """The post-gen hook runs `ruff check --fix` before `ruff format`, so a rendered
    tree (which neutralizes the hook's formatter) needs the same pass or every unused
    import the hook stripped reads as a client edit for the rest of the project's life."""
    (tmp_path / "m.py").write_text("import os\nx=1\n", encoding="utf-8")
    assert format_python(tmp_path, autofix=True) is True
    assert (tmp_path / "m.py").read_text(encoding="utf-8") == "x = 1\n"


def test_normalize_tree_autofixes_only_rendered_trees(tmp_path: Path) -> None:
    """`rendered=True` is the one deliberate asymmetry between the three trees."""
    for name in ("rendered", "ours"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "m.py").write_text("import os\nx = 1\n", encoding="utf-8")

    normalize_tree(tmp_path / "rendered", rendered=True)
    normalize_tree(tmp_path / "ours", rendered=False)

    assert (tmp_path / "rendered" / "m.py").read_text(encoding="utf-8") == "x = 1\n"
    assert (tmp_path / "ours" / "m.py").read_text(encoding="utf-8") == "import os\n\nx = 1\n"


def test_format_python_reports_false_when_ruff_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("fastapi_gen.upgrade.normalize._ruff_cmd", lambda *_a: None)
    (tmp_path / "m.py").write_text("x=1\n", encoding="utf-8")
    assert format_python(tmp_path) is False
    assert (tmp_path / "m.py").read_text(encoding="utf-8") == "x=1\n"


def test_normalize_tree_makes_formatting_symmetric(tmp_path: Path) -> None:
    """OURS-style formatted and THEIRS-style raw converge after normalization."""
    formatted = tmp_path / "ours"
    raw = tmp_path / "theirs"
    for tree, body in ((formatted, "x = 1\n"), (raw, "x=1\n")):
        (tree / "backend").mkdir(parents=True)
        (tree / "backend" / "m.py").write_text(body, encoding="utf-8")

    normalize_tree(formatted, generated_at=None, format_code=True)
    normalize_tree(raw, generated_at=None, format_code=True)

    assert (formatted / "backend" / "m.py").read_text() == (raw / "backend" / "m.py").read_text()


def test_format_frontend_runs_prettier_and_cleans_up(tmp_path: Path) -> None:
    tree = tmp_path / "tree"
    frontend = tree / "frontend"
    frontend.mkdir(parents=True)
    (frontend / "app.ts").write_text("a=1\n", encoding="utf-8")
    nm = _fake_node_modules(tmp_path, "#!/bin/sh\nprintf 'a = 1\\n' > app.ts\n")

    assert format_frontend(tree, node_modules=nm) is True
    assert (frontend / "app.ts").read_text() == "a = 1\n"
    assert not (frontend / "node_modules").exists()


def test_format_frontend_pins_shared_config_and_ignore(tmp_path: Path) -> None:
    """One config for all three trees, like the shared ruff config.

    Without it Prettier resolves each tree's own .prettierrc — the client's for OURS,
    the template's for BASE/THEIRS — so every .ts/.tsx file formats differently and
    reads as a client edit, turning each real template change into a conflict.
    """
    tree = tmp_path / "tree"
    frontend = tree / "frontend"
    frontend.mkdir(parents=True)
    (frontend / "app.ts").write_text("a=1\n", encoding="utf-8")
    config = tmp_path / "client.prettierrc"
    config.write_text("{}\n", encoding="utf-8")
    ignore = tmp_path / "client.prettierignore"
    ignore.write_text("dist\n", encoding="utf-8")
    nm = _fake_node_modules(tmp_path, '#!/bin/sh\nprintf "%s\\n" "$@" > args.txt\n')

    assert format_frontend(tree, node_modules=nm, config=config, ignore_path=ignore) is True

    args = (frontend / "args.txt").read_text().split()
    assert args == ["--write", "--config", str(config), "--ignore-path", str(ignore), "."]


def test_format_frontend_omits_missing_config(tmp_path: Path) -> None:
    """A client who deleted their .prettierrc still gets a Prettier pass."""
    tree = tmp_path / "tree"
    frontend = tree / "frontend"
    frontend.mkdir(parents=True)
    nm = _fake_node_modules(tmp_path, '#!/bin/sh\nprintf "%s\\n" "$@" > args.txt\n')

    assert (
        format_frontend(
            tree,
            node_modules=nm,
            config=tmp_path / "nope.prettierrc",
            ignore_path=tmp_path / "nope.prettierignore",
        )
        is True
    )
    assert (frontend / "args.txt").read_text().split() == ["--write", "."]


def test_format_frontend_skips_without_node_modules(tmp_path: Path) -> None:
    tree = tmp_path / "tree"
    (tree / "frontend").mkdir(parents=True)
    (tree / "frontend" / "app.ts").write_text("a=1\n", encoding="utf-8")

    assert format_frontend(tree, node_modules=None) is False
    assert (tree / "frontend" / "app.ts").read_text() == "a=1\n"


def test_format_frontend_skips_without_frontend_dir(tmp_path: Path) -> None:
    tree = tmp_path / "tree"
    tree.mkdir()
    nm = _fake_node_modules(tmp_path, "#!/bin/sh\nexit 0\n")
    assert format_frontend(tree, node_modules=nm) is False


def test_format_frontend_does_not_clobber_real_node_modules(tmp_path: Path) -> None:
    tree = tmp_path / "tree"
    frontend = tree / "frontend"
    (frontend / "node_modules").mkdir(parents=True)
    nm = _fake_node_modules(tmp_path, "#!/bin/sh\nexit 1\n")
    assert format_frontend(tree, node_modules=nm) is False
    assert (frontend / "node_modules").is_dir()


def test_format_frontend_returns_false_on_symlink_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tree = tmp_path / "tree"
    (tree / "frontend").mkdir(parents=True)
    nm = _fake_node_modules(tmp_path, "#!/bin/sh\n")

    def _boom(*_a: object, **_k: object) -> None:
        raise OSError("no symlinks")

    monkeypatch.setattr(Path, "symlink_to", _boom)
    assert format_frontend(tree, node_modules=nm) is False


def test_format_frontend_returns_false_when_prettier_exec_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken prettier (e.g. dangling symlink) must be swallowed, not abort the upgrade."""
    tree = tmp_path / "tree"
    (tree / "frontend").mkdir(parents=True)
    nm = _fake_node_modules(tmp_path, "#!/bin/sh\n")

    def _boom(*_a: object, **_k: object) -> None:
        raise OSError("cannot exec")

    monkeypatch.setattr(normalize_mod.subprocess, "run", _boom)
    assert format_frontend(tree, node_modules=nm) is False
    assert not (tree / "frontend" / "node_modules").exists()


def test_normalize_whitespace_leaves_prose_content_intact(tmp_path: Path) -> None:
    """Only line endings change for non-code files — trailing spaces (MD hard-breaks)
    and whitespace-only content survive so the merged tree never mutates them."""
    md = tmp_path / "README.md"
    md.write_text("line with break  \r\n\r\n", encoding="utf-8")
    normalize_whitespace(tmp_path)
    assert md.read_text(encoding="utf-8") == "line with break  \n\n"


def test_normalize_whitespace_strips_code_files(tmp_path: Path) -> None:
    py = tmp_path / "m.py"
    py.write_text("x = 1  \n\n\n", encoding="utf-8")
    normalize_whitespace(tmp_path)
    assert py.read_text(encoding="utf-8") == "x = 1\n"


def test_restore_generated_at_noop_when_value_empty(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text(f"# {_GENERATED_AT_PLACEHOLDER}\n", encoding="utf-8")
    restore_generated_at(tmp_path, None)
    assert _GENERATED_AT_PLACEHOLDER in f.read_text(encoding="utf-8")


def test_restore_generated_at_replaces_placeholder(tmp_path: Path) -> None:
    f = tmp_path / "versions" / "mig.py"
    f.parent.mkdir()
    f.write_text(f"# Create Date: {_GENERATED_AT_PLACEHOLDER}\n", encoding="utf-8")
    restore_generated_at(tmp_path, "2020-01-02 03:04:05")
    assert f.read_text(encoding="utf-8") == "# Create Date: 2020-01-02 03:04:05\n"


@pytest.mark.parametrize("parent", ["build", "dist", "venv", "node_modules"])
def test_skip_dirs_only_match_inside_the_tree(tmp_path: Path, parent: str) -> None:
    """A skip-list name in an *ancestor* directory must not veto the whole tree.

    rglob yields absolute paths, so matching the skip-list against the full path let a
    project at ~/build/myapp (or a Docker WORKDIR /build, or a CI checkout under
    /builds/) skip normalization entirely. That failed asymmetrically: the rendered
    trees live under /tmp and were still stripped, so restore_generated_at() over the
    client's repo silently no-op'd and the placeholder shipped into their migrations.
    """
    tree = tmp_path / parent / "myapp"
    migration = tree / "backend" / "alembic" / "versions" / "0000_init.py"
    migration.parent.mkdir(parents=True)
    migration.write_text(f"# Create Date: {_GENERATED_AT_PLACEHOLDER}\n", encoding="utf-8")

    restore_generated_at(tree, "2020-01-02 03:04:05")

    assert migration.read_text(encoding="utf-8") == "# Create Date: 2020-01-02 03:04:05\n"


def test_skip_dirs_still_match_inside_the_tree(tmp_path: Path) -> None:
    """The exclusion itself must keep working for real build output under the tree."""
    excluded = tmp_path / "frontend" / "node_modules" / "pkg" / "index.ts"
    excluded.parent.mkdir(parents=True)
    excluded.write_text(f"// {_GENERATED_AT_PLACEHOLDER}\n", encoding="utf-8")

    restore_generated_at(tmp_path, "2020-01-02 03:04:05")

    assert _GENERATED_AT_PLACEHOLDER in excluded.read_text(encoding="utf-8")


def test_merge_shares_the_single_skip_dir_set() -> None:
    """merge.is_excluded and normalize must never drift apart on what to skip.

    A dir the merge walks but normalize skips keeps its files unformatted in all three
    trees, so every template change there degrades into a conflict.
    """
    from fastapi_gen.upgrade import merge as merge_mod

    assert merge_mod._EXCLUDED_DIRS is normalize_mod.SKIP_DIRS


def test_is_binary_returns_true_on_oserror(tmp_path: Path) -> None:
    assert normalize_mod._is_binary(tmp_path) is True  # opening a dir raises → defensive True


def test_ruff_cmd_falls_back_to_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(normalize_mod.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        normalize_mod.subprocess, "run", lambda *_a, **_k: SimpleNamespace(returncode=0)
    )
    assert _ruff_cmd() == [sys.executable, "-m", "ruff"]


def test_ruff_cmd_none_when_module_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(normalize_mod.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        normalize_mod.subprocess, "run", lambda *_a, **_k: SimpleNamespace(returncode=1)
    )
    assert _ruff_cmd() is None
