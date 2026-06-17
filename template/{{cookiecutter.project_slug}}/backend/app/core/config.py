"""Application configuration using Pydantic BaseSettings."""
{% if cookiecutter.use_database or cookiecutter.enable_redis -%}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
{% endif %}
from pathlib import Path
from typing import Literal

{% if cookiecutter.use_database or cookiecutter.enable_redis or cookiecutter.enable_rag -%}
from pydantic import computed_field, field_validator, model_validator{% if cookiecutter.use_jwt or cookiecutter.use_api_key or cookiecutter.enable_cors %}, ValidationInfo{% endif %}
{% else -%}
from pydantic import field_validator, model_validator{% if cookiecutter.use_jwt or cookiecutter.use_api_key or cookiecutter.enable_cors %}, ValidationInfo{% endif %}
{% endif -%}
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> Path | None:
    """Find .env file in current or parent directories."""
    current = Path.cwd()
    for path in [current, current.parent]:
        env_file = path / ".env"
        if env_file.exists():
            return env_file
    return None


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_ignore_empty=True,
        extra="ignore",
    )

    # === Project ===
    PROJECT_NAME: str = "{{ cookiecutter.project_name }}"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "local", "staging", "production"] = "local"
    TIMEZONE: str = "{{ cookiecutter.timezone }}"  # IANA timezone (e.g. "UTC", "Europe/Warsaw", "America/New_York")
    MODELS_CACHE_DIR: Path = Path("./models_cache")
    MEDIA_DIR: Path = Path("./media")
    MAX_UPLOAD_SIZE_MB: int = 50  # Max file upload size in MB
    # Soft per-org storage cap surfaced on /billing — not enforced yet (5 GB).
    STORAGE_SOFT_LIMIT_BYTES: int = 5 * 1024 * 1024 * 1024

{%- if cookiecutter.enable_logfire %}

    # === Logfire ===
    LOGFIRE_TOKEN: str | None = None
    LOGFIRE_SERVICE_NAME: str = "{{ cookiecutter.project_slug }}"
    LOGFIRE_ENVIRONMENT: str = "development"
{%- endif %}

{%- if cookiecutter.use_postgresql %}

    # === Database (PostgreSQL async) ===
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "{{ cookiecutter.project_slug }}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Build async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Build sync PostgreSQL connection URL (for Alembic)."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Pool configuration
    DB_POOL_SIZE: int = {{ cookiecutter.db_pool_size }}
    DB_MAX_OVERFLOW: int = {{ cookiecutter.db_max_overflow }}
    DB_POOL_TIMEOUT: int = {{ cookiecutter.db_pool_timeout }}
{%- endif %}

{%- if cookiecutter.use_mongodb %}

    # === Database (MongoDB async) ===
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_DB: str = "{{ cookiecutter.project_slug }}"
    MONGO_USER: str | None = None
    MONGO_PASSWORD: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def MONGO_URL(self) -> str:
        """Build MongoDB connection URL."""
        if self.MONGO_USER and self.MONGO_PASSWORD:
            return f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}@{self.MONGO_HOST}:{self.MONGO_PORT}"
        return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}"
{%- endif %}

{%- if cookiecutter.use_sqlite %}

    # === Database (SQLite sync) ===
    SQLITE_PATH: str = "./data/{{ cookiecutter.project_slug }}.db"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Build SQLite connection URL."""
        return f"sqlite:///{self.SQLITE_PATH}"
{%- endif %}

{%- if cookiecutter.use_jwt or (cookiecutter.enable_admin_panel and cookiecutter.admin_require_auth) or cookiecutter.enable_oauth %}

    # === Auth (SECRET_KEY for JWT/Session/Admin) ===
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """Validate SECRET_KEY is secure in production."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        # Get environment from values if available
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if v == "change-me-in-production-use-openssl-rand-hex-32" and env == "production":
            raise ValueError(
                "SECRET_KEY must be changed in production! "
                "Generate a secure key with: openssl rand -hex 32"
            )
        return v
{%- endif %}

{%- if cookiecutter.use_jwt %}

    # === JWT Settings ===
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"
{%- endif %}

    # Public URL of the frontend; used to build OAuth redirect targets and
    # Stripe checkout/portal return URLs. Always declared (not gated) because
    # the billing model_validator references it unconditionally.
    FRONTEND_URL: str = "http://localhost:{{ cookiecutter.frontend_port }}"

