"""Project management CLI."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

import asyncio
import subprocess

import click
import uvicorn
from alembic import command
from alembic.config import Config
from tabulate import tabulate

from app.commands import register_commands
from app.main import app
{%- if cookiecutter.use_jwt %}
from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.db.models.user import UserRole
from app.db.session import async_session_maker
from app.schemas.user import UserCreate
from app.services.user import UserService
{%- endif %}


@click.group()
@click.version_option(version="0.1.0", prog_name="{{ cookiecutter.project_slug }}")
def cli():
    """{{ cookiecutter.project_name }} management CLI."""
    pass


@cli.group("server")
def server_cli():
    """Server commands."""
    pass


@server_cli.command("run")
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def server_run(host: str, port: int, reload: bool):
    """Run the development server."""
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@server_cli.command("routes")
def server_routes():
    """Show all registered routes."""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods"):
            for method in route.methods - {"HEAD", "OPTIONS"}:
                routes.append([method, route.path, getattr(route, "name", "-")])

    click.echo(tabulate(routes, headers=["Method", "Path", "Name"]))


@cli.group("db")
def db_cli():
    """Database commands."""
    pass


@db_cli.command("init")
def db_init():
    """Initialize the database (run all migrations)."""
    click.echo("Initializing database...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    click.secho("Database initialized.", fg="green")


@db_cli.command("migrate")
@click.option("-m", "--message", required=True, help="Migration message")
def db_migrate(message: str):
    """Create a new migration."""
    alembic_cfg = Config("alembic.ini")
    command.revision(alembic_cfg, message=message, autogenerate=True)
    click.secho(f"Migration created: {message}", fg="green")


@db_cli.command("upgrade")
@click.option("--revision", default="head", help="Revision to upgrade to")
def db_upgrade(revision: str):
    """Run database migrations."""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, revision)
    click.secho(f"Upgraded to: {revision}", fg="green")


@db_cli.command("downgrade")
@click.option("--revision", default="-1", help="Revision to downgrade to")
def db_downgrade(revision: str):
    """Rollback database migrations."""
    alembic_cfg = Config("alembic.ini")
    command.downgrade(alembic_cfg, revision)
    click.secho(f"Downgraded to: {revision}", fg="green")


@db_cli.command("current")
def db_current():
    """Show current migration revision."""
    alembic_cfg = Config("alembic.ini")
    command.current(alembic_cfg)


@db_cli.command("history")
def db_history():
    """Show migration history."""
    alembic_cfg = Config("alembic.ini")
    command.history(alembic_cfg)


{%- if cookiecutter.use_celery %}


@cli.group("celery")
def celery_cli():
    """Celery worker commands."""
    pass


@celery_cli.command("worker")
@click.option("--loglevel", default="info", help="Log level (debug, info, warning, error)")
@click.option("--concurrency", default=4, type=int, help="Number of concurrent workers")
def celery_worker(loglevel: str, concurrency: int):
    """Start Celery worker."""
    subprocess.run([
        "celery", "-A", "app.worker.celery_app", "worker",
        f"--loglevel={loglevel}",
        f"--concurrency={concurrency}",
    ])


@celery_cli.command("beat")
@click.option("--loglevel", default="info", help="Log level (debug, info, warning, error)")
def celery_beat(loglevel: str):
    """Start Celery beat scheduler."""
    subprocess.run([
        "celery", "-A", "app.worker.celery_app", "beat",
        f"--loglevel={loglevel}",
    ])


@celery_cli.command("flower")
@click.option("--port", default=5555, type=int, help="Flower web UI port")
def celery_flower(port: int):
    """Start Flower monitoring UI."""
    subprocess.run([
        "celery", "-A", "app.worker.celery_app", "flower",
        f"--port={port}",
    ])
{%- endif %}

{%- if cookiecutter.use_taskiq %}


@cli.group("taskiq")
def taskiq_cli():
    """Taskiq worker commands."""
    pass


@taskiq_cli.command("worker")
@click.option("--workers", default=2, type=int, help="Number of workers")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def taskiq_worker(workers: int, reload: bool):
    """Start Taskiq worker."""
    cmd = [
        "taskiq", "worker", "app.worker.taskiq_app:broker",
        f"--workers={workers}",
    ]
    if reload:
        cmd.append("--reload")
    subprocess.run(cmd)


@taskiq_cli.command("scheduler")
def taskiq_scheduler():
    """Start Taskiq scheduler for periodic tasks."""
    subprocess.run([
        "taskiq", "scheduler", "app.worker.taskiq_app:scheduler",
    ])
{%- endif %}

{%- if cookiecutter.use_jwt %}


@cli.group("user")
def user_cli():
    """User management commands."""
    pass


@user_cli.command("create")
@click.option("--email", prompt=True, help="User email")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="User password")
@click.option("--role", type=click.Choice(["user", "admin"]), default="user", help="User role")
@click.option("--superuser", is_flag=True, default=False, help="Create as superuser")
def user_create(email: str, password: str, role: str, superuser: bool):
    """Create a new user."""
    async def _create():
        async with async_session_maker() as session:
            user_service = UserService(session)
            try:
                user_in = UserCreate(email=email, password=password, role=UserRole(role))
                user = await user_service.register(user_in)

                if superuser:
                    user.role = UserRole.ADMIN.value
                    session.add(user)

                await session.commit()
                return user
            except AlreadyExistsError:
                click.secho(f"User already exists: {email}", fg="red")
                return None

    user = asyncio.run(_create())
    if user:
        click.secho(f"User created: {user.email} (role: {user.role})", fg="green")


@user_cli.command("create-admin")
@click.option("--email", prompt=True, help="Admin email")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password")
def user_create_admin(email: str, password: str):
    """Create an admin user.

    This is a shortcut for creating a user with admin role and superuser privileges.
    Use this to create the initial admin account after setting up the database.
    """
    async def _create():
        async with async_session_maker() as session:
            user_service = UserService(session)
            try:
                user_in = UserCreate(email=email, password=password, role=UserRole.ADMIN)
                user = await user_service.register(user_in)

                session.add(user)

                await session.commit()
                return user
            except AlreadyExistsError:
                click.secho(f"User already exists: {email}", fg="red")
                return None

    user = asyncio.run(_create())
    if user:
        click.secho(f"Admin user created: {user.email}", fg="green")
        click.echo("This user has admin role and superuser privileges.")


@user_cli.command("set-role")
@click.argument("email")
@click.option("--role", type=click.Choice(["user", "admin"]), required=True, help="New role")
def user_set_role(email: str, role: str):
    """Change a user's role."""
    async def _update():
        async with async_session_maker() as session:
            user_service = UserService(session)
            try:
                user = await user_service.get_by_email(email)
                user.role = UserRole(role).value
                session.add(user)
                await session.commit()
                return user
            except NotFoundError:
                click.secho(f"User not found: {email}", fg="red")
                return None

    user = asyncio.run(_update())
    if user:
        click.secho(f"User {email} role updated to: {role}", fg="green")


@user_cli.command("list")
def user_list():
    """List all users."""
    async def _list():
        async with async_session_maker() as session:
            user_service = UserService(session)
            return await user_service.get_multi()

    users = asyncio.run(_list())

    if not users:
        click.echo("No users found.")
        return

    table = [[u.id, u.email, u.role, u.is_active] for u in users]
    click.echo(tabulate(table, headers=["ID", "Email", "Role", "Active", "Superuser"]))
{%- endif %}


@cli.group("cmd")
def cmd_cli():
    """Custom commands."""
    pass


register_commands(cmd_cli)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
