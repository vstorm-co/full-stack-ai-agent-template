"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
{%- if cookiecutter.enable_redis or cookiecutter.enable_rag %}
from typing import TypedDict
{%- endif %}

from fastapi import FastAPI
{%- if cookiecutter.enable_orjson %}
from fastapi.responses import ORJSONResponse
{%- endif %}
{%- if cookiecutter.enable_pagination %}
from fastapi_pagination import add_pagination
{%- endif %}

from app.api.exception_handlers import register_exception_handlers
from app.api.router import api_router
from app.core.config import settings
{%- if cookiecutter.enable_logfire %}
from app.core.logfire_setup import instrument_app, setup_logfire
{%- endif %}
from app.core.middleware import RequestIDMiddleware

{%- if cookiecutter.enable_redis or cookiecutter.enable_rag %}
{%- if cookiecutter.enable_redis %}
from app.clients.redis import RedisClient
{%- endif %}
{%- if cookiecutter.enable_rag %}
from app.rag.embeddings import EmbeddingService
{%- if cookiecutter.use_milvus %}
from app.rag.vectorstore import MilvusVectorStore
{%- endif %}
{%- endif %}


class LifespanState(TypedDict, total=False):
    """Lifespan state - resources available via request.state."""

{%- if cookiecutter.enable_redis %}
    redis: RedisClient
{%- endif %}
{%- if cookiecutter.enable_rag %}
    embedding_service: EmbeddingService
{%- if cookiecutter.use_milvus %}
    vector_store: MilvusVectorStore
{%- endif %}
{%- endif %}
{%- endif %}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[{% if cookiecutter.enable_redis or cookiecutter.enable_rag %}LifespanState{% else %}None{% endif %}, None]:
    """Application lifespan - startup and shutdown events.

    Resources yielded here are available via request.state in route handlers.
    See: https://asgi.readthedocs.io/en/latest/specs/lifespan.html#lifespan-state
    """
    # === Startup ===
{%- if cookiecutter.enable_redis or cookiecutter.enable_rag %}
    state: LifespanState = {}
{%- endif %}
{%- if cookiecutter.enable_logfire %}
    setup_logfire()
{%- endif %}

{%- if cookiecutter.use_postgresql and cookiecutter.enable_logfire and cookiecutter.logfire_database %}
    from app.core.logfire_setup import instrument_asyncpg
    instrument_asyncpg()
{%- endif %}

{%- if cookiecutter.use_mongodb and cookiecutter.enable_logfire and cookiecutter.logfire_database %}
    from app.core.logfire_setup import instrument_pymongo
    instrument_pymongo()
{%- endif %}

{%- if cookiecutter.enable_redis and cookiecutter.enable_logfire and cookiecutter.logfire_redis %}
    from app.core.logfire_setup import instrument_redis
    instrument_redis()
{%- endif %}

{%- if cookiecutter.enable_logfire and cookiecutter.logfire_httpx %}
    from app.core.logfire_setup import instrument_httpx
    instrument_httpx()
{%- endif %}

{%- if cookiecutter.enable_logfire and cookiecutter.enable_ai_agent and cookiecutter.use_pydantic_ai %}
    from app.core.logfire_setup import instrument_pydantic_ai
    instrument_pydantic_ai()
{%- endif %}

{%- if cookiecutter.enable_redis %}
    redis_client = RedisClient()
    await redis_client.connect()
    state["redis"] = redis_client
{%- endif %}

{%- if cookiecutter.enable_caching and cookiecutter.enable_redis %}
    from app.core.cache import setup_cache
    setup_cache(redis_client)
{%- endif %}

{%- if cookiecutter.enable_rag %}
    from app.api.deps import get_embedding_service
    embedder = get_embedding_service()
    embedder.warmup()
    state["embedding_service"] = embedder

{%- if cookiecutter.use_milvus %}
    from app.api.deps import get_vectorstore
    # Warmup Milvus and verify health
    try:
        vector_store = get_vectorstore(embedder=embedder)
        # Verify connectivity
        await vector_store.client.list_collections()
        state["vector_store"] = vector_store
        
    except Exception as e:
        raise RuntimeError("Milvus is not ready. Check logs for details.") from e
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_redis or cookiecutter.enable_rag %}
    yield state
{%- else %}
    yield
{%- endif %}

    # === Shutdown ===
{%- if cookiecutter.enable_redis %}
    if "redis" in state:
        await state["redis"].close()
{%- endif %}

