# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""FastAPI application entry point."""

import logging
import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
{%- if cookiecutter.enable_redis or cookiecutter.enable_rag or cookiecutter.use_telegram or cookiecutter.use_slack %}
from typing import {% if cookiecutter.use_telegram or cookiecutter.use_slack %}Any, {% endif %}TypedDict
{%- endif %}

from fastapi import FastAPI
{%- if cookiecutter.enable_prometheus %}
from fastapi import Depends, Header, HTTPException, status as http_status
{%- endif %}
{%- if cookiecutter.enable_pagination %}
from fastapi_pagination import add_pagination
{%- endif %}
{%- if cookiecutter.enable_cors %}
from starlette.middleware.cors import CORSMiddleware
{%- endif %}
{%- if (cookiecutter.enable_admin_panel and cookiecutter.admin_require_auth and not cookiecutter.admin_env_disabled) or cookiecutter.enable_oauth %}
from starlette.middleware.sessions import SessionMiddleware
{%- endif %}

from app.api.exception_handlers import register_exception_handlers
from app.api.router import api_router
from app.core.config import settings
from app.db.session import close_db, get_db_context
{%- if cookiecutter.enable_logfire %}
from app.core.logfire_setup import instrument_app, setup_logfire
{%- if cookiecutter.logfire_database %}
from app.core.logfire_setup import instrument_asyncpg
{%- endif %}
{%- if cookiecutter.enable_redis and cookiecutter.logfire_redis %}
from app.core.logfire_setup import instrument_redis
{%- endif %}
{%- if cookiecutter.logfire_httpx %}
from app.core.logfire_setup import instrument_httpx
{%- endif %}
{%- if cookiecutter.use_pydantic_ai %}
from app.core.logfire_setup import instrument_pydantic_ai
{%- endif %}
{%- endif %}
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware

