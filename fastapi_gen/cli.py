"""CLI interface for FastAPI project generator."""

from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .config import (
    AIFrameworkType,
    AuthType,
    BackgroundTaskType,
    CIType,
    DatabaseType,
    FrontendType,
    LLMProviderType,
    OAuthProvider,
    OrmType,
    ProjectConfig,
)
from .generator import generate_project, post_generation_tasks
from .prompts import confirm_generation, run_interactive_prompts, show_summary

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="fastapi-fullstack")
def cli() -> None:
    """FastAPI Project Generator with Logfire observability."""


@cli.command()
@click.option(
    "-o",
    "--output",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Output directory for the generated project",
)
@click.option(
    "--no-input",
    is_flag=True,
    default=False,
    help="Use default values without prompts",
)
@click.option("--name", type=str, help="Project name (for --no-input mode)")
def new(output: Path | None, no_input: bool, name: str | None) -> None:
    """Create a new FastAPI project interactively."""
    try:
        if no_input:
            if not name:
                console.print("[red]Error:[/] --name is required when using --no-input")
                raise SystemExit(1)

            config = ProjectConfig(project_name=name)
        else:
            config = run_interactive_prompts()
            show_summary(config)

            if not confirm_generation():
                console.print("[yellow]Project generation cancelled.[/]")
                return

        project_path = generate_project(config, output)
        post_generation_tasks(project_path, config)

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/]")
        raise SystemExit(0) from None
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from None


