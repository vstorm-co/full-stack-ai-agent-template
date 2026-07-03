"""Tests for fastapi_gen.upgrade.rename_guard."""

from fastapi_gen.upgrade.rename_guard import detect_moves, uncovered_moves


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


class TestUncoveredMoves:
    def test_covered_by_exact_rename(self) -> None:
        moves = detect_moves({"a.py": "x\n"}, {"b.py": "x\n"})
        assert uncovered_moves(moves, {("a.py", "b.py")}) == []

    def test_covered_by_directory_rename(self) -> None:
        moves = detect_moves({"rag/x.py": "x\n"}, {"knowledge/x.py": "x\n"})
        assert uncovered_moves(moves, {("rag/", "knowledge/")}) == []

    def test_covered_by_waiver(self) -> None:
        moves = detect_moves({"a.py": "x\n"}, {"b.py": "x\n"})
        assert uncovered_moves(moves, set(), waivers={"a.py"}) == []

    def test_uncovered_is_reported(self) -> None:
        moves = detect_moves({"a.py": "x\n"}, {"b.py": "x\n"})
        result = uncovered_moves(moves, set())
        assert [(m.from_path, m.to_path) for m in result] == [("a.py", "b.py")]
