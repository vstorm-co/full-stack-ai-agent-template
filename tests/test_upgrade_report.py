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