{%- if cookiecutter.enable_oauth_google %}

    # === OAuth2 (Google) ===
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:{{ cookiecutter.backend_port }}/api/v1/oauth/google/callback"
{%- endif %}

{%- if cookiecutter.use_delegated_auth %}

    # === Delegated auth (external token issuer) ===
{%- if cookiecutter.use_shared_secret_jwt %}
    # Shared-secret HS256 mode: client backend signs short-lived JWTs for our
    # API using a pre-shared secret. Simpler than full IdP, suitable for
    # tight client-server integrations. The secret MUST be high-entropy
    # (32+ bytes recommended).
    IDP_SHARED_SECRET: str = ""
    """HMAC shared secret used to verify HS256 JWTs from the client."""
    IDP_AUDIENCE: str = ""
    """Optional `aud` claim check. Empty = skip audience verification."""
    IDP_ISSUER: str = ""
    """Optional `iss` claim check. Empty = skip issuer verification."""
{%- else %}
    # JWKS mode: backend trusts JWTs minted by Auth0/Clerk/Cognito/Keycloak/...
    # All four below are REQUIRED in production — startup will fail without them.
    IDP_JWKS_URL: str = ""
    """Public JWKS endpoint, e.g. https://your-tenant.auth0.com/.well-known/jwks.json"""
    IDP_AUDIENCE: str = ""
    """Expected `aud` claim — the API identifier configured in your IdP."""
    IDP_ISSUER: str = ""
    """Expected `iss` claim — usually your IdP base URL with trailing slash."""
    IDP_JWKS_CACHE_TTL_SECONDS: int = 3600
    """How long to cache the JWKS response. Refresh on key rotation."""
{%- endif %}
    IDP_USER_ID_CLAIM: str = "sub"
    """JWT claim used as stable external user ID. Standard is `sub`."""
    IDP_EMAIL_CLAIM: str = "email"
    """JWT claim used to populate User.email on first sign-in."""
    IDP_NAME_CLAIM: str = "name"
    """JWT claim used to populate User.full_name on first sign-in (optional)."""
{%- endif %}
{%- if cookiecutter.enable_seed_admin %}

    # === Initial app-admin seed ===
    # Set to a registered user's email to auto-promote them to app-admin on startup.
    # Run `{{ cookiecutter.project_slug }} cmd create-app-admin <email>` for the same effect.
    FIRST_ADMIN_EMAIL: str = "{{ cookiecutter.seed_admin_email }}"
{%- endif %}

{%- if cookiecutter.enable_email_domain_allowlist %}

    # === OAuth email domain allowlist ===
    # Comma-separated list of email domains permitted to register via OAuth.
    # Empty string = allow all domains.
    ALLOWED_EMAIL_DOMAINS: str = "{{ cookiecutter.allowed_email_domains }}"
{%- endif %}

{%- if cookiecutter.enable_embed_mode %}

    # === Embed mode ===
    # Comma-separated origins allowed to embed the app in an iframe.
    # Sets Content-Security-Policy frame-ancestors and CORS allow_origins.
    EMBED_ALLOWED_ORIGINS: str = "{{ cookiecutter.embed_allowed_origins }}"
{%- endif %}

{%- if cookiecutter.enable_brand_from_config %}

    # === Runtime brand (white-label) ===
    # Override the bake-time brand colour/logo at runtime via env vars.
    BRAND_COLOR: str = "{{ cookiecutter.brand_color }}"
    BRAND_LOGO_URL: str = ""
{%- endif %}

{%- if cookiecutter.use_api_key %}

    # === Auth (API Key) ===
    API_KEY: str = "change-me-in-production"
    API_KEY_HEADER: str = "X-API-Key"

    @field_validator("API_KEY")
    @classmethod
    def validate_api_key(cls, v: str, info: ValidationInfo) -> str:
        """Validate API_KEY is set in production."""
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if v == "change-me-in-production" and env == "production":
            raise ValueError(
                "API_KEY must be changed in production! "
                "Generate a secure key with: openssl rand -hex 32"
            )
        return v
{%- endif %}