@cli.command()
@click.argument("name", type=str)
@click.option(
    "-o",
    "--output",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Output directory",
)
@click.option(
    "--database",
    type=click.Choice(["postgresql", "mongodb", "sqlite", "sqlserver", "none"]),
    default="postgresql",
    help="Database type",
)
@click.option(
    "--orm",
    type=click.Choice(["sqlalchemy", "sqlmodel"]),
    default="sqlalchemy",
    help="ORM library (sqlalchemy or sqlmodel). SQLModel only works with PostgreSQL/SQLite",
)
@click.option(
    "--auth",
    type=click.Choice(["jwt", "api_key", "both", "none"]),
    default="jwt",
    help="Authentication method",
)
@click.option("--no-logfire", is_flag=True, help="Disable Logfire integration")
@click.option("--no-docker", is_flag=True, help="Disable Docker files")
@click.option("--no-env", is_flag=True, help="Skip .env file generation")
@click.option("--minimal", is_flag=True, help="Create minimal project (no extras)")
@click.option("--no-example-crud", is_flag=True, help="Skip example CRUD endpoint")
@click.option(
    "--frontend",
    type=click.Choice(["none", "nextjs"]),
    default="none",
    help="Frontend framework",
)
@click.option(
    "--backend-port",
    type=int,
    default=8000,
    help="Backend server port (default: 8000)",
)
@click.option(
    "--frontend-port",
    type=int,
    default=3000,
    help="Frontend server port (default: 3000)",
)
@click.option(
    "--db-pool-size",
    type=int,
    default=5,
    help="Database connection pool size (default: 5)",
)
@click.option(
    "--db-max-overflow",
    type=int,
    default=10,
    help="Database max overflow connections (default: 10)",
)
@click.option(
    "--ai-agent",
    is_flag=True,
    default=False,
    help="Enable AI agent with WebSocket streaming",
)
@click.option(
    "--ai-framework",
    type=click.Choice(["pydantic_ai", "langchain"]),
    default="pydantic_ai",
    help="AI framework (default: pydantic_ai)",
)
@click.option(
    "--llm-provider",
    type=click.Choice(["openai", "anthropic", "openrouter"]),
    default="openai",
    help="LLM provider (default: openai). Note: openrouter only works with pydantic_ai",
)
# New optional feature flags
@click.option("--redis", is_flag=True, help="Enable Redis")
@click.option("--caching", is_flag=True, help="Enable caching (requires --redis)")
@click.option("--rate-limiting", is_flag=True, help="Enable rate limiting")
@click.option("--admin-panel", is_flag=True, help="Enable admin panel (SQLAdmin)")
@click.option("--websockets", is_flag=True, help="Enable WebSocket support")
@click.option(
    "--task-queue",
    type=click.Choice(["none", "celery", "taskiq", "arq"]),
    default="none",
    help="Background task queue",
)
@click.option("--oauth-google", is_flag=True, help="Enable Google OAuth")
@click.option("--session-management", is_flag=True, help="Enable session management")
@click.option("--kubernetes", is_flag=True, help="Generate Kubernetes manifests")
@click.option(
    "--ci",
    type=click.Choice(["github", "gitlab", "none"]),
    default="github",
    help="CI/CD system",
)
@click.option("--sentry", is_flag=True, help="Enable Sentry error tracking")
@click.option("--prometheus", is_flag=True, help="Enable Prometheus metrics")
@click.option("--file-storage", is_flag=True, help="Enable S3/MinIO file storage")
@click.option("--webhooks", is_flag=True, help="Enable webhooks support")
@click.option(
    "--python-version",
    type=click.Choice(["3.11", "3.12", "3.13"]),
    default="3.12",
    help="Python version",
)
@click.option("--i18n", is_flag=True, help="Enable internationalization")
@click.option(
    "--preset",
    type=click.Choice(["production", "ai-agent"]),
    default=None,
    help="Apply configuration preset",
)
def create(
    name: str,
    output: Path | None,
    database: str,
    orm: str,
    auth: str,
    no_logfire: bool,
    no_docker: bool,
    no_env: bool,
    minimal: bool,
    no_example_crud: bool,
    frontend: str,
    backend_port: int,
    frontend_port: int,
    db_pool_size: int,
    db_max_overflow: int,
    ai_agent: bool,
    ai_framework: str,
    llm_provider: str,
    # New optional features
    redis: bool,
    caching: bool,
    rate_limiting: bool,
    admin_panel: bool,
    websockets: bool,
    task_queue: str,
    oauth_google: bool,
    session_management: bool,
    kubernetes: bool,
    ci: str,
    sentry: bool,
    prometheus: bool,
    file_storage: bool,
    webhooks: bool,
    python_version: str,
    i18n: bool,
    preset: str | None,
) -> None:
    """Create a new FastAPI project with specified options.

    NAME is the project name (e.g., my_project)
    """
    try:
        # Handle presets first
        if preset == "production":
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                auth=AuthType.JWT,
                enable_logfire=True,
                enable_redis=True,
                enable_caching=True,
                enable_rate_limiting=True,
                enable_sentry=True,
                enable_prometheus=True,
                enable_docker=True,
                enable_kubernetes=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                include_example_crud=True,
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
            )
        elif preset == "ai-agent":
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                auth=AuthType.JWT,
                enable_logfire=True,
                enable_redis=True,
                enable_ai_agent=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_websockets=True,
                enable_conversation_persistence=True,
                enable_docker=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
            )
        elif minimal:
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.NONE,
                auth=AuthType.NONE,
                enable_logfire=False,
                enable_redis=False,
                enable_caching=False,
                enable_rate_limiting=False,
                enable_pagination=False,
                enable_admin_panel=False,
                enable_websockets=False,
                enable_docker=False,
                enable_kubernetes=False,
                ci_type=CIType.NONE,
                generate_env=not no_env,
                include_example_crud=False,
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
            )
        else:
            # Full custom configuration with all options
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType(database),
                orm_type=OrmType(orm),
                auth=AuthType(auth),
                enable_logfire=not no_logfire,
                enable_docker=not no_docker,
                generate_env=not no_env,
                include_example_crud=not no_example_crud,
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                db_pool_size=db_pool_size,
                db_max_overflow=db_max_overflow,
                enable_ai_agent=ai_agent,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                # New options
                enable_redis=redis,
                enable_caching=caching,
                enable_rate_limiting=rate_limiting,
                enable_admin_panel=admin_panel,
                enable_websockets=websockets,
                background_tasks=BackgroundTaskType(task_queue),
                oauth_provider=OAuthProvider.GOOGLE if oauth_google else OAuthProvider.NONE,
                enable_session_management=session_management,
                enable_kubernetes=kubernetes,
                ci_type=CIType(ci),
                enable_sentry=sentry,
                enable_prometheus=prometheus,
                enable_file_storage=file_storage,
                enable_webhooks=webhooks,
                python_version=python_version,
                enable_i18n=i18n,
            )

        console.print(f"[cyan]Creating project:[/] {name}")
        if preset:
            console.print(f"[dim]Preset: {preset}[/]")
        console.print(f"[dim]Database: {config.database.value}[/]")
        console.print(f"[dim]Auth: {config.auth.value}[/]")
        if config.frontend != FrontendType.NONE:
            console.print(f"[dim]Frontend: {config.frontend.value}[/]")
        if config.enable_ai_agent:
            console.print(
                f"[dim]AI Agent: {config.ai_framework.value} ({config.llm_provider.value})[/]"
            )
        if config.background_tasks != BackgroundTaskType.NONE:
            console.print(f"[dim]Task Queue: {config.background_tasks.value}[/]")
        console.print()

        project_path = generate_project(config, output)
        post_generation_tasks(project_path, config)

    except ValueError as e:
        console.print(f"[red]Invalid configuration:[/] {e}")
        raise SystemExit(1) from None
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from None


