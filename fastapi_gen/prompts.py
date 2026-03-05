"""Interactive prompts for project configuration."""

import re
from typing import Any, cast

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .config import (
    AdminEnvironmentType,
    AIFrameworkType,
    AuthType,
    BackgroundTaskType,
    CIType,
    DatabaseType,
    FrontendType,
    LLMProviderType,
    LogfireFeatures,
    OAuthProvider,
    OrmType,
    ProjectConfig,
    RateLimitStorageType,
    ReverseProxyType,
    WebSocketAuthType,
)

console = Console()


def show_header() -> None:
    """Display the generator header."""
    header = Text()
    header.append("FastAPI Project Generator", style="bold cyan")
    header.append("\n")
    header.append("with Logfire Observability", style="dim")
    console.print(Panel(header, title="[bold green]fastapi-gen[/]", border_style="green"))
    console.print()


def _check_cancelled(value: Any) -> Any:
    """Check if the user cancelled the prompt and raise KeyboardInterrupt if so."""
    if value is None:
        raise KeyboardInterrupt
    return value


def _validate_project_name(name: str) -> bool | str:
    """Validate project name input.

    Returns True if valid, or an error message string if invalid.
    Allows alphanumeric characters, underscores, spaces, and dashes.
    First character must be a letter.
    """
    if not name:
        return "Project name cannot be empty"
    if not name[0].isalpha():
        return "Project name must start with a letter"
    if not all(c.isalnum() or c in "_- " for c in name):
        return "Project name can only contain letters, numbers, underscores, spaces, and dashes"
    return True


def _normalize_project_name(name: str) -> str:
    """Normalize project name to lowercase with underscores."""
    return name.lower().replace(" ", "_").replace("-", "_")


def _validate_email(email: str) -> bool | str:
    """Validate email format.

    Returns True if valid, or an error message string if invalid.
    """
    if not email:
        return "Email cannot be empty"
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return "Please enter a valid email address"
    return True


def prompt_basic_info() -> dict[str, str]:
    """Prompt for basic project information."""
    console.print("[bold cyan]Basic Information[/]")
    console.print()

    raw_project_name = _check_cancelled(
        questionary.text(
            "Project name:",
            validate=_validate_project_name,
        ).ask()
    )
    project_name = _normalize_project_name(raw_project_name)

    # Show converted name if it differs from input
    if project_name != raw_project_name:
        console.print(f"  [dim]→ Will be saved as:[/] [cyan]{project_name}[/]")
        console.print()

    project_description = _check_cancelled(
        questionary.text(
            "Project description:",
            default="My FastAPI project",
        ).ask()
    )

    author_name = _check_cancelled(
        questionary.text(
            "Author name:",
            default="Your Name",
        ).ask()
    )

    author_email = _check_cancelled(
        questionary.text(
            "Author email:",
            default="your@email.com",
            validate=_validate_email,
        ).ask()
    )

    return {
        "project_name": project_name,
        "project_description": project_description,
        "author_name": author_name,
        "author_email": author_email,
    }


