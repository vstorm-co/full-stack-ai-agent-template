# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""
Seed database with sample data.

This command is useful for development and testing.
Uses random data generation - install faker for better data:
    uv add faker --group dev
"""

import asyncio

import random
import string

import click

from app.commands import command, info, success, warning

# Try to import Faker for better data generation
try:
    from faker import Faker

    fake = Faker()
    HAS_FAKER = True
except ImportError:
    HAS_FAKER = False
    fake = None


def random_email() -> str:
    """Generate a random email address."""
    if HAS_FAKER:
        return str(fake.email())
    random_str = "".join(random.choices(string.ascii_lowercase, k=8))
    return f"{random_str}@example.com"


def random_name() -> str:
    """Generate a random full name."""
    if HAS_FAKER:
        return str(fake.name())
    first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Eve", "Frank"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"


@command("seed", help="Seed database with sample data")
@click.option("--count", "-c", default=10, type=int, help="Number of records to create")
@click.option("--clear", is_flag=True, help="Clear existing data before seeding")
@click.option("--dry-run", is_flag=True, help="Show what would be created without making changes")
@click.option("--users/--no-users", default=True, help="Seed users (default: True)")
def seed(
    count: int,
    clear: bool,
    dry_run: bool,
    users: bool,
) -> None:
    """
    Seed the database with sample data for development.

    Example:
        project cmd seed --count 50
        project cmd seed --clear --count 100
        project cmd seed --dry-run
        project cmd seed --no-users  # Skip user seeding
    """
    if not HAS_FAKER:
        warning(
            "Faker not installed. Using basic random data. For better data: uv add faker --group dev"
        )

    if dry_run:
        info(f"[DRY RUN] Would create {count} sample records per entity")
        if clear:
            info("[DRY RUN] Would clear existing data first")
        if users:
            info("[DRY RUN] Would create users")
        return
    from app.db.session import get_db_context
    from app.services.user import UserService
    from app.schemas.user import UserCreate

    async def _seed() -> None:
        async with get_db_context() as db:
            user_svc = UserService(db)
            created_counts = {}

            if users:
                if clear:
                    info("Clearing existing users (except admins)...")
                    await user_svc.delete_non_admins()

                if await user_svc.has_any() and not clear:
                    info("Users already exist. Use --clear to replace them.")
                else:
                    info(f"Creating {count} sample users...")
                    for _ in range(count):
                        await user_svc.register(
                            UserCreate(
                                email=random_email(),
                                password="password123",
                                full_name=random_name(),
                            )
                        )
                    created_counts["users"] = count

            if created_counts:
                summary = ", ".join(f"{v} {k}" for k, v in created_counts.items())
                success(f"Created: {summary}")
            else:
                info("No records created.")

    asyncio.run(_seed())