{%- if cookiecutter.use_postgresql %}
    from app.db.session import close_db
    await close_db()
{%- endif %}

{%- if cookiecutter.use_mongodb %}
    from app.db.session import close_db
    await close_db()
{%- endif %}

{%- if cookiecutter.use_sqlite %}
    from app.db.session import close_db
    close_db()
{%- endif %}

{%- if cookiecutter.enable_rag %}
{%- if cookiecutter.use_milvus %}
    try:
        if "vector_store" in state:
            await state["vector_store"].client.close()
    except Exception:
        pass
{%- endif %}
{%- endif %}


# Environments where API docs should be visible
SHOW_DOCS_ENVIRONMENTS = ("local", "staging", "development")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Only show docs in allowed environments (hide in production)
    show_docs = settings.ENVIRONMENT in SHOW_DOCS_ENVIRONMENTS
    openapi_url = f"{settings.API_V1_STR}/openapi.json" if show_docs else None
    docs_url = "/docs" if show_docs else None
    redoc_url = "/redoc" if show_docs else None

    # OpenAPI tags for better documentation organization
    openapi_tags = [
        {
            "name": "health",
            "description": "Health check endpoints for monitoring and Kubernetes probes",
        },
{%- if cookiecutter.use_jwt %}
        {
            "name": "auth",
            "description": "Authentication endpoints - login, register, token refresh",
        },
        {
            "name": "users",
            "description": "User management endpoints",
        },
{%- endif %}
{%- if cookiecutter.enable_oauth %}
        {
            "name": "oauth",
            "description": "OAuth2 social login endpoints (Google, etc.)",
        },
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
        {
            "name": "sessions",
            "description": "Session management - view and manage active login sessions",
        },
{%- endif %}
{%- if cookiecutter.include_example_crud %}
        {
            "name": "items",
            "description": "Example CRUD endpoints demonstrating the API pattern",
        },
{%- endif %}
{%- if cookiecutter.enable_conversation_persistence %}
        {
            "name": "conversations",
            "description": "AI conversation persistence - manage chat history",
        },
{%- endif %}
{%- if cookiecutter.enable_webhooks %}
        {
            "name": "webhooks",
            "description": "Webhook management - subscribe to events and manage deliveries",
        },
{%- endif %}
{%- if cookiecutter.enable_ai_agent %}
        {
            "name": "agent",
            "description": "AI agent WebSocket endpoint for real-time chat",
        },
{%- endif %}
{%- if cookiecutter.enable_websockets %}
        {
            "name": "websocket",
            "description": "WebSocket endpoints for real-time communication",
        },
{%- endif %}
{%- if cookiecutter.enable_rag %}
        {
            "name": "rag",
            "description": "Retrieval Augmented Generation endpoints",
        },
{%- endif %}
    ]

    app = FastAPI(
        title=settings.PROJECT_NAME,
        summary="FastAPI application{% if cookiecutter.enable_logfire %} with Logfire observability{% endif %}",
        description="""
{{ cookiecutter.project_description }}

## Features

{%- if cookiecutter.use_jwt %}
- **Authentication**: JWT-based authentication with refresh tokens
{%- endif %}
{%- if cookiecutter.use_api_key %}
- **API Key**: Header-based API key authentication
{%- endif %}
{%- if cookiecutter.use_database %}
- **Database**: Async database operations
{%- endif %}
{%- if cookiecutter.enable_redis %}
- **Redis**: Caching and session storage
{%- endif %}
{%- if cookiecutter.enable_rate_limiting %}
- **Rate Limiting**: Request rate limiting per client
{%- endif %}
{%- if cookiecutter.enable_ai_agent and cookiecutter.use_pydantic_ai %}
- **AI Agent**: PydanticAI-powered conversational assistant
{%- endif %}
{%- if cookiecutter.enable_ai_agent and cookiecutter.use_langchain %}
- **AI Agent**: LangChain-powered conversational assistant
{%- endif %}
{%- if cookiecutter.enable_logfire %}
- **Observability**: Logfire integration for tracing and monitoring
{%- endif %}
{%- if cookiecutter.enable_rag %}
- **RAG**: Retrieval Augmented Generation with Milvus and LangChain
{%- endif %}

## Documentation

- [Swagger UI](/docs) - Interactive API documentation
- [ReDoc](/redoc) - Alternative documentation view
        """.strip(),
        version="0.1.0",
        openapi_url=openapi_url,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_tags=openapi_tags,
        contact={
            "name": "{{ cookiecutter.author_name }}",
            "email": "{{ cookiecutter.author_email }}",
        },
        license_info={
            "name": "MIT",
            "identifier": "MIT",
        },
        lifespan=lifespan,
{%- if cookiecutter.enable_orjson %}
        default_response_class=ORJSONResponse,
{%- endif %}
    )

