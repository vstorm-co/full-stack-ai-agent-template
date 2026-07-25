"""Tests for fastapi_gen.upgrade.report — the human-facing upgrade summary."""

from __future__ import annotations

import pytest

from fastapi_gen.upgrade.classify import Classification
from fastapi_gen.upgrade.metadata import UpgradeMetadata
from fastapi_gen.upgrade.reconcile import ReconcileReport
from fastapi_gen.upgrade.report import print_report


def _print(**meta_kwargs: object) -> str:
    from io import StringIO

    from rich.console import Console

    import fastapi_gen.upgrade.report as report_mod

    buffer = StringIO()
    original = report_mod.console
    report_mod.console = Console(file=buffer, width=100, force_terminal=False)
    try:
        print_report(
            Classification(),
            ReconcileReport(),
            UpgradeMetadata(**meta_kwargs),  # type: ignore[arg-type]
            from_version="0.2.10",
            to_version="0.2.15",
            dry_run=True,
        )
    finally:
        report_mod.console = original
    return buffer.getvalue()


def _print_classification(classification: Classification) -> str:
    from io import StringIO

    from rich.console import Console

    import fastapi_gen.upgrade.report as report_mod

    buffer = StringIO()
    original = report_mod.console
    report_mod.console = Console(file=buffer, width=100, force_terminal=False)
    try:
        print_report(
            classification,
            ReconcileReport(),
            UpgradeMetadata(),
            from_version="0.2.10",
            to_version="0.2.15",
            dry_run=True,
        )
    finally:
        report_mod.console = original
    return buffer.getvalue()


def test_changed_migrations_carry_the_wont_re_run_warning() -> None:
    """Listing the path isn't enough — the reader has to learn why it matters."""
    mig = "backend/alembic/versions/0000_users.py"
    out = _print_classification(Classification(changed_migrations=[mig]))

    assert "Changed migrations" in out
    assert mig in out
    assert "revision id" in out


def test_no_changed_migrations_section_when_empty() -> None:
    out = _print_classification(Classification(auto_updated=["backend/app/main.py"]))
    assert "Changed migrations" not in out
    assert "revision id" not in out


def test_documented_removals_are_shown() -> None:
    out = _print(removed=["backend/app/legacy_auth.py"])
    assert "Removed on purpose (documented)" in out
    assert "backend/app/legacy_auth.py" in out


def test_no_removed_section_when_empty() -> None:
    out = _print()
    assert "Removed on purpose" not in out


def test_breaking_and_manual_steps_render() -> None:
    out = _print(
        breaking=["SECRET_KEY renamed to AUTH_SECRET_KEY."],
        manual_steps=["Rotate the admin token."],
    )
    assert "Breaking changes" in out
    assert "SECRET_KEY renamed to AUTH_SECRET_KEY." in out
    assert "Rotate the admin token." in out


@pytest.mark.parametrize("dry_run", [True, False])
def test_always_prints_plan_header(dry_run: bool) -> None:
    from io import StringIO

    from rich.console import Console

    import fastapi_gen.upgrade.report as report_mod

    buffer = StringIO()
    original = report_mod.console
    report_mod.console = Console(file=buffer, width=100, force_terminal=False)
    try:
        print_report(
            Classification(),
            ReconcileReport(),
            UpgradeMetadata(),
            from_version="0.2.10",
            to_version="0.2.15",
            dry_run=dry_run,
        )
    finally:
        report_mod.console = original
    assert "Upgrade plan: v0.2.10 → v0.2.15" in buffer.getvalue()


def _render_with(classification: Classification, reconcile: ReconcileReport) -> str:
    from io import StringIO

    import fastapi_gen.upgrade.report as report_mod
    from rich.console import Console

    buffer = StringIO()
    original = report_mod.console
    report_mod.console = Console(file=buffer, width=100, force_terminal=False)
    try:
        print_report(
            classification,
            reconcile,
            UpgradeMetadata(),
            from_version="0.1.0",
            to_version="0.2.0",
            dry_run=False,
        )
    finally:
        report_mod.console = original
    return buffer.getvalue()


def test_report_truncates_long_sections() -> None:
    out = _render_with(
        Classification(auto_updated=[f"f{i}.py" for i in range(25)]), ReconcileReport()
    )
    assert "and 5 more" in out


def test_report_new_features_not_accepted() -> None:
    out = _render_with(Classification(), ReconcileReport(new_features_available=["enable_x"]))
    assert "New optional features available" in out
    assert "not enabled" in out
    assert "Re-run with --with-new-features" in out


def test_report_new_features_accepted() -> None:
    out = _render_with(
        Classification(),
        ReconcileReport(new_features_available=["enable_x"], new_features_accepted=["enable_x"]),
    )
    assert "accepted" in out
