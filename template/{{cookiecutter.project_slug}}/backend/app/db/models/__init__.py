"""Database models."""
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
# ruff: noqa: I001, RUF022 - Imports structured for Jinja2 template conditionals
{%- endif %}
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
{%- set models = [] %}
{%- if cookiecutter.use_jwt %}
{%- set _ = models.append("User") %}
from app.db.models.user import User
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
{%- set _ = models.append("Session") %}
from app.db.models.session import Session
{%- endif %}
{%- if cookiecutter.include_example_crud %}
{%- set _ = models.append("Item") %}
from app.db.models.item import Item
{%- endif %}
{%- if cookiecutter.enable_conversation_persistence %}
{%- set _ = models.extend(["Conversation", "Message", "ToolCall"]) %}
from app.db.models.conversation import Conversation, Message, ToolCall
{%- endif %}
{%- if cookiecutter.enable_webhooks %}
{%- set _ = models.extend(["Webhook", "WebhookDelivery"]) %}
from app.db.models.webhook import Webhook, WebhookDelivery
{%- endif %}
{%- if cookiecutter.enable_conversation_persistence and cookiecutter.enable_ai_agent %}
{%- set _ = models.append("ChatFile") %}
from app.db.models.chat_file import ChatFile
{%- endif %}
{%- if models %}

__all__ = {{ models }}
{%- endif %}
{%- endif %}
