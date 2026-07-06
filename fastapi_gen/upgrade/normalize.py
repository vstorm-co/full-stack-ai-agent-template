"""Normalize rendered trees so the 3-way merge sees only real differences.

Two classes of noise would otherwise flood the merge with false conflicts:

* **Volatile stamps** — ``generated_at`` is rendered into every
  ``alembic/versions/*.py`` (``Create Date:``) and differs across BASE, OURS and
  THEIRS (three different render/generation times), which would conflict on every
  migration file. We blank it in all three trees.
* **Formatting** — the render neutralizes the hook's formatter, so BASE
  and THEIRS come out unformatted while OURS was formatted at generation. Running
  the *same* formatter over all three makes formatting cancel out. Backend uses
  ruff; frontend borrows the client's installed Prettier (see ``format_frontend``).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_GENERATED_AT_PLACEHOLDER = "<normalized-generated-at>"

_BINARY_SNIFF = 8192

_NORMALIZE_SUFFIXES = frozenset(
    {
        ".py",
        ".pyi",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".json",
        ".jsonc",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".html",
        ".vue",
        ".svelte",
        ".yaml",
        ".yml",
        ".toml",
    }
)


def _is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return b"\x00" in fh.read(_BINARY_SNIFF)
    except OSError:
        return True


_SKIP_DIRS = frozenset({".git", "node_modules", ".venv", "venv", ".next", "__pycache__"})


def _iter_text_files(tree: Path):
    for path in tree.rglob("*"):
        if _SKIP_DIRS.intersection(path.parts):
            continue
        if path.is_file() and not path.is_symlink() and not _is_binary(path):
            yield path


def strip_generated_at(tree: Path, value: str | None) -> None:
    """Replace the exact ``generated_at`` string with a fixed placeholder."""
    if not value:
        return
    for path in _iter_text_files(tree):
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
        if value in text:
            path.write_text(
                text.replace(value, _GENERATED_AT_PLACEHOLDER),
                encoding="utf-8",
                errors="surrogateescape",
            )


def restore_generated_at(tree: Path, value: str | None) -> None:
    """Reverse :func:`strip_generated_at` — put the real timestamp back.

    Run over the *materialized* client tree so the merged files never ship the
    ``<normalized-generated-at>`` placeholder (e.g. in Alembic ``Create Date:``).
    """
    if not value:
        return
    for path in _iter_text_files(tree):
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
        if _GENERATED_AT_PLACEHOLDER in text:
            path.write_text(
                text.replace(_GENERATED_AT_PLACEHOLDER, value),
                encoding="utf-8",
                errors="surrogateescape",
            )


def normalize_whitespace(tree: Path) -> None:
    """Convert CRLF→LF everywhere; strip trailing whitespace and enforce a single
    final newline only for formatter-owned code files.

    The final-newline rule matters for frontend files: generation runs Prettier
    (which trims blank lines at EOF) while the upgrade render is Prettier-neutralized,
    so raw trees keep the template's trailing blank lines. Collapsing them in all three
    trees cancels that difference before the merge. Prose files are only line-ending
    normalized, so writing the merged tree back never mutates intentional whitespace.
    """
    for path in _iter_text_files(tree):
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
        unified = text.replace("\r\n", "\n")
        if path.suffix in _NORMALIZE_SUFFIXES:
            stripped = "\n".join(line.rstrip() for line in unified.split("\n"))
            normalized = stripped.rstrip("\n") + "\n" if stripped.strip() else ""
        else:
            normalized = unified
        if normalized != text:
            path.write_text(normalized, encoding="utf-8", errors="surrogateescape")


def _ruff_cmd() -> list[str] | None:
    ruff = shutil.which("ruff")
    if ruff:
        return [ruff]
    probe = subprocess.run(
        [sys.executable, "-m", "ruff", "--version"], capture_output=True, check=False
    )
    return [sys.executable, "-m", "ruff"] if probe.returncode == 0 else None


def format_python(tree: Path) -> bool:
    """Best-effort ruff format+fix over a tree. Returns True if ruff ran."""
    backend = tree / "backend"
    target = backend if backend.exists() else tree
    cmd = _ruff_cmd()
    if not cmd:
        return False
    subprocess.run(
        [*cmd, "check", "--fix", "--quiet", str(target)], capture_output=True, check=False
    )
    subprocess.run([*cmd, "format", "--quiet", str(target)], capture_output=True, check=False)
    return True


def format_frontend(tree: Path, *, node_modules: Path | None) -> bool:
    """Best-effort Prettier pass over ``tree/frontend`` using the client's toolchain.

    Prettier can't be bundled (it needs Node + the project's plugins, e.g.
    prettier-plugin-tailwindcss), so we borrow the client's already-installed
    ``node_modules`` by symlinking it into the rendered tree, run the local Prettier
    binary, then remove the link. Returns True if Prettier ran.
    """
    frontend = tree / "frontend"
    if (
        node_modules is None
        or not (node_modules / ".bin" / "prettier").exists()
        or not frontend.is_dir()
    ):
        return False
    link = frontend / "node_modules"
    if link.exists() or link.is_symlink():
        return False
    try:
        link.symlink_to(node_modules.resolve())
    except OSError:
        return False
    try:
        subprocess.run(
            [str(link / ".bin" / "prettier"), "--write", "."],
            cwd=frontend,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    finally:
        link.unlink()
    return True


def normalize_tree(
    tree: Path,
    *,
    generated_at: str | None = None,
    format_code: bool = True,
    frontend_node_modules: Path | None = None,
) -> None:
    """Apply the full normalization pass to a tree (in place).

    Must be applied *identically* to BASE, OURS and THEIRS so differences cancel.
    """
    if format_code:
        format_python(tree)
        format_frontend(tree, node_modules=frontend_node_modules)
    strip_generated_at(tree, generated_at)
    normalize_whitespace(tree)
