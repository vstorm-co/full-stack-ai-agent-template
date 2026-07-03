"""Tests for scripts/record_renames.py helpers and rename-block formatting."""

from __future__ import annotations

from pathlib import Path

import scripts.record_renames as rr
from fastapi_gen.upgrade.metadata import compose_metadata, load_upgrades_file
from fastapi_gen.upgrade.rename_guard import Move, format_renames_block


def test_format_renames_block_matches_schema_style() -> None:
    block = format_renames_block("0.2.15", [Move("a/old.py", "a/new.py", 0.9)])
    assert block == (
        '- version: "0.2.15"\n'
        "  renames:\n"
        '    - from: "a/old.py"\n'
        '      to:   "a/new.py"\n'
    )


def test_write_preserves_header_comment(tmp_path: Path) -> None:
    path = tmp_path / "UPGRADES.yaml"
    path.write_text("# my header\n# schema notes\n\n[]\n", encoding="utf-8")

    rr._write_upgrades(path, [{"version": "0.3.0", "renames": [{"from": "a", "to": "b"}]}])

    text = path.read_text(encoding="utf-8")
    assert text.startswith("# my header\n# schema notes\n")
    assert "version: 0.3.0" in text


def test_write_round_trips_through_loader(tmp_path: Path) -> None:
    path = tmp_path / "UPGRADES.yaml"
    path.write_text("[]\n", encoding="utf-8")

    rr._write_upgrades(
        path,
        [{"version": "0.3.0", "renames": [{"from": "old/x.py", "to": "new/x.py"}]}],
    )

    meta = compose_metadata(load_upgrades_file(path), "0.2.0", "0.3.0")
    assert [(r.from_path, r.to_path) for r in meta.renames] == [("old/x.py", "new/x.py")]


def test_write_drops_empty_keys_and_sorts_versions(tmp_path: Path) -> None:
    path = tmp_path / "UPGRADES.yaml"
    path.write_text("[]\n", encoding="utf-8")

    rr._write_upgrades(
        path,
        [
            {"version": "0.4.0", "renames": [{"from": "c", "to": "d"}]},
            {"version": "0.3.0", "renames": [], "breaking": ["x"]},
        ],
    )

    blocks = load_upgrades_file(path)
    assert [b["version"] for b in blocks] == ["0.3.0", "0.4.0"]
    assert "renames" not in blocks[0]
    assert blocks[0]["breaking"] == ["x"]


def test_known_renames_collects_across_blocks() -> None:
    known = rr._known_renames(
        [
            {"version": "0.2.0", "renames": [{"from": "a", "to": "b"}]},
            {"version": "0.3.0", "renames": [{"from": "c", "to": "d"}]},
        ]
    )
    assert known == {("a", "b"), ("c", "d")}
