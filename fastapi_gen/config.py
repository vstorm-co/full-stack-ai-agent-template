"""Configuration models for project generation."""

from datetime import UTC, datetime
from enum import StrEnum
from importlib.metadata import version
from typing import Any

from pydantic import BaseModel, EmailStr, Field, computed_field, model_validator

GENERATOR_NAME = "fastapi-fullstack"


def get_generator_version() -> str:
    """Get the current generator version from package metadata."""
    try:
        return version(GENERATOR_NAME)
    except Exception:
        return "0.0.0"


class DatabaseType(StrEnum):
    """Supported database types."""

    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    SQLITE = "sqlite"
    NONE = "none"


class BackgroundTaskType(StrEnum):
    """Supported background task systems."""

    NONE = "none"
    CELERY = "celery"
    TASKIQ = "taskiq"
    ARQ = "arq"


class CIType(StrEnum):
    """Supported CI/CD systems."""

    GITHUB = "github"
    GITLAB = "gitlab"
    NONE = "none"


class FrontendType(StrEnum):
    """Supported frontend frameworks."""

    NONE = "none"
    NEXTJS = "nextjs"


class BrandColorType(StrEnum):
    """Brand color presets for the frontend theme."""

    BLUE = "blue"
    GREEN = "green"
    RED = "red"
    VIOLET = "violet"
    ORANGE = "orange"


class OAuthProvider(StrEnum):
    """Supported OAuth2 providers."""

    NONE = "none"
    GOOGLE = "google"


class AuthMode(StrEnum):
    """High-level authentication strategy.

    - ``local``: backend issues + validates its own JWTs via email/password +
      optional OAuth. Owns user storage including hashed passwords.
    - ``delegated``: backend trusts JWTs issued by an external IdP (Auth0,
      Clerk, Cognito, Keycloak, ...). Validates them against a public JWKS URL.
      No registration UI, no password storage, no email-based recovery flows.
      First request from an unknown user auto-provisions a row keyed by
      ``external_user_id`` (the IdP ``sub`` claim).
    """

    LOCAL = "local"
    DELEGATED = "delegated"


class AIFrameworkType(StrEnum):
    """Supported AI agent frameworks."""

    NONE = "none"  # plain SaaS — no AI/chat/agents generated
    PYDANTIC_AI = "pydantic_ai"
    LANGCHAIN = "langchain"
    LANGGRAPH = "langgraph"
    CREWAI = "crewai"
    DEEPAGENTS = "deepagents"
    PYDANTIC_DEEP = "pydantic_deep"


