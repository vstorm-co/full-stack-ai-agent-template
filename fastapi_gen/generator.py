"""Project generation logic."""

import shutil
from pathlib import Path

from cookiecutter.main import cookiecutter
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import DatabaseType, FrontendType, ProjectConfig

console = Console()


def _get_database_setup_commands(database: DatabaseType) -> list[tuple[str, str]]:
    """Get database-specific setup commands for post-generation messages.

    Args:
        database: The database type selected by the user

    Returns:
        List of (command, description) tuples to display
    """
    if database == DatabaseType.SQLITE:
        return [
            ("# SQLite database will be created automatically", ""),
            ("make db-migrate", "Create initial migration"),
            ("make db-upgrade", "Apply migrations"),
        ]
    elif database == DatabaseType.MONGODB:
        return [
            ("make docker-mongo", "Start MongoDB container"),
            ("# Or configure MongoDB Atlas connection in .env", ""),
        ]
    elif database == DatabaseType.SQLSERVER:
        return [
            ("# Configure SQL Server connection in .env", ""),
            ("# Ensure ODBC Driver 18 for SQL Server is installed", ""),
            ("make db-migrate", "Create initial migration"),
            ("make db-upgrade", "Apply migrations"),
        ]
    else:  # PostgreSQL
        return [
            ("make docker-db", "Start PostgreSQL container"),
            ("make db-migrate", "Create initial migration"),
            ("make db-upgrade", "Apply migrations"),
        ]


def _find_template_dir() -> Path:
    """Find the template directory.

    Works both in development (template at project root) and when installed
    (template bundled inside the package).
    """
    # Development: template is at project root (sibling to fastapi_gen/)
    dev_path = Path(__file__).parent.parent / "template"
    if dev_path.exists() and (dev_path / "cookiecutter.json").exists():
        return dev_path

    # Installed: template is inside the package
    installed_path = Path(__file__).parent / "template"
    if installed_path.exists() and (installed_path / "cookiecutter.json").exists():
        return installed_path

    raise FileNotFoundError(
        "Could not find cookiecutter template. "
        "Expected at 'template/' (development) or 'fastapi_gen/template/' (installed)."
    )


TEMPLATE_DIR = _find_template_dir()


def get_template_path() -> str:
    """Get the path to the cookiecutter template."""
    return str(TEMPLATE_DIR)


def generate_project(config: ProjectConfig, output_dir: Path | None = None) -> Path:
    """Generate a new FastAPI project from configuration.

    Args:
        config: Project configuration
        output_dir: Output directory (defaults to current directory)

    Returns:
        Path to the generated project

    Raises:
        ValueError: If target directory exists and is not empty
    """
    if output_dir is None:
        output_dir = Path.cwd()

    # Check if target directory already exists and is not empty
    target_dir = output_dir / config.project_slug
    if target_dir.exists() and any(target_dir.iterdir()):
        raise ValueError(f"Directory '{target_dir}' already exists and is not empty")

    context = config.to_cookiecutter_context()
    template_path = get_template_path()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description="Generating project...", total=None)

        try:
            # Generate project using cookiecutter
            project_path = cookiecutter(
                template_path,
                extra_context=context,
                output_dir=str(output_dir),
                no_input=True,
            )
        except Exception:
            # Cleanup partial files on failure
            if target_dir.exists():
                shutil.rmtree(target_dir)
            raise

    return Path(project_path)


def post_generation_tasks(project_path: Path, config: ProjectConfig) -> None:
    """Run post-generation tasks.

    Args:
        project_path: Path to the generated project
        config: Project configuration
    """
    console.print()
    console.print(f"[bold green]Project created at:[/] {project_path}")
    console.print()
    console.print("[bold cyan]Next steps:[/]")
    console.print()
    console.print(f"  cd {project_path.name}")

    step = 1
    if config.frontend != FrontendType.NONE:
        # Full-stack project
        console.print()
        if config.generate_env:
            console.print(f"[bold]{step}. Environment:[/]")
            console.print("  backend/.env and frontend/.env.local are pre-configured")
            console.print("  # Review and update settings as needed")
        else:
            console.print(f"[bold]{step}. Configure environment:[/]")
            console.print("  cd backend && cp .env.example .env")
            console.print("  cd frontend && cp .env.example .env.local")
            console.print("  # Edit with your settings (database, secrets, etc.)")
        step += 1
        console.print()
        console.print(f"[bold]{step}. Install backend dependencies:[/]")
        console.print("  make install")
        step += 1
        if config.database.value != "none":
            console.print()
            console.print(f"[bold]{step}. Database setup:[/]")
            db_commands = _get_database_setup_commands(config.database)
            for cmd, desc in db_commands:
                if desc:
                    console.print(f"  {cmd:22}# {desc}")
                else:
                    console.print(f"  {cmd}")
            if config.database != DatabaseType.MONGODB:
                console.print()
                console.print(
                    "  [dim]⚠️  Run all commands in order:[/] "
                    "[dim]db-migrate creates the migration, db-upgrade applies it[/]"
                )
            step += 1
        console.print()
        console.print(f"[bold]{step}. Run backend:[/]")
        console.print("  make run")
        step += 1
        console.print()
        console.print(f"[bold]{step}. Frontend setup (in new terminal):[/]")
        console.print("  cd frontend")
        console.print("  bun install")
        console.print("  bun run dev")
    else:
        # Backend-only project
        console.print()
        if config.generate_env:
            console.print(f"[bold]{step}. Environment:[/]")
            console.print("  backend/.env is pre-configured for development")
            console.print("  # Review and update settings as needed")
        else:
            console.print(f"[bold]{step}. Configure environment:[/]")
            console.print("  cd backend && cp .env.example .env")
            console.print("  # Edit backend/.env with your settings")
        step += 1
        console.print()
        console.print(f"[bold]{step}. Install dependencies:[/]")
        console.print("  make install")
        step += 1
        if config.database.value != "none":
            console.print()
            console.print(f"[bold]{step}. Database setup:[/]")
            db_commands = _get_database_setup_commands(config.database)
            for cmd, desc in db_commands:
                if desc:
                    console.print(f"  {cmd:22}# {desc}")
                else:
                    console.print(f"  {cmd}")
            if config.database != DatabaseType.MONGODB:
                console.print()
                console.print(
                    "  [dim]⚠️  Run all commands in order:[/] "
                    "[dim]db-migrate creates the migration, db-upgrade applies it[/]"
                )
            step += 1
        console.print()
        console.print(f"[bold]{step}. Run server:[/]")
        console.print("  make run")

    console.print()

    if config.enable_logfire:
        console.print("[dim]To enable Logfire, set LOGFIRE_TOKEN in backend/.env[/]")
        console.print("[dim]Get your token at: https://logfire.pydantic.dev[/]")
        console.print()

    if config.frontend == FrontendType.NEXTJS:
        console.print(f"[dim]Frontend runs on http://localhost:{config.frontend_port}[/]")
        console.print(f"[dim]Backend API runs on http://localhost:{config.backend_port}[/]")
    else:
        console.print(f"[dim]API runs on http://localhost:{config.backend_port}[/]")
        console.print(f"[dim]API docs: http://localhost:{config.backend_port}/docs[/]")
    console.print()
