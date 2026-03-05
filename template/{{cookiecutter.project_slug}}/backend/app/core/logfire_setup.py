{%- if cookiecutter.enable_logfire %}
"""Logfire observability configuration."""

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


def instrument_app(app):
    """Instrument FastAPI app with Logfire."""
{%- if cookiecutter.logfire_fastapi %}
    logfire.instrument_fastapi(app)
{%- else %}
    pass
{%- endif %}


{%- if cookiecutter.use_postgresql and cookiecutter.logfire_database %}


def instrument_asyncpg():
    """Instrument asyncpg for PostgreSQL."""
    logfire.instrument_asyncpg()
{%- endif %}


{%- if cookiecutter.use_mongodb and cookiecutter.logfire_database %}


def instrument_pymongo():
    """Instrument PyMongo/Motor for MongoDB."""
    logfire.instrument_pymongo(capture_statement=settings.DEBUG)
{%- endif %}


{%- if cookiecutter.use_sqlite and cookiecutter.logfire_database %}


def instrument_sqlalchemy(engine):
    """Instrument SQLAlchemy for SQLite."""
    logfire.instrument_sqlalchemy(engine=engine)
{%- endif %}

{%- if cookiecutter.use_sqlserver and cookiecutter.logfire_database %}


def instrument_sqlalchemy(engine):
    """Instrument SQLAlchemy for SQL Server."""
    logfire.instrument_sqlalchemy(engine=engine)
{%- endif %}

{%- if cookiecutter.enable_redis and cookiecutter.logfire_redis %}


def instrument_redis():
    """Instrument Redis."""
    logfire.instrument_redis()
{%- endif %}


{%- if cookiecutter.use_celery and cookiecutter.logfire_celery %}


def instrument_celery():
    """Instrument Celery."""
    logfire.instrument_celery()
{%- endif %}


{%- if cookiecutter.logfire_httpx %}


def instrument_httpx():
    """Instrument HTTPX for outgoing HTTP requests."""
    logfire.instrument_httpx()
{%- endif %}


{%- if cookiecutter.enable_ai_agent and cookiecutter.use_pydantic_ai %}


def instrument_pydantic_ai():
    """Instrument PydanticAI for AI agent observability."""
    logfire.instrument_pydantic_ai()
{%- endif %}
{%- else %}
"""Logfire is disabled for this project."""


def setup_logfire() -> None:
    """No-op when Logfire is disabled."""
    pass


def instrument_app(app):
    """No-op when Logfire is disabled."""
    pass
{%- endif %}
