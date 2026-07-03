"""Tests for fastapi_gen.upgrade.normalize — formatter availability + tree passes."""

from __future__ import annotations

from pathlib import Path

from fastapi_gen.upgrade.normalize import (
    _ruff_cmd,
    format_frontend,
    format_python,
    normalize_tree,
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


def test_format_python_reports_false_when_ruff_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("fastapi_gen.upgrade.normalize._ruff_cmd", lambda: None)
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
