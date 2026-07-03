"""Classify every path across BASE / OURS / THEIRS for the upgrade report.

Implements the file-classification matrix. The merge engine (merge.py) decides
what actually gets written; this module produces the human-facing grouping shown in
the report so the developer sees *why* each change is proposed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from .merge import is_excluded

_MIGRATIONS_MARKER = "alembic/versions/"


def _file_hashes(tree: Path) -> dict[str, str]:
    """Map in-scope repo-relative path → content hash for a rendered tree."""
    hashes: dict[str, str] = {}
    for path in tree.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(tree).as_posix()
        if is_excluded(rel):
            continue
        hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


@dataclass
class Classification:
    """Grouped upgrade outcome (each list holds repo-relative paths)."""

    auto_updated: list[str] = field(default_factory=list)
    client_kept: list[str] = field(default_factory=list)
    converged: list[str] = field(default_factory=list)
    auto_merged: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    new_files: list[str] = field(default_factory=list)
    new_migrations: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    client_only: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    other: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.auto_updated
            or self.converged
            or self.auto_merged
            or self.conflicts
            or self.other
            or self.new_files
            or self.new_migrations
            or self.removed
        )


def classify_trees(
    base_dir: Path,
    ours_dir: Path,
    theirs_dir: Path,
    conflicted_paths: set[str],
) -> Classification:
    """Classify each path per the classification matrix; conflicts come from the merge."""
    base, ours, theirs = _file_hashes(base_dir), _file_hashes(ours_dir), _file_hashes(theirs_dir)
    result = Classification()

    for path in sorted(set(base) | set(ours) | set(theirs)):
        in_base, in_ours, in_theirs = path in base, path in ours, path in theirs

        if path in conflicted_paths:
            result.conflicts.append(path)
            continue

        if not in_base and not in_ours and in_theirs:
            (result.new_migrations if _MIGRATIONS_MARKER in path else result.new_files).append(path)
        elif in_base and in_ours and not in_theirs:
            if base[path] == ours[path]:
                result.removed.append(path)
            else:
                result.auto_merged.append(path)
        elif not in_base and in_ours and not in_theirs:
            result.client_only.append(path)
        elif not in_base and in_ours and in_theirs:
            if ours[path] == theirs[path]:
                result.converged.append(path)
            else:
                result.auto_merged.append(path)
        elif in_base and in_ours and in_theirs:
            b, o, t = base[path], ours[path], theirs[path]
            if b == o == t:
                result.unchanged.append(path)
            elif o == b and t != b:
                result.auto_updated.append(path)
            elif t == b and o != b:
                result.client_kept.append(path)
            elif o == t and o != b:
                result.converged.append(path)
            else:
                result.auto_merged.append(path)
        else:
            result.other.append(path)

    return result
