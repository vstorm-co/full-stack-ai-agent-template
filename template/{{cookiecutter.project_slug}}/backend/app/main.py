"""FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
{%- if cookiecutter.enable_redis or cookiecutter.enable_rag or cookiecutter.use_telegram or cookiecutter.use_slack %}
from typing import TypedDict
{%- endif %}

logger = logging.getLogger(__name__)

from fastapi import FastAPI
{%- if cookiecutter.enable_pagination %}
from fastapi_pagination import add_pagination
{%- endif %}

from app.api.exception_handlers import register_exception_handlers
from app.api.router import api_router
from app.core.config import settings
{%- if cookiecutter.enable_logfire %}
from app.core.logfire_setup import instrument_app, setup_logfire
{%- endif %}
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware

{%- if cookiecutter.enable_redis or cookiecutter.enable_rag %}
{%- if cookiecutter.enable_redis %}
from app.clients.redis import RedisClient
{%- endif %}
{%- if cookiecutter.enable_rag %}
from app.services.rag.embeddings import EmbeddingService
{%- if cookiecutter.use_milvus %}
from app.services.rag.vectorstore import MilvusVectorStore
{%- elif cookiecutter.use_qdrant %}
from app.services.rag.vectorstore import QdrantVectorStore
{%- elif cookiecutter.use_chromadb %}
from app.services.rag.vectorstore import ChromaVectorStore
{%- elif cookiecutter.use_pgvector %}
from app.services.rag.vectorstore import PgVectorStore
{%- endif %}
from app.services.rag.vectorstore import BaseVectorStore
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_redis or cookiecutter.enable_rag or cookiecutter.use_telegram or cookiecutter.use_slack %}


class LifespanState(TypedDict, total=False):
    """Lifespan state - resources available via request.state."""

{%- if cookiecutter.enable_redis %}
    redis: RedisClient
{%- endif %}
{%- if cookiecutter.enable_rag %}
    embedding_service: EmbeddingService
    vector_store: BaseVectorStore
{%- endif %}
{%- endif %}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[{% if cookiecutter.enable_redis or cookiecutter.enable_rag or cookiecutter.use_telegram or cookiecutter.use_slack %}LifespanState{% else %}None{% endif %}, None]:
    """Application lifespan - startup and shutdown events.

    Resources yielded here are available via request.state in route handlers.
    See: https://asgi.readthedocs.io/en/latest/specs/lifespan.html#lifespan-state
    """
    # === Startup ===
{%- if cookiecutter.enable_redis or cookiecutter.enable_rag or cookiecutter.use_telegram or cookiecutter.use_slack %}
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

{%- if cookiecutter.enable_logfire and cookiecutter.use_pydantic_ai %}
    from app.core.logfire_setup import instrument_pydantic_ai
    instrument_pydantic_ai()
{%- endif %}

{%- if cookiecutter.enable_redis %}
    redis_client = RedisClient()
    await redis_client.connect()
    state["redis"] = redis_client
{%- endif %}
{%- if cookiecutter.enable_deep_research %}

    if settings.ENABLE_DEEP_RESEARCH:
        from app.db.todo_pool import init_todo_pool

        await init_todo_pool()
{%- endif %}

{%- if cookiecutter.enable_caching and cookiecutter.enable_redis %}
    from app.core.cache import setup_cache
    setup_cache(redis_client)
{%- endif %}

{%- if cookiecutter.enable_rag %}
    from app.core.config import settings
    try:
        embedder = EmbeddingService(settings=settings.rag)
        embedder.warmup()
        state["embedding_service"] = embedder
    except Exception as e:
        logger.error(f"Embedding service warmup failed: {e}. RAG will not be available.")

{%- if cookiecutter.enable_reranker %}
    # Initialize and warmup reranker (downloads model or validates API key)
    try:
        from app.services.rag.reranker import RerankService
        rerank_service = RerankService(settings=settings.rag)
        rerank_service.warmup()
        state["rerank_service"] = rerank_service
    except Exception as e:
        logger.warning(f"Reranker warmup failed: {e}. Reranking will be disabled.")
{%- endif %}

{%- if cookiecutter.use_milvus %}
    # Warmup Milvus and verify health
    if "embedding_service" in state:
        try:
            vector_store = MilvusVectorStore(settings=settings.rag, embedding_service=embedder)
            await vector_store.client.list_collections()
            state["vector_store"] = vector_store
        except Exception as e:
            logger.error(f"Milvus connection failed: {e}. Vector store will not be available.")
{%- endif %}
{%- if cookiecutter.use_qdrant %}
    if "embedding_service" in state:
        try:
            vector_store = QdrantVectorStore(settings=settings.rag, embedding_service=embedder)
            state["vector_store"] = vector_store
        except Exception as e:
            logger.error(f"Qdrant connection failed: {e}. Vector store will not be available.")
{%- endif %}
{%- if cookiecutter.use_chromadb %}
    if "embedding_service" in state:
        try:
            vector_store = ChromaVectorStore(settings=settings.rag, embedding_service=embedder)
            state["vector_store"] = vector_store
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}. Vector store will not be available.")
{%- endif %}
{%- if cookiecutter.use_pgvector %}
    if "embedding_service" in state:
        try:
            vector_store = PgVectorStore(settings=settings.rag, embedding_service=embedder)
            state["vector_store"] = vector_store
        except Exception as e:
            logger.error(f"pgvector connection failed: {e}. Vector store will not be available.")
{%- endif %}
{%- endif %}

{%- if cookiecutter.use_telegram %}

    # === Telegram Channel Polling ===
    from app.services.channels import register_adapter
    from app.services.channels.telegram import TelegramAdapter
    from app.core.channel_crypto import decrypt_token
    _telegram_adapter = TelegramAdapter()
    register_adapter(_telegram_adapter)
    try:
{%- if cookiecutter.use_postgresql %}
        from app.db.session import get_db_context
        async with get_db_context() as _db:
            from app.repositories.channel_bot import get_active_polling_bots
            _polling_bots = await get_active_polling_bots(_db, "telegram")
{%- elif cookiecutter.use_sqlite %}
        from contextlib import contextmanager as _cm
        from app.db.session import get_db_session as _get_db
        with _cm(_get_db)() as _db:
            from app.repositories.channel_bot import get_active_polling_bots
            _polling_bots = get_active_polling_bots(_db, "telegram")
{%- elif cookiecutter.use_mongodb %}
        from app.repositories.channel_bot import get_active_polling_bots
        _polling_bots = await get_active_polling_bots("telegram")
{%- endif %}
        for _bot in _polling_bots:
            _token = decrypt_token(_bot.token_encrypted)
            await _telegram_adapter.start_polling(str(_bot.id), _token)
        logger.info("Telegram: polling started for %d bot(s)", len(_polling_bots))
    except Exception as _exc:
        logger.error("Telegram: failed to start polling: %s", _exc)
{%- endif %}

{%- if cookiecutter.use_slack %}

    # === Slack Adapter (Socket Mode polling for dev, Events API for prod) ===
    from app.services.channels import register_adapter as _slack_register
    from app.services.channels.slack import SlackAdapter
    from app.core.channel_crypto import decrypt_token as _slack_decrypt
    _slack_adapter = SlackAdapter()
    _slack_register(_slack_adapter)
    try:
{%- if cookiecutter.use_postgresql %}
        from app.db.session import get_db_context
        async with get_db_context() as _slack_db:
            from app.repositories.channel_bot import get_active_polling_bots
            _slack_bots = await get_active_polling_bots(_slack_db, "slack")
{%- elif cookiecutter.use_sqlite %}
        from contextlib import contextmanager as _slack_cm
        from app.db.session import get_db_session as _slack_get_db
        with _slack_cm(_slack_get_db)() as _slack_db:
            from app.repositories.channel_bot import get_active_polling_bots
            _slack_bots = get_active_polling_bots(_slack_db, "slack")
{%- elif cookiecutter.use_mongodb %}
        from app.repositories.channel_bot import get_active_polling_bots
        _slack_bots = await get_active_polling_bots("slack")
{%- endif %}
        for _sbot in _slack_bots:
            _stoken = _slack_decrypt(_sbot.token_encrypted)
            await _slack_adapter.start_polling(str(_sbot.id), _stoken)
        logger.info("Slack: Socket Mode started for %d bot(s)", len(_slack_bots))
    except Exception as _slack_exc:
        logger.error("Slack: failed to start Socket Mode: %s", _slack_exc)
{%- endif %}

{%- if cookiecutter.enable_seed_admin and (cookiecutter.use_postgresql or cookiecutter.use_sqlite or cookiecutter.use_mongodb) %}
    # === Auto-promote FIRST_ADMIN_EMAIL to app-admin ===
    from app.core.config import settings as _settings
    _first_admin = getattr(_settings, "FIRST_ADMIN_EMAIL", "")
    if _first_admin:
{%- if cookiecutter.use_postgresql %}
        from app.db.session import get_db_context as _get_db_ctx
        from app.repositories import user_repo as _user_repo
        try:
            async with _get_db_ctx() as _db:
                _u = await _user_repo.get_by_email(_db, _first_admin)
                if _u and not getattr(_u, "is_app_admin", False):
                    _u.is_app_admin = True
                    await _db.flush()
                    logger.info("Auto-promoted %s to app-admin (FIRST_ADMIN_EMAIL)", _first_admin)
        except Exception as _e:
            logger.warning("FIRST_ADMIN_EMAIL promotion failed: %s", _e)
{%- elif cookiecutter.use_sqlite %}
        from app.db.session import get_db_session as _get_db_s
        from app.repositories import user_repo as _user_repo
        try:
            with next(_get_db_s()) as _db:
                _u = _user_repo.get_by_email(_db, _first_admin)
                if _u and not getattr(_u, "is_app_admin", False):
                    _u.is_app_admin = True
                    _db.flush()
                    logger.info("Auto-promoted %s to app-admin (FIRST_ADMIN_EMAIL)", _first_admin)
        except Exception as _e:
            logger.warning("FIRST_ADMIN_EMAIL promotion failed: %s", _e)
{%- elif cookiecutter.use_mongodb %}
        from app.db.session import init_db as _init_db
        from app.repositories import user_repo as _user_repo
        try:
            await _init_db()
            _u = await _user_repo.get_by_email(_first_admin)
            if _u and not getattr(_u, "is_app_admin", False):
                _u.is_app_admin = True
                await _u.save()
                logger.info("Auto-promoted %s to app-admin (FIRST_ADMIN_EMAIL)", _first_admin)
        except Exception as _e:
            logger.warning("FIRST_ADMIN_EMAIL promotion failed: %s", _e)
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_redis or cookiecutter.enable_rag or cookiecutter.use_telegram or cookiecutter.use_slack %}
    yield state
{%- else %}
    yield
{%- endif %}

    # === Shutdown ===
{%- if cookiecutter.enable_deep_research %}
    if settings.ENABLE_DEEP_RESEARCH:
        from app.db.todo_pool import close_todo_pool

        await close_todo_pool()
{%- endif %}
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
            await state["vector_store"].client.close()  # type: ignore[attr-defined]
    except Exception:
        pass
{%- endif %}
{%- if cookiecutter.use_qdrant %}
    try:
        if "vector_store" in state:
            await state["vector_store"].client.close()  # type: ignore[attr-defined]
    except Exception:
        pass
{%- endif %}
{%- if cookiecutter.use_pgvector %}
    try:
        if "vector_store" in state:
            await state["vector_store"].engine.dispose()  # type: ignore[attr-defined]
    except Exception:
        pass
{%- endif %}
{%- endif %}

{%- if cookiecutter.use_telegram %}
    for _bid in list(_telegram_adapter._polling_tasks.keys()):
        await _telegram_adapter.stop_polling(_bid)
{%- endif %}

{%- if cookiecutter.use_slack %}
    for _sbid in list(_slack_adapter._socket_tasks.keys()):
        await _slack_adapter.stop_polling(_sbid)
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
{%- if cookiecutter.use_ai %}
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
{%- if cookiecutter.use_ai %}
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

    # PII redaction in logs (GDPR/compliance)
    setup_logging()

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
{%- if cookiecutter.use_pydantic_ai %}
- **AI Agent**: PydanticAI-powered conversational assistant
{%- endif %}
{%- if cookiecutter.use_langchain %}
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
    )

{%- if cookiecutter.enable_logfire %}
    # Logfire instrumentation. setup_logfire() is also called from the lifespan
    # for the runtime app, but we call it here too so that import-time test
    # clients (which never run lifespan) silence the "configure first" warning.
    setup_logfire()
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
    # Optional Bearer-token guard so the metrics endpoint can be exposed on a
    # public ingress without leaking internals. When PROMETHEUS_AUTH_TOKEN is
    # empty the endpoint is unauthenticated (typical for private networks).
    if settings.PROMETHEUS_AUTH_TOKEN:
        from fastapi import Depends, Header, HTTPException, status as http_status

        def _verify_metrics_token(authorization: str = Header(default="")) -> None:
            expected = f"Bearer {settings.PROMETHEUS_AUTH_TOKEN}"
            import secrets as _secrets
            if not _secrets.compare_digest(authorization, expected):
                raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED)

        instrumentator.instrument(app).expose(
            app,
            endpoint=settings.PROMETHEUS_METRICS_PATH,
            include_in_schema=settings.PROMETHEUS_INCLUDE_IN_SCHEMA,
            dependencies=[Depends(_verify_metrics_token)],
        )
    else:
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
