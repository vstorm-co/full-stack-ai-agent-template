"""Loader for ``UPGRADES.yaml`` — maintainer-curated structural metadata.

Content diffing can't see that a file was renamed/moved or a variable renamed
between versions; it reads those as unrelated delete+add and loses the client's
edits. ``UPGRADES.yaml`` records those structural facts per release. The
loader composes every block in the half-open range ``(from_version, to_version]``
into a single view the upgrade run consumes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from packaging.version import InvalidVersion, Version

UPGRADES_FILENAME = "UPGRADES.yaml"


@dataclass
class Rename:
    """A file/dir move. A trailing ``/`` on ``from_path`` means a whole directory."""

    from_path: str
    to_path: str
    version: str

    @property
    def is_dir(self) -> bool:
        return self.from_path.endswith("/")


@dataclass
class VariableRename:
    from_key: str
    to_key: str
    version: str
    value_map: dict[str, str] = field(default_factory=dict)


@dataclass
class UpgradeMetadata:
    """Composed structural metadata for a version range."""

    renames: list[Rename] = field(default_factory=list)
    variable_renames: list[VariableRename] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    breaking: list[str] = field(default_factory=list)
    manual_steps: list[str] = field(default_factory=list)


def _parse_version(version: str) -> Version:
    """Parse a version with correct pre/post-release ordering (PEP 440).

    Falls back to ``0`` for an unparseable string so a malformed UPGRADES.yaml entry
    sorts first instead of crashing the whole run.
    """
    try:
        return Version(version.lstrip("v"))
    except InvalidVersion:
        return Version("0")


def _in_range(version: str, from_version: str, to_version: str) -> bool:
    """True for from_version < version <= to_version (half-open, ascending)."""
    return _parse_version(from_version) < _parse_version(version) <= _parse_version(to_version)


def load_upgrades_file(path: Path) -> list[dict]:
    """Parse UPGRADES.yaml into an ascending-by-version list of release blocks.

    Raises:
        ValueError: If the file is not a list of well-formed release blocks.
    """
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a list of release blocks.")
    blocks: list[dict] = []
    for raw in data:
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: every release block must be a mapping, got {raw!r}.")
        _validate_block(path, raw)
        blocks.append(raw)
    return sorted(blocks, key=lambda b: _parse_version(str(b.get("version", "0"))))


def _validate_block(path: Path, block: dict) -> None:
    """Reject a malformed release block here, at the one place the file is read.

    UPGRADES.yaml is hand-curated, and three separate consumers walk these blocks
    (:func:`compose_metadata` plus the two release scripts). Each indexes ``r["from"]``
    / ``r["to"]`` directly, so a typo'd or half-written entry would surface as a bare
    ``KeyError`` from whichever one happened to run — with nothing naming the file.
    """
    for key in ("renames", "variable_renames"):
        for entry in block.get(key) or []:
            if not isinstance(entry, dict) or "from" not in entry or "to" not in entry:
                raise ValueError(
                    f"{path}: every `{key}` entry needs both `from:` and `to:` — "
                    f"got {entry!r} in block {block.get('version', '?')!r}."
                )


def compose_metadata(
    blocks: list[dict],
    from_version: str,
    to_version: str,
) -> UpgradeMetadata:
    """Compose all release blocks in (from_version, to_version] into one view.

    Renames are collected in version order so multi-version chains (a→b at V1,
    b→c at V2) can later be resolved a→c by applying them in sequence.
    """
    meta = UpgradeMetadata()
    for block in blocks:
        version = str(block.get("version", "0"))
        if not _in_range(version, from_version, to_version):
            continue
        for r in block.get("renames", []) or []:
            meta.renames.append(Rename(from_path=r["from"], to_path=r["to"], version=version))
        for v in block.get("variable_renames", []) or []:
            meta.variable_renames.append(
                VariableRename(
                    from_key=v["from"],
                    to_key=v["to"],
                    version=version,
                    value_map=dict(v.get("value_map", {}) or {}),
                )
            )
        meta.removed.extend(block.get("removed", []) or [])
        meta.breaking.extend(block.get("breaking", []) or [])
        meta.manual_steps.extend(block.get("manual_steps", []) or [])
    return meta


def load_metadata(repo_or_file: Path, from_version: str, to_version: str) -> UpgradeMetadata:
    """Convenience: locate UPGRADES.yaml, load, and compose for a version range."""
    path = repo_or_file if repo_or_file.is_file() else repo_or_file / UPGRADES_FILENAME
    return compose_metadata(load_upgrades_file(path), from_version, to_version)
