"""Tests for fastapi_gen.upgrade.rename_guard."""

from pathlib import Path

import pytest

from fastapi_gen.upgrade.rename_guard import (
    _strip_slug,
    detect_moves,
    template_files,
    uncovered_moves,
)


class TestDetectMoves:
    def test_detects_move_by_similarity(self) -> None:
        old = {"a.py": "def hello():\n    return 1\n"}
        new = {"b.py": "def hello():\n    return 1\n"}
        moves = detect_moves(old, new)
        assert len(moves) == 1
        assert (moves[0].from_path, moves[0].to_path) == ("a.py", "b.py")
        assert moves[0].similarity == 1.0

    def test_ignores_dissimilar_add_delete(self) -> None:
        old = {"a.py": "completely unrelated alpha content here\n"}
        new = {"b.py": "totally different beta payload zzz\n"}
        assert detect_moves(old, new, threshold=0.7) == []

    def test_unchanged_files_are_not_moves(self) -> None:
        old = {"keep.py": "same\n", "a.py": "content\n"}
        new = {"keep.py": "same\n", "b.py": "content\n"}
        moves = detect_moves(old, new)
        assert [m.from_path for m in moves] == ["a.py"]

    def test_each_addition_claimed_once(self) -> None:
        old = {"a.py": "shared body\n", "a2.py": "shared body\n"}
        new = {"b.py": "shared body\n"}
        moves = detect_moves(old, new)
        assert len(moves) == 1

    def test_skips_trivially_small_deleted_file(self) -> None:
        assert detect_moves({"a.py": "x\n"}, {"b.py": "def f():\n    return 1\n"}) == []

    def test_skips_trivially_small_added_file(self) -> None:
        assert detect_moves({"a.py": "def f():\n    return 1\n"}, {"b.py": "x\n"}) == []


class TestUncoveredMoves:
    def test_covered_by_exact_rename(self) -> None:
        moves = detect_moves(
            {"a.py": "def f():\n    return 1\n"}, {"b.py": "def f():\n    return 1\n"}
        )
        assert uncovered_moves(moves, {("a.py", "b.py")}) == []

    def test_covered_by_directory_rename(self) -> None:
        moves = detect_moves(
            {"rag/x.py": "def f():\n    return 1\n"},
            {"knowledge/x.py": "def f():\n    return 1\n"},
        )
        assert uncovered_moves(moves, {("rag/", "knowledge/")}) == []

    def test_covered_by_waiver(self) -> None:
        moves = detect_moves(
            {"a.py": "def f():\n    return 1\n"}, {"b.py": "def f():\n    return 1\n"}
        )
        assert uncovered_moves(moves, set(), waivers={"a.py"}) == []

    def test_uncovered_is_reported(self) -> None:
        moves = detect_moves(
            {"a.py": "def f():\n    return 1\n"}, {"b.py": "def f():\n    return 1\n"}
        )
        result = uncovered_moves(moves, set())
        assert [(m.from_path, m.to_path) for m in result] == [("a.py", "b.py")]


class TestTemplateFiles:
    def test_maps_and_strips_slug_prefix(self, tmp_path: Path) -> None:
        slug = tmp_path / "{{cookiecutter.project_slug}}"
        (slug / "backend").mkdir(parents=True)
        (slug / "backend" / "app.py").write_text("x", encoding="utf-8")
        (tmp_path / "cookiecutter.json").write_text("{}", encoding="utf-8")  # outside slug
        assert template_files(tmp_path) == {"backend/app.py": "x"}

    def test_strip_slug_passthrough(self) -> None:
        assert _strip_slug("other/x.py") == "other/x.py"

    def test_skips_unreadable_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        slug = tmp_path / "{{cookiecutter.project_slug}}"
        slug.mkdir()
        (slug / "x.py").write_text("data", encoding="utf-8")

        def _boom(*_a: object, **_k: object) -> str:
            raise OSError("unreadable")

        monkeypatch.setattr(Path, "read_text", _boom)
        assert template_files(tmp_path) == {}
