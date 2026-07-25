#!/usr/bin/env python
"""Release guard — fail if a template file move lacks an UPGRADES.yaml entry.

Compares the current (working-tree) template against the latest published release
(or ``--old VERSION``) and requires every detected move to be covered by a
``renames`` block in UPGRADES.yaml or an explicit ``--waive PATH``.

Usage:
    uv run python scripts/check_rename_coverage.py [--old 0.2.13] [--threshold 0.5] \
        [--waive backend/app/x.py ...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fastapi_gen.config import get_generator_version
from fastapi_gen.generator import _find_template_dir
from fastapi_gen.upgrade.fetch import TemplateFetchError, fetch_template, latest_pypi_version
from fastapi_gen.upgrade.metadata import UPGRADES_FILENAME, _parse_version, load_upgrades_file
from fastapi_gen.upgrade.rename_guard import (
    DEFAULT_THRESHOLD,
    Move,
    covering_rename,
    detect_moves,
    format_renames_block,
    recorded_waivers,
    template_files,
    uncovered_moves,
)


def _known_renames(repo_root: Path) -> dict[tuple[str, str], str]:
    """Map (from, to) → the newest version whose block records that rename."""
    blocks = load_upgrades_file(repo_root / UPGRADES_FILENAME)
    versions: dict[tuple[str, str], str] = {}
    for block in blocks:
        version = str(block.get("version", "0"))
        for r in block.get("renames", []) or []:
            key = (r["from"], r["to"])
            if key not in versions or _parse_version(version) > _parse_version(versions[key]):
                versions[key] = version
    return versions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", default=None, help="Baseline version (default: latest on PyPI).")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--waive", nargs="*", default=[], help="Paths to exempt from the check.")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    current_template = _find_template_dir()

    try:
        old_version = args.old or latest_pypi_version()
        old_template = fetch_template(old_version)
    except TemplateFetchError as exc:
        msg = str(exc)
        no_baseline = args.old is None and ("404" in msg or "Not Found" in msg)
        if no_baseline:
            print(f"::warning:: no published baseline yet ({exc}); skipping rename guard.")
            return 0
        print(f"::error:: could not fetch baseline template: {exc}")
        return 2

    moves = detect_moves(
        template_files(old_template),
        template_files(current_template),
        threshold=args.threshold,
    )
    known = _known_renames(repo_root)
    blocks = load_upgrades_file(repo_root / UPGRADES_FILENAME)
    waived = set(args.waive) | recorded_waivers(blocks)
    uncovered = uncovered_moves(moves, set(known), waived)

    # Presence in the YAML isn't enough: a rename recorded under a version <= the
    # baseline is filtered out by the half-open (from, to] range at upgrade time.
    # Look the version up via the *covering* entry, not the move's own paths — a
    # directory rename `a/ → b/` covers files that are keyed by neither, and it is
    # the higher-stakes case: one stale entry loses client edits across a whole subtree.
    baseline = _parse_version(old_version)
    stale: list[tuple[Move, str]] = []
    for move in moves:
        if move in uncovered or move.from_path in waived:
            continue
        key = covering_rename(move, set(known))
        if key is not None and _parse_version(known[key]) <= baseline:
            stale.append((move, known[key]))

    if not uncovered and not stale:
        print(f"Rename guard OK — {len(moves)} move(s) detected, all covered.")
        return 0

    if stale:
        print(
            f"::error:: File moves recorded under a version <= baseline v{old_version} — "
            "they'd be filtered out of the upgrade range. Record them under the next release:"
        )
        for move, ver in stale:
            print(f"  {move.from_path}  →  {move.to_path}  (recorded under v{ver})")

    if not uncovered:
        return 1

    print("::error:: Uncovered file moves — add a `renames` entry to UPGRADES.yaml:")
    for move in uncovered:
        print(f"  {move.from_path}  →  {move.to_path}  (similarity {move.similarity})")
    print(
        f"\nPaste this block into {UPGRADES_FILENAME} "
        "(or run `uv run python scripts/record_renames.py`):\n"
    )
    print(format_renames_block(get_generator_version(), uncovered))
    print(
        "For an intentional delete+add (not a rename), record the path under `removed:` "
        "or `waived:` in the version's UPGRADES.yaml block so the waiver is versioned "
        "and CI honours it (or re-run locally with --waive <path>)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
