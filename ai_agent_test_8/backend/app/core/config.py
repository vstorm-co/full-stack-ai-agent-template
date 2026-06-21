"""Application configuration using Pydantic BaseSettings."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from pathlib import Path
from typing import Literal

from pydantic import computed_field, field_validator, model_validator, ValidationInfo
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

    PROJECT_NAME: str = "ai_agent_test_8"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    DB_ECHO: bool = (
        False  # Set DB_ECHO=true to log SQL queries (latency + log-noise drain by default)
    )
    ENVIRONMENT: Literal["development", "local", "staging", "production"] = "local"
    TIMEZONE: str = "UTC"  # IANA timezone (e.g. "UTC", "Europe/Warsaw", "America/New_York")
    MODELS_CACHE_DIR: Path = Path("./models_cache")
    MEDIA_DIR: Path = Path("./media")
    MAX_UPLOAD_SIZE_MB: int = 50  # Max file upload size in MB
    # Soft per-org storage cap surfaced on /billing — not enforced yet (5 GB).
    STORAGE_SOFT_LIMIT_BYTES: int = 5 * 1024 * 1024 * 1024

    LOGFIRE_TOKEN: str | None = None
    LOGFIRE_SERVICE_NAME: str = "ai_agent_test_8"
    LOGFIRE_ENVIRONMENT: str = "development"

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "ai_agent_test_8"

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

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """Validate SECRET_KEY is secure in production."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if v == "change-me-in-production-use-openssl-rand-hex-32" and env == "production":
            raise ValueError(
                "SECRET_KEY must be changed in production! "
                "Generate a secure key with: openssl rand -hex 32"
            )
        return v

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    # Public URL of the frontend; used to build OAuth redirect targets and
    # Stripe checkout/portal return URLs. Always declared (not gated) because
    # the billing model_validator references it unconditionally.
    FRONTEND_URL: str = "http://localhost:3000"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/oauth/google/callback"

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

    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds

    # Prefect API — set to http://prefect-server:4200/api for self-hosted,
    # or the Prefect Cloud workspace URL for cloud mode.
    PREFECT_API_URL: str = "http://localhost:4200/api"
    # Only required when PREFECT_CLOUD=true (your workspace API key)
    PREFECT_API_KEY: str | None = None
    OPENROUTER_API_KEY: str = ""
    AI_MODEL: str = "anthropic/claude-opus-4-7"
    AI_TEMPERATURE: float = 0.7
    AI_THINKING_ENABLED: bool = False
    AI_THINKING_EFFORT: str = "medium"  # "low", "medium", "high"
    AI_AVAILABLE_MODELS: list[str] = [
        "anthropic/claude-opus-4-7",
        "anthropic/claude-sonnet-4-6",
        "openai/gpt-5.5",
        "google/gemini-2.5-flash",
        "deepseek/deepseek-r1",
    ]
    AI_FRAMEWORK: str = "pydantic_ai"
    LLM_PROVIDER: str = "openrouter"

    TAVILY_API_KEY: str = ""

    CODE_EXECUTION_TIMEOUT_SECS: float = 10.0
    CODE_EXECUTION_MAX_ALLOCATIONS: int = 50_000_000

    ENABLE_DEEP_RESEARCH: bool = False
    DEEP_RESEARCH_MAX_TOKENS: int = 120_000
    DEEP_RESEARCH_COMPRESS_THRESHOLD: float = 0.8

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

    # Telegram: webhook base URL (e.g. https://api.yourdomain.com) — leave empty to use polling
    TELEGRAM_WEBHOOK_BASE_URL: str = ""
    # Slack: signing secret for verifying webhook requests (from Slack app settings)
    SLACK_SIGNING_SECRET: str = ""
    # Slack: bot token (xoxb-...) — used for sending messages via Web API
    SLACK_BOT_TOKEN: str = ""
    # Slack: app-level token (xapp-...) — used for Socket Mode (dev/polling)
    SLACK_APP_TOKEN: str = ""
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_DATABASE: str = "default"
    MILVUS_TOKEN: str = "root:Milvus"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def MILVUS_URI(self) -> str:
        """Build Milvus connection URI."""
        return f"http://{self.MILVUS_HOST}:{self.MILVUS_PORT}"

    EMBEDDING_MODEL: str = "text-embedding-3-large"

    RAG_CHUNK_SIZE: int = 512
    RAG_CHUNK_OVERLAP: int = 50

    RAG_DEFAULT_COLLECTION: str = "documents"
    RAG_TOP_K: int = 10
    RAG_CHUNKING_STRATEGY: str = "recursive"  # recursive, markdown, or fixed
    RAG_HYBRID_SEARCH: bool = False  # Enable BM25 + vector hybrid search
    RAG_ENABLE_OCR: bool = False  # OCR fallback for scanned PDFs (requires tesseract)
    PDF_PARSER: str = "pymupdf"  # For RAG ingestion: pymupdf, llamaparse, liteparse
    CHAT_PDF_PARSER: str = "pymupdf"  # For chat file attachments: pymupdf, llamaparse, liteparse
    LLAMAPARSE_API_KEY: str = ""
    LLAMAPARSE_TIER: str = "agentic"  # fast, cost_effective, agentic, agentic_plus
    # LiteParse OCR — empty url uses bundled Tesseract.js;
    # point at e.g. http://easyocr:8000 or http://paddleocr:8000 for HTTP OCR.
    LITEPARSE_OCR_SERVER_URL: str = ""
    LITEPARSE_OCR_LANGUAGE: str = "en"
    LITEPARSE_TIMEOUT_SECONDS: float = 600.0
    RAG_ENABLE_IMAGE_DESCRIPTION: bool = True  # set to false to disable LLM image description
    RAG_IMAGE_DESCRIPTION_MODEL: str = ""  # empty = use AI_MODEL
    GOOGLE_DRIVE_CREDENTIALS_FILE: str = "credentials/google-drive-sa.json"
    S3_RAG_ENDPOINT: str | None = None
    S3_RAG_ACCESS_KEY: str = ""
    S3_RAG_SECRET_KEY: str = ""
    S3_RAG_BUCKET: str = "ai_agent_test_8-rag"
    S3_RAG_REGION: str = "us-east-1"

    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_API_VERSION: str = "2025-04-30.acacia"
    STRIPE_TRIAL_DAYS_DEFAULT: int = 14
    STRIPE_TRIAL_REQUIRES_PAYMENT_METHOD: bool = True

    BILLING_DEFAULT_CURRENCY: str = "usd"
    BILLING_SUCCESS_URL: str = ""
    BILLING_CANCEL_URL: str = ""
    BILLING_PORTAL_RETURN_URL: str = ""

    @model_validator(mode="after")
    def _set_billing_urls(self) -> "Settings":
        frontend = self.FRONTEND_URL.rstrip("/")
        if not self.BILLING_SUCCESS_URL:
            self.BILLING_SUCCESS_URL = (
                frontend + "/billing?status=success&session_id={CHECKOUT_SESSION_ID}"
            )
        if not self.BILLING_CANCEL_URL:
            self.BILLING_CANCEL_URL = frontend + "/pricing?status=canceled"
        if not self.BILLING_PORTAL_RETURN_URL:
            self.BILLING_PORTAL_RETURN_URL = frontend + "/billing"
        return self

    CREDITS_PER_USD: int = 1000
    CREDITS_LOW_THRESHOLD: int = 100
    CREDITS_FREE_TIER_GRANT: int = 500

    EMAIL_PROVIDER: str = "resend"
    EMAIL_FROM: str = "noreply@ai_agent_test_8.com"
    EMAIL_FROM_NAME: str = "ai_agent_test_8"
    EMAIL_REPLY_TO: str | None = None
    RESEND_API_KEY: str = ""
    LOG_PROVIDER_WRITE_TO_DISK: bool = False

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
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
                "CORS_ORIGINS cannot contain '*' in production! Specify explicit allowed origins."
            )
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rag(self) -> "RAGSettings":
        """Build RAG-specific settings."""
        pdf_parser = PdfParser(
            method=self.PDF_PARSER,
            api_key=self.LLAMAPARSE_API_KEY,
            tier=self.LLAMAPARSE_TIER,
            liteparse_ocr_server_url=self.LITEPARSE_OCR_SERVER_URL or None,
            liteparse_ocr_language=self.LITEPARSE_OCR_LANGUAGE,
            liteparse_timeout_seconds=self.LITEPARSE_TIMEOUT_SECONDS,
        )

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
            enable_image_description=self.RAG_ENABLE_IMAGE_DESCRIPTION,
            image_description_model=self.RAG_IMAGE_DESCRIPTION_MODEL,
        )


# Rebuild Settings to resolve RAGSettings forward reference
from app.services.rag.config import DocumentParser, EmbeddingsConfig, PdfParser, RAGSettings

Settings.model_rebuild()


settings = Settings()
