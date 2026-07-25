"""Tests for scripts/record_renames.py helpers and rename-block formatting."""

from __future__ import annotations

from pathlib import Path

import scripts.check_rename_coverage as cc
import scripts.record_renames as rr
from fastapi_gen.upgrade.fetch import TemplateFetchError
from fastapi_gen.upgrade.metadata import compose_metadata, load_upgrades_file
from fastapi_gen.upgrade.rename_guard import Move, format_renames_block

_SHARED = "def handler():\n    return compute() + 1\n" * 4  # long, identical → similarity 1.0


def _make_template(root: Path, files: dict[str, str]) -> Path:
    """Build a minimal cookiecutter template tree that ``template_files`` can read."""
    for rel, content in files.items():
        target = root / "{{cookiecutter.project_slug}}" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return root


def test_format_renames_block_matches_schema_style() -> None:
    block = format_renames_block("0.2.15", [Move("a/old.py", "a/new.py", 0.9)])
    assert block == (
        '- version: "0.2.15"\n  renames:\n    - from: "a/old.py"\n      to:   "a/new.py"\n'
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


# --- check_rename_coverage.main() -------------------------------------------------


def test_coverage_main_skips_when_no_published_baseline(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cc, "_find_template_dir", lambda: _make_template(tmp_path, {"a.py": "x"}))

    def _boom(**_kwargs):
        raise TemplateFetchError("404 Not Found")

    monkeypatch.setattr(cc, "latest_pypi_version", _boom)
    # No --old → a missing baseline is a soft skip (return 0), not a failure.
    assert cc.main([]) == 0


def test_coverage_main_fails_on_uncovered_move(tmp_path, monkeypatch) -> None:
    old = _make_template(tmp_path / "old", {"backend/app/old.py": _SHARED})
    new = _make_template(tmp_path / "new", {"backend/app/new.py": _SHARED})
    monkeypatch.setattr(cc, "_find_template_dir", lambda: new)
    monkeypatch.setattr(cc, "latest_pypi_version", lambda **_: "0.1.0")
    monkeypatch.setattr(cc, "fetch_template", lambda *_a, **_k: old)
    monkeypatch.setattr(cc, "load_upgrades_file", lambda _p: [])
    monkeypatch.setattr(cc, "_known_renames", lambda _r: {})

    assert cc.main([]) == 1


def test_coverage_main_passes_when_move_is_recorded(tmp_path, monkeypatch) -> None:
    old = _make_template(tmp_path / "old", {"backend/app/old.py": _SHARED})
    new = _make_template(tmp_path / "new", {"backend/app/new.py": _SHARED})
    monkeypatch.setattr(cc, "_find_template_dir", lambda: new)
    monkeypatch.setattr(cc, "latest_pypi_version", lambda **_: "0.1.0")
    monkeypatch.setattr(cc, "fetch_template", lambda *_a, **_k: old)
    monkeypatch.setattr(cc, "load_upgrades_file", lambda _p: [])
    # Recorded under a version newer than the baseline → covered, not stale.
    monkeypatch.setattr(
        cc, "_known_renames", lambda _r: {("backend/app/old.py", "backend/app/new.py"): "9.9.9"}
    )

    assert cc.main([]) == 0


def test_coverage_main_honours_versioned_waiver(tmp_path, monkeypatch) -> None:
    old = _make_template(tmp_path / "old", {"backend/app/old.py": _SHARED})
    new = _make_template(tmp_path / "new", {"backend/app/new.py": _SHARED})
    monkeypatch.setattr(cc, "_find_template_dir", lambda: new)
    monkeypatch.setattr(cc, "latest_pypi_version", lambda **_: "0.1.0")
    monkeypatch.setattr(cc, "fetch_template", lambda *_a, **_k: old)
    monkeypatch.setattr(cc, "_known_renames", lambda _r: {})
    # A `removed:` entry for the source path is a sanctioned "intentional delete+add".
    monkeypatch.setattr(
        cc,
        "load_upgrades_file",
        lambda _p: [{"version": "9.9.9", "removed": ["backend/app/old.py"]}],
    )

    assert cc.main([]) == 0


def test_coverage_main_fails_closed_when_the_baseline_wheel_is_missing(
    tmp_path, monkeypatch, capsys
) -> None:
    """A 404 fetching the *wheel* of a published version is infrastructure, not a
    missing baseline — treating it as one skips the guard in exactly the case it exists
    to block."""
    monkeypatch.setattr(cc, "_find_template_dir", lambda: _make_template(tmp_path, {"a.py": "x"}))
    monkeypatch.setattr(cc, "latest_pypi_version", lambda **_: "0.1.0")

    def _boom(*_a, **_k):
        raise TemplateFetchError("HTTP Error 404: Not Found")

    monkeypatch.setattr(cc, "fetch_template", _boom)

    assert cc.main([]) == 2
    assert "::error::" in capsys.readouterr().out


def test_coverage_main_refuses_to_suggest_a_stale_version(tmp_path, monkeypatch, capsys) -> None:
    """Mid-cycle the working tree still reports the published version, and a block
    recorded there is filtered right back out by the half-open (from, to] range."""
    old = _make_template(tmp_path / "old", {"backend/app/old.py": _SHARED})
    new = _make_template(tmp_path / "new", {"backend/app/new.py": _SHARED})
    monkeypatch.setattr(cc, "_find_template_dir", lambda: new)
    monkeypatch.setattr(cc, "latest_pypi_version", lambda **_: "0.1.0")
    monkeypatch.setattr(cc, "fetch_template", lambda *_a, **_k: old)
    monkeypatch.setattr(cc, "load_upgrades_file", lambda _p: [])
    monkeypatch.setattr(cc, "_known_renames", lambda _r: {})
    monkeypatch.setattr(cc, "get_generator_version", lambda: "0.1.0")

    assert cc.main([]) == 1
    out = capsys.readouterr().out
    assert '- version: "<next-release>"' in out
    assert '- version: "0.1.0"' not in out


def test_coverage_main_suggests_the_running_version_once_bumped(
    tmp_path, monkeypatch, capsys
) -> None:
    old = _make_template(tmp_path / "old", {"backend/app/old.py": _SHARED})
    new = _make_template(tmp_path / "new", {"backend/app/new.py": _SHARED})
    monkeypatch.setattr(cc, "_find_template_dir", lambda: new)
    monkeypatch.setattr(cc, "latest_pypi_version", lambda **_: "0.1.0")
    monkeypatch.setattr(cc, "fetch_template", lambda *_a, **_k: old)
    monkeypatch.setattr(cc, "load_upgrades_file", lambda _p: [])
    monkeypatch.setattr(cc, "_known_renames", lambda _r: {})
    monkeypatch.setattr(cc, "get_generator_version", lambda: "0.2.0")

    assert cc.main([]) == 1
    assert '- version: "0.2.0"' in capsys.readouterr().out


# --- record_renames.main() --------------------------------------------------------


def test_record_main_refuses_recording_at_or_below_baseline(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(rr, "_find_template_dir", lambda: _make_template(tmp_path, {"a.py": "x"}))
    monkeypatch.setattr(rr, "fetch_template", lambda *_a, **_k: tmp_path)
    # Recording under 0.0.1 with baseline 9.9.9 would be filtered out of the range.
    assert rr.main(["--old", "9.9.9", "--version", "0.0.1"]) == 1


def test_record_main_dry_run_prints_block(tmp_path, monkeypatch, capsys) -> None:
    old = _make_template(tmp_path / "old", {"backend/app/old.py": _SHARED})
    new = _make_template(tmp_path / "new", {"backend/app/new.py": _SHARED})
    monkeypatch.setattr(rr, "_find_template_dir", lambda: new)

    def _fetch(_version, **_kwargs):
        return old

    monkeypatch.setattr(rr, "fetch_template", _fetch)
    monkeypatch.setattr(rr, "load_upgrades_file", lambda _p: [])

    rc = rr.main(["--old", "0.1.0", "--version", "9.9.9", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "backend/app/old.py" in out and "backend/app/new.py" in out

def test_coverage_main_flags_stale_directory_rename(tmp_path, monkeypatch) -> None:
    old = _make_template(tmp_path / "old", {"old/x.py": _SHARED})
    new = _make_template(tmp_path / "new", {"new/x.py": _SHARED})
    monkeypatch.setattr(cc, "_find_template_dir", lambda: new)
    monkeypatch.setattr(cc, "latest_pypi_version", lambda **_: "9.9.9")
    monkeypatch.setattr(cc, "fetch_template", lambda *_a, **_k: old)
    monkeypatch.setattr(cc, "load_upgrades_file", lambda _p: [])
    # Recorded under a version <= the baseline: the half-open (from, to] range drops it
    # at upgrade time, so a whole subtree of client edits would silently degrade to
    # delete+add. The file's own paths are in no entry — only the directory key is.
    monkeypatch.setattr(cc, "_known_renames", lambda _r: {("old/", "new/"): "0.1.0"})

    assert cc.main([]) == 1


def test_coverage_main_accepts_fresh_directory_rename(tmp_path, monkeypatch) -> None:
    old = _make_template(tmp_path / "old", {"old/x.py": _SHARED})
    new = _make_template(tmp_path / "new", {"new/x.py": _SHARED})
    monkeypatch.setattr(cc, "_find_template_dir", lambda: new)
    monkeypatch.setattr(cc, "latest_pypi_version", lambda **_: "0.1.0")
    monkeypatch.setattr(cc, "fetch_template", lambda *_a, **_k: old)
    monkeypatch.setattr(cc, "load_upgrades_file", lambda _p: [])
    monkeypatch.setattr(cc, "_known_renames", lambda _r: {("old/", "new/"): "9.9.9"})

    assert cc.main([]) == 0


def test_record_main_honours_versioned_waiver(tmp_path, monkeypatch, capsys) -> None:
    old = _make_template(tmp_path / "old", {"backend/app/old.py": _SHARED})
    new = _make_template(tmp_path / "new", {"backend/app/new.py": _SHARED})
    monkeypatch.setattr(rr, "_find_template_dir", lambda: new)
    monkeypatch.setattr(rr, "fetch_template", lambda *_a, **_k: old)
    # CI already honours `removed:`. If the recorder didn't, it would write the waived
    # pair back as a rename — CI would then pass because the move is "covered", and the
    # upgrade would move the client's copy of a deleted file onto an unrelated path.
    monkeypatch.setattr(
        rr,
        "load_upgrades_file",
        lambda _p: [{"version": "0.1.0", "removed": ["backend/app/old.py"]}],
    )
    written: list[Path] = []
    monkeypatch.setattr(rr, "_write_upgrades", lambda path, _blocks: written.append(path))

    rc = rr.main(["--old", "0.1.0", "--version", "9.9.9"])

    assert rc == 0
    assert written == []
    assert "No new moves to record" in capsys.readouterr().out
