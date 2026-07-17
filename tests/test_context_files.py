"""Anti-duplication guard for generated agent context files.

Background: the June 2026 revision of *Are Repository-Level Context Files
Helpful for Coding Agents?* (https://arxiv.org/abs/2602.11988) found that
always-loaded repository context files raise inference cost while repository
overviews (directory trees) don't improve task success. The useful content is
narrow: non-inferable commands, hard boundaries, and pointers.

The generated root ``CLAUDE.md`` is always loaded, while ``.claude/rules/*``
files are path-scoped (they carry ``globs:`` frontmatter and load only when a
matching file is edited). So any convention detailed in a rules file must NOT
also live in the always-loaded root file, or that guidance loads twice.

This guard is intentionally deterministic — a denylist of section headings plus
a line budget — rather than a fuzzy semantic diff, so the check itself stays
stable (issue #119).

``AGENTS.md`` is deliberately exempt: non-Claude agents (Codex, Cursor,
Copilot, ...) do not read ``.claude/rules/*``, so it must stay self-contained.
"""

from pathlib import Path

import pytest

TEMPLATE_DIR = Path(__file__).parent.parent / "template"
PROJECT_ROOT = TEMPLATE_DIR / "{{cookiecutter.project_slug}}"
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"

# Section headings whose detail belongs in .claude/rules/* and must not be
# restated in the always-loaded root CLAUDE.md. Matched case-insensitively as
# markdown headings.
BANNED_HEADINGS = (
    "Project Structure",
    "Dependency Injection",
    "Schema Conventions",
    "Exception Handling",
    "Response Format",
    "Key Conventions",
)

# The reduced root file must stay small; this backstops gradual regrowth.
MAX_LINES = 110


class TestClaudeMdIsReduced:
    """Root CLAUDE.md must stay an index, not a duplicate of the scoped rules."""

    @pytest.fixture
    def content(self) -> str:
        assert CLAUDE_MD.exists(), f"CLAUDE.md not found at {CLAUDE_MD}"
        return CLAUDE_MD.read_text()

    def test_no_banned_sections(self, content: str) -> None:
        """No section already covered by .claude/rules/* may appear here."""
        headings = {
            line.lstrip("#").strip().lower()
            for line in content.splitlines()
            if line.lstrip().startswith("#")
        }
        offenders = [
            banned
            for banned in BANNED_HEADINGS
            if any(banned.lower() in heading for heading in headings)
        ]
        assert not offenders, (
            "CLAUDE.md restates sections that belong in .claude/rules/* "
            f"(duplicated always-loaded guidance): {offenders}"
        )

    def test_no_directory_tree(self, content: str) -> None:
        """The generated directory tree does not improve outcomes — keep it out."""
        tree_lines = [line for line in content.splitlines() if "├──" in line or "└──" in line]
        assert not tree_lines, (
            "CLAUDE.md contains a directory tree; repository overviews are "
            f"unhelpful always-loaded context. First offending line: {tree_lines[0]!r}"
        )

    def test_within_line_budget(self, content: str) -> None:
        """Line budget prevents the reduced file from silently regrowing."""
        line_count = len(content.splitlines())
        assert line_count <= MAX_LINES, (
            f"CLAUDE.md has {line_count} lines (budget {MAX_LINES}). Move detail "
            "into .claude/rules/* instead of growing the always-loaded root file."
        )

    def test_keeps_useful_content(self, content: str) -> None:
        """The reduced file must still carry the non-inferable, useful parts."""
        assert "## Commands" in content, "CLAUDE.md must keep the Commands section"
        assert ".claude/rules" in content, (
            "CLAUDE.md must point to the scoped .claude/rules/* files"
        )
