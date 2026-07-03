"""Render the upgrade report."""

from __future__ import annotations

from rich.console import Console

from .classify import Classification
from .metadata import UpgradeMetadata
from .reconcile import ReconcileReport

console = Console()

_MAX_LISTED = 20


def _section(title: str, paths: list[str], style: str) -> None:
    if not paths:
        return
    console.print(f"[{style}]{title}[/] ({len(paths)})")
    for p in paths[:_MAX_LISTED]:
        console.print(f"  {p}")
    if len(paths) > _MAX_LISTED:
        console.print(f"  [dim]… and {len(paths) - _MAX_LISTED} more[/]")
    console.print()


def print_report(
    classification: Classification,
    reconcile: ReconcileReport,
    metadata: UpgradeMetadata,
    *,
    from_version: str,
    to_version: str,
    dry_run: bool,
) -> None:
    """Print the grouped upgrade summary plus the breaking/manual-steps digest."""
    console.print()
    console.print(f"[bold]Upgrade plan: v{from_version} → v{to_version}[/]")
    console.print()

    _section("Auto-updates (template changed, you didn't)", classification.auto_updated, "green")
    _section("New files", classification.new_files, "green")
    _section("New migrations (auto-added)", classification.new_migrations, "cyan")
    _section("Kept your changes (template unchanged)", classification.client_kept, "blue")
    _section("Auto-merged (both changed, merged cleanly)", classification.auto_merged, "green")
    _section("Already converged", classification.converged, "dim")
    _section("Removed by template", classification.removed, "yellow")
    _section("Removed on purpose (documented)", metadata.removed, "dim")
    _section("Conflicts (need manual resolution)", classification.conflicts, "bold red")
    _section("Other changes (review on the branch)", classification.other, "yellow")
    _section("Your files (left untouched)", classification.client_only, "dim")

    if reconcile.new_features_available:
        style = "magenta"
        console.print(f"[{style}]New optional features available[/]")
        for key in reconcile.new_features_available:
            state = "accepted" if key in reconcile.new_features_accepted else "not enabled"
            console.print(f"  {key} [dim]({state})[/]")
        if not reconcile.new_features_accepted:
            console.print("  [dim]Re-run with --with-new-features to adopt any of these.[/]")
        console.print()

    if metadata.breaking:
        console.print("[bold red]Breaking changes[/]")
        for item in metadata.breaking:
            console.print(f"  ⚠ {item}")
        console.print()

    manual_steps = list(metadata.manual_steps)
    if classification.new_migrations:
        manual_steps.append("Run `alembic upgrade head` (new migrations were added).")
    manual_steps.append("Re-run `uv lock` / `bun install` if dependencies changed.")
    if manual_steps:
        console.print("[bold]Manual steps after merge[/]")
        for step in manual_steps:
            console.print(f"  • {step}")
        console.print()

    if dry_run:
        console.print("[dim]Dry run — nothing was changed. Re-run without --dry-run to apply.[/]")
    console.print()
