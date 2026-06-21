"""CLI interface for Full-Stack AI Agent Template Generator."""

from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .config import (
    AIFrameworkType,
    AuthMode,
    BackgroundTaskType,
    BillingModelType,
    CIType,
    DatabaseType,
    EmailProviderType,
    FrontendType,
    LLMProviderType,
    NewsletterProviderType,
    OAuthProvider,
    OrmType,
    PaymentProviderType,
    PdfParserType,
    ProjectConfig,
    RAGFeatures,
    RerankerType,
    ReverseProxyType,
    TenancyMode,
    VectorStoreType,
)
from .generator import generate_project, post_generation_tasks
from .prompts import confirm_generation, run_interactive_prompts, show_summary

console = Console()


def _preflight_check(  # noqa: C901
    *,
    billing: bool,
    credits: bool,
    teams: bool,
    usage_dashboard: bool,
    anomaly_detection: bool,
    slack_alerts: bool,
    newsletter: bool,
    email: bool,
    rag: bool,
    database: str,
    vector_store: str,
    frontend: str,
    admin_panel: bool,
    marketing_site: bool,
    oauth_google: bool,
    gdrive_rag: bool,
    s3_rag: bool,
    task_queue: str,
    redis: bool,
    caching: bool,
    rate_limiting: bool,  # noqa: ARG001 — reserved for future pre-flight checks
    llm_provider: str,
) -> None:
    """Catch common flag conflicts BEFORE ProjectConfig validation.

    Pydantic raises one error at a time after parsing finishes. This pre-flight
    collects ALL conflicts and shows them with "Quick fix" hints, so users can
    correct everything in one go. Pydantic validators stay as the source of
    truth for programmatic use; this is purely UX polish.
    """
    issues: list[tuple[str, str]] = []  # (problem, quick_fix)

    # --- Teams / billing dependency chain ---
    if billing and not teams:
        issues.append(
            (
                "--billing requires --teams (Stripe subscriptions are scoped to organizations)",
                "Add --teams or remove --billing",
            )
        )
    if credits and not billing:
        issues.append(
            (
                "--credits requires --billing (credits are tied to Stripe pricing)",
                "Add --billing --teams (or drop --credits)",
            )
        )
    if usage_dashboard and not credits:
        issues.append(
            (
                "--usage-dashboard requires --credits (it visualises credit consumption)",
                "Add --credits --billing --teams",
            )
        )
    if anomaly_detection and not credits:
        issues.append(
            (
                "--anomaly-detection requires --credits (it flags credit-spend anomalies)",
                "Add --credits --billing --teams",
            )
        )
    if slack_alerts and not anomaly_detection:
        issues.append(
            (
                "--slack-alerts requires --anomaly-detection (alerts ride on detected anomalies)",
                "Add --anomaly-detection --credits --billing --teams",
            )
        )

    # --- Email / newsletter ---
    if newsletter and not email:
        issues.append(
            (
                "--newsletter requires --email (signup confirmation needs a transactional sender)",
                "Add --email or drop --newsletter",
            )
        )

    # --- RAG dependency chain ---
    if rag and database == "none":
        issues.append(
            (
                "--rag requires a database (RAGDocument table stores per-doc metadata)",
                "Pick --database postgresql",
            )
        )
    if rag and vector_store == "pgvector" and database != "postgresql":
        issues.append(
            (
                f"--vector-store=pgvector requires --database=postgresql, got {database}",
                "Switch to --database postgresql or pick --vector-store milvus|qdrant|chromadb",
            )
        )
    if gdrive_rag and not rag:
        issues.append(
            (
                "--gdrive-rag requires --rag (Drive sync feeds the vector store)",
                "Add --rag",
            )
        )
    if s3_rag and not rag:
        issues.append(
            (
                "--s3-rag requires --rag (S3 sync feeds the vector store)",
                "Add --rag",
            )
        )

    # --- Frontend-dependent features ---
    if marketing_site and frontend == "none":
        issues.append(
            (
                "--marketing-site requires --frontend nextjs (landing/blog/legal pages need a UI)",
                "Add --frontend nextjs or drop --marketing-site",
            )
        )
    if admin_panel and frontend == "none":
        click.echo(
            click.style(
                "⚠ --admin-panel: SQLAdmin UI lives in the frontend. "
                "Backend admin REST routes (/admin/users, /admin/conversations, etc.) "
                "still work without it — add --frontend nextjs for the visual panel.",
                fg="yellow",
            ),
            err=True,
        )
    if oauth_google and frontend == "none":
        issues.append(
            (
                "--oauth-google needs the frontend callback page",
                "Add --frontend nextjs or drop --oauth-google",
            )
        )

    # --- Background queue / Redis ---
    if task_queue in ("celery", "taskiq", "arq") and not redis:
        issues.append(
            (
                f"--task-queue={task_queue} requires --redis (broker/result backend)",
                f"Add --redis (it'll auto-enable for queue={task_queue})",
            )
        )
    if caching and not redis:
        issues.append(
            (
                "--caching requires --redis (cache backend)",
                "Add --redis or drop --caching",
            )
        )

    # --- Multi-LLM context ---
    if llm_provider == "all" and frontend == "none":
        # Not an error — just a warning. Skip for headless/API-only uses.
        click.echo(
            click.style(
                "⚠ --llm-provider=all is most useful with the chat UI provider switcher; "
                "without --frontend you'll need to pick the model server-side per-request.",
                fg="yellow",
            ),
            err=True,
        )

    if not issues:
        return

    msg_lines = [
        click.style(
            f"✗ {len(issues)} conflicting flag combination{'s' if len(issues) > 1 else ''} found:",
            fg="red",
            bold=True,
        ),
        "",
    ]
    for i, (problem, fix) in enumerate(issues, 1):
        msg_lines.append(click.style(f"  {i}. {problem}", fg="red"))
        msg_lines.append(click.style(f"     Quick fix: {fix}", fg="yellow"))
        msg_lines.append("")
    msg_lines.append(
        click.style(
            "Run `fastapi-fullstack templates` to see preset shortcuts for common scenarios.",
            fg="cyan",
        )
    )
    raise click.UsageError("\n".join(msg_lines))


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="fastapi-fullstack")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Full-Stack AI Agent Template Generator.

    Generate production-ready FastAPI + Next.js projects with AI agents,
    WebSocket streaming, 20+ enterprise integrations, and observability.
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(new)


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
@click.option(
    "--minimal",
    is_flag=True,
    default=False,
    help="Skip wizard — ask only for project name and use minimal defaults (PostgreSQL, no Docker/Redis/CI)",
)
def new(output: Path | None, no_input: bool, name: str | None, minimal: bool) -> None:
    """Create a new FastAPI project interactively."""
    try:
        if no_input or minimal:
            if not name:
                if minimal:
                    import questionary

                    name = questionary.text(
                        "Project name:",
                        validate=lambda v: bool(v) or "Name cannot be empty",
                    ).ask()
                    if not name:
                        console.print("\n[yellow]Cancelled.[/]")
                        return
                else:
                    console.print("[red]Error:[/] --name is required when using --no-input")
                    raise SystemExit(1)

            if minimal:
                config = ProjectConfig(
                    project_name=name,
                    database=DatabaseType.POSTGRESQL,
                    enable_logfire=False,
                    enable_redis=False,
                    enable_caching=False,
                    enable_rate_limiting=False,
                    enable_pagination=False,
                    enable_admin_panel=False,
                    enable_docker=False,
                    enable_kubernetes=False,
                    background_tasks=BackgroundTaskType.NONE,
                    ci_type=CIType.NONE,
                )
                console.print(f"[cyan]Creating minimal project:[/] {name}")
                console.print("[dim]PostgreSQL · no Docker · no Redis · no CI[/]")
                console.print()
            else:
                config = ProjectConfig(project_name=name, background_tasks=BackgroundTaskType.NONE)
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
    type=click.Choice(["postgresql"]),
    default="postgresql",
    help="Database type",
)
@click.option(
    "--orm",
    type=click.Choice(["sqlalchemy", "sqlmodel"]),
    default="sqlalchemy",
    help="ORM library (sqlalchemy or sqlmodel)",
)
@click.option("--no-logfire", is_flag=True, help="Disable Logfire integration")
@click.option("--no-docker", is_flag=True, help="Disable Docker files")
@click.option("--no-env", is_flag=True, help="Skip .env file generation")
@click.option("--minimal", is_flag=True, help="Create minimal project (no extras)")
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
    "--timezone",
    type=str,
    default="UTC",
    help="IANA timezone (e.g. UTC, Europe/Warsaw, America/New_York)",
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
    "--ai-framework",
    type=click.Choice(
        ["none", "pydantic_ai", "langchain", "langgraph", "deepagents", "pydantic_deep"]
    ),
    default="pydantic_ai",
    help="AI framework (default: pydantic_ai). Use 'none' for plain SaaS without AI/chat.",
)
@click.option(
    "--llm-provider",
    type=click.Choice(["openai", "anthropic", "google", "openrouter", "all"]),
    default="openai",
    help=(
        "LLM provider (default: openai). 'all' installs every SDK and lets users "
        "pick the model at runtime. openrouter requires pydantic_ai."
    ),
)
@click.option("--redis", is_flag=True, help="Enable Redis")
@click.option("--caching", is_flag=True, help="Enable caching (requires --redis)")
@click.option("--rate-limiting", is_flag=True, help="Enable rate limiting")
@click.option("--admin-panel", is_flag=True, help="Enable admin panel (SQLAdmin)")
@click.option(
    "--admin-features",
    type=str,
    default=None,
    help=(
        "Comma-separated list of admin panel sections to enable "
        "(users,orgs,subs,usage,events,audit,health). "
        "Defaults to all sections when --admin-panel is set."
    ),
)
@click.option(
    "--task-queue",
    type=click.Choice(["none", "celery", "taskiq", "arq"]),
    default="none",
    help="Background task queue",
)
@click.option("--oauth-google", is_flag=True, help="Enable Google OAuth")
@click.option(
    "--auth-mode",
    type=click.Choice(["local", "delegated"]),
    default="local",
    help=(
        "local (default): backend handles email/password + optional OAuth. "
        "delegated: backend trusts JWTs from external IdP (Auth0/Clerk/Cognito/Keycloak) "
        "validated against a public JWKS URL. No registration UI, no password storage."
    ),
)
@click.option(
    "--shared-secret-jwt",
    is_flag=True,
    default=False,
    help=(
        "When --auth-mode=delegated: validate JWTs with a shared HMAC secret "
        "(HS256) instead of fetching public keys from a JWKS URL. Use when the "
        "client backend signs short-lived tokens for our API with a known secret."
    ),
)
@click.option(
    "--external-user-id",
    is_flag=True,
    default=False,
    help=(
        "When --auth-mode=delegated: denormalize the IdP `sub` onto Conversation "
        "rows so client APIs can list conversations by their user identifier "
        "without leaking internal UUIDs."
    ),
)
@click.option(
    "--websockets",
    is_flag=True,
    default=False,
    help="Enable WebSocket support (required for real-time AI chat)",
)
@click.option(
    "--web-search",
    is_flag=True,
    default=False,
    help="Enable web search tool for AI agents (Tavily)",
)
@click.option(
    "--web-fetch", is_flag=True, default=False, help="Enable web fetch/scraping tool for AI agents"
)
@click.option(
    "--charts",
    is_flag=True,
    default=False,
    help="Enable the chart-generation tool for AI agents (line/bar/pie/area/scatter)",
)
@click.option(
    "--code-execution",
    is_flag=True,
    default=False,
    help="Enable the run_python code-execution tool backed by the Monty sandbox (PydanticAI only)",
)
@click.option(
    "--skills",
    is_flag=True,
    default=False,
    help="Enable the skills system (SkillsToolset loads SKILL.md files from backend/skills/, PydanticAI only)",
)
@click.option(
    "--deep-research",
    is_flag=True,
    default=False,
    help="Enable the deep research agent (TODO planner + subagents + context manager, PydanticAI only)",
)
@click.option("--session-management", is_flag=True, help="Enable session management")
@click.option(
    "--reverse-proxy",
    type=click.Choice(["none", "nginx", "traefik"]),
    default="nginx",
    help="Reverse proxy configuration (default: nginx — external nginx, config template only)",
)
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
    "--langsmith",
    is_flag=True,
    help="Enable LangSmith observability (LangChain/LangGraph/DeepAgents)",
)
@click.option(
    "--python-version",
    type=click.Choice(["3.11", "3.12", "3.13"]),
    default="3.12",
    help="Python version",
)
@click.option(
    "--preset",
    type=click.Choice(
        [
            "production",
            "ai-agent",
            "production-saas",
            "b2b-multi-tenant",
            "internal-tool",
            "embedded-chatbot",
            "blog-saas",
            "consumer-app",
            "dev-playground",
        ]
    ),
    default=None,
    help=("Apply configuration preset. Run `fastapi-fullstack templates` for full descriptions."),
)
@click.option(
    "--rag",
    is_flag=True,
    default=False,
    help="Enable RAG feature.",
)
@click.option(
    "--vector-store",
    type=click.Choice(["milvus", "qdrant", "chromadb", "pgvector"]),
    default="milvus",
    help="Vector store backend (default: milvus)",
)
@click.option(
    "--gdrive-rag",
    is_flag=True,
    default=False,
    help="Use Google Drive for document ingestion",
)
@click.option(
    "--s3-rag",
    is_flag=True,
    default=False,
    help="Use S3/MinIO for document ingestion",
)
@click.option(
    "--reranker",
    type=click.Choice(["none", "cohere", "cross_encoder"]),
    default="none",
    help="Choose reranking logic.",
)
@click.option(
    "--pdf-parser",
    type=click.Choice(["pymupdf", "liteparse", "llamaparse", "all"]),
    default="pymupdf",
    help="PDF parser (pymupdf=local, liteparse=local AI, llamaparse=cloud, all=runtime selection)",
)
@click.option("--telegram", is_flag=True, default=False, help="Enable Telegram notifications")
@click.option("--slack", is_flag=True, default=False, help="Enable Slack notifications")
@click.option("--teams", is_flag=True, default=False, help="Enable Teams/organizations feature")
@click.option(
    "--billing", is_flag=True, default=False, help="Enable Stripe billing (requires --teams)"
)
@click.option(
    "--credits",
    is_flag=True,
    default=False,
    help="Enable credits system (requires --billing)",
)
@click.option(
    "--usage-dashboard",
    is_flag=True,
    default=False,
    help="Enable usage dashboard (requires --credits)",
)
@click.option(
    "--anomaly-detection",
    is_flag=True,
    default=False,
    help="Enable usage anomaly detection (requires --credits)",
)
@click.option(
    "--slack-alerts",
    is_flag=True,
    default=False,
    help="Enable Slack alerts for anomalies (requires --anomaly-detection)",
)
@click.option(
    "--billing-currency",
    type=str,
    default="usd",
    help="Default billing currency (default: usd)",
)
@click.option(
    "--trial-days",
    type=int,
    default=14,
    help="Free trial length in days (default: 14)",
)
@click.option(
    "--trial-requires-card/--no-trial-requires-card",
    default=True,
    help="Require a payment card to start a trial (default: yes; pass --no-trial-requires-card to allow card-free trials)",
)
@click.option("--email", is_flag=True, default=False, help="Enable transactional email")
@click.option(
    "--email-provider",
    type=click.Choice(["resend", "smtp", "log"]),
    default="log",
    help="Email provider (default: log — prints to console)",
)
@click.option(
    "--newsletter",
    is_flag=True,
    default=False,
    help="Enable newsletter signup (requires --email)",
)
@click.option(
    "--marketing-site",
    is_flag=True,
    default=False,
    help="Generate marketing/landing pages",
)
@click.option(
    "--i18n/--no-i18n",
    "i18n",
    default=True,
    help="Generate i18n infrastructure (next-intl + locale switcher). "
    "Disable for single-language English-only frontends.",
)
@click.option(
    "--example-resource",
    is_flag=True,
    default=False,
    help=(
        "Scaffold an example Item CRUD (model + repo + service + routes + "
        "migration) as a reference for adding new domains. "
        "Requires --database postgresql."
    ),
)
@click.option("--changelog", is_flag=True, default=False, help="Generate changelog page")
@click.option("--testimonials", is_flag=True, default=False, help="Generate testimonials section")
@click.option(
    "--comparison-pages",
    is_flag=True,
    default=False,
    help="Generate competitor comparison pages",
)
@click.option("--affiliate", is_flag=True, default=False, help="Generate affiliate program pages")
@click.option(
    "--status-badge", is_flag=True, default=False, help="Add status/uptime badge to frontend"
)
@click.option(
    "--allowed-email-domains",
    type=str,
    default="",
    help=(
        "Comma-separated email domains allowed to register via OAuth "
        "(e.g. 'example.com,acme.com'). Empty = allow all."
    ),
)
@click.option(
    "--seed-admin-email",
    type=str,
    default="",
    help="Email to auto-promote to app-admin on first startup (written to .env as FIRST_ADMIN_EMAIL).",
)
@click.option(
    "--embed-allowed-origins",
    type=str,
    default="",
    help=(
        "Comma-separated origins allowed to embed the app in an iframe "
        "(sets CSP frame-ancestors + CORS). Empty = 'frame-ancestors none'."
    ),
)
@click.option(
    "--brand-from-config",
    is_flag=True,
    default=False,
    help="Load brand color/logo from BRAND_COLOR/BRAND_LOGO_URL env vars at runtime (white-label).",
)
@click.option(
    "--newsletter-provider",
    type=click.Choice(["resend", "mailchimp", "convertkit"]),
    default="resend",
    help="Newsletter/audience provider when --newsletter is set (default: resend).",
)
@click.option(
    "--tenancy",
    type=click.Choice(["single", "multi_org", "platform"]),
    default="single",
    help="Tenancy architecture: single (default), multi_org (requires --teams), platform.",
)
@click.option(
    "--per-org-quotas",
    is_flag=True,
    default=False,
    help="Enable per-organisation usage quotas (requires --teams).",
)
@click.option(
    "--payment-provider",
    type=click.Choice(["stripe", "paddle", "lemonsqueezy", "polar"]),
    default="stripe",
    help="Payment processor (default: stripe — only Stripe is fully implemented).",
)
@click.option(
    "--billing-model",
    type=click.Choice(["subscription", "usage", "hybrid", "one_time"]),
    default="subscription",
    help="Billing model (default: subscription — hybrid = base plan + credits).",
)
@click.option(
    "--storybook",
    is_flag=True,
    default=False,
    help="Generate Storybook setup for frontend components.",
)
def create(
    name: str,
    output: Path | None,
    database: str,
    orm: str,
    no_logfire: bool,
    no_docker: bool,
    no_env: bool,
    minimal: bool,
    frontend: str,
    backend_port: int,
    frontend_port: int,
    db_pool_size: int,
    db_max_overflow: int,
    ai_framework: str,
    llm_provider: str,
    # Optional features
    redis: bool,
    caching: bool,
    rate_limiting: bool,
    admin_panel: bool,
    admin_features: str | None,
    task_queue: str,
    oauth_google: bool,
    auth_mode: str,
    shared_secret_jwt: bool,
    external_user_id: bool,
    websockets: bool,
    web_search: bool,
    web_fetch: bool,
    charts: bool,
    code_execution: bool,
    skills: bool,
    deep_research: bool,
    session_management: bool,
    reverse_proxy: str,
    kubernetes: bool,
    ci: str,
    sentry: bool,
    prometheus: bool,
    file_storage: bool,
    webhooks: bool,
    langsmith: bool,
    python_version: str,
    rag: bool,
    vector_store: str,
    gdrive_rag: bool,
    s3_rag: bool,
    reranker: str,
    pdf_parser: str,
    timezone: str,
    preset: str | None,
    telegram: bool,
    slack: bool,
    teams: bool,
    billing: bool,
    credits: bool,
    usage_dashboard: bool,
    anomaly_detection: bool,
    slack_alerts: bool,
    billing_currency: str,
    trial_days: int,
    trial_requires_card: bool,
    email: bool,
    email_provider: str,
    newsletter: bool,
    marketing_site: bool,
    i18n: bool,
    example_resource: bool,
    changelog: bool,
    testimonials: bool,
    comparison_pages: bool,
    affiliate: bool,
    status_badge: bool,
    allowed_email_domains: str,
    seed_admin_email: str,
    embed_allowed_origins: str,
    brand_from_config: bool,
    newsletter_provider: str,
    tenancy: str,
    per_org_quotas: bool,
    payment_provider: str,
    billing_model: str,
    storybook: bool,
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
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "ai-agent":
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=True,
                enable_redis=True,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_langsmith=ai_framework in ("langchain", "langgraph", "deepagents"),
                enable_docker=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "production-saas":
            # Full SaaS stack: Stripe billing + credits + teams + admin + email +
            # Sentry + Kubernetes + GitHub Actions. Postgres + Redis + RAG-ready.
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=True,
                enable_redis=True,
                enable_caching=True,
                enable_rate_limiting=True,
                enable_sentry=True,
                enable_prometheus=True,
                enable_admin_panel=True,
                enable_session_management=True,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_langsmith=ai_framework in ("langchain", "langgraph", "deepagents"),
                enable_teams=True,
                enable_billing=True,
                enable_credits_system=True,
                enable_usage_dashboard=True,
                enable_email=True,
                email_provider=EmailProviderType.RESEND,
                enable_marketing_site=True,
                enable_docker=True,
                enable_kubernetes=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType.NEXTJS,
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "b2b-multi-tenant":
            # B2B with workspaces, billing, credits, usage dashboard, admin.
            # Note: full scenario also wants invite-only signup + 2FA — those
            # require new --auth-mode flag which doesn't exist yet (see notes/
            # thingstofix.md §A). For now we ship session_management + admin so
            # account-takeover surface is reasonable.
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=True,
                enable_redis=True,
                enable_caching=True,
                enable_rate_limiting=True,
                enable_sentry=True,
                enable_admin_panel=True,
                enable_session_management=True,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_teams=True,
                enable_billing=True,
                enable_credits_system=True,
                enable_usage_dashboard=True,
                enable_email=True,
                email_provider=EmailProviderType.RESEND,
                enable_marketing_site=False,
                enable_docker=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType.NEXTJS,
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "internal-tool":
            # Internal tool / staff dashboard: SSO via Google OAuth, no public
            # signup landing pages, no billing. Teams + admin enabled. Note:
            # SSO-only enforcement (disable email/password registration) needs
            # --auth-mode=sso-only which is wishlist (see thingstofix §A).
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=True,
                enable_redis=True,
                enable_admin_panel=True,
                enable_session_management=True,
                oauth_provider=OAuthProvider.GOOGLE,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_teams=True,
                enable_billing=False,
                enable_marketing_site=False,
                enable_docker=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType.NEXTJS,
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "embedded-chatbot":
            # Chat widget to be embedded in client's existing site. Delegated
            # auth — backend trusts JWTs from client's IdP (Auth0/Clerk/...).
            # No marketing pages, no teams, no billing. Note: --embed-mode
            # (widget loader + iframe-ready chat) is still wishlist; deployer
            # wires client-side embed integration manually.
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                auth_mode=AuthMode.DELEGATED,
                enable_logfire=True,
                enable_redis=False,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_teams=False,
                enable_billing=False,
                enable_marketing_site=False,
                enable_session_management=False,
                enable_admin_panel=False,
                background_tasks=BackgroundTaskType.NONE,
                enable_docker=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType.NEXTJS,
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "blog-saas":
            # Content-first SaaS with auth + marketing/blog/legal. No AI/chat —
            # plain SaaS with newsletter, email, and public marketing pages.
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=False,
                enable_redis=False,
                enable_websockets=False,
                ai_framework=AIFrameworkType.NONE,
                llm_provider=LLMProviderType.OPENAI,
                enable_teams=False,
                enable_billing=False,
                enable_email=True,
                email_provider=EmailProviderType.RESEND,
                enable_newsletter_signup=True,
                enable_marketing_site=True,
                enable_changelog=True,
                enable_admin_panel=False,
                background_tasks=BackgroundTaskType.NONE,
                enable_docker=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType.NEXTJS,
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "consumer-app":
            # B2C consumer SaaS: OAuth login, marketing site, billing.
            # Note: --magic-link, --analytics=plausible|posthog, and
            # --billing=consumer (one-time purchases vs subscription) are
            # wishlist. For now we ship Google OAuth + Stripe subscription.
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=True,
                enable_redis=True,
                enable_caching=True,
                enable_sentry=True,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                oauth_provider=OAuthProvider.GOOGLE,
                enable_teams=True,
                enable_billing=True,
                enable_credits_system=True,
                enable_email=True,
                email_provider=EmailProviderType.RESEND,
                enable_marketing_site=True,
                enable_admin_panel=True,
                enable_session_management=True,
                enable_docker=True,
                ci_type=CIType.GITHUB,
                generate_env=not no_env,
                frontend=FrontendType.NEXTJS,
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif preset == "dev-playground":
            # Local prototyping for AI features: PostgreSQL, no Docker, no CI,
            # ChromaDB (file-based vector store, no separate Milvus container).
            # Use this when iterating on agents/prompts/RAG locally without
            # spinning up the full production stack.
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=False,
                enable_redis=False,
                enable_caching=False,
                enable_rate_limiting=False,
                enable_pagination=False,
                enable_admin_panel=False,
                enable_websockets=True,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_teams=False,
                enable_billing=False,
                enable_marketing_site=False,
                enable_docker=False,
                enable_kubernetes=False,
                background_tasks=BackgroundTaskType.NONE,
                ci_type=CIType.NONE,
                generate_env=not no_env,
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        elif minimal:
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType.POSTGRESQL,
                enable_logfire=False,
                enable_redis=False,
                enable_caching=False,
                enable_rate_limiting=False,
                enable_pagination=False,
                enable_admin_panel=False,
                enable_docker=False,
                enable_kubernetes=False,
                background_tasks=BackgroundTaskType.NONE,
                ci_type=CIType.NONE,
                generate_env=not no_env,
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                python_version=python_version,
                timezone=timezone,
            )
        else:
            # Pre-flight: catch common conflicting combinations BEFORE Pydantic
            # validation so users get all errors at once with quick-fix hints.
            # Pydantic still runs after this and is the source of truth.
            _preflight_check(
                billing=billing,
                credits=credits,
                teams=teams,
                usage_dashboard=usage_dashboard,
                anomaly_detection=anomaly_detection,
                slack_alerts=slack_alerts,
                newsletter=newsletter,
                email=email,
                rag=rag,
                database=database,
                vector_store=vector_store,
                frontend=frontend,
                admin_panel=admin_panel,
                marketing_site=marketing_site,
                oauth_google=oauth_google,
                gdrive_rag=gdrive_rag,
                s3_rag=s3_rag,
                task_queue=task_queue,
                redis=redis,
                caching=caching,
                rate_limiting=rate_limiting,
                llm_provider=llm_provider,
            )

            # Parse --admin-features comma-separated list
            _all_admin = {"users", "orgs", "subs", "usage", "events", "audit", "health"}
            if admin_features is not None:
                _chosen = {f.strip() for f in admin_features.split(",")} & _all_admin
            else:
                _chosen = _all_admin  # default: all enabled

            # Map --reverse-proxy shorthand to ReverseProxyType
            _rp_map = {
                "none": ReverseProxyType.NONE,
                "nginx": ReverseProxyType.NGINX_EXTERNAL,
                "traefik": ReverseProxyType.TRAEFIK_EXTERNAL,
            }

            # Full custom configuration with all options
            config = ProjectConfig(
                project_name=name,
                database=DatabaseType(database),
                orm_type=OrmType(orm),
                enable_logfire=not no_logfire,
                enable_docker=not no_docker,
                generate_env=not no_env,
                frontend=FrontendType(frontend),
                backend_port=backend_port,
                frontend_port=frontend_port,
                db_pool_size=db_pool_size,
                db_max_overflow=db_max_overflow,
                ai_framework=AIFrameworkType(ai_framework),
                llm_provider=LLMProviderType(llm_provider),
                enable_redis=redis,
                enable_caching=caching,
                enable_rate_limiting=rate_limiting,
                enable_admin_panel=admin_panel,
                enable_admin_features_users="users" in _chosen,
                enable_admin_features_organizations="orgs" in _chosen,
                enable_admin_features_subscriptions="subs" in _chosen,
                enable_admin_features_usage="usage" in _chosen,
                enable_admin_features_stripe_events="events" in _chosen,
                enable_admin_features_audit_log="audit" in _chosen,
                enable_admin_features_system_health="health" in _chosen,
                background_tasks=BackgroundTaskType(task_queue),
                oauth_provider=OAuthProvider.GOOGLE if oauth_google else OAuthProvider.NONE,
                auth_mode=AuthMode(auth_mode),
                delegated_auth_use_shared_secret=shared_secret_jwt,
                enable_external_user_id_in_conversations=external_user_id,
                enable_websockets=websockets,
                enable_web_search=web_search,
                enable_web_fetch=web_fetch,
                enable_charts=charts,
                enable_code_execution=code_execution,
                enable_skills=skills,
                enable_deep_research=deep_research,
                enable_session_management=session_management,
                reverse_proxy=_rp_map[reverse_proxy],
                enable_kubernetes=kubernetes,
                ci_type=CIType(ci),
                enable_sentry=sentry,
                enable_prometheus=prometheus,
                enable_file_storage=file_storage,
                enable_webhooks=webhooks,
                enable_langsmith=langsmith,
                python_version=python_version,
                timezone=timezone,
                rag_features=RAGFeatures(
                    enable_rag=rag,
                    vector_store=VectorStoreType(vector_store),
                    enable_google_drive_ingestion=gdrive_rag,
                    enable_s3_ingestion=s3_rag,
                    reranker_type=RerankerType(reranker),
                    pdf_parser=PdfParserType(pdf_parser),
                ),
                use_telegram=telegram,
                use_slack=slack,
                enable_teams=teams,
                enable_billing=billing,
                enable_credits_system=credits,
                enable_usage_dashboard=usage_dashboard,
                enable_usage_anomaly_detection=anomaly_detection,
                enable_slack_alerts=slack_alerts,
                billing_default_currency=billing_currency,
                billing_trial_days_default=trial_days,
                billing_trial_requires_card=trial_requires_card,
                enable_email=email,
                email_provider=EmailProviderType(email_provider),
                enable_newsletter_signup=newsletter,
                enable_marketing_site=marketing_site,
                enable_i18n=i18n,
                include_example_crud=example_resource,
                enable_changelog=changelog,
                enable_testimonials=testimonials,
                enable_comparison_pages=comparison_pages,
                enable_affiliate_program=affiliate,
                enable_status_badge=status_badge,
                allowed_email_domains=allowed_email_domains,
                seed_admin_email=seed_admin_email,
                embed_allowed_origins=embed_allowed_origins,
                enable_brand_from_config=brand_from_config,
                newsletter_provider=NewsletterProviderType(newsletter_provider),
                tenancy=TenancyMode(tenancy),
                enable_per_org_quotas=per_org_quotas,
                payment_provider=PaymentProviderType(payment_provider),
                billing_model=BillingModelType(billing_model),
                enable_storybook=storybook,
            )

        console.print(f"[cyan]Creating project:[/] {name}")
        if preset:
            console.print(f"[dim]Preset: {preset}[/]")
        console.print(f"[dim]Database: {config.database.value}[/]")
        console.print("[dim]Auth: JWT + API Key[/]")
        if config.frontend != FrontendType.NONE:
            console.print(f"[dim]Frontend: {config.frontend.value}[/]")
        if config.ai_framework == AIFrameworkType.NONE:
            console.print("[dim]AI: disabled (plain SaaS)[/]")
        else:
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
    console.print("[bold cyan]Full-Stack AI Agent Template — Available Options[/]")
    console.print()

    console.print("[bold]Presets:[/]")
    console.print("  --preset production       Full production setup (Redis, Sentry, K8s, etc.)")
    console.print(
        "  --preset ai-agent         AI agent with WebSocket streaming + conversation persistence"
    )
    console.print(
        "  --preset production-saas  Full SaaS: Stripe billing + credits + teams + admin + email + Sentry + K8s"
    )
    console.print(
        "  --preset b2b-multi-tenant Workspaces + billing + credits + usage dashboard (no marketing pages)"
    )
    console.print(
        "  --preset internal-tool    Staff dashboard: Google SSO + teams + admin, no billing/marketing"
    )
    console.print(
        "  --preset embedded-chatbot Chat widget for embed in client's site (no marketing/teams/billing)"
    )
    console.print(
        "  --preset blog-saas        Content-first SaaS: marketing + blog + changelog + newsletter (minimal AI)"
    )
    console.print("  --preset consumer-app     B2C app: OAuth + marketing + billing + credits")
    console.print(
        "  --preset dev-playground   Local AI prototyping: PostgreSQL + no Docker/K8s, fast iteration"
    )
    console.print(
        "  --minimal                 Minimal project (PostgreSQL, no Docker/K8s/CI, no Redis)"
    )
    console.print()

    console.print("[bold]Database:[/]")
    console.print("  --database postgresql  PostgreSQL with asyncpg (async, default)")
    console.print("  --orm sqlalchemy       SQLAlchemy (default)")
    console.print("  --orm sqlmodel         SQLModel")
    console.print()

    console.print("[bold]Authentication (always included):[/]")
    console.print("  JWT + User Management (email/password, roles, profiles)")
    console.print("  API Key utility (X-API-Key header, available for custom use)")
    console.print("  --oauth-google                 Enable Google OAuth")
    console.print("  --session-management           Enable session management")
    console.print(
        "  --auth-mode local              Default: backend handles email/password + OAuth"
    )
    console.print(
        "  --auth-mode delegated          Trust JWTs from external IdP (Auth0/Clerk/Cognito/Keycloak)"
    )
    console.print(
        "  --shared-secret-jwt            With delegated: use HMAC shared secret instead of JWKS"
    )
    console.print(
        "  --external-user-id             With delegated: store IdP sub on Conversation rows"
    )
    console.print()

    console.print("[bold]AI Agent:[/]")
    console.print(
        "  --ai-framework none             No AI — plain SaaS (removes agents/chat/conversations)"
    )
    console.print("  --ai-framework pydantic_ai      PydanticAI (recommended)")
    console.print("  --ai-framework langchain        LangChain")
    console.print("  --ai-framework langgraph        LangGraph (ReAct agent)")
    console.print("  --ai-framework deepagents       DeepAgents (agentic coding, HITL)")
    console.print(
        "  --ai-framework pydantic_deep    PydanticDeep (deep agentic coding, Docker sandbox)"
    )
    console.print("  --llm-provider openai           OpenAI (gpt-5.5)")
    console.print("  --llm-provider anthropic        Anthropic (claude-opus-4-7)")
    console.print("  --llm-provider google           Google Gemini (gemini-2.5-flash)")
    console.print("  --llm-provider openrouter       OpenRouter (pydantic_ai only)")
    console.print(
        "  --websockets                    Enable WebSocket support (real-time chat streaming)"
    )
    console.print("  --web-search                    Enable web search tool for AI agents (Tavily)")
    console.print("  --web-fetch                     Enable web fetch/scraping tool for AI agents")
    console.print()

    console.print("[bold]Background Tasks:[/]")
    console.print("  --task-queue none      FastAPI BackgroundTasks only")
    console.print("  --task-queue celery    Celery (classic)")
    console.print("  --task-queue taskiq    Taskiq (async-native)")
    console.print("  --task-queue arq       ARQ (lightweight)")
    console.print()

    console.print("[bold]Frontend:[/]")
    console.print("  --frontend none        API only (no frontend)")
    console.print("  --frontend nextjs      Next.js 15 (App Router, TypeScript, Bun, i18n)")
    console.print(
        "  --no-i18n              Single-language English-only frontend (no locale switcher)"
    )
    console.print(
        "  --marketing-site       Generate marketing/landing pages (blog, pricing, legal)"
    )
    console.print("  --changelog            Generate changelog page")
    console.print()

    console.print("[bold]RAG (Retrieval Augmented Generation):[/]")
    console.print("  --rag                               Enable RAG")
    console.print("  --vector-store milvus|qdrant|chromadb|pgvector  Vector store backend")
    console.print("  --gdrive-rag                        Enable Google Drive ingestion")
    console.print("  --s3-rag                            Enable S3/MinIO ingestion")
    console.print("  --reranker none|cohere|cross_encoder Reranker logic")
    console.print("  --pdf-parser pymupdf|liteparse|llamaparse  PDF parser")
    console.print()

    console.print("[bold]Integrations:[/]")
    console.print("  --redis            Enable Redis")
    console.print("  --caching          Enable caching (requires --redis)")
    console.print("  --rate-limiting    Enable rate limiting")
    console.print("  --admin-panel      Enable admin panel (SQLAdmin)")
    console.print("  --admin-features users,orgs,subs,usage,events,audit,health")
    console.print("                     Select which admin panel sections to enable (default: all)")
    console.print("  --file-storage     Enable S3/MinIO file storage")
    console.print("  --webhooks         Enable webhooks support")
    console.print("  --telegram         Enable Telegram bot integration")
    console.print("  --slack            Enable Slack app integration")
    console.print()

    console.print("[bold]Authentication:[/]")
    console.print("  --allowed-email-domains example.com,acme.com")
    console.print("                     Restrict OAuth registration to specific email domains")
    console.print("  --seed-admin-email admin@example.com")
    console.print("                     Auto-promote this address to app-admin on first startup")
    console.print()

    console.print("[bold]Teams & Billing:[/]")
    console.print("  --teams            Enable multi-tenant organizations")
    console.print("  --tenancy single|multi_org|platform  Tenancy architecture (default: single)")
    console.print("  --billing          Enable billing (requires --teams)")
    console.print("  --payment-provider stripe|paddle|lemonsqueezy|polar  (default: stripe)")
    console.print("  --billing-model subscription|usage|hybrid|one_time  (default: subscription)")
    console.print("  --credits          Enable credits system (requires --billing)")
    console.print("  --per-org-quotas   Enable per-organisation usage quotas (requires --teams)")
    console.print("  --usage-dashboard  Enable usage dashboard (requires --credits)")
    console.print("  --email            Enable transactional email")
    console.print("  --email-provider resend|smtp|log  Email provider (default: log)")
    console.print("  --newsletter       Enable newsletter signup (requires --email)")
    console.print("  --newsletter-provider resend|mailchimp|convertkit  (default: resend)")
    console.print()

    console.print("[bold]Embedding & White-label:[/]")
    console.print("  --embed-allowed-origins https://app.example.com")
    console.print("                     Allow iframe embedding from these origins (CSP + CORS)")
    console.print("  --brand-from-config")
    console.print(
        "                     Load brand color/logo from env vars at runtime (white-label)"
    )
    console.print("  --storybook        Generate Storybook for frontend components")
    console.print()

    console.print("[bold]Observability:[/]")
    console.print("  --no-logfire       Disable Logfire integration (PydanticAI)")
    console.print("  --langsmith        Enable LangSmith (LangChain/LangGraph/DeepAgents)")
    console.print("  --sentry           Enable Sentry error tracking")
    console.print("  --prometheus       Enable Prometheus metrics")
    console.print()

    console.print("[bold]DevOps:[/]")
    console.print("  --no-docker                  Disable Docker files")
    console.print("  --kubernetes                 Generate Kubernetes manifests")
    console.print("  --reverse-proxy none         No reverse proxy, expose ports directly")
    console.print("  --reverse-proxy nginx        External Nginx config template (default)")
    console.print("  --reverse-proxy traefik      External Traefik labels only")
    console.print("  --ci github                  GitHub Actions (default)")
    console.print("  --ci gitlab                  GitLab CI")
    console.print("  --ci none                    No CI/CD")
    console.print()

    console.print("[bold]Scaffold:[/]")
    console.print("  --example-resource    Generate example Item CRUD scaffold")
    console.print("                        (model → repo → service → route → migration)")
    console.print("                        Requires --database postgresql")
    console.print()

    console.print("[bold]Other:[/]")
    console.print("  --python-version 3.11|3.12|3.13  Python version")
    console.print("  --no-env           Skip .env file generation")
    console.print("  --backend-port N   Backend port (default: 8000)")
    console.print("  --frontend-port N  Frontend port (default: 3000)")


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":  # pragma: no cover
    main()