@cli.command()
def templates() -> None:
    """List available template options."""
    console.print("[bold cyan]Available Options[/]")
    console.print()

    console.print("[bold]Presets:[/]")
    console.print("  --preset production   Full production setup (Redis, Sentry, K8s, etc.)")
    console.print("  --preset ai-agent     AI agent with WebSocket streaming")
    console.print("  --minimal             Minimal project (no extras)")
    console.print()

    console.print("[bold]Databases:[/]")
    console.print("  --database postgresql   PostgreSQL with asyncpg (async)")
    console.print("  --database mongodb      MongoDB with Motor (async)")
    console.print("  --database sqlite       SQLite with SQLAlchemy (sync)")
    console.print("  --database sqlserver  MS SQL Server with aioodbc (async)")
    console.print("  --database none         No database")
    console.print()

    console.print("[bold]Authentication:[/]")
    console.print("  --auth jwt         JWT + User Management")
    console.print("  --auth api_key     API Key (header-based)")
    console.print("  --auth both        JWT with API Key fallback")
    console.print("  --auth none        No authentication")
    console.print("  --oauth-google     Enable Google OAuth")
    console.print("  --session-management  Enable session management")
    console.print()

    console.print("[bold]Background Tasks:[/]")
    console.print("  --task-queue none      FastAPI BackgroundTasks only")
    console.print("  --task-queue celery    Celery (classic)")
    console.print("  --task-queue taskiq    Taskiq (async-native)")
    console.print("  --task-queue arq       ARQ (lightweight)")
    console.print()

    console.print("[bold]Frontend:[/]")
    console.print("  --frontend none        API only (no frontend)")
    console.print("  --frontend nextjs      Next.js 15 (App Router, TypeScript, Bun)")
    console.print("  --i18n                 Enable internationalization")
    console.print()

    console.print("[bold]AI Agent:[/]")
    console.print("  --ai-agent                  Enable AI agent")
    console.print("  --ai-framework pydantic_ai  PydanticAI (recommended)")
    console.print("  --ai-framework langchain    LangChain")
    console.print("  --llm-provider openai       OpenAI (gpt-4o-mini)")
    console.print("  --llm-provider anthropic    Anthropic (claude-sonnet-4-5)")
    console.print("  --llm-provider openrouter   OpenRouter (pydantic_ai only)")
    console.print()

    console.print("[bold]Integrations:[/]")
    console.print("  --redis            Enable Redis")
    console.print("  --caching          Enable caching (requires --redis)")
    console.print("  --rate-limiting    Enable rate limiting")
    console.print("  --admin-panel      Enable admin panel (SQLAdmin)")
    console.print("  --websockets       Enable WebSocket support")
    console.print("  --file-storage     Enable S3/MinIO file storage")
    console.print("  --webhooks         Enable webhooks support")
    console.print()

    console.print("[bold]Observability:[/]")
    console.print("  --no-logfire       Disable Logfire integration")
    console.print("  --sentry           Enable Sentry error tracking")
    console.print("  --prometheus       Enable Prometheus metrics")
    console.print()

    console.print("[bold]DevOps:[/]")
    console.print("  --no-docker        Disable Docker files")
    console.print("  --kubernetes       Generate Kubernetes manifests")
    console.print("  --ci github        GitHub Actions (default)")
    console.print("  --ci gitlab        GitLab CI")
    console.print("  --ci none          No CI/CD")
    console.print()

    console.print("[bold]Other:[/]")
    console.print("  --python-version 3.11|3.12|3.13  Python version")
    console.print("  --no-example-crud  Skip example CRUD endpoint")
    console.print("  --no-env           Skip .env file generation")


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":  # pragma: no cover
    main()