{%- if cookiecutter.enable_deep_research %}
from app.db.todo_pool import close_todo_pool, init_todo_pool
{%- endif %}
{%- if cookiecutter.enable_caching and cookiecutter.enable_redis %}
from app.core.cache import setup_cache
{%- endif %}
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
{%- if cookiecutter.enable_reranker %}
from app.services.rag.reranker import RerankService
{%- endif %}
{%- endif %}
{%- endif %}
{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
from app.repositories.channel_bot import get_active_polling_bots
{%- endif %}
{%- if cookiecutter.use_telegram %}
from app.core.channel_crypto import decrypt_token
from app.services.channels import register_adapter
from app.services.channels.telegram import TelegramAdapter
{%- endif %}
{%- if cookiecutter.use_slack %}
from app.core.channel_crypto import decrypt_token as _slack_decrypt
from app.services.channels import register_adapter as _slack_register
from app.services.channels.slack import SlackAdapter
{%- endif %}
{%- if cookiecutter.enable_seed_admin %}
from app.repositories import user_repo
{%- endif %}
{%- if cookiecutter.enable_admin_panel and not cookiecutter.admin_env_disabled %}
from app.admin import setup_admin
{%- endif %}
{%- if cookiecutter.enable_rate_limiting %}
from app.core.rate_limit import limiter
{%- endif %}

logger = logging.getLogger(__name__)

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


{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
async def _start_channel_polling(adapter: Any, channel: str, decrypt_fn: Any) -> None:
    """Start polling for all active bots of the given channel type."""
    async with get_db_context() as _db:
        _bots = await get_active_polling_bots(_db, channel)
    for _bot in _bots:
        _token = decrypt_fn(_bot.token_encrypted)
        await adapter.start_polling(str(_bot.id), _token)
    logger.info("%s: polling started for %d bot(s)", channel.capitalize(), len(_bots))
{%- endif %}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[{% if cookiecutter.enable_redis or cookiecutter.enable_rag or cookiecutter.use_telegram or cookiecutter.use_slack %}LifespanState{% else %}None{% endif %}, None]:
    """Application lifespan - startup and shutdown events.

    Resources yielded here are available via request.state in route handlers.
    See: https://asgi.readthedocs.io/en/latest/specs/lifespan.html#lifespan-state
    """
{%- if cookiecutter.enable_redis or cookiecutter.enable_rag or cookiecutter.use_telegram or cookiecutter.use_slack %}
    state: LifespanState = {}
{%- endif %}
{%- if cookiecutter.enable_logfire %}
    setup_logfire()
{%- endif %}

{%- if cookiecutter.enable_logfire and cookiecutter.logfire_database %}
    instrument_asyncpg()
{%- endif %}

{%- if cookiecutter.enable_redis and cookiecutter.enable_logfire and cookiecutter.logfire_redis %}
    instrument_redis()
{%- endif %}

{%- if cookiecutter.enable_logfire and cookiecutter.logfire_httpx %}
    instrument_httpx()
{%- endif %}

{%- if cookiecutter.enable_logfire and cookiecutter.use_pydantic_ai %}
    instrument_pydantic_ai()
{%- endif %}

{%- if cookiecutter.enable_redis %}
    redis_client = RedisClient()
    await redis_client.connect()
    state["redis"] = redis_client
{%- endif %}
{%- if cookiecutter.enable_deep_research %}

    if settings.ENABLE_DEEP_RESEARCH:
        await init_todo_pool()
{%- endif %}

{%- if cookiecutter.enable_caching and cookiecutter.enable_redis %}
    setup_cache(redis_client)
{%- endif %}

{%- if cookiecutter.enable_rag %}
    embedder: EmbeddingService | None = None
    try:
        embedder = EmbeddingService(settings=settings.rag)
        embedder.warmup()
        state["embedding_service"] = embedder
    except Exception as e:
        logger.error("Embedding service warmup failed: %s. RAG will not be available.", e)

{%- if cookiecutter.enable_reranker %}
    # Initialize and warmup reranker (downloads model or validates API key)
    try:
        rerank_service = RerankService(settings=settings.rag)
        rerank_service.warmup()
        state["rerank_service"] = rerank_service
    except Exception as e:
        logger.warning("Reranker warmup failed: %s. Reranking will be disabled.", e)
{%- endif %}

{%- if cookiecutter.use_milvus %}
    if embedder is not None:
        try:
            vector_store = MilvusVectorStore(settings=settings.rag, embedding_service=embedder)
            await vector_store.client.list_collections()
            state["vector_store"] = vector_store
        except Exception as e:
            logger.error("Milvus connection failed: %s. Vector store will not be available.", e)
{%- endif %}
{%- if cookiecutter.use_qdrant %}
    if embedder is not None:
        try:
            vector_store = QdrantVectorStore(settings=settings.rag, embedding_service=embedder)
            state["vector_store"] = vector_store
        except Exception as e:
            logger.error("Qdrant connection failed: %s. Vector store will not be available.", e)
{%- endif %}
{%- if cookiecutter.use_chromadb %}
    if embedder is not None:
        try:
            vector_store = ChromaVectorStore(settings=settings.rag, embedding_service=embedder)
            state["vector_store"] = vector_store
        except Exception as e:
            logger.error("ChromaDB init failed: %s. Vector store will not be available.", e)
{%- endif %}
{%- if cookiecutter.use_pgvector %}
    if embedder is not None:
        try:
            vector_store = PgVectorStore(settings=settings.rag, embedding_service=embedder)
            state["vector_store"] = vector_store
        except Exception as e:
            logger.error("pgvector connection failed: %s. Vector store will not be available.", e)
{%- endif %}
{%- endif %}

{%- if cookiecutter.use_telegram %}

    _telegram_adapter = TelegramAdapter()
    register_adapter(_telegram_adapter)
    try:
        await _start_channel_polling(_telegram_adapter, "telegram", decrypt_token)
    except (OSError, ValueError, RuntimeError) as _exc:
        logger.error("Telegram: failed to start polling: %s", _exc)
{%- endif %}

{%- if cookiecutter.use_slack %}

    _slack_adapter = SlackAdapter()
    _slack_register(_slack_adapter)
    try:
        await _start_channel_polling(_slack_adapter, "slack", _slack_decrypt)
    except (OSError, ValueError, RuntimeError) as _slack_exc:
        logger.error("Slack: failed to start Socket Mode: %s", _slack_exc)
{%- endif %}

{%- if cookiecutter.enable_seed_admin %}
    _first_admin = getattr(settings, "FIRST_ADMIN_EMAIL", "")
    if _first_admin:
        try:
            async with get_db_context() as _db:
                _u = await user_repo.get_by_email(_db, _first_admin)
                if _u and not getattr(_u, "is_app_admin", False):
                    _u.is_app_admin = True
                    await _db.flush()
                    logger.info("Auto-promoted %s to app-admin (FIRST_ADMIN_EMAIL)", _first_admin)
        except Exception as _e:
            logger.warning("FIRST_ADMIN_EMAIL promotion failed: %s", _e)
{%- endif %}

{%- if cookiecutter.enable_redis or cookiecutter.enable_rag or cookiecutter.use_telegram or cookiecutter.use_slack %}
    yield state
{%- else %}
    yield
{%- endif %}

{%- if cookiecutter.enable_rag %}
{%- if cookiecutter.use_milvus or cookiecutter.use_qdrant %}
    if "vector_store" in state:
        with suppress(Exception):
            await state["vector_store"].client.close()  # type: ignore[attr-defined]
{%- endif %}
{%- if cookiecutter.use_pgvector %}
    if "vector_store" in state:
        with suppress(Exception):
            await state["vector_store"].engine.dispose()  # type: ignore[attr-defined]
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

{%- if cookiecutter.enable_deep_research %}
    if settings.ENABLE_DEEP_RESEARCH:
        await close_todo_pool()
{%- endif %}
{%- if cookiecutter.enable_redis %}
    if "redis" in state:
        await state["redis"].close()
{%- endif %}

    await close_db()


SHOW_DOCS_ENVIRONMENTS = ("local", "staging", "development")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    show_docs = settings.ENVIRONMENT in SHOW_DOCS_ENVIRONMENTS
    openapi_url = f"{settings.API_V1_STR}/openapi.json" if show_docs else None
    docs_url = "/docs" if show_docs else None
    redoc_url = "/redoc" if show_docs else None

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
    # setup_logfire() is also called from the lifespan for the runtime app, but
    # we call it here too so that import-time test clients (which never run
    # lifespan) silence the "configure first" warning. setup_logfire() is
    # idempotent via a module-level guard in logfire_setup.py.
    setup_logfire()
    instrument_app(app)
{%- endif %}

    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)

{%- if cookiecutter.enable_cors %}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
{%- endif %}

{%- if cookiecutter.enable_sentry %}

    if settings.SENTRY_DSN:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.SENTRY_DSN, enable_tracing=True)
{%- endif %}

