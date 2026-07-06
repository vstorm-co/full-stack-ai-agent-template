#!/usr/bin/env python
"""Auto-record file moves into UPGRADES.yaml so releases don't lose client edits.

Detects likely renames/moves between the latest published template and the current
working tree (content-similarity pairing), then writes the ones not already covered
into UPGRADES.yaml under the current version's block. You review the diff and add
any `breaking` / `manual_steps` / `variable_renames` by hand — those describe intent
a diff cannot infer.

Usage:
    uv run python scripts/record_renames.py [--old 0.2.13] [--version 0.2.15] \
        [--threshold 0.5] [--dry-run] [--waive backend/app/x.py ...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from fastapi_gen.config import get_generator_version
from fastapi_gen.generator import _find_template_dir
from fastapi_gen.upgrade.fetch import TemplateFetchError, fetch_template, latest_pypi_version
from fastapi_gen.upgrade.metadata import UPGRADES_FILENAME, _parse_version, load_upgrades_file
from fastapi_gen.upgrade.rename_guard import (
    DEFAULT_THRESHOLD,
    detect_moves,
    format_renames_block,
    template_files,
    uncovered_moves,
)

_KEY_ORDER = ["version", "renames", "variable_renames", "removed", "breaking", "manual_steps"]


def _known_renames(blocks: list[dict]) -> set[tuple[str, str]]:
    known: set[tuple[str, str]] = set()
    for block in blocks:
        for r in block.get("renames", []) or []:
            known.add((r["from"], r["to"]))
    return known


def _split_header(text: str) -> str:
    """Return the leading comment/blank block so the rewrite preserves it."""
    header: list[str] = []
    for line in text.splitlines():
        if line.strip() == "" or line.lstrip().startswith("#"):
            header.append(line)
        else:
            break
    if not header:
        return ""
    return "\n".join(header).rstrip("\n") + "\n\n"


def _clean_block(block: dict) -> dict:
    return {k: block[k] for k in _KEY_ORDER if block.get(k)}


def _write_upgrades(path: Path, blocks: list[dict]) -> None:
    header = _split_header(path.read_text(encoding="utf-8")) if path.exists() else ""
    ordered = sorted(blocks, key=lambda b: _parse_version(str(b.get("version", "0"))))
    cleaned = [_clean_block(b) for b in ordered]
    body = yaml.safe_dump(cleaned, sort_keys=False, allow_unicode=True) if cleaned else "[]\n"
    path.write_text(header + body, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", default=None, help="Baseline version (default: latest on PyPI).")
    parser.add_argument("--version", default=None, help="Target version (default: current).")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--dry-run", action="store_true", help="Print the block, write nothing.")
    parser.add_argument("--waive", nargs="*", default=[], help="Paths to skip.")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    upgrades_path = repo_root / UPGRADES_FILENAME
    current_template = _find_template_dir()
    version = args.version or get_generator_version()

    try:
        old_version = args.old or latest_pypi_version()
        old_template = fetch_template(old_version)
    except TemplateFetchError as exc:
        print(f"Could not resolve/fetch baseline template: {exc}", file=sys.stderr)
        return 1

    moves = detect_moves(
        template_files(old_template),
        template_files(current_template),
        threshold=args.threshold,
    )
    blocks = load_upgrades_file(upgrades_path)
    new_moves = uncovered_moves(moves, _known_renames(blocks), set(args.waive))

    if not new_moves:
        print(f"No new moves to record ({len(moves)} detected, all already covered).")
        return 0

    print(f"Detected {len(new_moves)} new move(s) for version {version}:")
    for move in new_moves:
        print(f"  {move.from_path}  →  {move.to_path}  (similarity {move.similarity})")

    if args.dry_run:
        print("\n--- proposed UPGRADES.yaml block (dry-run, nothing written) ---")
        print(format_renames_block(version, new_moves), end="")
        return 0

    target = next((b for b in blocks if str(b.get("version")) == version), None)
    if target is None:
        target = {"version": version}
        blocks.append(target)
    renames = list(target.get("renames", []) or [])
    renames.extend({"from": m.from_path, "to": m.to_path} for m in new_moves)
    target["renames"] = renames

    _write_upgrades(upgrades_path, blocks)
    print(f"\nWrote {len(new_moves)} rename(s) to {UPGRADES_FILENAME} under version {version}.")
    print("Review the diff — fix any mis-paired moves, then add breaking / manual_steps by hand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