class LLMProviderType(StrEnum):
    """Supported LLM providers.

    `ALL` installs SDKs for every provider and lets users pick the model at
    runtime via the chat model picker — useful when you want to compare
    providers or pass model selection through to end users.
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENROUTER = "openrouter"
    ALL = "all"


class RateLimitStorageType(StrEnum):
    """Rate limiting storage backends."""

    MEMORY = "memory"
    REDIS = "redis"


class ReverseProxyType(StrEnum):
    """Reverse proxy configuration options."""

    TRAEFIK_INCLUDED = "traefik_included"  # Include Traefik service + labels
    TRAEFIK_EXTERNAL = "traefik_external"  # External Traefik, include labels only
    NGINX_INCLUDED = "nginx_included"  # Include Nginx service in docker-compose
    NGINX_EXTERNAL = "nginx_external"  # External Nginx, config template only
    NONE = "none"  # No reverse proxy, expose ports directly


class OrmType(StrEnum):
    """Supported ORM libraries for SQL databases."""

    SQLALCHEMY = "sqlalchemy"
    SQLMODEL = "sqlmodel"


class LogfireFeatures(BaseModel):
    """Logfire instrumentation features."""

    fastapi: bool = True
    database: bool = True
    redis: bool = False
    celery: bool = False
    httpx: bool = False


class EmbeddingProviderType(StrEnum):
    """Define the embedding provider for LLM models."""

    OPENAI = "openai"  # text-embedding-3-small
    VOYAGE = "voyage"  # voyage-3 (Anthropic users)
    GEMINI = "gemini"  # gemini-embedding-2-preview (multimodal)
    SENTENCE_TRANSFORMERS = "sentence_transformers"  # all-MiniLM-L6-v2 (local, for OpenRouter)


class RerankerType(StrEnum):
    """Define the reranker type and provider for reranking purposes."""

    NONE = "none"
    COHERE = "cohere"  # rerank-v3.5
    CROSS_ENCODER = "cross_encoder"  # ms-marco-MiniLM (local)


class DocumentParserType(StrEnum):
    """Define the document parser used to process non-PDF documents.
    Note: PDF parsing is now controlled separately via PdfParserType.
    This setting applies to TXT, MD, and DOCX files only.
    """

    PYTHON_NATIVE = "python_native"  # python-docx for DOCX


class PdfParserType(StrEnum):
    """Define the PDF parser used to process PDF documents.
    PYMUPDF: Local PDF extraction using PyMuPDF. Supports text, tables
             (→ markdown), images, headers/footers detection, OCR fallback.
    LLAMAPARSE: AI-powered cloud extraction. Handles 130+ formats,
                complex layouts, and scanned documents. Requires API key.
    LITEPARSE: Fast local AI-native parsing from LlamaIndex. Layout-aware text
               extraction, built-in OCR via Tesseract.js. Requires Node.js.
    """

    PYMUPDF = "pymupdf"  # Local PDF extraction (default)
    LLAMAPARSE = "llamaparse"  # LlamaParse cloud API
    LITEPARSE = "liteparse"  # LiteParse local AI-native
    ALL = "all"  # All parsers installed, runtime selection via PDF_PARSER env var


class VectorStoreType(StrEnum):
    """Define a Vector Store type."""

    MILVUS = "milvus"
    QDRANT = "qdrant"
    CHROMADB = "chromadb"
    PGVECTOR = "pgvector"


class EmailProviderType(StrEnum):
    """Supported transactional email providers."""

    RESEND = "resend"
    SMTP = "smtp"
    LOG = "log"  # Prints to console — useful for development


class NewsletterProviderType(StrEnum):
    """Dedicated newsletter/audience providers (separate from transactional email)."""

    RESEND = "resend"  # Resend Audiences API
    MAILCHIMP = "mailchimp"
    CONVERTKIT = "convertkit"


class TenancyMode(StrEnum):
    """Tenancy architecture for multi-tenancy scenarios."""

    SINGLE = "single"  # Single workspace / single tenant
    MULTI_ORG = "multi_org"  # Multi-tenant organisations (requires --teams)
    PLATFORM = "platform"  # Each org owns multiple sub-projects


class PaymentProviderType(StrEnum):
    """Supported payment processors (Stripe is the only fully implemented one)."""

    STRIPE = "stripe"
    PADDLE = "paddle"
    LEMONSQUEEZY = "lemonsqueezy"
    POLAR = "polar"


class BillingModelType(StrEnum):
    """High-level billing model for the generated project."""

    SUBSCRIPTION = "subscription"  # Recurring plans (current default)
    USAGE = "usage"  # Pure pay-as-you-go credits
    HYBRID = "hybrid"  # Subscription base + overage credits
    ONE_TIME = "one_time"  # Single purchase / lifetime deal


class RAGFeatures(BaseModel):
    """RAG features."""

    enable_rag: bool = False
    enable_google_drive_ingestion: bool = False
    enable_s3_ingestion: bool = False
    reranker_type: RerankerType = RerankerType.NONE
    enable_image_description: bool = False
    # pdf_parser is stored here since it's only used when RAG is enabled
    pdf_parser: PdfParserType = PdfParserType.PYMUPDF
    vector_store: VectorStoreType = VectorStoreType.MILVUS


class ProjectConfig(BaseModel):
    """Full project configuration.

    Interactive prompt order: basic info → database → orm → oauth → session →
    background tasks → logfire → integrations → dev tools → reverse proxy →
    frontend → python version → ports → AI framework → LLM provider → RAG →
    langsmith → rate limit config → brand color
    """

    # Basic info
    project_name: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    project_description: str = "A FastAPI project"

    author_name: str = "Your Name"
    author_email: EmailStr = "your@email.com"
    timezone: str = "UTC"

    # Database
    database: DatabaseType = DatabaseType.POSTGRESQL
    orm_type: OrmType = OrmType.SQLALCHEMY
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30

    # RAG
    rag_features: RAGFeatures = Field(default_factory=RAGFeatures)

    # Authentication (always JWT + API Key)
    oauth_provider: OAuthProvider = OAuthProvider.NONE
    auth_mode: AuthMode = AuthMode.LOCAL
    # Comma-separated email domains allowed to register via OAuth (e.g. "example.com,acme.com").
    # Empty string = allow all domains.
    allowed_email_domains: str = ""
    # Email address to auto-promote to app-admin on first seed/startup.
    seed_admin_email: str = ""
    # When auth_mode=delegated: use a shared HMAC secret instead of fetching
    # public keys from a JWKS URL. Simpler integration when client backend
    # signs short-lived tokens for our backend with a known secret. Default
    # (False) uses RSA/ES via JWKS — the IdP-friendly path.
    delegated_auth_use_shared_secret: bool = False
    # When auth_mode=delegated: denormalize the IdP `sub` claim onto
    # Conversation rows so client APIs can fetch conversations by THEIR
    # user identifier without leaking internal UUIDs.
    enable_external_user_id_in_conversations: bool = False
    enable_session_management: bool = False

    # Observability
    enable_logfire: bool = True
    logfire_features: LogfireFeatures = Field(default_factory=LogfireFeatures)

    # Background tasks
    background_tasks: BackgroundTaskType = BackgroundTaskType.CELERY

    # Optional integrations
    enable_redis: bool = False
    enable_caching: bool = False
    enable_rate_limiting: bool = False
    rate_limit_requests: int = 100
    rate_limit_period: int = 60
    rate_limit_storage: RateLimitStorageType = RateLimitStorageType.MEMORY
    enable_pagination: bool = True
    enable_sentry: bool = False
    enable_prometheus: bool = False
    enable_admin_panel: bool = False
    enable_websockets: bool = False
    enable_file_storage: bool = False
    ai_framework: AIFrameworkType = AIFrameworkType.PYDANTIC_AI
    llm_provider: LLMProviderType = LLMProviderType.OPENAI
    sandbox_backend: str = "state"  # "state" or "daytona" (for DeepAgents/PydanticDeep)
    enable_webhooks: bool = False
    enable_langsmith: bool = False
    enable_web_search: bool = False
    enable_web_fetch: bool = False
    enable_charts: bool = False
    enable_antv_charts: bool = False
    enable_code_execution: bool = False
    enable_skills: bool = False
    enable_deep_research: bool = False
    use_telegram: bool = False
    use_slack: bool = False
    enable_cors: bool = True
    # Comma-separated embed origins for iframe CORS + CSP frame-ancestors.
    # Empty string keeps the default "frame-ancestors 'none'".
    embed_allowed_origins: str = ""
    # Load brand colour/logo from BRAND_COLOR / BRAND_LOGO_URL env vars at runtime
    # instead of baking them in at generation time.
    enable_brand_from_config: bool = False

    # Dev tools
    enable_pytest: bool = True
    enable_precommit: bool = True
    enable_makefile: bool = True
    enable_docker: bool = True
    reverse_proxy: ReverseProxyType = ReverseProxyType.NGINX_EXTERNAL
    ci_type: CIType = CIType.GITHUB
    enable_kubernetes: bool = False
    generate_env: bool = True

    # Python version
    python_version: str = "3.12"

    # Frontend
    frontend: FrontendType = FrontendType.NONE
    frontend_port: int = 3000
    brand_color: BrandColorType = BrandColorType.BLUE

    # Backend
    backend_port: int = 8000

    # Teams & Billing
    enable_teams: bool = False
    enable_billing: bool = False
    enable_credits_system: bool = False
    enable_usage_anomaly_detection: bool = False
    enable_usage_dashboard: bool = False
    enable_slack_alerts: bool = False
    billing_default_currency: str = "usd"
    billing_trial_days_default: int = 14
    billing_trial_requires_card: bool = True
    billing_credits_per_usd: int = 1000
    billing_credits_low_threshold: int = 100
    billing_credits_free_tier_grant: int = 500
    enable_per_org_quotas: bool = False
    payment_provider: PaymentProviderType = PaymentProviderType.STRIPE
    billing_model: BillingModelType = BillingModelType.SUBSCRIPTION
    # Tenancy architecture (single = default one-workspace app)
    tenancy: TenancyMode = TenancyMode.SINGLE

    # Email
    enable_email: bool = False
    email_provider: EmailProviderType = EmailProviderType.LOG
    enable_newsletter_signup: bool = False
    newsletter_provider: NewsletterProviderType = NewsletterProviderType.RESEND

    # Admin features (visible in frontend admin panel)
    enable_admin_features_users: bool = True
    enable_admin_features_organizations: bool = True
    enable_admin_features_subscriptions: bool = True
    enable_admin_features_usage: bool = True
    enable_admin_features_stripe_events: bool = True
    enable_admin_features_audit_log: bool = True
    enable_admin_features_system_health: bool = True

    # Marketing / Frontend pages
    enable_marketing_site: bool = False
    enable_i18n: bool = True
    include_example_crud: bool = False
    enable_changelog: bool = False
    enable_testimonials: bool = False
    enable_comparison_pages: bool = False
    enable_affiliate_program: bool = False
    enable_status_badge: bool = False
    enable_storybook: bool = False

    @computed_field
    @property
    def project_slug(self) -> str:
        """Return project slug (underscores instead of hyphens)."""
        return self.project_name.replace("-", "_")

    @computed_field
    @property
    def use_ai(self) -> bool:
        """True when an AI framework is selected (i.e. ai_framework != none)."""
        return self.ai_framework != AIFrameworkType.NONE

    @computed_field
    @property
    def use_sqlalchemy(self) -> bool:
        """Check if SQLAlchemy ORM is selected."""
        return self.orm_type == OrmType.SQLALCHEMY

    @computed_field
    @property
    def use_sqlmodel(self) -> bool:
        """Check if SQLModel ORM is selected."""
        return self.orm_type == OrmType.SQLMODEL

    @model_validator(mode="after")
    def validate_option_combinations(self) -> "ProjectConfig":
        """Validate that option combinations are valid.

        Raises ValueError for invalid combinations:
        - Admin panel requires a database (PostgreSQL or SQLite)
        - Admin panel (SQLAdmin) does not support MongoDB
        - Caching requires Redis to be enabled
        - Session management requires a database
        - Conversation persistence requires a database
        - SQLModel requires a SQL database (PostgreSQL or SQLite)
        """
        if self.database == DatabaseType.NONE:
            raise ValueError("A database is required (JWT auth needs user storage)")
        if self.enable_admin_panel and self.database == DatabaseType.MONGODB:
            raise ValueError("Admin panel (SQLAdmin) requires PostgreSQL or SQLite")
        if self.orm_type == OrmType.SQLMODEL and self.database not in (
            DatabaseType.POSTGRESQL,
            DatabaseType.SQLITE,
        ):
            raise ValueError("SQLModel requires PostgreSQL or SQLite database")
        if self.enable_caching and not self.enable_redis:
            raise ValueError("Caching requires Redis to be enabled")
        if (
            self.ai_framework != AIFrameworkType.NONE
            and self.llm_provider == LLMProviderType.OPENROUTER
            and self.ai_framework
            not in (
                AIFrameworkType.PYDANTIC_AI,
                AIFrameworkType.PYDANTIC_DEEP,
            )
        ):
            raise ValueError(
                f"OpenRouter is only supported with PydanticAI or PydanticDeep, "
                f"not {self.ai_framework.value}"
            )
        if (
            self.enable_rate_limiting
            and self.rate_limit_storage == RateLimitStorageType.REDIS
            and not self.enable_redis
        ):
            raise ValueError("Rate limiting with Redis storage requires Redis to be enabled")

        # pgvector requires PostgreSQL
        if (
            self.rag_features.enable_rag
            and self.rag_features.vector_store == VectorStoreType.PGVECTOR
            and self.database != DatabaseType.POSTGRESQL
        ):
            raise ValueError("pgvector requires PostgreSQL database")

        # LangSmith requires LangChain-ecosystem framework
        if self.enable_langsmith and self.ai_framework not in (
            AIFrameworkType.LANGCHAIN,
            AIFrameworkType.LANGGRAPH,
            AIFrameworkType.DEEPAGENTS,
        ):
            raise ValueError(
                "LangSmith requires LangChain, LangGraph, or DeepAgents framework. "
                "PydanticDeep uses Logfire for observability."
            )

        if self.enable_deep_research and self.ai_framework != AIFrameworkType.PYDANTIC_AI:
            raise ValueError(
                "Deep research requires the PydanticAI framework. "
                "Quick fix: set --ai-framework pydantic_ai, or drop --deep-research."
            )

        # CrewAI 1.13.x pins opentelemetry-sdk<1.35 which conflicts with
        # logfire>=4.30 (needs opentelemetry-sdk>=1.39). Disable logfire when
        # using CrewAI to keep dependencies resolvable.
        if self.ai_framework == AIFrameworkType.CREWAI and self.enable_logfire:
            raise ValueError(
                "CrewAI is incompatible with Logfire — CrewAI pins an older "
                "opentelemetry-sdk that conflicts with current logfire. "
                "Disable Logfire (enable_logfire=False) when using CrewAI."
            )

        # --no-ai: RAG and websockets require an AI framework
        if not self.use_ai and self.rag_features.enable_rag:
            raise ValueError(
                "--rag requires an AI framework. "
                "Quick fix: set --ai-framework pydantic_ai (or any other), or drop --rag."
            )
        if not self.use_ai and self.enable_langsmith:
            raise ValueError("--langsmith requires an AI framework. Quick fix: drop --langsmith.")
        if not self.use_ai and (self.use_slack or self.use_telegram):
            raise ValueError(
                "Slack/Telegram channels require an AI framework — a channel bot exists "
                "only to relay messages to the agent (it calls AgentInvocationService). "
                "Quick fix: set --ai-framework pydantic_ai (or any other), or drop "
                "--slack/--telegram."
            )

        # Tenancy: multi_org / platform imply teams
        if self.tenancy != TenancyMode.SINGLE and not self.enable_teams:
            raise ValueError(
                f"--tenancy={self.tenancy.value} requires --teams "
                "(multi-org and platform tenancy are built on the organisations feature)."
            )

        # per_org_quotas requires teams
        if self.enable_per_org_quotas and not self.enable_teams:
            raise ValueError(
                "--per-org-quotas requires --teams (quotas are scoped to organisations)."
            )

        # Admin panel requires SQLAlchemy (SQLAdmin doesn't fully support SQLModel)
        if self.enable_admin_panel and self.orm_type == OrmType.SQLMODEL:
            raise ValueError(
                "Admin panel (SQLAdmin) requires SQLAlchemy ORM. "
                "SQLModel is not fully supported. Use orm_type=sqlalchemy or disable admin panel."
            )

        # Background task queues require Redis
        if (
            self.background_tasks
            in (
                BackgroundTaskType.CELERY,
                BackgroundTaskType.TASKIQ,
                BackgroundTaskType.ARQ,
            )
            and not self.enable_redis
        ):
            raise ValueError(
                f"{self.background_tasks.value.title()} requires Redis to be enabled. "
                "All task queue systems use Redis as broker/backend."
            )

        # Logfire feature-specific validations (only when logfire is enabled)
        if self.enable_logfire:
            if self.logfire_features.redis and not self.enable_redis:
                raise ValueError("Logfire Redis instrumentation requires Redis to be enabled")

            if self.logfire_features.celery and self.background_tasks != BackgroundTaskType.CELERY:
                raise ValueError(
                    "Logfire Celery instrumentation requires Celery as background task system"
                )

        # Teams & Billing dependency chain
        if self.enable_billing and not self.enable_teams:
            raise ValueError("Billing requires Teams to be enabled (enable_teams=true)")
        if self.enable_credits_system and not self.enable_billing:
            raise ValueError("Credits system requires Billing to be enabled (enable_billing=true)")
        if self.enable_usage_anomaly_detection and not self.enable_credits_system:
            raise ValueError(
                "Usage anomaly detection requires Credits system to be enabled (enable_credits_system=true)"
            )
        if self.enable_usage_dashboard and not self.enable_credits_system:
            raise ValueError(
                "Usage dashboard requires Credits system to be enabled (enable_credits_system=true)"
            )
        if self.enable_slack_alerts and not self.enable_usage_anomaly_detection:
            raise ValueError(
                "Slack alerts require Usage anomaly detection to be enabled (enable_usage_anomaly_detection=true)"
            )

        # Email dependency chain
        if self.enable_newsletter_signup and not self.enable_email:
            raise ValueError("Newsletter signup requires Email to be enabled (enable_email=true)")

        # Teams requires SQL database with JWT
        if self.enable_teams and self.database not in (
            DatabaseType.POSTGRESQL,
            DatabaseType.SQLITE,
            DatabaseType.MONGODB,
        ):
            raise ValueError("Teams requires a database")

        # RAG-oriented checks

        if (
            self.rag_features.enable_rag
            and self.rag_features.vector_store in (VectorStoreType.MILVUS, VectorStoreType.QDRANT)
            and not self.enable_docker
        ):
            raise ValueError(
                f"RAG with {self.rag_features.vector_store.value} requires Docker to be enabled."
            )

        # RAG sub-features require RAG itself
        if self.rag_features.enable_google_drive_ingestion and not self.rag_features.enable_rag:
            raise ValueError(
                "Google Drive ingestion requires RAG to be enabled. "
                "Quick fix: add --rag, or remove --gdrive-rag."
            )
        if self.rag_features.enable_s3_ingestion and not self.rag_features.enable_rag:
            raise ValueError(
                "S3/MinIO ingestion requires RAG to be enabled. "
                "Quick fix: add --rag, or remove --s3-rag."
            )
        if (
            self.rag_features.reranker_type != RerankerType.NONE
            and not self.rag_features.enable_rag
        ):
            raise ValueError(
                "Reranker requires RAG to be enabled. Quick fix: add --rag, or set --reranker none."
            )
        if self.rag_features.enable_image_description and not self.rag_features.enable_rag:
            raise ValueError(
                "RAG image description requires RAG to be enabled. Quick fix: add --rag."
            )

        # Frontend-dependent surfaces
        if self.enable_marketing_site and self.frontend == FrontendType.NONE:
            raise ValueError(
                "Marketing site requires a frontend (landing/blog/legal pages need a UI). "
                "Quick fix: add --frontend nextjs, or drop --marketing-site."
            )
        if self.oauth_provider != OAuthProvider.NONE and self.frontend == FrontendType.NONE:
            raise ValueError(
                "OAuth requires a frontend for the callback page. "
                "Quick fix: add --frontend nextjs, or set --oauth-provider none."
            )
        if self.enable_brand_from_config and self.frontend == FrontendType.NONE:
            raise ValueError(
                "--brand-from-config requires a frontend (the BrandOverride component lives in Next.js). "
                "Quick fix: add --frontend nextjs, or drop --brand-from-config."
            )

        # Kubernetes implies Docker
        if self.enable_kubernetes and not self.enable_docker:
            raise ValueError(
                "Kubernetes manifests reference the Docker image — Docker must be enabled. "
                "Quick fix: drop --no-docker, or remove --kubernetes."
            )

        # Delegated auth supersedes local-auth options. Loud-fail any combo
        # that's a footgun rather than silently dropping user choices.
        if self.auth_mode == AuthMode.DELEGATED:
            if self.oauth_provider != OAuthProvider.NONE:
                raise ValueError(
                    "--auth-mode=delegated handles OAuth via the external IdP. "
                    "Quick fix: drop --oauth-google (your IdP will handle social login)."
                )
            if self.enable_session_management:
                raise ValueError(
                    "--auth-mode=delegated invalidates by IdP token expiry; the local "
                    "session table is unused. Quick fix: drop --session-management."
                )

        # Example CRUD scaffold needs the SQL stack — Items belong to a User
        if self.include_example_crud and self.database not in (
            DatabaseType.POSTGRESQL,
            DatabaseType.SQLITE,
        ):
            raise ValueError(
                "--example-resource scaffold supports PostgreSQL/SQLite only today. "
                "Quick fix: switch to --database postgresql or drop --example-resource."
            )

        # Sub-flags that only make sense in delegated mode
        if self.delegated_auth_use_shared_secret and self.auth_mode != AuthMode.DELEGATED:
            raise ValueError(
                "--shared-secret-jwt only applies when --auth-mode=delegated. "
                "Quick fix: add --auth-mode delegated, or drop --shared-secret-jwt."
            )
        if self.enable_external_user_id_in_conversations and self.auth_mode != AuthMode.DELEGATED:
            raise ValueError(
                "--external-user-id is meaningful only with --auth-mode=delegated "
                "(it denormalizes the IdP `sub` claim onto conversations). "
                "Quick fix: add --auth-mode delegated, or drop --external-user-id."
            )

        return self

    def to_cookiecutter_context(self) -> dict[str, Any]:
        """Convert config to cookiecutter context."""
        return {
            # Generator metadata
            "generator_name": GENERATOR_NAME,
            "generator_version": get_generator_version(),
            "generated_at": datetime.now(UTC).isoformat(),
            # Project info
            "project_name": self.project_name,
            "project_slug": self.project_slug,
            "project_description": self.project_description,
            "author_name": self.author_name,
            "author_email": self.author_email,
            "timezone": self.timezone,
            # Database
            "database": self.database.value,
            "use_postgresql": self.database == DatabaseType.POSTGRESQL,
            "use_mongodb": self.database == DatabaseType.MONGODB,
            "use_sqlite": self.database == DatabaseType.SQLITE,
            "use_database": self.database != DatabaseType.NONE,
            "db_pool_size": self.db_pool_size,
            "db_max_overflow": self.db_max_overflow,
            "db_pool_timeout": self.db_pool_timeout,
            # ORM
            "orm_type": self.orm_type.value,
            "use_sqlalchemy": self.use_sqlalchemy,
            "use_sqlmodel": self.use_sqlmodel,
            # Auth (always JWT + API Key)
            "auth": "both",
            "use_jwt": True,
            "use_api_key": True,
            "use_auth": True,
            # OAuth + Auth restrictions
            "oauth_provider": self.oauth_provider.value,
            "enable_oauth": self.oauth_provider != OAuthProvider.NONE,
            "enable_oauth_google": self.oauth_provider == OAuthProvider.GOOGLE,
            "allowed_email_domains": self.allowed_email_domains,
            "enable_email_domain_allowlist": bool(self.allowed_email_domains.strip()),
            # Admin seeding
            "seed_admin_email": self.seed_admin_email,
            "enable_seed_admin": bool(self.seed_admin_email.strip()),
            # Auth mode (local password+OAuth vs delegated/IdP)
            "auth_mode": self.auth_mode.value,
            "use_local_auth": self.auth_mode == AuthMode.LOCAL,
            "use_delegated_auth": self.auth_mode == AuthMode.DELEGATED,
            "use_shared_secret_jwt": (
                self.auth_mode == AuthMode.DELEGATED and self.delegated_auth_use_shared_secret
            ),
            "use_jwks_idp": (
                self.auth_mode == AuthMode.DELEGATED and not self.delegated_auth_use_shared_secret
            ),
            "use_external_user_id_in_conversations": (
                self.auth_mode == AuthMode.DELEGATED
                and self.enable_external_user_id_in_conversations
            ),
            # Session Management
            "enable_session_management": self.enable_session_management,
            # Logfire
            "enable_logfire": self.enable_logfire,
            "logfire_fastapi": self.logfire_features.fastapi,
            "logfire_database": self.logfire_features.database,
            "logfire_redis": self.logfire_features.redis,
            "logfire_celery": self.logfire_features.celery,
            "logfire_httpx": self.logfire_features.httpx,
            # Background tasks
            "background_tasks": self.background_tasks.value,
            "use_celery": self.background_tasks == BackgroundTaskType.CELERY,
            "use_taskiq": self.background_tasks == BackgroundTaskType.TASKIQ,
            "use_arq": self.background_tasks == BackgroundTaskType.ARQ,
            # Integrations
            "enable_redis": self.enable_redis,
            "enable_caching": self.enable_caching,
            "enable_rate_limiting": self.enable_rate_limiting,
            "rate_limit_requests": self.rate_limit_requests,
            "rate_limit_period": self.rate_limit_period,
            "rate_limit_storage": self.rate_limit_storage.value,
            "rate_limit_storage_memory": self.rate_limit_storage == RateLimitStorageType.MEMORY,
            "rate_limit_storage_redis": self.rate_limit_storage == RateLimitStorageType.REDIS,
            "enable_pagination": self.enable_pagination,
            "enable_sentry": self.enable_sentry,
            "enable_prometheus": self.enable_prometheus,
            "enable_admin_panel": self.enable_admin_panel,
            # Legacy fixed values (required by templates, not user-configurable)
            "admin_environments": "dev_staging",
            "admin_env_all": False,
            "admin_env_dev_only": False,
            "admin_env_dev_staging": True,
            "admin_env_disabled": False,
            "admin_require_auth": True,
            "enable_websockets": self.enable_websockets,
            "enable_file_storage": self.enable_file_storage,
            "ai_framework": self.ai_framework.value,
            "use_pydantic_ai": self.ai_framework == AIFrameworkType.PYDANTIC_AI,
            "use_langchain": self.ai_framework == AIFrameworkType.LANGCHAIN,
            "use_langgraph": self.ai_framework == AIFrameworkType.LANGGRAPH,
            "use_crewai": self.ai_framework == AIFrameworkType.CREWAI,
            "use_deepagents": self.ai_framework == AIFrameworkType.DEEPAGENTS,
            "use_pydantic_deep": self.ai_framework == AIFrameworkType.PYDANTIC_DEEP,
            "sandbox_backend": self.sandbox_backend,
            "llm_provider": self.llm_provider.value,
            # ALL turns on every provider so users can pick the model at runtime.
            "use_openai": self.llm_provider in (LLMProviderType.OPENAI, LLMProviderType.ALL),
            "use_anthropic": self.llm_provider in (LLMProviderType.ANTHROPIC, LLMProviderType.ALL),
            "use_google": self.llm_provider in (LLMProviderType.GOOGLE, LLMProviderType.ALL),
            "use_openrouter": self.llm_provider
            in (LLMProviderType.OPENROUTER, LLMProviderType.ALL),
            "use_all_providers": self.llm_provider == LLMProviderType.ALL,
            # Legacy fixed values (always enabled, not user-configurable)
            # AI
            "use_ai": self.use_ai,
            "enable_conversation_persistence": self.use_ai,
            "enable_langsmith": self.enable_langsmith,
            "enable_web_search": self.enable_web_search,
            "enable_web_fetch": self.enable_web_fetch,
            # PydanticAI/PydanticDeep have a model-native WebFetch capability;
            # the other frameworks don't, so they get a portable fetch_url tool.
            "web_fetch_tool": self.enable_web_fetch
            and self.ai_framework
            in (
                AIFrameworkType.LANGCHAIN,
                AIFrameworkType.LANGGRAPH,
                AIFrameworkType.CREWAI,
                AIFrameworkType.DEEPAGENTS,
            ),
            "enable_charts": self.enable_charts,
            "charts_channel_png": self.enable_charts and (self.use_slack or self.use_telegram),
            "enable_antv_charts": self.enable_antv_charts,
            "enable_code_execution": self.enable_code_execution,
            "enable_skills": self.enable_skills,
            "enable_deep_research": self.enable_deep_research,
            "enable_webhooks": self.enable_webhooks,
            # Legacy fixed values (WebSocket always uses JWT)
            "websocket_auth": "jwt",
            "websocket_auth_jwt": True,
            "websocket_auth_api_key": False,
            "websocket_auth_none": False,
            "enable_cors": self.enable_cors,
            # Embed / brand
            "embed_allowed_origins": self.embed_allowed_origins,
            "enable_embed_mode": bool(self.embed_allowed_origins.strip()),
            "enable_brand_from_config": self.enable_brand_from_config,
            # Frontend features
            "enable_i18n": self.enable_i18n,
            # Example CRUD scaffold (Items resource — pattern reference for new domains)
            "include_example_crud": self.include_example_crud,
            # Dev tools
            "enable_pytest": self.enable_pytest,
            "enable_precommit": self.enable_precommit,
            "enable_makefile": self.enable_makefile,
            "enable_docker": self.enable_docker,
            # Reverse proxy
            "reverse_proxy": self.reverse_proxy.value,
            "include_traefik_service": self.reverse_proxy == ReverseProxyType.TRAEFIK_INCLUDED,
            "include_traefik_labels": self.reverse_proxy
            in (ReverseProxyType.TRAEFIK_INCLUDED, ReverseProxyType.TRAEFIK_EXTERNAL),
            "use_traefik": self.reverse_proxy
            in (ReverseProxyType.TRAEFIK_INCLUDED, ReverseProxyType.TRAEFIK_EXTERNAL),
            "include_nginx_service": self.reverse_proxy == ReverseProxyType.NGINX_INCLUDED,
            "include_nginx_config": self.reverse_proxy
            in (ReverseProxyType.NGINX_INCLUDED, ReverseProxyType.NGINX_EXTERNAL),
            "use_nginx": self.reverse_proxy
            in (ReverseProxyType.NGINX_INCLUDED, ReverseProxyType.NGINX_EXTERNAL),
            "ci_type": self.ci_type.value,
            "use_github_actions": self.ci_type == CIType.GITHUB,
            "use_gitlab_ci": self.ci_type == CIType.GITLAB,
            "enable_kubernetes": self.enable_kubernetes,
            "generate_env": self.generate_env,
            # Python version
            "python_version": self.python_version,
            # Frontend
            "frontend": self.frontend.value,
            "use_frontend": self.frontend != FrontendType.NONE,
            "use_nextjs": self.frontend == FrontendType.NEXTJS,
            "frontend_port": self.frontend_port,
            "brand_color": self.brand_color.value,
            "brand_color_hue": {
                BrandColorType.BLUE: "250",
                BrandColorType.GREEN: "155",
                BrandColorType.RED: "25",
                BrandColorType.VIOLET: "295",
                BrandColorType.ORANGE: "55",
            }[self.brand_color],
            # Backend
            "backend_port": self.backend_port,
            # RAG
            "enable_rag": self.rag_features.enable_rag,
            "vector_store": self.rag_features.vector_store.value
            if self.rag_features.enable_rag
            else "milvus",
            "use_milvus": self.rag_features.enable_rag
            and self.rag_features.vector_store == VectorStoreType.MILVUS,
            "use_qdrant": self.rag_features.enable_rag
            and self.rag_features.vector_store == VectorStoreType.QDRANT,
            "use_chromadb": self.rag_features.enable_rag
            and self.rag_features.vector_store == VectorStoreType.CHROMADB,
            "use_pgvector": self.rag_features.enable_rag
            and self.rag_features.vector_store == VectorStoreType.PGVECTOR,
            # Embedding provider is auto-derived from LLM provider
            "embedding_provider": (
                EmbeddingProviderType.VOYAGE.value
                if self.llm_provider == LLMProviderType.ANTHROPIC
                else EmbeddingProviderType.GEMINI.value
                if self.llm_provider == LLMProviderType.GOOGLE
                else EmbeddingProviderType.SENTENCE_TRANSFORMERS.value
                if self.llm_provider == LLMProviderType.OPENROUTER
                else EmbeddingProviderType.OPENAI.value
            ),
            "use_openai_embeddings": self.rag_features.enable_rag
            and self.llm_provider
            not in (
                LLMProviderType.ANTHROPIC,
                LLMProviderType.GOOGLE,
                LLMProviderType.OPENROUTER,
            ),
            "use_voyage_embeddings": self.rag_features.enable_rag
            and self.llm_provider == LLMProviderType.ANTHROPIC,
            "use_gemini_embeddings": self.rag_features.enable_rag
            and self.llm_provider == LLMProviderType.GOOGLE,
            "use_sentence_transformers": self.rag_features.enable_rag
            and self.llm_provider == LLMProviderType.OPENROUTER,
            "enable_reranker": self.rag_features.enable_rag
            and self.rag_features.reranker_type != RerankerType.NONE,
            "use_cohere_reranker": self.rag_features.enable_rag
            and self.rag_features.reranker_type == RerankerType.COHERE,
            "use_cross_encoder_reranker": self.rag_features.enable_rag
            and self.rag_features.reranker_type == RerankerType.CROSS_ENCODER,
            "pdf_parser": self.rag_features.pdf_parser.value
            if self.rag_features.enable_rag
            else "pymupdf",
            "use_llamaparse": self.rag_features.enable_rag
            and self.rag_features.pdf_parser in (PdfParserType.LLAMAPARSE, PdfParserType.ALL),
            "use_liteparse": self.rag_features.enable_rag
            and self.rag_features.pdf_parser in (PdfParserType.LITEPARSE, PdfParserType.ALL),
            "use_pymupdf": self.rag_features.enable_rag
            and self.rag_features.pdf_parser in (PdfParserType.PYMUPDF, PdfParserType.ALL),
            "use_all_pdf_parsers": self.rag_features.enable_rag
            and self.rag_features.pdf_parser == PdfParserType.ALL,
            "use_python_parser": True,  # Always use Python parser for non-PDF
            "enable_google_drive_ingestion": self.rag_features.enable_google_drive_ingestion
            if self.rag_features.enable_rag
            else False,
            "enable_s3_ingestion": self.rag_features.enable_s3_ingestion
            if self.rag_features.enable_rag
            else False,
            "enable_rag_image_description": self.rag_features.enable_image_description
            if self.rag_features.enable_rag
            else False,
            # Messaging channels
            "use_telegram": self.use_telegram,
            "use_slack": self.use_slack,
            # Teams & Billing
            "enable_teams": self.enable_teams,
            "enable_billing": self.enable_billing,
            "enable_credits_system": self.enable_credits_system,
            "enable_usage_anomaly_detection": self.enable_usage_anomaly_detection,
            "enable_usage_dashboard": self.enable_usage_dashboard,
            "enable_slack_alerts": self.enable_slack_alerts,
            "billing_default_currency": self.billing_default_currency,
            "billing_trial_days_default": self.billing_trial_days_default,
            "billing_trial_requires_card": self.billing_trial_requires_card,
            "billing_credits_per_usd": self.billing_credits_per_usd,
            "billing_credits_low_threshold": self.billing_credits_low_threshold,
            "billing_credits_free_tier_grant": self.billing_credits_free_tier_grant,
            "enable_per_org_quotas": self.enable_per_org_quotas,
            "payment_provider": self.payment_provider.value,
            "payment_provider_stripe": self.payment_provider == PaymentProviderType.STRIPE,
            "payment_provider_paddle": self.payment_provider == PaymentProviderType.PADDLE,
            "payment_provider_lemonsqueezy": self.payment_provider
            == PaymentProviderType.LEMONSQUEEZY,
            "payment_provider_polar": self.payment_provider == PaymentProviderType.POLAR,
            "billing_model": self.billing_model.value,
            "billing_model_subscription": self.billing_model == BillingModelType.SUBSCRIPTION,
            "billing_model_usage": self.billing_model == BillingModelType.USAGE,
            "billing_model_hybrid": self.billing_model == BillingModelType.HYBRID,
            "billing_model_one_time": self.billing_model == BillingModelType.ONE_TIME,
            # Tenancy
            "tenancy": self.tenancy.value,
            "tenancy_single": self.tenancy == TenancyMode.SINGLE,
            "tenancy_multi_org": self.tenancy == TenancyMode.MULTI_ORG,
            "tenancy_platform": self.tenancy == TenancyMode.PLATFORM,
            # Email
            "enable_email": self.enable_email,
            "email_provider": self.email_provider.value,
            "enable_newsletter_signup": self.enable_newsletter_signup,
            "newsletter_provider": self.newsletter_provider.value,
            "newsletter_provider_resend": self.newsletter_provider == NewsletterProviderType.RESEND,
            "newsletter_provider_mailchimp": self.newsletter_provider
            == NewsletterProviderType.MAILCHIMP,
            "newsletter_provider_convertkit": self.newsletter_provider
            == NewsletterProviderType.CONVERTKIT,
            # Admin features
            "enable_admin_features_users": self.enable_admin_features_users,
            "enable_admin_features_organizations": self.enable_admin_features_organizations,
            "enable_admin_features_subscriptions": self.enable_admin_features_subscriptions,
            "enable_admin_features_usage": self.enable_admin_features_usage,
            "enable_admin_features_stripe_events": self.enable_admin_features_stripe_events,
            "enable_admin_features_audit_log": self.enable_admin_features_audit_log,
            "enable_admin_features_system_health": self.enable_admin_features_system_health,
            # Marketing / Frontend pages
            "enable_marketing_site": self.enable_marketing_site,
            "enable_changelog": self.enable_changelog,
            "enable_testimonials": self.enable_testimonials,
            "enable_comparison_pages": self.enable_comparison_pages,
            "enable_affiliate_program": self.enable_affiliate_program,
            "enable_status_badge": self.enable_status_badge,
            "enable_storybook": self.enable_storybook,
        }