def prompt_database() -> DatabaseType:
    """Prompt for database selection."""
    console.print()
    console.print("[bold cyan]Database Configuration[/]")
    console.print()

    choices = [
        questionary.Choice("PostgreSQL (async - asyncpg)", value=DatabaseType.POSTGRESQL),
        questionary.Choice("SQL Server (async - aioodbc)", value=DatabaseType.SQLSERVER),
        questionary.Choice("MongoDB (async - motor)", value=DatabaseType.MONGODB),
        questionary.Choice("SQLite (sync)", value=DatabaseType.SQLITE),
        questionary.Choice("None", value=DatabaseType.NONE),
    ]

    return cast(
        DatabaseType,
        _check_cancelled(
            questionary.select(
                "Select database:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_orm_type() -> OrmType:
    """Prompt for ORM library selection."""
    choices = [
        questionary.Choice(
            "SQLAlchemy — full control, supports admin panel",
            value=OrmType.SQLALCHEMY,
        ),
        questionary.Choice(
            "SQLModel — less boilerplate, no admin panel support",
            value=OrmType.SQLMODEL,
        ),
    ]

    return cast(
        OrmType,
        _check_cancelled(
            questionary.select(
                "ORM Library:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_auth() -> AuthType:
    """Prompt for authentication method."""
    console.print()
    console.print("[bold cyan]Authentication[/]")
    console.print()

    choices = [
        questionary.Choice("JWT + User Management", value=AuthType.JWT),
        questionary.Choice("API Key (header-based)", value=AuthType.API_KEY),
        questionary.Choice("Both (JWT + API Key fallback)", value=AuthType.BOTH),
        questionary.Choice("None", value=AuthType.NONE),
    ]

    return cast(
        AuthType,
        _check_cancelled(
            questionary.select(
                "Select auth method:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_oauth() -> OAuthProvider:
    """Prompt for OAuth provider selection."""
    console.print()
    console.print("[bold cyan]OAuth2 Social Login[/]")
    console.print()

    choices = [
        questionary.Choice("None (email/password only)", value=OAuthProvider.NONE),
        questionary.Choice("Google OAuth2", value=OAuthProvider.GOOGLE),
    ]

    return cast(
        OAuthProvider,
        _check_cancelled(
            questionary.select(
                "Enable social login?",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_logfire(background_tasks: BackgroundTaskType) -> tuple[bool, LogfireFeatures]:
    """Prompt for Logfire configuration.

    Args:
        background_tasks: Selected background task system (affects which options are shown).
    """
    console.print()
    console.print("[bold cyan]Observability (Logfire)[/]")
    console.print()

    enable_logfire = _check_cancelled(
        questionary.confirm(
            "Enable Logfire integration?",
            default=True,
        ).ask()
    )

    if not enable_logfire:
        return False, LogfireFeatures()

    # Build choices dynamically - only show Celery option when Celery is selected
    choices = [
        questionary.Choice("FastAPI instrumentation", value="fastapi", checked=True),
        questionary.Choice("Database instrumentation", value="database", checked=True),
        questionary.Choice("Redis instrumentation", value="redis", checked=False),
        questionary.Choice("HTTPX instrumentation", value="httpx", checked=False),
    ]

    if background_tasks == BackgroundTaskType.CELERY:
        choices.insert(
            3, questionary.Choice("Celery instrumentation", value="celery", checked=False)
        )

    features = _check_cancelled(
        questionary.checkbox(
            "Logfire features:",
            choices=choices,
        ).ask()
    )

    return True, LogfireFeatures(
        fastapi="fastapi" in features,
        database="database" in features,
        redis="redis" in features,
        celery="celery" in features,
        httpx="httpx" in features,
    )


def prompt_background_tasks() -> BackgroundTaskType:
    """Prompt for background task system."""
    console.print()
    console.print("[bold cyan]Background Tasks[/]")
    console.print()

    choices = [
        questionary.Choice("None (use FastAPI BackgroundTasks)", value=BackgroundTaskType.NONE),
        questionary.Choice("Celery (classic, battle-tested)", value=BackgroundTaskType.CELERY),
        questionary.Choice("Taskiq (async-native, modern)", value=BackgroundTaskType.TASKIQ),
        questionary.Choice("ARQ (lightweight async Redis)", value=BackgroundTaskType.ARQ),
    ]

    return cast(
        BackgroundTaskType,
        _check_cancelled(
            questionary.select(
                "Select background task system:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_integrations(
    database: DatabaseType,
    orm_type: OrmType,
) -> dict[str, bool]:
    """Prompt for optional integrations.

    Args:
        database: Selected database type (affects which options are shown).
        orm_type: Selected ORM type (SQLModel doesn't support admin panel).
    """
    console.print()
    console.print("[bold cyan]Optional Integrations[/]")
    console.print()

    # Build choices dynamically based on context
    choices: list[questionary.Choice] = [
        questionary.Choice(
            "Redis — required for caching, rate limiting (Redis), task queues",
            value="redis",
        ),
        questionary.Choice(
            "Caching (fastapi-cache2) — requires Redis",
            value="caching",
        ),
        questionary.Choice(
            "Rate limiting (slowapi) — optional Redis storage",
            value="rate_limiting",
        ),
        questionary.Choice(
            "Pagination (fastapi-pagination)",
            value="pagination",
            checked=True,
        ),
        questionary.Choice(
            "Sentry — error tracking & monitoring",
            value="sentry",
        ),
        questionary.Choice(
            "Prometheus — metrics endpoint for monitoring",
            value="prometheus",
        ),
    ]

    # Admin Panel only available with SQLAlchemy (not SQLModel) and SQL database
    if (
        database in (DatabaseType.POSTGRESQL, DatabaseType.SQLITE)
        and orm_type == OrmType.SQLALCHEMY
    ):
        choices.append(
            questionary.Choice(
                "Admin Panel (SQLAdmin) — web UI for database management",
                value="admin_panel",
            )
        )

    choices.extend(
        [
            questionary.Choice(
                "WebSockets — real-time bidirectional communication",
                value="websockets",
            ),
            questionary.Choice(
                "File Storage (S3/MinIO) — file upload/download support",
                value="file_storage",
            ),
            questionary.Choice(
                "AI Agent (PydanticAI/LangGraph/CrewAI) — LLM-powered assistant",
                value="ai_agent",
                checked=True,
            ),
        ]
    )

    # Webhooks require database
    if database != DatabaseType.NONE:
        choices.append(
            questionary.Choice(
                "Webhooks — outbound event notifications",
                value="webhooks",
            )
        )

    choices.extend(
        [
            questionary.Choice(
                "Example CRUD (Item model) — sample API endpoints",
                value="example_crud",
                checked=True,
            ),
            questionary.Choice(
                "CORS middleware — cross-origin request support",
                value="cors",
                checked=True,
            ),
            questionary.Choice(
                "orjson — faster JSON serialization",
                value="orjson",
                checked=True,
            ),
        ]
    )

    features = _check_cancelled(
        questionary.checkbox(
            "Select additional features:",
            choices=choices,
        ).ask()
    )

    # Auto-enable Redis for caching (show info message)
    if "caching" in features and "redis" not in features:
        console.print("[yellow]ℹ Caching requires Redis — auto-enabled[/]")
        features.append("redis")

    return {
        "enable_redis": "redis" in features,
        "enable_caching": "caching" in features,
        "enable_rate_limiting": "rate_limiting" in features,
        "enable_pagination": "pagination" in features,
        "enable_sentry": "sentry" in features,
        "enable_prometheus": "prometheus" in features,
        "enable_admin_panel": "admin_panel" in features,
        "enable_websockets": "websockets" in features,
        "enable_file_storage": "file_storage" in features,
        "enable_ai_agent": "ai_agent" in features,
        "enable_webhooks": "webhooks" in features,
        "include_example_crud": "example_crud" in features,
        "enable_cors": "cors" in features,
        "enable_orjson": "orjson" in features,
    }


def _validate_positive_integer(value: str) -> bool | str:
    """Validate that input is a positive integer.

    Returns True if valid, or an error message string if invalid.
    """
    if not value:
        return "Value cannot be empty"
    if not value.isdigit():
        return "Must be a positive number"
    if int(value) <= 0:
        return "Must be greater than 0"
    return True


def prompt_rate_limit_config(redis_enabled: bool) -> tuple[int, int, RateLimitStorageType]:
    """Prompt for rate limiting configuration.

    Args:
        redis_enabled: Whether Redis is enabled (affects storage choices).

    Returns:
        Tuple of (requests, period, storage).
    """
    console.print()
    console.print("[bold cyan]Rate Limiting Configuration[/]")
    console.print()

    requests_str = _check_cancelled(
        questionary.text(
            "Requests per period:",
            default="100",
            validate=_validate_positive_integer,
        ).ask()
    )

    period_str = _check_cancelled(
        questionary.text(
            "Period in seconds:",
            default="60",
            validate=_validate_positive_integer,
        ).ask()
    )

    # Build storage choices based on whether Redis is enabled
    storage_choices = [
        questionary.Choice("Memory (single instance)", value=RateLimitStorageType.MEMORY),
    ]
    if redis_enabled:
        storage_choices.append(
            questionary.Choice("Redis (distributed)", value=RateLimitStorageType.REDIS)
        )

    storage = cast(
        RateLimitStorageType,
        _check_cancelled(
            questionary.select(
                "Storage backend:",
                choices=storage_choices,
                default=storage_choices[0],
            ).ask()
        ),
    )

    return int(requests_str), int(period_str), storage


def prompt_dev_tools() -> dict[str, Any]:
    """Prompt for development tools."""
    console.print()
    console.print("[bold cyan]Development Tools[/]")
    console.print()

    features = _check_cancelled(
        questionary.checkbox(
            "Include dev tools:",
            choices=[
                questionary.Choice("pytest + fixtures", value="pytest", checked=True),
                questionary.Choice("pre-commit hooks", value="precommit", checked=True),
                questionary.Choice("Docker + docker-compose", value="docker", checked=True),
                questionary.Choice("Kubernetes manifests", value="kubernetes"),
            ],
        ).ask()
    )

    ci_type = _check_cancelled(
        questionary.select(
            "CI/CD system:",
            choices=[
                questionary.Choice("GitHub Actions", value=CIType.GITHUB),
                questionary.Choice("GitLab CI", value=CIType.GITLAB),
                questionary.Choice("None", value=CIType.NONE),
            ],
        ).ask()
    )

    return {
        "enable_pytest": "pytest" in features,
        "enable_precommit": "precommit" in features,
        "enable_docker": "docker" in features,
        "enable_kubernetes": "kubernetes" in features,
        "ci_type": ci_type,
    }


def prompt_reverse_proxy() -> ReverseProxyType:
    """Prompt for reverse proxy configuration."""
    console.print()
    console.print("[bold cyan]Reverse Proxy (Production)[/]")
    console.print()

    choices = [
        questionary.Choice(
            "Traefik (included in docker-compose)", value=ReverseProxyType.TRAEFIK_INCLUDED
        ),
        questionary.Choice(
            "Traefik (external, shared between projects)",
            value=ReverseProxyType.TRAEFIK_EXTERNAL,
        ),
        questionary.Choice(
            "Nginx (included in docker-compose)", value=ReverseProxyType.NGINX_INCLUDED
        ),
        questionary.Choice(
            "Nginx (external, config template only)", value=ReverseProxyType.NGINX_EXTERNAL
        ),
        questionary.Choice(
            "None (expose ports directly, use own proxy)", value=ReverseProxyType.NONE
        ),
    ]

    return cast(
        ReverseProxyType,
        _check_cancelled(
            questionary.select(
                "Select reverse proxy configuration:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_frontend() -> FrontendType:
    """Prompt for frontend framework selection."""
    console.print()
    console.print("[bold cyan]Frontend Framework[/]")
    console.print()

    choices = [
        questionary.Choice("Next.js 15 (App Router, TypeScript, Bun)", value=FrontendType.NEXTJS),
        questionary.Choice("None (API only)", value=FrontendType.NONE),
    ]

    return cast(
        FrontendType,
        _check_cancelled(
            questionary.select(
                "Select frontend framework:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_frontend_features() -> dict[str, bool]:
    """Prompt for frontend-specific features."""
    console.print()
    console.print("[bold cyan]Frontend Features[/]")
    console.print()

    features = _check_cancelled(
        questionary.checkbox(
            "Select frontend features:",
            choices=[
                questionary.Choice("i18n (internationalization with next-intl)", value="i18n"),
            ],
        ).ask()
    )

    return {
        "enable_i18n": "i18n" in features,
    }


def prompt_ai_framework() -> AIFrameworkType:
    """Prompt for AI framework selection."""
    console.print()
    console.print("[bold cyan]AI Agent Framework[/]")
    console.print()

    choices = [
        questionary.Choice("PydanticAI (recommended)", value=AIFrameworkType.PYDANTIC_AI),
        questionary.Choice("LangChain", value=AIFrameworkType.LANGCHAIN),
        questionary.Choice("LangGraph (ReAct agent)", value=AIFrameworkType.LANGGRAPH),
        questionary.Choice("CrewAI (multi-agent crews)", value=AIFrameworkType.CREWAI),
        questionary.Choice("DeepAgents (agentic coding)", value=AIFrameworkType.DEEPAGENTS),
    ]

    return cast(
        AIFrameworkType,
        _check_cancelled(
            questionary.select(
                "Select AI framework:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_llm_provider(ai_framework: AIFrameworkType) -> LLMProviderType:
    """Prompt for LLM provider selection.

    Args:
        ai_framework: The selected AI framework. OpenRouter is only
            available for PydanticAI (not LangChain, LangGraph, CrewAI, or DeepAgents).
    """
    console.print()
    console.print("[bold cyan]LLM Provider[/]")
    console.print()

    choices = [
        questionary.Choice("OpenAI (gpt-4o-mini)", value=LLMProviderType.OPENAI),
        questionary.Choice("Anthropic (claude-sonnet-4-5)", value=LLMProviderType.ANTHROPIC),
    ]

    # OpenRouter only available for PydanticAI (not LangChain, LangGraph, or CrewAI)
    if ai_framework == AIFrameworkType.PYDANTIC_AI:
        choices.append(
            questionary.Choice("OpenRouter (multi-provider)", value=LLMProviderType.OPENROUTER)
        )

    return cast(
        LLMProviderType,
        _check_cancelled(
            questionary.select(
                "Select LLM provider:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_websocket_auth(auth: AuthType) -> WebSocketAuthType:
    """Prompt for WebSocket authentication method for AI Agent.

    Args:
        auth: The main auth type. JWT WebSocket auth is only available
            if JWT is enabled (JWT or BOTH).
    """
    console.print()
    console.print("[bold cyan]AI Agent WebSocket Authentication[/]")
    console.print()

    choices = [
        questionary.Choice("None (public access)", value=WebSocketAuthType.NONE),
    ]

    # JWT WebSocket auth only available if main auth uses JWT
    if auth in (AuthType.JWT, AuthType.BOTH):
        choices.append(questionary.Choice("JWT token required", value=WebSocketAuthType.JWT))

    # API Key WebSocket auth available if main auth uses API keys
    if auth in (AuthType.API_KEY, AuthType.BOTH):
        choices.append(
            questionary.Choice("API Key required (query param)", value=WebSocketAuthType.API_KEY)
        )

    return cast(
        WebSocketAuthType,
        _check_cancelled(
            questionary.select(
                "Select WebSocket authentication:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_admin_config() -> tuple[AdminEnvironmentType, bool]:
    """Prompt for admin panel configuration."""
    console.print()
    console.print("[bold cyan]Admin Panel Configuration[/]")
    console.print()

    env_choices = [
        questionary.Choice(
            "Development + Staging (recommended)", value=AdminEnvironmentType.DEV_STAGING
        ),
        questionary.Choice("Development only", value=AdminEnvironmentType.DEV_ONLY),
        questionary.Choice("All environments", value=AdminEnvironmentType.ALL),
        questionary.Choice("Disabled", value=AdminEnvironmentType.DISABLED),
    ]

    admin_environments = cast(
        AdminEnvironmentType,
        _check_cancelled(
            questionary.select(
                "Enable admin panel in which environments?",
                choices=env_choices,
                default=env_choices[0],
            ).ask()
        ),
    )

    # If disabled, skip auth question
    if admin_environments == AdminEnvironmentType.DISABLED:
        return admin_environments, False

    require_auth = _check_cancelled(
        questionary.confirm(
            "Require authentication for admin panel? (superuser login)",
            default=True,
        ).ask()
    )

    return admin_environments, require_auth


def prompt_python_version() -> str:
    """Prompt for Python version selection."""
    console.print()
    console.print("[bold cyan]Python Version[/]")
    console.print()

    choices = [
        questionary.Choice("Python 3.12 (recommended)", value="3.12"),
        questionary.Choice("Python 3.11", value="3.11"),
        questionary.Choice("Python 3.13", value="3.13"),
    ]

    return cast(
        str,
        _check_cancelled(
            questionary.select(
                "Select Python version:",
                choices=choices,
                default=choices[0],
            ).ask()
        ),
    )


def prompt_ports(has_frontend: bool) -> dict[str, int]:
    """Prompt for port configuration."""
    console.print()
    console.print("[bold cyan]Port Configuration[/]")
    console.print()

    def validate_port(value: str) -> bool:
        try:
            port = int(value)
            return 1024 <= port <= 65535
        except ValueError:
            return False

    backend_port_str = _check_cancelled(
        questionary.text(
            "Backend port:",
            default="8000",
            validate=validate_port,
        ).ask()
    )

    result = {"backend_port": int(backend_port_str)}

    if has_frontend:
        frontend_port_str = _check_cancelled(
            questionary.text(
                "Frontend port:",
                default="3000",
                validate=validate_port,
            ).ask()
        )
        result["frontend_port"] = int(frontend_port_str)

    return result


def run_interactive_prompts() -> ProjectConfig:
    """Run all interactive prompts and return configuration."""
    show_header()

    # Basic info
    basic_info = prompt_basic_info()

    # Database
    database = prompt_database()

    # ORM type (only for PostgreSQL or SQLite)
    orm_type = OrmType.SQLALCHEMY
    if database in (DatabaseType.POSTGRESQL, DatabaseType.SQLITE):
        orm_type = prompt_orm_type()

    # Auth
    auth = prompt_auth()

    # OAuth (only if JWT auth is enabled)
    oauth_provider = OAuthProvider.NONE
    enable_session_management = False
    if auth in (AuthType.JWT, AuthType.BOTH):
        oauth_provider = prompt_oauth()
        # Session management (only if JWT and database enabled)
        if database != DatabaseType.NONE:
            enable_session_management = _check_cancelled(
                questionary.confirm(
                    "Enable session management? (track active sessions, logout from devices)",
                    default=False,
                ).ask()
            )

    # Background tasks (before Logfire so we can conditionally show Celery instrumentation)
    background_tasks = prompt_background_tasks()

    # Logfire
    enable_logfire, logfire_features = prompt_logfire(background_tasks)

    # Integrations (pass context for dynamic option filtering)
    integrations = prompt_integrations(database=database, orm_type=orm_type)

    # Dev tools
    dev_tools = prompt_dev_tools()

    # Reverse proxy (only if Docker is enabled)
    reverse_proxy = ReverseProxyType.TRAEFIK_INCLUDED
    if dev_tools.get("enable_docker"):
        reverse_proxy = prompt_reverse_proxy()

    # Frontend
    frontend = prompt_frontend()

    # Python version
    python_version = prompt_python_version()

    # Port configuration
    ports = prompt_ports(has_frontend=frontend != FrontendType.NONE)

    # Auto-enable Redis for Celery/Taskiq/ARQ (they require Redis as broker)
    if background_tasks in (
        BackgroundTaskType.CELERY,
        BackgroundTaskType.TASKIQ,
        BackgroundTaskType.ARQ,
    ):
        integrations["enable_redis"] = True

    # AI framework, LLM provider, WebSocket auth and conversation persistence for AI Agent
    ai_framework = AIFrameworkType.PYDANTIC_AI
    llm_provider = LLMProviderType.OPENAI
    websocket_auth = WebSocketAuthType.NONE
    enable_conversation_persistence = False
    if integrations.get("enable_ai_agent"):
        ai_framework = prompt_ai_framework()
        llm_provider = prompt_llm_provider(ai_framework)
        websocket_auth = prompt_websocket_auth(auth=auth)
        # Only offer persistence if database is enabled
        if database != DatabaseType.NONE:
            enable_conversation_persistence = _check_cancelled(
                questionary.confirm(
                    "Enable conversation persistence (save chat history to database)?",
                    default=True,
                ).ask()
            )

    # Admin panel configuration (when enabled and SQL database - PostgreSQL or SQLite)
    admin_environments = AdminEnvironmentType.DEV_STAGING
    admin_require_auth = True
    if integrations.get("enable_admin_panel") and database in (
        DatabaseType.POSTGRESQL,
        DatabaseType.SQLITE,
    ):
        admin_environments, admin_require_auth = prompt_admin_config()

    # Rate limit configuration (when rate limiting is enabled)
    rate_limit_requests = 100
    rate_limit_period = 60
    rate_limit_storage = RateLimitStorageType.MEMORY
    if integrations.get("enable_rate_limiting"):
        rate_limit_requests, rate_limit_period, rate_limit_storage = prompt_rate_limit_config(
            redis_enabled=integrations.get("enable_redis", False)
        )

    # Frontend features (i18n, etc.)
    frontend_features: dict[str, bool] = {}
    if frontend != FrontendType.NONE:
        frontend_features = prompt_frontend_features()

    # Extract ci_type separately for type safety
    ci_type = cast(CIType, dev_tools.pop("ci_type"))

    # Build config
    config = ProjectConfig(
        project_name=basic_info["project_name"],
        project_description=basic_info["project_description"],
        author_name=basic_info["author_name"],
        author_email=basic_info["author_email"],
        database=database,
        orm_type=orm_type,
        auth=auth,
        oauth_provider=oauth_provider,
        enable_session_management=enable_session_management,
        enable_logfire=enable_logfire,
        logfire_features=logfire_features,
        background_tasks=background_tasks,
        ai_framework=ai_framework,
        llm_provider=llm_provider,
        websocket_auth=websocket_auth,
        enable_conversation_persistence=enable_conversation_persistence,
        admin_environments=admin_environments,
        admin_require_auth=admin_require_auth,
        rate_limit_requests=rate_limit_requests,
        rate_limit_period=rate_limit_period,
        rate_limit_storage=rate_limit_storage,
        python_version=python_version,
        ci_type=ci_type,
        reverse_proxy=reverse_proxy,
        frontend=frontend,
        backend_port=ports["backend_port"],
        frontend_port=ports.get("frontend_port", 3000),
        **integrations,
        **dev_tools,
        **frontend_features,
    )

    return config


def show_summary(config: ProjectConfig) -> None:
    """Display configuration summary."""
    console.print()
    console.print("[bold green]Configuration Summary[/]")
    console.print()

    console.print(f"  [cyan]Project:[/] {config.project_name}")
    console.print(f"  [cyan]Database:[/] {config.database.value}")
    if config.database in (DatabaseType.POSTGRESQL, DatabaseType.SQLITE):
        console.print(f"  [cyan]ORM:[/] {config.orm_type.value}")
    auth_str = config.auth.value
    if config.oauth_provider != OAuthProvider.NONE:
        auth_str += f" + {config.oauth_provider.value} OAuth"
    console.print(f"  [cyan]Auth:[/] {auth_str}")
    console.print(f"  [cyan]Logfire:[/] {'enabled' if config.enable_logfire else 'disabled'}")
    console.print(f"  [cyan]Background Tasks:[/] {config.background_tasks.value}")
    console.print(f"  [cyan]Frontend:[/] {config.frontend.value}")

    enabled_features = []
    if config.enable_redis:
        enabled_features.append("Redis")
    if config.enable_caching:
        enabled_features.append("Caching")
    if config.enable_rate_limiting:
        rate_info = f"Rate Limiting ({config.rate_limit_requests}/{config.rate_limit_period}s, {config.rate_limit_storage.value})"
        enabled_features.append(rate_info)
    if config.enable_admin_panel:
        admin_info = "Admin Panel"
        if config.admin_environments.value != "all":
            admin_info += f" ({config.admin_environments.value})"
        if config.admin_require_auth:
            admin_info += " [auth]"
        enabled_features.append(admin_info)
    if config.enable_websockets:
        enabled_features.append("WebSockets")
    if config.enable_ai_agent:
        ai_info = f"AI Agent ({config.ai_framework.value}, {config.llm_provider.value})"
        enabled_features.append(ai_info)
    if config.enable_webhooks:
        enabled_features.append("Webhooks")
    if config.enable_i18n:
        enabled_features.append("i18n")
    if config.include_example_crud:
        enabled_features.append("Example CRUD")
    if config.enable_docker:
        enabled_features.append("Docker")

    if enabled_features:
        console.print(f"  [cyan]Features:[/] {', '.join(enabled_features)}")

    console.print()


def confirm_generation() -> bool:
    """Confirm project generation."""
    return cast(
        bool,
        _check_cancelled(
            questionary.confirm(
                "Generate project with this configuration?",
                default=True,
            ).ask()
        ),
    )
