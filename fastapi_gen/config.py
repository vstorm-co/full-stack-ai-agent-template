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


class AuthType(StrEnum):
    """Supported authentication types."""

    JWT = "jwt"
    API_KEY = "api_key"
    BOTH = "both"
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


class WebSocketAuthType(StrEnum):
    """WebSocket authentication types for AI Agent."""

    NONE = "none"
    JWT = "jwt"
    API_KEY = "api_key"


class AdminEnvironmentType(StrEnum):
    """Admin panel environment restriction types."""

    ALL = "all"  # Available in all environments
    DEV_ONLY = "dev_only"  # Only in development
    DEV_STAGING = "dev_staging"  # Development + Staging (recommended)
    DISABLED = "disabled"  # Disabled everywhere


class OAuthProvider(StrEnum):
    """Supported OAuth2 providers."""

    NONE = "none"
    GOOGLE = "google"


class AIFrameworkType(StrEnum):
    """Supported AI agent frameworks."""

    PYDANTIC_AI = "pydantic_ai"
    LANGCHAIN = "langchain"
    LANGGRAPH = "langgraph"
    CREWAI = "crewai"
    DEEPAGENTS = "deepagents"


class LLMProviderType(StrEnum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"


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

    OPENAI = "openai"  # test-embedding-3-small
    VOYAGE = "voyage"  # voyage-3 (Anthropic users)
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
    PDFPLUMBER: Fast, free, local PDF extraction using pdfplumber.
               Only extracts text layer - fails on scanned images.
    LLAMAPARSE: AI-powered cloud extraction. Handles complex layouts,
                tables, and scanned documents. Requires API key.
    """

    PDFPLUMBER = "pdfplumber"  # Local PDF extraction
    LLAMAPARSE = "llamaparse"  # LlamaParse cloud API


class VectorStoreType(StrEnum):
    """Define a Vector Store type."""

    MILVUS = "milvus"


class RAGFeatures(BaseModel):
    """RAG features."""

    enable_rag: bool = False
    enable_google_drive_ingestion: bool = False
    enable_reranker: bool = False
    # pdf_parser is stored here since it's only used when RAG is enabled
    pdf_parser: PdfParserType = PdfParserType.PDFPLUMBER
    vector_store: VectorStoreType = VectorStoreType.MILVUS


class ProjectConfig(BaseModel):
    """Full project configuration."""

    # Basic info
    project_name: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    project_description: str = "A FastAPI project"

    author_name: str = "Your Name"
    author_email: EmailStr = "your@email.com"

    # Database
    database: DatabaseType = DatabaseType.POSTGRESQL
    orm_type: OrmType = OrmType.SQLALCHEMY
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30

    # RAG
    rag_features: RAGFeatures = Field(default_factory=RAGFeatures)

    # Authentication
    auth: AuthType = AuthType.JWT
    oauth_provider: OAuthProvider = OAuthProvider.NONE
    enable_session_management: bool = False

    # Observability
    enable_logfire: bool = True
    logfire_features: LogfireFeatures = Field(default_factory=LogfireFeatures)

    # Background tasks
    background_tasks: BackgroundTaskType = BackgroundTaskType.NONE

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
    admin_environments: AdminEnvironmentType = AdminEnvironmentType.DEV_STAGING
    admin_require_auth: bool = True
    enable_websockets: bool = False
    enable_file_storage: bool = False
    enable_ai_agent: bool = True
    ai_framework: AIFrameworkType = AIFrameworkType.PYDANTIC_AI
    llm_provider: LLMProviderType = LLMProviderType.OPENAI
    enable_conversation_persistence: bool = False
    enable_webhooks: bool = False
    websocket_auth: WebSocketAuthType = WebSocketAuthType.NONE
    enable_langsmith: bool = False
    enable_cors: bool = True
    enable_orjson: bool = True

    # Frontend features
    enable_i18n: bool = False

    # Example CRUD
    include_example_crud: bool = True

    # Dev tools
    enable_pytest: bool = True
    enable_precommit: bool = True
    enable_makefile: bool = True
    enable_docker: bool = True
    reverse_proxy: ReverseProxyType = ReverseProxyType.TRAEFIK_INCLUDED
    ci_type: CIType = CIType.GITHUB
    enable_kubernetes: bool = False
    generate_env: bool = True

    # Python version
    python_version: str = "3.12"

    # Frontend
    frontend: FrontendType = FrontendType.NEXTJS
    frontend_port: int = 3000

    # Backend
    backend_port: int = 8000

    @computed_field
    @property
    def project_slug(self) -> str:
        """Return project slug (underscores instead of hyphens)."""
        return self.project_name.replace("-", "_")

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
        if self.enable_admin_panel and self.database == DatabaseType.NONE:
            raise ValueError("Admin panel requires a database")
        if self.enable_admin_panel and self.database == DatabaseType.MONGODB:
            raise ValueError("Admin panel (SQLAdmin) requires PostgreSQL or SQLite")
        if self.orm_type == OrmType.SQLMODEL and self.database not in (
            DatabaseType.POSTGRESQL,
            DatabaseType.SQLITE,
        ):
            raise ValueError("SQLModel requires PostgreSQL or SQLite database")
        if self.enable_caching and not self.enable_redis:
            raise ValueError("Caching requires Redis to be enabled")
        if self.enable_session_management and self.database == DatabaseType.NONE:
            raise ValueError("Session management requires a database")
        if self.enable_conversation_persistence and self.database == DatabaseType.NONE:
            raise ValueError("Conversation persistence requires a database")
        if (
            self.enable_ai_agent
            and self.ai_framework == AIFrameworkType.LANGCHAIN
            and self.llm_provider == LLMProviderType.OPENROUTER
        ):
            raise ValueError("OpenRouter is not supported with LangChain")
        if (
            self.enable_ai_agent
            and self.ai_framework == AIFrameworkType.LANGGRAPH
            and self.llm_provider == LLMProviderType.OPENROUTER
        ):
            raise ValueError("OpenRouter is not supported with LangGraph")
        if (
            self.enable_ai_agent
            and self.ai_framework == AIFrameworkType.CREWAI
            and self.llm_provider == LLMProviderType.OPENROUTER
        ):
            raise ValueError("OpenRouter is not supported with CrewAI")
        if (
            self.enable_ai_agent
            and self.ai_framework == AIFrameworkType.DEEPAGENTS
            and self.llm_provider == LLMProviderType.OPENROUTER
        ):
            raise ValueError(
                "DeepAgents does not support OpenRouter. Use OpenAI or Anthropic provider instead."
            )
        if (
            self.enable_rate_limiting
            and self.rate_limit_storage == RateLimitStorageType.REDIS
            and not self.enable_redis
        ):
            raise ValueError("Rate limiting with Redis storage requires Redis to be enabled")

        # LangSmith requires LangChain-ecosystem framework
        if self.enable_langsmith and self.ai_framework not in (
            AIFrameworkType.LANGCHAIN,
            AIFrameworkType.LANGGRAPH,
            AIFrameworkType.DEEPAGENTS,
        ):
            raise ValueError("LangSmith requires LangChain, LangGraph, or DeepAgents framework")

        # WebSocket JWT auth requires main JWT auth
        if self.websocket_auth == WebSocketAuthType.JWT and self.auth not in (
            AuthType.JWT,
            AuthType.BOTH,
        ):
            raise ValueError("WebSocket JWT authentication requires JWT auth to be enabled")

        # WebSocket API key auth requires main API key auth
        if self.websocket_auth == WebSocketAuthType.API_KEY and self.auth not in (
            AuthType.API_KEY,
            AuthType.BOTH,
        ):
            raise ValueError("WebSocket API key authentication requires API key auth to be enabled")

        # Admin panel authentication requires JWT (for User model and security functions)
        if (
            self.enable_admin_panel
            and self.admin_require_auth
            and self.auth not in (AuthType.JWT, AuthType.BOTH)
        ):
            raise ValueError(
                "Admin panel authentication requires JWT auth to be enabled. "
                "Either enable JWT auth or set admin_require_auth=False"
            )

        # Conversation persistence requires AI agent
        if self.enable_conversation_persistence and not self.enable_ai_agent:
            raise ValueError("Conversation persistence requires AI agent to be enabled")

        # Admin panel requires SQLAlchemy (SQLAdmin doesn't fully support SQLModel)
        if self.enable_admin_panel and self.orm_type == OrmType.SQLMODEL:
            raise ValueError(
                "Admin panel (SQLAdmin) requires SQLAlchemy ORM. "
                "SQLModel is not fully supported. Use orm_type=sqlalchemy or disable admin panel."
            )

        # Session management requires JWT auth
        if self.enable_session_management and self.auth not in (AuthType.JWT, AuthType.BOTH):
            raise ValueError("Session management requires JWT auth to be enabled")

        # Webhooks require a database
        if self.enable_webhooks and self.database == DatabaseType.NONE:
            raise ValueError(
                "Webhooks require a database to store subscriptions and delivery history"
            )

        # OAuth requires JWT authentication
        if self.oauth_provider != OAuthProvider.NONE and self.auth not in (
            AuthType.JWT,
            AuthType.BOTH,
        ):
            raise ValueError(
                "OAuth authentication requires JWT auth to be enabled. "
                "OAuth uses JWT tokens for session management after social login."
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
            if self.logfire_features.database and self.database == DatabaseType.NONE:
                raise ValueError(
                    "Logfire database instrumentation requires a database to be enabled"
                )

            if self.logfire_features.redis and not self.enable_redis:
                raise ValueError("Logfire Redis instrumentation requires Redis to be enabled")

            if self.logfire_features.celery and self.background_tasks != BackgroundTaskType.CELERY:
                raise ValueError(
                    "Logfire Celery instrumentation requires Celery as background task system"
                )

        # RAG-oriented checks
        if self.rag_features.enable_rag and not self.enable_ai_agent:
            raise ValueError("RAG requires AI agent to be enabled.")

        if self.rag_features.enable_rag and self.background_tasks == BackgroundTaskType.NONE:
            raise ValueError("RAG requires a background task system for scheduled ingestion.")

        if self.rag_features.enable_rag and not self.enable_docker:
            raise ValueError(
                "RAG (w/ Milvus) requires Docker to be enabled for local orchestration."
            )

        if (
            self.rag_features.enable_google_drive_ingestion
            and self.oauth_provider != OAuthProvider.GOOGLE
        ):
            raise ValueError("Google Drive ingestion requires OAuth Provider to be set.")

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
            # Auth
            "auth": self.auth.value,
            "use_jwt": self.auth in (AuthType.JWT, AuthType.BOTH),
            "use_api_key": self.auth in (AuthType.API_KEY, AuthType.BOTH),
            "use_auth": self.auth != AuthType.NONE,
            # OAuth
            "oauth_provider": self.oauth_provider.value,
            "enable_oauth": self.oauth_provider != OAuthProvider.NONE,
            "enable_oauth_google": self.oauth_provider == OAuthProvider.GOOGLE,
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
            "admin_environments": self.admin_environments.value,
            "admin_env_all": self.admin_environments == AdminEnvironmentType.ALL,
            "admin_env_dev_only": self.admin_environments == AdminEnvironmentType.DEV_ONLY,
            "admin_env_dev_staging": self.admin_environments == AdminEnvironmentType.DEV_STAGING,
            "admin_env_disabled": self.admin_environments == AdminEnvironmentType.DISABLED,
            "admin_require_auth": self.admin_require_auth,
            "enable_websockets": self.enable_websockets,
            "enable_file_storage": self.enable_file_storage,
            "enable_ai_agent": self.enable_ai_agent,
            "ai_framework": self.ai_framework.value,
            "use_pydantic_ai": self.ai_framework == AIFrameworkType.PYDANTIC_AI,
            "use_langchain": self.ai_framework == AIFrameworkType.LANGCHAIN,
            "use_langgraph": self.ai_framework == AIFrameworkType.LANGGRAPH,
            "use_crewai": self.ai_framework == AIFrameworkType.CREWAI,
            "use_deepagents": self.ai_framework == AIFrameworkType.DEEPAGENTS,
            "llm_provider": self.llm_provider.value,
            "use_openai": self.llm_provider == LLMProviderType.OPENAI,
            "use_anthropic": self.llm_provider == LLMProviderType.ANTHROPIC,
            "use_openrouter": self.llm_provider == LLMProviderType.OPENROUTER,
            "enable_conversation_persistence": self.enable_conversation_persistence,
            "enable_langsmith": self.enable_langsmith,
            "enable_webhooks": self.enable_webhooks,
            "websocket_auth": self.websocket_auth.value,
            "websocket_auth_jwt": self.websocket_auth == WebSocketAuthType.JWT,
            "websocket_auth_api_key": self.websocket_auth == WebSocketAuthType.API_KEY,
            "websocket_auth_none": self.websocket_auth == WebSocketAuthType.NONE,
            "enable_cors": self.enable_cors,
            "enable_orjson": self.enable_orjson,
            # Frontend features
            "enable_i18n": self.enable_i18n,
            # Example CRUD
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
            # Backend
            "backend_port": self.backend_port,
            # RAG
            "enable_rag": self.rag_features.enable_rag,
            "use_milvus": self.rag_features.enable_rag,
            # Embedding provider is auto-derived from LLM provider
            "embedding_provider": (
                EmbeddingProviderType.VOYAGE.value
                if self.llm_provider == LLMProviderType.ANTHROPIC
                else EmbeddingProviderType.SENTENCE_TRANSFORMERS.value
                if self.llm_provider == LLMProviderType.OPENROUTER
                else EmbeddingProviderType.OPENAI.value
            ),
            "use_openai_embeddings": self.rag_features.enable_rag
            and self.llm_provider != LLMProviderType.ANTHROPIC
            and self.llm_provider != LLMProviderType.OPENROUTER,
            "use_voyage_embeddings": self.rag_features.enable_rag
            and self.llm_provider == LLMProviderType.ANTHROPIC,
            "use_sentence_transformers": self.rag_features.enable_rag
            and self.llm_provider == LLMProviderType.OPENROUTER,
            "enable_reranker": self.rag_features.enable_reranker
            if self.rag_features.enable_rag
            else False,
            "use_cohere_reranker": self.rag_features.enable_reranker
            and self.llm_provider != LLMProviderType.OPENROUTER,
            "use_cross_encoder_reranker": self.rag_features.enable_reranker
            and self.llm_provider == LLMProviderType.OPENROUTER,
            "pdf_parser": self.rag_features.pdf_parser.value
            if self.rag_features.enable_rag
            else "pdfplumber",
            "use_llamaparse": self.rag_features.enable_rag
            and self.rag_features.pdf_parser == PdfParserType.LLAMAPARSE,
            "use_pdfplumber": self.rag_features.enable_rag
            and self.rag_features.pdf_parser == PdfParserType.PDFPLUMBER,
            "use_python_parser": True,  # Always use Python parser for non-PDF
            "enable_google_drive_ingestion": self.rag_features.enable_google_drive_ingestion
            if self.rag_features.enable_rag
            else False,
        }