{%- if cookiecutter.enable_logfire %}
    # Logfire instrumentation
    instrument_app(app)
{%- endif %}

    # Request ID middleware (for request correlation/debugging)
    app.add_middleware(RequestIDMiddleware)

    # Exception handlers
    register_exception_handlers(app)

{%- if cookiecutter.enable_cors %}

    # CORS middleware
    from starlette.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
{%- endif %}

{%- if cookiecutter.enable_sentry %}

    # Sentry
    if settings.SENTRY_DSN:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.SENTRY_DSN, enable_tracing=True)
{%- endif %}

{%- if cookiecutter.enable_prometheus %}

    # Prometheus metrics
    from prometheus_fastapi_instrumentator import Instrumentator

    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/health/ready", "/health/live", settings.PROMETHEUS_METRICS_PATH],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )
    instrumentator.instrument(app).expose(
        app,
        endpoint=settings.PROMETHEUS_METRICS_PATH,
        include_in_schema=settings.PROMETHEUS_INCLUDE_IN_SCHEMA,
    )
{%- endif %}

{%- if cookiecutter.enable_rate_limiting %}

    # Rate limiting
    # Note: slowapi requires app.state.limiter - this is a library requirement,
    # not suitable for lifespan state pattern which is for request-scoped access
    from app.core.rate_limit import limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
{%- endif %}

{%- if (cookiecutter.enable_admin_panel and cookiecutter.use_postgresql and cookiecutter.admin_require_auth and not cookiecutter.admin_env_disabled) or cookiecutter.enable_oauth %}

    # Session middleware (for admin authentication and/or OAuth)
    from starlette.middleware.sessions import SessionMiddleware
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
{%- endif %}

{%- if cookiecutter.enable_admin_panel and cookiecutter.use_postgresql %}
{%- if cookiecutter.admin_env_disabled %}
    # Admin panel - disabled
{%- elif cookiecutter.admin_env_all %}

    # Admin panel (all environments)
    from app.admin import setup_admin
    setup_admin(app)
{%- else %}

    # Admin panel (environment restricted)
    {%- if cookiecutter.admin_env_dev_only %}
    ADMIN_ALLOWED_ENVIRONMENTS = ["development", "local"]
    {%- elif cookiecutter.admin_env_dev_staging %}
    ADMIN_ALLOWED_ENVIRONMENTS = ["development", "local", "staging"]
    {%- endif %}

    if settings.ENVIRONMENT in ADMIN_ALLOWED_ENVIRONMENTS:
        from app.admin import setup_admin
        setup_admin(app)
{%- endif %}
{%- endif %}

    # API Version Deprecation (uncomment when deprecating old versions)
    # Example: Mark v1 as deprecated when v2 is ready
    # from app.api.versioning import VersionDeprecationMiddleware
    # app.add_middleware(
    #     VersionDeprecationMiddleware,
    #     deprecated_versions={
    #         "v1": {
    #             "sunset": "2025-12-31",
    #             "link": "/docs/migration/v2",
    #             "message": "Please migrate to API v2",
    #         }
    #     },
    # )

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)

{%- if cookiecutter.enable_pagination %}

    # Pagination
    add_pagination(app)
{%- endif %}

    return app


app = create_app()