{%- if cookiecutter.enable_prometheus %}

    from prometheus_fastapi_instrumentator import Instrumentator

    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/health/ready", "/health/live", settings.PROMETHEUS_METRICS_PATH],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )
    instrumentator.instrument(app)
    # Optional Bearer-token guard so the metrics endpoint can be exposed on a
    # public ingress without leaking internals. When PROMETHEUS_AUTH_TOKEN is
    # empty the endpoint is unauthenticated (typical for private networks).
    if settings.PROMETHEUS_AUTH_TOKEN:
        def _verify_metrics_token(authorization: str = Header(default="")) -> None:
            expected = f"Bearer {settings.PROMETHEUS_AUTH_TOKEN}"
            if not secrets.compare_digest(authorization, expected):
                raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED)

        instrumentator.expose(
            app,
            endpoint=settings.PROMETHEUS_METRICS_PATH,
            include_in_schema=settings.PROMETHEUS_INCLUDE_IN_SCHEMA,
            dependencies=[Depends(_verify_metrics_token)],
        )
    else:
        instrumentator.expose(
            app,
            endpoint=settings.PROMETHEUS_METRICS_PATH,
            include_in_schema=settings.PROMETHEUS_INCLUDE_IN_SCHEMA,
        )
{%- endif %}

{%- if cookiecutter.enable_rate_limiting %}

    # slowapi requires app.state.limiter, not lifespan state (library constraint)
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
{%- endif %}

{%- if (cookiecutter.enable_admin_panel and cookiecutter.admin_require_auth and not cookiecutter.admin_env_disabled) or cookiecutter.enable_oauth %}

    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
{%- endif %}

{%- if cookiecutter.enable_admin_panel %}
{%- if cookiecutter.admin_env_disabled %}
{%- elif cookiecutter.admin_env_all %}
    setup_admin(app)
{%- else %}

    {%- if cookiecutter.admin_env_dev_only %}
    ADMIN_ALLOWED_ENVIRONMENTS = ["development", "local"]
    {%- elif cookiecutter.admin_env_dev_staging %}
    ADMIN_ALLOWED_ENVIRONMENTS = ["development", "local", "staging"]
    {%- endif %}

    if settings.ENVIRONMENT in ADMIN_ALLOWED_ENVIRONMENTS:
        setup_admin(app)
{%- endif %}
{%- endif %}

    app.include_router(api_router, prefix=settings.API_V1_STR)

{%- if cookiecutter.enable_pagination %}

    add_pagination(app)
{%- endif %}

    return app


app = create_app()
