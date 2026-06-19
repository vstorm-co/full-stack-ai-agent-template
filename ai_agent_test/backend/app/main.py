"""FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TypedDict

logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi_pagination import add_pagination

from app.api.exception_handlers import register_exception_handlers
from app.api.router import api_router
from app.clients.redis import RedisClient
from app.core.config import settings
from app.core.logfire_setup import instrument_app, setup_logfire
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.vectorstore import BaseVectorStore, MilvusVectorStore


class LifespanState(TypedDict, total=False):
    """Lifespan state - resources available via request.state."""

    redis: RedisClient
    embedding_service: EmbeddingService
    vector_store: BaseVectorStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[LifespanState, None]:
    """Application lifespan - startup and shutdown events.

    Resources yielded here are available via request.state in route handlers.
    See: https://asgi.readthedocs.io/en/latest/specs/lifespan.html#lifespan-state
    """
    # === Startup ===
    state: LifespanState = {}
    setup_logfire()
    from app.core.logfire_setup import instrument_asyncpg

    instrument_asyncpg()
    from app.core.logfire_setup import instrument_redis

    instrument_redis()
    from app.core.logfire_setup import instrument_httpx

    instrument_httpx()
    from app.core.logfire_setup import instrument_pydantic_ai

    instrument_pydantic_ai()
    redis_client = RedisClient()
    await redis_client.connect()
    state["redis"] = redis_client

    if settings.ENABLE_DEEP_RESEARCH:
        from app.db.todo_pool import init_todo_pool

        await init_todo_pool()
    from app.core.cache import setup_cache

    setup_cache(redis_client)

    try:
        embedder = EmbeddingService(settings=settings.rag)
        embedder.warmup()
        state["embedding_service"] = embedder
    except Exception as e:
        logger.error(f"Embedding service warmup failed: {e}. RAG will not be available.")
    # Warmup Milvus and verify health
    if "embedding_service" in state:
        try:
            vector_store = MilvusVectorStore(settings=settings.rag, embedding_service=embedder)
            await vector_store.client.list_collections()
            state["vector_store"] = vector_store
        except Exception as e:
            logger.error(f"Milvus connection failed: {e}. Vector store will not be available.")

    # === Telegram Channel Polling ===
    from app.core.channel_crypto import decrypt_token
    from app.services.channels import register_adapter
    from app.services.channels.telegram import TelegramAdapter

    _telegram_adapter = TelegramAdapter()
    register_adapter(_telegram_adapter)
    try:
        from app.db.session import get_db_context

        async with get_db_context() as _db:
            from app.repositories.channel_bot import get_active_polling_bots

            _polling_bots = await get_active_polling_bots(_db, "telegram")
        for _bot in _polling_bots:
            _token = decrypt_token(_bot.token_encrypted)
            await _telegram_adapter.start_polling(str(_bot.id), _token)
        logger.info("Telegram: polling started for %d bot(s)", len(_polling_bots))
    except Exception as _exc:
        logger.error("Telegram: failed to start polling: %s", _exc)

    # === Slack Adapter (Socket Mode polling for dev, Events API for prod) ===
    from app.core.channel_crypto import decrypt_token as _slack_decrypt
    from app.services.channels import register_adapter as _slack_register
    from app.services.channels.slack import SlackAdapter

    _slack_adapter = SlackAdapter()
    _slack_register(_slack_adapter)
    try:
        from app.db.session import get_db_context

        async with get_db_context() as _slack_db:
            from app.repositories.channel_bot import get_active_polling_bots

            _slack_bots = await get_active_polling_bots(_slack_db, "slack")
        for _sbot in _slack_bots:
            _stoken = _slack_decrypt(_sbot.token_encrypted)
            await _slack_adapter.start_polling(str(_sbot.id), _stoken)
        logger.info("Slack: Socket Mode started for %d bot(s)", len(_slack_bots))
    except Exception as _slack_exc:
        logger.error("Slack: failed to start Socket Mode: %s", _slack_exc)
    yield state

    # === Shutdown ===
    if settings.ENABLE_DEEP_RESEARCH:
        from app.db.todo_pool import close_todo_pool

        await close_todo_pool()
    if "redis" in state:
        await state["redis"].close()
    from app.db.session import close_db

    await close_db()
    try:
        if "vector_store" in state:
            await state["vector_store"].client.close()  # type: ignore[attr-defined]
    except Exception:
        pass
    for _bid in list(_telegram_adapter._polling_tasks.keys()):
        await _telegram_adapter.stop_polling(_bid)
    for _sbid in list(_slack_adapter._socket_tasks.keys()):
        await _slack_adapter.stop_polling(_sbid)


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
        {
            "name": "auth",
            "description": "Authentication endpoints - login, register, token refresh",
        },
        {
            "name": "users",
            "description": "User management endpoints",
        },
        {
            "name": "oauth",
            "description": "OAuth2 social login endpoints (Google, etc.)",
        },
        {
            "name": "sessions",
            "description": "Session management - view and manage active login sessions",
        },
        {
            "name": "conversations",
            "description": "AI conversation persistence - manage chat history",
        },
        {
            "name": "agent",
            "description": "AI agent WebSocket endpoint for real-time chat",
        },
        {
            "name": "rag",
            "description": "Retrieval Augmented Generation endpoints",
        },
    ]

    # PII redaction in logs (GDPR/compliance)
    setup_logging()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        summary="FastAPI application with Logfire observability",
        description="""
My FastAPI project

## Features
- **Authentication**: JWT-based authentication with refresh tokens
- **API Key**: Header-based API key authentication
- **Database**: Async database operations
- **Redis**: Caching and session storage
- **Rate Limiting**: Request rate limiting per client
- **AI Agent**: PydanticAI-powered conversational assistant
- **Observability**: Logfire integration for tracing and monitoring
- **RAG**: Retrieval Augmented Generation with Milvus and LangChain

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
            "name": "Your Name",
            "email": "your@email.com",
        },
        license_info={
            "name": "MIT",
            "identifier": "MIT",
        },
        lifespan=lifespan,
    )
    # Logfire instrumentation. setup_logfire() is also called from the lifespan
    # for the runtime app, but we call it here too so that import-time test
    # clients (which never run lifespan) silence the "configure first" warning.
    setup_logfire()
    instrument_app(app)

    # Request ID middleware (for request correlation/debugging)
    app.add_middleware(RequestIDMiddleware)

    # Exception handlers
    register_exception_handlers(app)

    # CORS middleware
    from starlette.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Rate limiting
    # Note: slowapi requires app.state.limiter - this is a library requirement,
    # not suitable for lifespan state pattern which is for request-scoped access
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    from app.core.rate_limit import limiter

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Session middleware (for admin authentication and/or OAuth)
    from starlette.middleware.sessions import SessionMiddleware

    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

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

    # Pagination
    add_pagination(app)

    return app


app = create_app()
