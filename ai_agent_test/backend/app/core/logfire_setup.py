"""Logfire observability configuration."""

from typing import Any

import logfire

from app.core.config import settings


def setup_logfire() -> None:
    """Configure Logfire instrumentation."""
    logfire.configure(
        token=settings.LOGFIRE_TOKEN,
        service_name=settings.LOGFIRE_SERVICE_NAME,
        environment=settings.LOGFIRE_ENVIRONMENT,
        send_to_logfire="if-token-present",
    )


def instrument_app(app: Any) -> None:
    """Instrument FastAPI app with Logfire."""
    logfire.instrument_fastapi(app)


def instrument_asyncpg() -> None:
    """Instrument asyncpg for PostgreSQL."""
    logfire.instrument_asyncpg()


def instrument_redis() -> None:
    """Instrument Redis."""
    logfire.instrument_redis()


def instrument_celery() -> None:
    """Instrument Celery."""
    logfire.instrument_celery()


def instrument_httpx() -> None:
    """Instrument HTTPX for outgoing HTTP requests."""
    logfire.instrument_httpx()


def instrument_pydantic_ai() -> None:
    """Instrument PydanticAI for AI agent observability."""
    logfire.instrument_pydantic_ai()
