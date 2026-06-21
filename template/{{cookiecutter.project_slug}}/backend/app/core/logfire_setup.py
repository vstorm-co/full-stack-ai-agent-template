{%- if cookiecutter.enable_logfire %}
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
{%- if cookiecutter.logfire_fastapi %}
    logfire.instrument_fastapi(app)
{%- else %}
    pass
{%- endif %}


{%- if cookiecutter.logfire_database %}


def instrument_asyncpg() -> None:
    """Instrument asyncpg for PostgreSQL."""
    logfire.instrument_asyncpg()
{%- endif %}


{%- if cookiecutter.enable_redis and cookiecutter.logfire_redis %}


def instrument_redis() -> None:
    """Instrument Redis."""
    logfire.instrument_redis()
{%- endif %}


{%- if cookiecutter.use_celery and cookiecutter.logfire_celery %}


def instrument_celery() -> None:
    """Instrument Celery."""
    logfire.instrument_celery()
{%- endif %}


{%- if cookiecutter.logfire_httpx %}


def instrument_httpx() -> None:
    """Instrument HTTPX for outgoing HTTP requests."""
    logfire.instrument_httpx()
{%- endif %}


{%- if cookiecutter.use_pydantic_ai %}


def instrument_pydantic_ai() -> None:
    """Instrument PydanticAI for AI agent observability."""
    logfire.instrument_pydantic_ai()
{%- endif %}
{%- else %}
"""Logfire is disabled for this project."""


def setup_logfire() -> None:
    """No-op when Logfire is disabled."""
    pass


def instrument_app(app: object) -> None:
    """No-op when Logfire is disabled."""
    pass
{%- endif %}
