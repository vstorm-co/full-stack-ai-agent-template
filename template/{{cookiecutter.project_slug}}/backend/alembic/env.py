"""Alembic migration environment."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
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
from app.db.models.conversation import Conversation, Message, ToolCall  # noqa: F401
{%- if cookiecutter.use_jwt %}
from app.db.models.message_rating import MessageRating  # noqa: F401
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
from app.db.models.session import Session  # noqa: F401
{%- endif %}
{%- if cookiecutter.enable_webhooks %}
from app.db.models.webhook import Webhook, WebhookDelivery  # noqa: F401
{%- endif %}
from app.db.models.chat_file import ChatFile  # noqa: F401
{%- if cookiecutter.enable_rag %}
from app.db.models.rag_document import RAGDocument  # noqa: F401
from app.db.models.sync_log import SyncLog  # noqa: F401
from app.db.models.sync_source import SyncSource  # noqa: F401
{%- endif %}
{%- if cookiecutter.enable_teams %}
from app.db.models.organization import Invitation, Organization, OrganizationMember  # noqa: F401
from app.db.models.audit_log import AppAdminAuditLog  # noqa: F401
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
from app.db.models.knowledge_base import KnowledgeBase  # noqa: F401
{%- endif %}

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

{%- if cookiecutter.use_sqlmodel %}
target_metadata = SQLModel.metadata
{%- else %}
target_metadata = Base.metadata
{%- endif %}


# Ensure SQLite data directory exists before connecting


def get_url() -> str:
    """Get database URL from settings."""
    return settings.DATABASE_URL_SYNC


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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
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


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
