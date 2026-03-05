{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite or cookiecutter.use_sqlserver %}
"""Alembic migration environment."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlserver %}
import asyncio
{%- endif %}
from logging.config import fileConfig

from alembic import context
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlserver %}
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
{%- else %}
from sqlalchemy import engine_from_config, pool
{%- endif %}
{%- if cookiecutter.use_sqlmodel %}
from sqlmodel import SQLModel
{%- endif %}

from app.core.config import settings
{%- if not cookiecutter.use_sqlmodel %}
from app.db.base import Base
{%- endif %}

# Import all models here to ensure they are registered with metadata
{%- if cookiecutter.use_jwt %}
from app.db.models.user import User  # noqa: F401
{%- endif %}

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

{%- if cookiecutter.use_sqlmodel %}
target_metadata = SQLModel.metadata
{%- else %}
target_metadata = Base.metadata
{%- endif %}


def get_url() -> str:
    """Get database URL from settings."""
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlserver %}
async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection) -> None:
    """Run migrations with sync connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())
{%- else %}
def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()
{%- endif %}


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
{%- else %}
# Alembic - not configured (no SQL database)
{%- endif %}
