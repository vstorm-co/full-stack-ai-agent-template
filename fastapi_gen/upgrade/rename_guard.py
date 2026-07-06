"""Release guard: fail if a file move lacks an ``UPGRADES.yaml`` rename entry.

``UPGRADES.yaml`` is only as reliable as the discipline behind it — a forgotten
``renames`` block silently degrades to delete+add and loses client edits. This guard
(run in CI on every release) diffs the previous release's template tree against the
candidate's, finds likely moves (a deletion + an addition of similar content), and
requires each to be covered by a ``renames`` entry or an explicit waiver.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_THRESHOLD = 0.5

_MIN_MATCH_LEN = 8

_SLUG_PREFIX = "{{cookiecutter.project_slug}}/"


@dataclass(frozen=True)
class Move:
    from_path: str
    to_path: str
    similarity: float


def _strip_slug(rel: str) -> str:
    return rel[len(_SLUG_PREFIX) :] if rel.startswith(_SLUG_PREFIX) else rel


def template_files(template_dir: Path) -> dict[str, str]:
    """Map rendered-relative path → file text for a template's project subtree."""
    files: dict[str, str] = {}
    for path in template_dir.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(template_dir).as_posix()
        if not rel.startswith(_SLUG_PREFIX):
            continue
        try:
            files[_strip_slug(rel)] = path.read_text(encoding="utf-8", errors="surrogateescape")
        except OSError:
            continue
    return files


def detect_moves(
    old_files: dict[str, str],
    new_files: dict[str, str],
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[Move]:
    """Pair deletions with additions by content similarity to infer moves.

    Greedy best-match: each deleted path is matched to its most-similar addition
    above ``threshold``; each addition is claimed at most once.
    """
    deleted = sorted(set(old_files) - set(new_files))
    added = sorted(set(new_files) - set(old_files))
    moves: list[Move] = []
    claimed: set[str] = set()

    for old_path in deleted:
        best_ratio, best_new = 0.0, None
        old_text = old_files[old_path]
        if len(old_text) < _MIN_MATCH_LEN:
            continue
        for new_path in added:
            if new_path in claimed:
                continue
            new_text = new_files[new_path]
            if len(new_text) < _MIN_MATCH_LEN:
                continue
            ratio = difflib.SequenceMatcher(None, old_text, new_text).ratio()
            if ratio > best_ratio:
                best_ratio, best_new = ratio, new_path
        if best_new is not None and best_ratio >= threshold:
            claimed.add(best_new)
            moves.append(Move(old_path, best_new, round(best_ratio, 3)))
    return moves


def format_renames_block(version: str, moves: list[Move]) -> str:
    """Render moves as a ready-to-paste ``UPGRADES.yaml`` release block."""
    lines = [f'- version: "{version}"', "  renames:"]
    for move in moves:
        lines.append(f'    - from: "{move.from_path}"')
        lines.append(f'      to:   "{move.to_path}"')
    return "\n".join(lines) + "\n"


def uncovered_moves(
    moves: list[Move],
    known_renames: set[tuple[str, str]],
    waivers: set[str] | None = None,
) -> list[Move]:
    """Return moves lacking a matching UPGRADES.yaml rename entry or waiver.

    A directory rename ``a/ → b/`` in ``known_renames`` covers any file move whose
    paths sit under those prefixes.
    """
    waivers = waivers or set()
    uncovered: list[Move] = []
    for move in moves:
        if move.from_path in waivers:
            continue
        if (move.from_path, move.to_path) in known_renames:
            continue
        if any(
            frm.endswith("/")
            and to.endswith("/")
            and move.from_path.startswith(frm)
            and move.to_path.startswith(to)
            for frm, to in known_renames
        ):
            continue
        uncovered.append(move)
    return uncovered
