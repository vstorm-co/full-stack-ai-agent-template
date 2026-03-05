"""Application configuration using Pydantic BaseSettings."""
{% if cookiecutter.use_database or cookiecutter.enable_redis -%}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
{% endif %}
from pathlib import Path
from typing import Literal

{% if cookiecutter.use_database or cookiecutter.enable_redis -%}
from pydantic import computed_field, field_validator{% if cookiecutter.use_jwt or cookiecutter.use_api_key or cookiecutter.enable_cors %}, ValidationInfo{% endif %}
{% else -%}
from pydantic import field_validator{% if cookiecutter.use_jwt or cookiecutter.use_api_key or cookiecutter.enable_cors %}, ValidationInfo{% endif %}
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
    SQLITE_PATH: str = "./{{ cookiecutter.project_slug }}.db"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Build SQLite connection URL."""
        return f"sqlite:///{self.SQLITE_PATH}"
{%- endif %}

{%- if cookiecutter.use_sqlserver %}

    # === Database (MS SQL Server async) ===
    MSSQL_HOST: str = "localhost"
    MSSQL_PORT: int = 1433
    MSSQL_USER: str = "sa"
    MSSQL_PASSWORD: str = ""
    MSSQL_DB: str = "{{ cookiecutter.project_slug }}"
    MSSQL_DRIVER: str = "ODBC Driver 18 for SQL Server"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Build async MS SQL Server connection URL."""
        return (
            f"mssql+aioodbc://{self.MSSQL_USER}:{self.MSSQL_PASSWORD}"
            f"@{self.MSSQL_HOST}:{self.MSSQL_PORT}/{self.MSSQL_DB}"
            f"?driver={self.MSSQL_DRIVER.replace(' ', '+')}"
            "&TrustServerCertificate=yes"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Build sync MS SQL Server connection URL (for Alembic)."""
        return (
            f"mssql+pyodbc://{self.MSSQL_USER}:{self.MSSQL_PASSWORD}"
            f"@{self.MSSQL_HOST}:{self.MSSQL_PORT}/{self.MSSQL_DB}"
            f"?driver={self.MSSQL_DRIVER.replace(' ', '+')}"
            "&TrustServerCertificate=yes"
        )

    # Pool configuration
    DB_POOL_SIZE: int = {{ cookiecutter.db_pool_size }}
    DB_MAX_OVERFLOW: int = {{ cookiecutter.db_max_overflow }}
    DB_POOL_TIMEOUT: int = {{ cookiecutter.db_pool_timeout }}
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

{%- if cookiecutter.enable_oauth_google %}

    # === OAuth2 (Google) ===
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:{{ cookiecutter.backend_port }}/api/v1/oauth/google/callback"
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
{%- endif %}

{%- if cookiecutter.enable_file_storage %}

    # === File Storage (S3/MinIO) ===
    S3_ENDPOINT: str | None = None
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "{{ cookiecutter.project_slug }}"
    S3_REGION: str = "us-east-1"
{%- endif %}

{%- if cookiecutter.enable_ai_agent %}

    # === AI Agent ({{ cookiecutter.ai_framework }}, {{ cookiecutter.llm_provider }}) ===
{%- if cookiecutter.use_openai %}
    OPENAI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4o-mini"
{%- endif %}
{%- if cookiecutter.use_anthropic %}
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-sonnet-4-5-20241022"
{%- endif %}
{%- if cookiecutter.use_openrouter %}
    OPENROUTER_API_KEY: str = ""
    AI_MODEL: str = "anthropic/claude-3.5-sonnet"
{%- endif %}
    AI_TEMPERATURE: float = 0.7
    AI_FRAMEWORK: str = "{{ cookiecutter.ai_framework }}"
    LLM_PROVIDER: str = "{{ cookiecutter.llm_provider }}"
{%- if cookiecutter.use_langchain %}

    # === LangSmith (LangChain observability) ===
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str | None = None
    LANGCHAIN_PROJECT: str = "{{ cookiecutter.project_slug }}"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
{%- endif %}
{%- if cookiecutter.use_deepagents %}

    # === DeepAgents Configuration ===
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
{%- endif %}

{%- if cookiecutter.enable_cors %}

    # === CORS ===
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]
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


settings = Settings()
