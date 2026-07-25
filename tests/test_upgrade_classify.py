"""Tests for fastapi_gen.upgrade.classify — the §6 matrix."""

from pathlib import Path

from fastapi_gen.upgrade.classify import classify_trees


def _w(tree: Path, rel: str, content: str) -> None:
    p = tree / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _row(base: Path, ours: Path, theirs: Path, rel: str, b: str, o: str, t: str) -> None:
    """Write a file across the three trees; empty string = absent from that tree."""
    for tree, content in ((base, b), (ours, o), (theirs, t)):
        if content:
            _w(tree, rel, content)


def test_classify_matrix(tmp_path: Path) -> None:
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()

    _row(base, ours, theirs, "aab.txt", "x", "x", "y")
    _row(base, ours, theirs, "aba.txt", "x", "z", "x")
    _row(base, ours, theirs, "abb.txt", "x", "y", "y")
    _row(base, ours, theirs, "same.txt", "x", "x", "x")
    _row(base, ours, theirs, "new.txt", "", "", "n")
    _row(base, ours, theirs, "backend/alembic/versions/0099_x.py", "", "", "m")
    _row(base, ours, theirs, "mine.txt", "", "c", "")
    _row(base, ours, theirs, "gone.txt", "g", "g", "")

    result = classify_trees(base, ours, theirs, conflicted_paths=set())

    assert result.auto_updated == ["aab.txt"]
    assert result.client_kept == ["aba.txt"]
    assert result.converged == ["abb.txt"]
    assert result.unchanged == ["same.txt"]
    assert result.new_files == ["new.txt"]
    assert result.new_migrations == ["backend/alembic/versions/0099_x.py"]
    assert result.client_only == ["mine.txt"]
    assert result.removed == ["gone.txt"]


def test_template_edit_to_an_existing_migration_is_reported_separately(tmp_path: Path) -> None:
    """A rewritten migration must not hide inside the Auto-updates list.

    It has almost certainly already run against the client's database, and alembic keys
    off the revision id — so the new body never re-runs and the file silently stops
    describing the schema it produced. The change still applies (it lands on a branch),
    but the reader has to see it.
    """
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()

    mig = "backend/alembic/versions/0000_users.py"
    _row(base, ours, theirs, mig, "rev = 1", "rev = 1", "rev = 1  # fixed")
    _row(base, ours, theirs, "backend/app/main.py", "a", "a", "b")

    result = classify_trees(base, ours, theirs, conflicted_paths=set())

    assert result.changed_migrations == [mig]
    assert result.auto_updated == ["backend/app/main.py"]


def test_both_edited_an_existing_migration_is_reported_separately(tmp_path: Path) -> None:
    """Same for the both-changed case — it would otherwise land in Auto-merged."""
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()

    mig = "backend/alembic/versions/0000_users.py"
    _row(base, ours, theirs, mig, "rev = 1", "rev = 1  # mine", "rev = 1  # theirs")

    result = classify_trees(base, ours, theirs, conflicted_paths=set())

    assert result.changed_migrations == [mig]
    assert result.auto_merged == []


def test_client_only_edit_to_a_migration_stays_kept(tmp_path: Path) -> None:
    """The client's own edit to a migration the template didn't touch is not 'changed'."""
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()

    mig = "backend/alembic/versions/0000_users.py"
    _row(base, ours, theirs, mig, "rev = 1", "rev = 1  # mine", "rev = 1")

    result = classify_trees(base, ours, theirs, conflicted_paths=set())

    assert result.client_kept == [mig]
    assert result.changed_migrations == []


def test_conflicted_migration_stays_a_conflict(tmp_path: Path) -> None:
    """Conflicts outrank the migration bucket — they're already blocking and visible."""
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()

    mig = "backend/alembic/versions/0000_users.py"
    _row(base, ours, theirs, mig, "rev = 1", "rev = 2", "rev = 3")

    result = classify_trees(base, ours, theirs, conflicted_paths={mig})

    assert result.conflicts == [mig]
    assert result.changed_migrations == []


def test_conflicts_take_precedence(tmp_path: Path) -> None:
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()
    _row(base, ours, theirs, "f.txt", "x", "o", "t")
    result = classify_trees(base, ours, theirs, conflicted_paths={"f.txt"})
    assert result.conflicts == ["f.txt"]
    assert result.auto_updated == []


