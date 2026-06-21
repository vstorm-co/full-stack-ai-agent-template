"""Repository layer for database operations."""
# ruff: noqa: I001, RUF022 - Imports structured for Jinja2 template conditionals
{%- if cookiecutter.use_jwt %}

from app.repositories import user as user_repo
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}

from app.repositories import session as session_repo
{%- endif %}
{%- if cookiecutter.use_ai %}

from app.repositories import conversation as conversation_repo
{%- endif %}
{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}

from app.repositories import webhook as webhook_repo
{%- endif %}
{%- if cookiecutter.enable_rag %}

from app.repositories import rag_document as rag_document_repo
from app.repositories import sync_log as sync_log_repo
from app.repositories import sync_source as sync_source_repo
{%- endif %}
{%- if cookiecutter.use_jwt %}

from app.repositories import chat_file as chat_file_repo
{%- endif %}
{%- if cookiecutter.use_ai and cookiecutter.use_jwt %}

from app.repositories import conversation_share as conversation_share_repo
from app.repositories import message_rating as message_rating_repo
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}

from app.repositories import knowledge_base as knowledge_base_repo
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}

from app.repositories import project as project_repo
{%- endif %}
{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}

from app.repositories import channel_bot as channel_bot_repo
from app.repositories import channel_identity as channel_identity_repo
from app.repositories import channel_session as channel_session_repo
{%- endif %}
{%- if cookiecutter.enable_teams %}

from app.repositories import invitation as invitation_repo
from app.repositories import member as member_repo
from app.repositories import organization as organization_repo
{%- endif %}
{%- if cookiecutter.use_auth and cookiecutter.use_ai %}

from app.repositories import user_slash_command as user_slash_command_repo
{%- endif %}

__all__ = [
{%- if cookiecutter.use_jwt %}
    "user_repo",
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
    "session_repo",
{%- endif %}
{%- if cookiecutter.use_ai %}
    "conversation_repo",
{%- endif %}
{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}
    "webhook_repo",
{%- endif %}
{%- if cookiecutter.enable_rag %}
    "rag_document_repo",
    "sync_log_repo",
    "sync_source_repo",
{%- endif %}
{%- if cookiecutter.use_jwt %}
    "chat_file_repo",
{%- endif %}
{%- if cookiecutter.use_ai and cookiecutter.use_jwt %}
    "conversation_share_repo",
    "message_rating_repo",
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
    "knowledge_base_repo",
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    "project_repo",
{%- endif %}
{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
    "channel_bot_repo",
    "channel_identity_repo",
    "channel_session_repo",
{%- endif %}
{%- if cookiecutter.enable_teams %}
    "organization_repo",
    "member_repo",
    "invitation_repo",
{%- endif %}
{%- if cookiecutter.use_auth and cookiecutter.use_ai %}
    "user_slash_command_repo",
{%- endif %}
]
