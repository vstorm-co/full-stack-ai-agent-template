"""
Custom commands system with auto-discovery.

This module provides a Django-like custom commands system for FastAPI + Click.
Commands are auto-discovered from this package and registered to the CLI.

Usage:
    # In app/commands/my_command.py
    from app.commands import command
    import click

    @command("my-command", help="Description of my command")
    @click.option("--option", "-o", help="Some option")
    def my_command(option: str):
        click.echo(f"Running with {option}")

    # Then use it:
    # project cmd my-command --option value
"""

import importlib
import pkgutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

# Registry for custom commands
_commands: list[click.Command] = []
_discovered = False


def command(name: str | None = None, **kwargs: Any) -> Callable[..., Any]:
    """
    Decorator to register a custom command.

    Args:
        name: Command name (defaults to function name with underscores replaced by hyphens)
        **kwargs: Additional arguments passed to click.command()

    Example:
        @command("seed", help="Seed database with initial data")
        @click.option("--count", "-c", default=10)
        def seed_data(count: int):
            click.echo(f"Seeding {count} records...")
    """

    def decorator(func: Callable[..., Any]) -> click.Command:
        cmd_name = name or func.__name__.replace("_", "-")
        cmd: click.Command = click.command(cmd_name, **kwargs)(func)  # type: ignore[no-untyped-call]
        _commands.append(cmd)
        return cmd

    return decorator


def discover_commands() -> list[click.Command]:
    """
    Auto-discover all commands in this package.

    Imports all modules in the app.commands package (except those starting with _)
    which triggers the @command decorator to register them.

    Returns:
        List of discovered click.Command objects
    """
    global _discovered

    if _discovered:
        return _commands

    package_dir = Path(__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if module_name.startswith("_"):
            continue

        try:
            importlib.import_module(f"app.commands.{module_name}")
        except ImportError as e:
            click.secho(f"Warning: Failed to import command module '{module_name}': {e}", fg="yellow")

    _discovered = True
    return _commands


def register_commands(cli: click.Group) -> None:
    """
    Register all discovered commands to a CLI group.

    Args:
        cli: The click.Group to add commands to
    """
    commands = discover_commands()

    for cmd in commands:
        cli.add_command(cmd)


def success(message: str) -> None:
    """Print success message in green."""
    click.secho(message, fg="green")


def error(message: str) -> None:
    """Print error message in red."""
    click.secho(message, fg="red")


def warning(message: str) -> None:
    """Print warning message in yellow."""
    click.secho(message, fg="yellow")


def info(message: str) -> None:
    """Print info message."""
    click.echo(message)
