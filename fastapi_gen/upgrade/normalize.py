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

import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
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


# The single source of truth for "never look inside this directory" — merge.py imports
# it as its own exclusion set, because the two must agree in both directions: a dir the
# merge walks but we skip keeps its files unformatted in all three trees, so every
# template change there degrades into a conflict; a dir we walk but the merge skips is
# pure I/O (restore_generated_at() runs over the client's *whole* repo, so leaving build
# output in meant reading every file under .ruff_cache/, dist/ and friends).
SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".next",
        ".turbo",
        "dist",
        "build",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
)


def _iter_text_files(tree: Path) -> Iterator[Path]:
    # os.walk with an in-place `dirs` filter, not rglob: matching the skip-list against
    # rglob's *absolute* paths let an ancestor of the tree veto everything inside it (a
    # project at ~/build/myapp, a Docker WORKDIR /build, a CI checkout under /builds/),
    # which failed asymmetrically and silently — the rendered trees live under /tmp and
    # were still stripped, but restore_generated_at() over the client's repo became a
    # no-op and the placeholder shipped into their files. Walking relative to the tree
    # fixes that; pruning `dirs` is what makes it cheap, since rglob cannot prune and
    # would still descend into every node_modules just to discard the entries one by one
    # — and restore_generated_at() runs over the client's *whole* repo.
    for root, dirs, names in os.walk(tree):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            path = Path(root) / name
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


def _ruff_cmd(preferred: Path | None = None) -> list[str] | None:
    if preferred is not None and preferred.exists():
        return [str(preferred)]
    ruff = shutil.which("ruff")
    if ruff:
        return [ruff]
    probe = subprocess.run(
        [sys.executable, "-m", "ruff", "--version"], capture_output=True, check=False
    )
    return [sys.executable, "-m", "ruff"] if probe.returncode == 0 else None


def format_python(
    tree: Path,
    *,
    config: Path | None = None,
    ruff_bin: Path | None = None,
    autofix: bool = False,
) -> bool:
    """Best-effort ruff pass over a tree. Returns True if ruff ran.

    Four deliberate choices keep this from corrupting the merge:

    * ``autofix`` runs ``ruff check --fix`` before the format pass, and must be set for
      the *rendered* trees (BASE/THEIRS) only. The post-gen hook runs ``check --fix``
      *and* ``format`` at generation time, so OURS arrives already autofixed while a
      render — which neutralizes the hook's formatter — does not. Without this the two
      sides disagree on every unused import the hook stripped and every ``# ruff: noqa``
      it removed, and ~a third of the backend reads as client edits that never happened.
      Running it on OURS instead would rewrite the client's own code into the merged
      result, which is why it is opt-in per tree rather than unconditional.
    * The check pass deliberately gets **no** ``--config``: ``--config <file>`` moves
      ruff's project root to that file's directory (the client's ``backend/``), which
      changes isort's first-party detection and re-orders imports differently than
      generation did. Each rendered tree carries its own version's ``pyproject.toml``,
      which is exactly what that version's generator resolved.
    * A single ``config`` is applied to the *format* pass on all three trees. Without it
      ruff resolves each tree's own ``pyproject.toml`` — the *client's* (often customized
      line-length / rule set) for OURS but the template's for BASE/THEIRS — so the trees
      format differently and every file looks edited, drowning the merge in false
      conflicts.
    * A single ``ruff_bin`` (the client's own, when present) formats all three trees, so
      the delivered merged tree matches the ruff the client's project pins — otherwise a
      style change between the bundled ruff and theirs churns files the template never
      touched.

    A non-zero ruff exit is surfaced as a warning: if ruff fails on one tree (a syntax
    error in a client file, say) but not the others, the trees format asymmetrically and
    the merge floods with false conflicts — the user needs to know why.
    """
    backend = tree / "backend"
    target = backend if backend.exists() else tree
    cmd = _ruff_cmd(ruff_bin)
    if not cmd:
        return False
    if autofix:
        subprocess.run(
            [*cmd, "check", "--fix", "--quiet", str(target)], capture_output=True, check=False
        )
    fmt = [*cmd, "format", "--quiet"]
    if config is not None and config.exists():
        fmt += ["--config", str(config)]
    fmt.append(str(target))
    proc = subprocess.run(fmt, capture_output=True, check=False)
    if proc.returncode != 0:
        # Lazy import — report → classify → merge → normalize is a module cycle.
        from .report import console

        console.print(
            f"[yellow]⚠ ruff format exited {proc.returncode} on {target}[/] — formatting "
            "may be uneven across trees, which can add spurious merge conflicts."
        )
    return True