def test_all_three_differ_but_not_flagged_is_auto_merged(tmp_path: Path) -> None:
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()
    _row(base, ours, theirs, "f.txt", "x", "o", "t")
    result = classify_trees(base, ours, theirs, conflicted_paths=set())
    assert result.auto_merged == ["f.txt"]
    assert result.conflicts == []


def test_conflict_only_from_merge_tree(tmp_path: Path) -> None:
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()
    _row(base, ours, theirs, "f.txt", "x", "o", "t")
    result = classify_trees(base, ours, theirs, conflicted_paths={"f.txt"})
    assert result.conflicts == ["f.txt"]
    assert result.auto_merged == []


def test_add_add_identical_is_converged(tmp_path: Path) -> None:
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()
    _row(base, ours, theirs, "f.txt", "", "same", "same")
    result = classify_trees(base, ours, theirs, conflicted_paths=set())
    assert result.converged == ["f.txt"]


def test_add_add_differing_clean_is_auto_merged(tmp_path: Path) -> None:
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()
    _row(base, ours, theirs, "f.txt", "", "ours", "theirs")
    result = classify_trees(base, ours, theirs, conflicted_paths=set())
    assert result.auto_merged == ["f.txt"]


def test_client_deleted_while_template_kept_has_its_own_bucket(tmp_path: Path) -> None:
    """It used to land in "other", which reads as a problem for a genuine no-op."""
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()
    _row(base, ours, theirs, "f.txt", "x", "", "x")
    result = classify_trees(base, ours, theirs, conflicted_paths=set())
    assert result.client_deleted == ["f.txt"]
    assert result.other == []


def test_client_modified_file_template_deleted_is_auto_merged(tmp_path: Path) -> None:
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()
    _row(base, ours, theirs, "f.txt", "x", "y", "")
    result = classify_trees(base, ours, theirs, conflicted_paths=set())
    assert result.auto_merged == ["f.txt"]


def test_client_deleted_a_file_the_template_still_ships(tmp_path: Path) -> None:
    # Common: the user removes a module they don't want. git keeps it deleted, and the
    # old code dumped it into "Other changes (review on the branch)" — which reads as
    # "the upgrade lost my file" for something that needs no action at all.
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()
    _row(base, ours, theirs, "dropped.py", "same\n", "", "same\n")

    result = classify_trees(base, ours, theirs, set())

    assert result.client_deleted == ["dropped.py"]
    assert result.other == []


def test_client_and_template_both_deleted_is_converged(tmp_path: Path) -> None:
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()
    _row(base, ours, theirs, "gone.py", "old\n", "", "")

    result = classify_trees(base, ours, theirs, set())

    assert result.converged == ["gone.py"]
    assert result.other == []


def test_client_deleted_but_template_changed_is_not_silently_dropped(tmp_path: Path) -> None:
    # A template-side change here is a modify/delete conflict in practice; if the merge
    # somehow resolved it, the file still has to be reviewed rather than called a no-op.
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()
    _row(base, ours, theirs, "touched.py", "old\n", "", "new\n")

    result = classify_trees(base, ours, theirs, set())

    assert result.client_deleted == []
    assert result.auto_merged == ["touched.py"]


def test_the_matrix_is_exhaustive(tmp_path: Path) -> None:
    """Every reachable (base, ours, theirs) membership lands in a named bucket.

    `other` is a defensive catch-all, not a real outcome: a path always comes from the
    union of the three trees, so the all-absent state can't occur and the other seven
    are handled. If an edit ever opens a hole this fails instead of quietly telling a
    user to "review on the branch".
    """
    base, ours, theirs = tmp_path / "b", tmp_path / "o", tmp_path / "t"
    for t in (base, ours, theirs):
        t.mkdir()

    for index, (b, o, x) in enumerate(
        [
            ("", "", "t"),
            ("", "o", ""),
            ("", "o", "t"),
            ("b", "", ""),
            ("b", "", "t"),
            ("b", "o", ""),
            ("b", "o", "t"),
        ]
    ):
        # Distinct content per tree so no state collapses into "identical everywhere".
        _row(
            base,
            ours,
            theirs,
            f"f{index}.txt",
            b and f"{b}{index}",
            o and f"{o}{index}",
            x and f"{x}{index}",
        )

    result = classify_trees(base, ours, theirs, conflicted_paths=set())

    assert result.other == []
