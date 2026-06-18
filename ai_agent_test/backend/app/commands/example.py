"""
Example custom command.

This is a template showing how to create custom CLI commands.
Copy this file and modify it to create your own commands.
"""

import click

from app.commands import command, info, success


@command("hello", help="Example command that greets the user")
@click.option("--name", "-n", default="World", help="Name to greet")
@click.option("--count", "-c", default=1, type=int, help="Number of greetings")
def hello(name: str, count: int) -> None:
    """
    Greet someone multiple times.

    Example:
        project cmd hello --name Alice --count 3
    """
    info(f"Greeting {name} {count} time(s)...")

    for i in range(count):
        click.echo(f"  [{i + 1}] Hello, {name}!")

    success("Done!")
