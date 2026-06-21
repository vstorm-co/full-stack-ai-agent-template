"""Pydantic schemas."""
{%- set schemas = [] %}
{%- if cookiecutter.use_jwt or cookiecutter.enable_webhooks %}
# ruff: noqa: I001, RUF022 - Imports structured for Jinja2 template conditionals
{%- endif %}
{%- if cookiecutter.use_jwt %}
{%- set _ = schemas.extend(["UserCreate", "UserRead", "UserUpdate", "Token", "TokenPayload"]) %}

from app.schemas.token import Token, TokenPayload
from app.schemas.user import UserCreate, UserRead, UserUpdate
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
{%- set _ = schemas.extend(["SessionRead", "SessionListResponse", "LogoutAllResponse"]) %}

from app.schemas.session import SessionRead, SessionListResponse, LogoutAllResponse
{%- endif %}
{%- if cookiecutter.use_ai %}
{%- set _ = schemas.extend(["ConversationCreate", "ConversationRead", "ConversationUpdate", "MessageCreate", "MessageRead", "ToolCallRead"]) %}

from app.schemas.conversation import (
    ConversationCreate,
    ConversationRead,
    ConversationUpdate,
    MessageCreate,
    MessageRead,
    ToolCallRead,
)
{%- endif %}
{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}
{%- set _ = schemas.extend(["WebhookCreate", "WebhookRead", "WebhookUpdate", "WebhookDeliveryRead", "WebhookListResponse", "WebhookDeliveryListResponse", "WebhookTestResponse"]) %}

from app.schemas.webhook import (
    WebhookCreate,
    WebhookRead,
    WebhookUpdate,
    WebhookDeliveryRead,
    WebhookListResponse,
    WebhookDeliveryListResponse,
    WebhookTestResponse,
)
{%- endif %}
{%- if cookiecutter.enable_rag %}
{%- set _ = schemas.extend(["SyncSourceCreate", "SyncSourceRead", "SyncSourceUpdate", "SyncSourceList", "ConnectorInfo", "ConnectorList", "ConnectorConfigField"]) %}

from app.schemas.sync_source import (
    ConnectorConfigField,
    ConnectorInfo,
    ConnectorList,
    SyncSourceCreate,
    SyncSourceList,
    SyncSourceRead,
    SyncSourceUpdate,
)
{%- endif %}
{%- if schemas %}

__all__ = {{ schemas }}
{%- endif %}
