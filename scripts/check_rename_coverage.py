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
from fastapi_gen.upgrade.metadata import UPGRADES_FILENAME, load_upgrades_file
from fastapi_gen.upgrade.rename_guard import (
    DEFAULT_THRESHOLD,
    detect_moves,
    format_renames_block,
    template_files,
    uncovered_moves,
)


def _known_renames(repo_root: Path) -> set[tuple[str, str]]:
    blocks = load_upgrades_file(repo_root / UPGRADES_FILENAME)
    renames: set[tuple[str, str]] = set()
    for block in blocks:
        for r in block.get("renames", []) or []:
            renames.add((r["from"], r["to"]))
    return renames


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
        print(f"::warning:: could not resolve/fetch baseline template: {exc}")
        return 0

    moves = detect_moves(
        template_files(old_template),
        template_files(current_template),
        threshold=args.threshold,
    )
    uncovered = uncovered_moves(moves, _known_renames(repo_root), set(args.waive))

    if not uncovered:
        print(f"Rename guard OK — {len(moves)} move(s) detected, all covered.")
        return 0

    print("::error:: Uncovered file moves — add a `renames` entry to UPGRADES.yaml:")
    for move in uncovered:
        print(f"  {move.from_path}  →  {move.to_path}  (similarity {move.similarity})")
    print(
        f"\nPaste this block into {UPGRADES_FILENAME} "
        "(or run `uv run python scripts/record_renames.py`):\n"
    )
    print(format_renames_block(get_generator_version(), uncovered))
    print("For intentional delete+add pairs, re-run with --waive <path>.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
