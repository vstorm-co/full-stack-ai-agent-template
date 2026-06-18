"""
Cleanup old or stale data from the database.

This command is useful for maintenance tasks.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import click

from app.commands import command, info, success, warning


@command("cleanup", help="Clean up old data from the database")
@click.option("--days", "-d", default=90, type=int, help="Delete records older than N days")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without making changes")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
def cleanup(days: int, dry_run: bool, force: bool) -> None:
    """
    Remove old records from the database.

    Example:
        project cmd cleanup --days 90
        project cmd cleanup --days 30 --dry-run
        project cmd cleanup --days 7 --force
    """
    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    if dry_run:
        info(f"[DRY RUN] Would delete records older than {cutoff_date}")
        return

    if not force and not click.confirm(
        f"Delete all records older than {days} days ({cutoff_date})?"
    ):
        warning("Aborted.")
        return

    async def _cleanup() -> None:
        info(f"Cleaning up records older than {cutoff_date}...")
        total_deleted = 0
        success(f"Done. Total deleted: {total_deleted} rows.")

    asyncio.run(_cleanup())
