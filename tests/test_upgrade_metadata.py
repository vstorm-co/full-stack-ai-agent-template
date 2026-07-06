"""Tests for fastapi_gen.upgrade.metadata (UPGRADES.yaml)."""

from pathlib import Path

import pytest
import yaml

from fastapi_gen.upgrade.metadata import (
    Rename,
    compose_metadata,
    load_metadata,
    load_upgrades_file,
)

_BLOCKS = [
    {
        "version": "0.2.10",
        "renames": [{"from": "a.py", "to": "b.py"}],
        "variable_renames": [{"from": "use_x", "to": "enable_x", "value_map": {"1": "on"}}],
        "removed": ["old.py"],
        "breaking": ["X changed"],
        "manual_steps": ["do Y"],
    },
    {
        "version": "0.2.12",
        "renames": [{"from": "b.py", "to": "c.py"}],
    },
    {
        "version": "0.2.20",
        "breaking": ["far future"],
    },
]


class TestLoad:
    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert load_upgrades_file(tmp_path / "nope.yaml") == []

    def test_sorted_ascending(self, tmp_path: Path) -> None:
        p = tmp_path / "UPGRADES.yaml"
        p.write_text(yaml.safe_dump(list(reversed(_BLOCKS))), encoding="utf-8")
        loaded = load_upgrades_file(p)
        versions = [b["version"] for b in loaded]
        assert versions == ["0.2.10", "0.2.12", "0.2.20"]


class TestCompose:
    def test_range_is_half_open(self) -> None:
        meta = compose_metadata(_BLOCKS, "0.2.10", "0.2.12")
        assert [r.from_path for r in meta.renames] == ["b.py"]

    def test_composes_multiple_versions_in_order(self) -> None:
        meta = compose_metadata(_BLOCKS, "0.2.9", "0.2.12")
        assert [(r.from_path, r.to_path) for r in meta.renames] == [
            ("a.py", "b.py"),
            ("b.py", "c.py"),
        ]
        assert meta.removed == ["old.py"]
        assert meta.breaking == ["X changed"]
        assert meta.manual_steps == ["do Y"]
        assert meta.variable_renames[0].value_map == {"1": "on"}

    def test_excludes_out_of_range(self) -> None:
        meta = compose_metadata(_BLOCKS, "0.2.9", "0.2.12")
        assert "far future" not in meta.breaking


def test_load_metadata_convenience(tmp_path: Path) -> None:
    p = tmp_path / "UPGRADES.yaml"
    p.write_text(yaml.safe_dump(_BLOCKS), encoding="utf-8")
    meta = load_metadata(tmp_path, "0.2.9", "0.2.12")
    assert len(meta.renames) == 2


def test_rename_is_dir() -> None:
    assert Rename("a/", "b/", "1").is_dir is True
    assert Rename("a", "b", "1").is_dir is False


def test_load_upgrades_rejects_non_list(tmp_path: Path) -> None:
    path = tmp_path / "UPGRADES.yaml"
    path.write_text("version: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a list"):
        load_upgrades_file(path)


def test_parse_version_orders_prereleases_correctly() -> None:
    from fastapi_gen.upgrade.metadata import _parse_version

    assert _parse_version("0.2.14rc1") < _parse_version("0.2.14")
    assert _parse_version("v2.0") == _parse_version("2.0.0")


def test_parse_version_falls_back_on_garbage() -> None:
    from fastapi_gen.upgrade.metadata import _parse_version

    assert str(_parse_version("not-a-version")) == "0"