def format_frontend(
    tree: Path,
    *,
    node_modules: Path | None,
    config: Path | None = None,
    ignore_path: Path | None = None,
) -> bool:
    """Best-effort Prettier pass over ``tree/frontend`` using the client's toolchain.

    Prettier can't be bundled (it needs Node + the project's plugins, e.g.
    prettier-plugin-tailwindcss), so we borrow the client's already-installed
    ``node_modules`` by symlinking it into the rendered tree, run the local Prettier
    binary, then remove the link. A tree that already holds a usable install — OURS,
    when the client committed their ``node_modules`` — uses that one in place and is
    left untouched. Returns True if Prettier ran.

    ``config`` and ``ignore_path`` are the frontend twin of ``format_python``'s shared
    ruff config, and matter for the same reason: without them Prettier resolves each
    tree's *own* ``.prettierrc`` / ``.prettierignore`` — the client's (often a tweaked
    ``printWidth`` or ``singleQuote``) for OURS but the template's for BASE and THEIRS —
    so every ``.ts``/``.tsx`` file formats differently between the trees and reads as a
    client edit, which turns each real template change into a conflict.

    A non-zero Prettier exit is surfaced as a warning for the same reason
    :func:`format_python` does it: Prettier still formats what it can parse, so one tree
    that hits an unparseable file comes out formatted differently from the other two —
    and returning ``True`` (Prettier *did* run) means the caller's evenness check can't
    see it either.
    """
    frontend = tree / "frontend"
    if not frontend.is_dir():
        return False

    # A tree that already carries an install is OURS whenever the client committed their
    # frontend/node_modules, and it is never the freshly rendered BASE/THEIRS. Bailing
    # out there is exactly what made the run uneven — Prettier on two trees of three, so
    # every .tsx read as a client edit. Use the install that is already here instead.
    # Prettier ignores node_modules unless asked with --with-node-modules, so passing `.`
    # is safe either way.
    link = frontend / "node_modules"
    borrowed = not (link.exists() or link.is_symlink())
    if borrowed:
        if node_modules is None or not (node_modules / ".bin" / "prettier").exists():
            return False
        try:
            link.symlink_to(node_modules.resolve())
        except OSError:
            return False
    elif not (link / ".bin" / "prettier").exists():
        return False

    cmd = [str(link / ".bin" / "prettier"), "--write"]
    if config is not None and config.exists():
        cmd += ["--config", str(config)]
    if ignore_path is not None and ignore_path.exists():
        cmd += ["--ignore-path", str(ignore_path)]
    cmd.append(".")
    try:
        proc = subprocess.run(cmd, cwd=frontend, capture_output=True, check=False)
    except OSError:
        return False
    finally:
        if borrowed:
            link.unlink()
    if proc.returncode != 0:
        # Lazy import — report → classify → merge → normalize is a module cycle.
        from .report import console

        console.print(
            f"[yellow]⚠ Prettier exited {proc.returncode} on {frontend}[/] — formatting "
            "may be uneven across trees, which can add spurious merge conflicts."
        )
    return True


@dataclass(frozen=True, slots=True)
class FormattersRun:
    """Which formatters actually ran over a tree during normalization."""

    python: bool
    frontend: bool


def normalize_tree(
    tree: Path,
    *,
    generated_at: str | None = None,
    format_code: bool = True,
    frontend_node_modules: Path | None = None,
    ruff_config: Path | None = None,
    ruff_bin: Path | None = None,
    prettier_config: Path | None = None,
    prettier_ignore: Path | None = None,
    rendered: bool = False,
) -> FormattersRun:
    """Apply the full normalization pass to a tree (in place).

    Must be applied *identically* to BASE, OURS and THEIRS so differences cancel —
    which is why ``ruff_config`` / ``prettier_config`` (the one shared config per
    language) and ``ruff_bin`` (the one shared binary) are passed the same for all three.

    ``rendered`` is the one deliberate asymmetry: a freshly rendered tree (BASE/THEIRS)
    has not been through the post-gen hook's ``ruff check --fix``, while OURS was
    autofixed at generation time. See :func:`format_python`.

    Returns which formatters actually ran, so the caller can check they ran on *all*
    three trees. That is the invariant the merge rests on, and it can still break
    per-tree — a client who committed a ``frontend/node_modules`` with no Prettier in
    it, or whose platform refuses symlinks, gets Prettier on some trees and not others,
    and every ``.tsx`` file then reads as an edit they never made.
    """
    if not format_code:
        strip_generated_at(tree, generated_at)
        normalize_whitespace(tree)
        return FormattersRun(python=False, frontend=False)

    ran = FormattersRun(
        python=format_python(tree, config=ruff_config, ruff_bin=ruff_bin, autofix=rendered),
        frontend=format_frontend(
            tree,
            node_modules=frontend_node_modules,
            config=prettier_config,
            ignore_path=prettier_ignore,
        ),
    )
    strip_generated_at(tree, generated_at)
    normalize_whitespace(tree)
    return ran