{%- if cookiecutter.enable_redis %}

    # === Redis ===
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        """Build Redis connection URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
{%- endif %}

{%- if cookiecutter.enable_rate_limiting %}

    # === Rate Limiting ===
    RATE_LIMIT_REQUESTS: int = {{ cookiecutter.rate_limit_requests }}
    RATE_LIMIT_PERIOD: int = {{ cookiecutter.rate_limit_period }}  # seconds
{%- endif %}

{%- if cookiecutter.use_celery %}

    # === Celery ===
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
{%- endif %}

{%- if cookiecutter.use_taskiq %}

    # === Taskiq ===
    TASKIQ_BROKER_URL: str = "redis://localhost:6379/1"
    TASKIQ_RESULT_BACKEND: str = "redis://localhost:6379/1"
{%- endif %}

{%- if cookiecutter.use_arq %}

    # === ARQ (Async Redis Queue) ===
    ARQ_REDIS_HOST: str = "localhost"
    ARQ_REDIS_PORT: int = 6379
    ARQ_REDIS_PASSWORD: str | None = None
    ARQ_REDIS_DB: int = 2
{%- endif %}

{%- if cookiecutter.enable_sentry %}

    # === Sentry ===
    SENTRY_DSN: str | None = None
{%- endif %}

{%- if cookiecutter.enable_prometheus %}

    # === Prometheus ===
    PROMETHEUS_METRICS_PATH: str = "/metrics"
    PROMETHEUS_INCLUDE_IN_SCHEMA: bool = False
    # When set, /metrics requires `Authorization: Bearer <token>`. Leave empty
    # to expose unauthenticated (recommended only behind a private network or
    # a reverse-proxy-level allow-list — Prometheus scrapes internally).
    PROMETHEUS_AUTH_TOKEN: str = ""
{%- endif %}

{%- if cookiecutter.enable_file_storage %}

    # === File Storage (S3/MinIO) ===
    S3_ENDPOINT: str | None = None
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "{{ cookiecutter.project_slug }}"
    S3_REGION: str = "us-east-1"
{%- endif %}


    # === AI Agent ({{ cookiecutter.ai_framework }}, {{ cookiecutter.llm_provider }}) ===
{%- if cookiecutter.use_openai %}
    OPENAI_API_KEY: str = ""
{%- endif %}
{%- if cookiecutter.use_anthropic %}
    ANTHROPIC_API_KEY: str = ""
{%- endif %}
{%- if cookiecutter.use_google %}
    GOOGLE_API_KEY: str = ""
{%- endif %}
{%- if cookiecutter.use_openrouter %}
    OPENROUTER_API_KEY: str = ""
{%- endif %}
{%- if cookiecutter.use_all_providers %}
    # Multi-provider: model can come from any installed SDK. Prefix with the
    # provider name (`openai/gpt-5.5`, `anthropic/claude-opus-4-7`,
    # `google/gemini-2.5-flash`, `openrouter/anthropic/claude-opus-4-7`)
    # so the dispatcher in agents/assistant.py routes to the right backend.
    AI_MODEL: str = "openai/gpt-5.5"
{%- elif cookiecutter.use_openai %}
    AI_MODEL: str = "gpt-5.5"
{%- elif cookiecutter.use_anthropic %}
    AI_MODEL: str = "claude-opus-4-7"
{%- elif cookiecutter.use_google %}
    AI_MODEL: str = "gemini-2.5-flash"
{%- elif cookiecutter.use_openrouter %}
    AI_MODEL: str = "anthropic/claude-opus-4-7"
{%- endif %}
    AI_TEMPERATURE: float = 0.7
    AI_THINKING_ENABLED: bool = False
    AI_THINKING_EFFORT: str = "medium"  # "low", "medium", "high"
{%- if cookiecutter.use_all_providers %}
    AI_AVAILABLE_MODELS: list[str] = [
        # OpenAI
        "openai/gpt-5.5",
        "openai/gpt-5.5-pro",
        "openai/gpt-5.4",
        "openai/gpt-5-mini",
        "openai/gpt-4.1",
        # Anthropic
        "anthropic/claude-opus-4-7",
        "anthropic/claude-sonnet-4-6",
        "anthropic/claude-haiku-4-5-20251001",
        # Google
        "google/gemini-2.5-flash",
        "google/gemini-2.5-pro",
        # OpenRouter (proxies many providers)
        "openrouter/anthropic/claude-opus-4-7",
        "openrouter/deepseek/deepseek-r1",
    ]
{%- elif cookiecutter.use_openai %}
    AI_AVAILABLE_MODELS: list[str] = [
        "gpt-5.5",
        "gpt-5.5-pro",
        "gpt-5.4",
        "gpt-5.4-pro",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-5",
        "gpt-4.1",
    ]
{%- elif cookiecutter.use_anthropic %}
    AI_AVAILABLE_MODELS: list[str] = [
        "claude-opus-4-7",
        "claude-opus-4-6",
        "claude-opus-4-5",
        "claude-opus-4-1",
        "claude-opus-4-20250514",
        "claude-sonnet-4-6",
        "claude-sonnet-4-5",
        "claude-sonnet-4-20250514",
        "claude-haiku-4-5-20251001",
        "claude-haiku-3-5-20241022",
    ]
{%- elif cookiecutter.use_google %}
    AI_AVAILABLE_MODELS: list[str] = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
    ]
{%- elif cookiecutter.use_openrouter %}
    AI_AVAILABLE_MODELS: list[str] = [
        "anthropic/claude-opus-4-7",
        "anthropic/claude-sonnet-4-6",
        "openai/gpt-5.5",
        "google/gemini-2.5-flash",
        "deepseek/deepseek-r1",
    ]
{%- endif %}
    AI_FRAMEWORK: str = "{{ cookiecutter.ai_framework }}"
    LLM_PROVIDER: str = "{{ cookiecutter.llm_provider }}"
{%- if cookiecutter.enable_langsmith %}

    # === LangSmith Observability ===
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str | None = None
    LANGCHAIN_PROJECT: str = "{{ cookiecutter.project_slug }}"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
{%- endif %}
{%- if cookiecutter.enable_web_search %}

    # === Web Search (Tavily) ===
    TAVILY_API_KEY: str = ""
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}

    # === AntV charts (advanced diagrams via mcp-server-chart sidecar) ===
    # Opt-in at runtime: the code ships, but stays off until you flip this on
    # and start the antvis-chart sidecar (docker compose --profile antv).
    ENABLE_ANTV_CHARTS: bool = False
    # MCP endpoint of the antvis-chart sidecar (streamable HTTP)
    ANTV_MCP_URL: str = "http://antvis-chart:1122/mcp"
    # Optional self-hosted GPT-Vis render backend (empty = AntV public service)
    ANTV_VIS_REQUEST_SERVER: str = ""
    # Comma-separated AntV tools to disable — defaults (set on the sidecar) drop
    # the basic charts that overlap create_chart and the China-only maps.
    ANTV_DISABLED_TOOLS: str = ""
{%- endif %}
{%- if cookiecutter.enable_code_execution %}

    ENABLE_CODE_EXECUTION: bool = False
    CODE_EXECUTION_TIMEOUT_SECS: float = 10.0
    CODE_EXECUTION_MAX_ALLOCATIONS: int = 50_000_000
{%- endif %}
{%- if cookiecutter.enable_deep_research %}

    ENABLE_DEEP_RESEARCH: bool = False
    DEEP_RESEARCH_MAX_TOKENS: int = 120_000
    DEEP_RESEARCH_COMPRESS_THRESHOLD: float = 0.8
{%- endif %}
{%- if cookiecutter.use_deepagents %}

    # === DeepAgents Configuration ===
    # Backend type: "state" (in-memory, ephemeral per WebSocket connection)
    DEEPAGENTS_BACKEND_TYPE: str = "{{ cookiecutter.sandbox_backend }}"
    # Memory file paths (comma-separated AGENTS.md paths, e.g. "/memory/AGENTS.md")
    DEEPAGENTS_MEMORY_PATHS: str | None = None
    # Skills paths (comma-separated, relative to backend dir)
    DEEPAGENTS_SKILLS_PATHS: str | None = None  # e.g. "/skills/user/,/skills/project/"
    # Enable built-in tools
    DEEPAGENTS_ENABLE_FILESYSTEM: bool = True  # ls, read_file, write_file, edit_file, glob, grep
    DEEPAGENTS_ENABLE_EXECUTE: bool = False  # shell execution (disabled by default for security)
    DEEPAGENTS_ENABLE_TODOS: bool = True  # write_todos tool
    DEEPAGENTS_ENABLE_SUBAGENTS: bool = True  # task tool for spawning subagents
    # Human-in-the-loop: tools requiring approval (comma-separated)
    # e.g. "write_file,edit_file,execute" or "all" for all tools
    DEEPAGENTS_INTERRUPT_TOOLS: str | None = None
    # Allowed decisions for interrupted tools: approve,edit,reject
    DEEPAGENTS_ALLOWED_DECISIONS: str = "approve,edit,reject"
{%- endif %}
{%- if cookiecutter.use_pydantic_deep %}

    # === PydanticDeep Configuration ===
    # Backend type: "state" (in-memory) or "daytona" (Daytona cloud workspace)
    PYDANTIC_DEEP_BACKEND_TYPE: str = "{{ cookiecutter.sandbox_backend }}"
    # Feature flags
    PYDANTIC_DEEP_INCLUDE_SUBAGENTS: bool = True   # subagent delegation
    PYDANTIC_DEEP_INCLUDE_SKILLS: bool = True       # SKILL.md discovery
    PYDANTIC_DEEP_INCLUDE_PLAN: bool = True         # planner subagent
    PYDANTIC_DEEP_INCLUDE_MEMORY: bool = True       # MEMORY.md persistence
    PYDANTIC_DEEP_INCLUDE_EXECUTE: bool = False     # shell execution (security risk — off by default)
    PYDANTIC_DEEP_WEB_SEARCH: bool = True           # built-in pydantic-ai web search
{%- endif %}

{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}

    # === Messaging Channels ===
    # Fernet encryption key for bot tokens — generate with: openssl rand -hex 32
    CHANNEL_ENCRYPTION_KEY: str = "change-me-generate-with-openssl-rand-hex-32"

    @field_validator("CHANNEL_ENCRYPTION_KEY")
    @classmethod
    def validate_channel_encryption_key(cls, v: str, info: ValidationInfo) -> str:
        """Reject the default key in production — bot tokens at rest would be
        encrypted with a public, well-known key."""
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if v == "change-me-generate-with-openssl-rand-hex-32" and env == "production":
            raise ValueError(
                "CHANNEL_ENCRYPTION_KEY must be changed in production! "
                "Generate a secure key with: openssl rand -hex 32"
            )
        return v
{%- if cookiecutter.use_telegram %}
    # Telegram: webhook base URL (e.g. https://api.yourdomain.com) — leave empty to use polling
    TELEGRAM_WEBHOOK_BASE_URL: str = ""
{%- endif %}
{%- if cookiecutter.use_slack %}
    # Slack: signing secret for verifying webhook requests (from Slack app settings)
    SLACK_SIGNING_SECRET: str = ""
    # Slack: bot token (xoxb-...) — used for sending messages via Web API
    SLACK_BOT_TOKEN: str = ""
    # Slack: app-level token (xapp-...) — used for Socket Mode (dev/polling)
    SLACK_APP_TOKEN: str = ""
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_rag %}

    # === RAG (Retrieval Augmented Generation) ===
{%- if cookiecutter.use_milvus %}
    # Vector Database (Milvus)
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_DATABASE: str = "default"
    MILVUS_TOKEN: str = "root:Milvus"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def MILVUS_URI(self) -> str:
        """Build Milvus connection URI."""
        return f"http://{self.MILVUS_HOST}:{self.MILVUS_PORT}"
{%- endif %}
{%- if cookiecutter.use_qdrant %}
    # Vector Database (Qdrant)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""
{%- endif %}
{%- if cookiecutter.use_chromadb %}
    # Vector Database (ChromaDB)
    CHROMA_HOST: str = ""  # empty = embedded/persistent mode
    CHROMA_PORT: int = 8100
    CHROMA_PERSIST_DIR: str = "./chroma_data"
{%- endif %}
{%- if cookiecutter.use_pgvector %}
    # Vector Database (pgvector) — uses existing PostgreSQL
{%- endif %}

    # Embeddings
    {%- if cookiecutter.use_openai_embeddings %}
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    {%- elif cookiecutter.use_voyage_embeddings %}
    EMBEDDING_MODEL: str = "voyage-3"
    VOYAGE_API_KEY: str = ""
    {%- elif cookiecutter.use_gemini_embeddings %}
    EMBEDDING_MODEL: str = "gemini-embedding-exp-03-07"
    {%- elif cookiecutter.use_sentence_transformers %}
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    {%- else %}
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    {%- endif %}

    # Chunking
    RAG_CHUNK_SIZE: int = 512
    RAG_CHUNK_OVERLAP: int = 50

    # Retrieval
    RAG_DEFAULT_COLLECTION: str = "documents"
    RAG_TOP_K: int = 10
    RAG_CHUNKING_STRATEGY: str = "recursive"  # recursive, markdown, or fixed
    RAG_HYBRID_SEARCH: bool = False  # Enable BM25 + vector hybrid search
    RAG_ENABLE_OCR: bool = False  # OCR fallback for scanned PDFs (requires tesseract)

    # Reranker
    {%- if cookiecutter.enable_reranker and cookiecutter.use_cohere_reranker %}
    COHERE_API_KEY: str = ""
    {%- endif %}

    {%- if cookiecutter.enable_reranker and cookiecutter.use_cross_encoder_reranker %}
    HF_TOKEN: str = ""
    CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L6-v2"
    {%- endif %}

    # Document Parser
    {%- if cookiecutter.use_all_pdf_parsers %}
    # PDF Parser runtime selection
    PDF_PARSER: str = "pymupdf"  # For RAG ingestion: pymupdf, llamaparse, liteparse
    CHAT_PDF_PARSER: str = "pymupdf"  # For chat file attachments: pymupdf, llamaparse, liteparse
    LLAMAPARSE_API_KEY: str = ""
    LLAMAPARSE_TIER: str = "agentic"  # fast, cost_effective, agentic, agentic_plus
    {%- elif cookiecutter.pdf_parser == "llamaparse" or cookiecutter.use_llamaparse %}
    LLAMAPARSE_API_KEY: str = ""
    LLAMAPARSE_TIER: str = "agentic"  # fast, cost_effective, agentic, agentic_plus
    {%- endif %}
    {%- if cookiecutter.use_liteparse or cookiecutter.use_all_pdf_parsers %}
    # LiteParse OCR — empty url uses bundled Tesseract.js;
    # point at e.g. http://easyocr:8000 or http://paddleocr:8000 for HTTP OCR.
    LITEPARSE_OCR_SERVER_URL: str = ""
    LITEPARSE_OCR_LANGUAGE: str = "en"
    LITEPARSE_TIMEOUT_SECONDS: float = 600.0
    {%- endif %}

{%- if cookiecutter.enable_rag_image_description %}
    # Image Description (LLM vision)
    RAG_ENABLE_IMAGE_DESCRIPTION: bool = True  # set to false to disable LLM image description
    RAG_IMAGE_DESCRIPTION_MODEL: str = ""  # empty = use AI_MODEL
{%- endif %}

    # Google Drive (optional, for document ingestion via service account)
    {%- if cookiecutter.enable_google_drive_ingestion %}
    GOOGLE_DRIVE_CREDENTIALS_FILE: str = "credentials/google-drive-sa.json"
    {%- endif %}

    # S3 (optional, for document ingestion from S3/MinIO)
    {%- if cookiecutter.enable_s3_ingestion %}
    S3_RAG_ENDPOINT: str | None = None
    S3_RAG_ACCESS_KEY: str = ""
    S3_RAG_SECRET_KEY: str = ""
    S3_RAG_BUCKET: str = "{{ cookiecutter.project_slug }}-rag"
    S3_RAG_REGION: str = "us-east-1"
    {%- endif %}

{%- endif %}

{%- if cookiecutter.enable_billing %}

    # === Stripe Billing ===
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_API_VERSION: str = "2025-04-30.acacia"
    STRIPE_TRIAL_DAYS_DEFAULT: int = {{ cookiecutter.billing_trial_days_default }}
    STRIPE_TRIAL_REQUIRES_PAYMENT_METHOD: bool = {{ "True" if cookiecutter.billing_trial_requires_card else "False" }}

    BILLING_DEFAULT_CURRENCY: str = "{{ cookiecutter.billing_default_currency }}"
    BILLING_SUCCESS_URL: str = ""
    BILLING_CANCEL_URL: str = ""
    BILLING_PORTAL_RETURN_URL: str = ""

    @model_validator(mode="after")
    def _set_billing_urls(self) -> "Settings":
        frontend = self.FRONTEND_URL.rstrip("/")
        if not self.BILLING_SUCCESS_URL:
            self.BILLING_SUCCESS_URL = frontend + "/billing?status=success&session_id={CHECKOUT_SESSION_ID}"
        if not self.BILLING_CANCEL_URL:
            self.BILLING_CANCEL_URL = frontend + "/pricing?status=canceled"
        if not self.BILLING_PORTAL_RETURN_URL:
            self.BILLING_PORTAL_RETURN_URL = frontend + "/billing"
        return self

{%- if cookiecutter.enable_credits_system %}
    CREDITS_PER_USD: int = {{ cookiecutter.billing_credits_per_usd }}
    CREDITS_LOW_THRESHOLD: int = {{ cookiecutter.billing_credits_low_threshold }}
    CREDITS_FREE_TIER_GRANT: int = {{ cookiecutter.billing_credits_free_tier_grant }}
{%- endif %}
{%- if cookiecutter.enable_slack_alerts %}
    SLACK_ANOMALY_WEBHOOK_URL: str = ""
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_email %}

    # === Email ===
    EMAIL_PROVIDER: str = "{{ cookiecutter.email_provider }}"
    EMAIL_FROM: str = "noreply@{{ cookiecutter.project_slug }}.com"
    EMAIL_FROM_NAME: str = "{{ cookiecutter.project_name }}"
    EMAIL_REPLY_TO: str | None = None
{%- if cookiecutter.email_provider == "resend" %}
    RESEND_API_KEY: str = ""
{%- elif cookiecutter.email_provider == "smtp" %}
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True
{%- endif %}
    LOG_PROVIDER_WRITE_TO_DISK: bool = False
{%- endif %}

{%- if cookiecutter.enable_cors %}

    # === CORS ===
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
{%- if cookiecutter.enable_embed_mode %}
        # Embed mode: populate from env or baked-in defaults
        *[o.strip() for o in "{{ cookiecutter.embed_allowed_origins }}".split(",") if o.strip()],
{%- endif %}
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: list[str], info: ValidationInfo) -> list[str]:
        """Warn if CORS_ORIGINS is too permissive in production."""
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if "*" in v and env == "production":
            raise ValueError(
                "CORS_ORIGINS cannot contain '*' in production! "
                "Specify explicit allowed origins."
            )
        return v
{%- endif %}

{%- if cookiecutter.enable_rag %}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rag(self) -> "RAGSettings":
        """Build RAG-specific settings."""
        from app.services.rag.config import RAGSettings, DocumentParser, PdfParser, EmbeddingsConfig

        {%- if cookiecutter.use_all_pdf_parsers %}
        pdf_parser = PdfParser(
            method=self.PDF_PARSER,
            api_key=self.LLAMAPARSE_API_KEY,
            tier=self.LLAMAPARSE_TIER,
            liteparse_ocr_server_url=self.LITEPARSE_OCR_SERVER_URL or None,
            liteparse_ocr_language=self.LITEPARSE_OCR_LANGUAGE,
            liteparse_timeout_seconds=self.LITEPARSE_TIMEOUT_SECONDS,
        )
        {%- elif cookiecutter.use_llamaparse %}
        pdf_parser = PdfParser(api_key=self.LLAMAPARSE_API_KEY, tier=self.LLAMAPARSE_TIER)
        {%- elif cookiecutter.use_liteparse %}
        pdf_parser = PdfParser(
            liteparse_ocr_server_url=self.LITEPARSE_OCR_SERVER_URL or None,
            liteparse_ocr_language=self.LITEPARSE_OCR_LANGUAGE,
            liteparse_timeout_seconds=self.LITEPARSE_TIMEOUT_SECONDS,
        )
        {%- else %}
        pdf_parser = PdfParser()
        {%- endif %}

        return RAGSettings(
            collection_name=self.RAG_DEFAULT_COLLECTION,
            chunk_size=self.RAG_CHUNK_SIZE,
            chunk_overlap=self.RAG_CHUNK_OVERLAP,
            chunking_strategy=self.RAG_CHUNKING_STRATEGY,
            enable_hybrid_search=self.RAG_HYBRID_SEARCH,
            enable_ocr=self.RAG_ENABLE_OCR,
            embeddings_config=EmbeddingsConfig(model=self.EMBEDDING_MODEL),
            document_parser=DocumentParser(),
            pdf_parser=pdf_parser,
{%- if cookiecutter.enable_rag_image_description %}
            enable_image_description=self.RAG_ENABLE_IMAGE_DESCRIPTION,
            image_description_model=self.RAG_IMAGE_DESCRIPTION_MODEL,
{%- endif %}
        )

{%- endif %}

{%- if cookiecutter.enable_rag %}
# Rebuild Settings to resolve RAGSettings forward reference
from app.services.rag.config import RAGSettings
Settings.model_rebuild()
{%- endif %}


settings = Settings()
