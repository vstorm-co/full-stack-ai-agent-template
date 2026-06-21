"""Database models."""
# ruff: noqa: I001, RUF022 - Imports structured for Jinja2 template conditionals
{%- set models = [] %}
{%- if cookiecutter.use_jwt %}
{%- set _ = models.append("User") %}
from app.db.models.user import User
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
{%- set _ = models.append("Session") %}
from app.db.models.session import Session
{%- endif %}
{%- if cookiecutter.use_ai %}
{%- set _ = models.extend(["Conversation", "Message", "ToolCall"]) %}
from app.db.models.conversation import Conversation, Message, ToolCall
{%- endif %}
{%- if cookiecutter.enable_webhooks %}
{%- set _ = models.extend(["Webhook", "WebhookDelivery"]) %}
from app.db.models.webhook import Webhook, WebhookDelivery
{%- endif %}
{%- set _ = models.append("ChatFile") %}
from app.db.models.chat_file import ChatFile
{%- if cookiecutter.use_jwt and cookiecutter.use_ai %}
{%- set _ = models.append("MessageRating") %}
from app.db.models.message_rating import MessageRating
{%- endif %}
{%- if cookiecutter.enable_rag %}
{%- set _ = models.append("RAGDocument") %}
from app.db.models.rag_document import RAGDocument
{%- set _ = models.append("SyncLog") %}
from app.db.models.sync_log import SyncLog
{%- set _ = models.append("SyncSource") %}
from app.db.models.sync_source import SyncSource
{%- endif %}
{%- if cookiecutter.use_jwt and cookiecutter.use_ai %}
{%- set _ = models.append("ConversationShare") %}
from app.db.models.conversation_share import ConversationShare
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
{%- set _ = models.extend(["Project", "ProjectMember"]) %}
from app.db.models.project import Project, ProjectMember
{%- endif %}
{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
{%- set _ = models.extend(["ChannelBot", "ChannelIdentity", "ChannelSession"]) %}
from app.db.models.channel_bot import ChannelBot
from app.db.models.channel_identity import ChannelIdentity
from app.db.models.channel_session import ChannelSession
{%- endif %}
{%- if cookiecutter.enable_teams %}
{%- set _ = models.extend(["Organization", "OrganizationMember", "Invitation", "AppAdminAuditLog"]) %}
from app.db.models.organization import Invitation, Organization, OrganizationMember
from app.db.models.audit_log import AppAdminAuditLog
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
{%- set _ = models.append("KnowledgeBase") %}
from app.db.models.knowledge_base import KnowledgeBase
{%- endif %}
{%- if cookiecutter.use_auth and cookiecutter.use_ai %}
{%- set _ = models.append("UserSlashCommand") %}
from app.db.models.user_slash_command import UserSlashCommand
{%- endif %}
{%- if models %}

__all__ = {{ models }}
{%- endif %}
