"""create core tables (conversations, messages, chat_files, sessions, rag, channels)

Revision ID: 0004_5_core_tables
Revises: 0004_audit_log
Create Date: {{ cookiecutter.generated_at }}

Creates the core conversational, RAG, channel, and session tables that
later migrations modify (0005, 0006, 0007, 0009). Splits feature-flagged
groups so the schema only contains what was selected at generation time.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0004_5_core_tables"
down_revision = "0004_audit_log"
branch_labels = None
depends_on = None


def _id_col() -> sa.Column:
    return sa.Column(
        "id",
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _user_fk(*, nullable: bool, ondelete: str = "CASCADE") -> sa.Column:
    return sa.Column(
        "user_id",
        PG_UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete=ondelete),
        nullable=nullable,
    )


_UUID = PG_UUID(as_uuid=True)
_JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "conversations",
        _id_col(),
        _user_fk(nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "messages",
        _id_col(),
        sa.Column("conversation_id", _UUID, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    op.create_table(
        "tool_calls",
        _id_col(),
        sa.Column("message_id", _UUID, sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_call_id", sa.String(100), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("args", _JSONB, nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.create_index("ix_tool_calls_message_id", "tool_calls", ["message_id"])

    op.create_table(
        "chat_files",
        _id_col(),
        _user_fk(nullable=False),
        sa.Column("message_id", _UUID, sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("parsed_content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_chat_files_user_id", "chat_files", ["user_id"])
{%- if cookiecutter.use_jwt %}

    op.create_table(
        "conversation_shares",
        _id_col(),
        sa.Column("conversation_id", _UUID, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shared_by", _UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shared_with", _UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("share_token", sa.String(64), nullable=True, unique=True),
        sa.Column("permission", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("conversation_id", "shared_with", name="uq_share_conv_user"),
    )
    op.create_index("ix_conversation_shares_conversation_id", "conversation_shares", ["conversation_id"])
    op.create_index("ix_conversation_shares_shared_with", "conversation_shares", ["shared_with"])

    op.create_table(
        "message_ratings",
        _id_col(),
        sa.Column("message_id", _UUID, sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        _user_fk(nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("rating IN (1, -1)", name="message_ratings_ck_rating_value_check"),
        sa.UniqueConstraint("message_id", "user_id", name="uq_message_user_rating"),
    )
    op.create_index("ix_message_ratings_message_id", "message_ratings", ["message_id"])
    op.create_index("ix_message_ratings_user_id", "message_ratings", ["user_id"])
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}

    op.create_table(
        "sessions",
        _id_col(),
        _user_fk(nullable=False),
        sa.Column("refresh_token_hash", sa.String(255), nullable=False),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("device_type", sa.String(50), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_refresh_token_hash", "sessions", ["refresh_token_hash"])
{%- endif %}
{%- if cookiecutter.enable_rag %}

    op.create_table(
        "rag_documents",
        _id_col(),
        sa.Column("collection_name", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("filesize", sa.Integer(), nullable=False),
        sa.Column("filetype", sa.String(20), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("vector_document_id", sa.String(255), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_rag_documents_collection_name", "rag_documents", ["collection_name"])

    op.create_table(
        "sync_sources",
        _id_col(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("connector_type", sa.String(20), nullable=False),
        sa.Column("collection_name", sa.String(255), nullable=False),
        sa.Column("config", _JSONB, server_default="{}", nullable=False),
        sa.Column("sync_mode", sa.String(20), nullable=False),
        sa.Column("schedule_minutes", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(20), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sync_sources_collection_name", "sync_sources", ["collection_name"])

    op.create_table(
        "sync_logs",
        _id_col(),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("collection_name", sa.String(255), nullable=False),
        sa.Column("sync_source_id", _UUID, sa.ForeignKey("sync_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sync_logs_collection_name", "sync_logs", ["collection_name"])
{%- endif %}
{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}

    op.create_table(
        "channel_bots",
        _id_col(),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("token_encrypted", sa.String(1000), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("webhook_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("webhook_url", sa.String(500), nullable=True),
        sa.Column("webhook_secret", sa.String(255), nullable=True),
        sa.Column("access_policy", sa.JSON(), nullable=False),
        sa.Column("ai_model_override", sa.String(255), nullable=True),
        sa.Column("system_prompt_override", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_channel_bots_platform", "channel_bots", ["platform"])

    op.create_table(
        "channel_identities",
        _id_col(),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("platform_user_id", sa.String(100), nullable=False),
        sa.Column("platform_username", sa.String(100), nullable=True),
        sa.Column("platform_display_name", sa.String(255), nullable=True),
        _user_fk(nullable=True, ondelete="SET NULL"),
        sa.Column("link_code", sa.String(10), nullable=True),
        sa.Column("link_code_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("platform", "platform_user_id", name="uq_channel_identity_platform_user"),
    )
    op.create_index("ix_channel_identities_platform", "channel_identities", ["platform"])
    op.create_index("ix_channel_identities_platform_user_id", "channel_identities", ["platform_user_id"])
    op.create_index("ix_channel_identities_user_id", "channel_identities", ["user_id"])

    op.create_table(
        "channel_sessions",
        _id_col(),
        sa.Column("bot_id", _UUID, sa.ForeignKey("channel_bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identity_id", _UUID, sa.ForeignKey("channel_identities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", _UUID, sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("platform_chat_id", sa.String(100), nullable=False),
        sa.Column("chat_type", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("bot_id", "platform_chat_id", name="uq_channel_session_bot_chat"),
    )
    op.create_index("ix_channel_sessions_bot_id", "channel_sessions", ["bot_id"])
    op.create_index("ix_channel_sessions_identity_id", "channel_sessions", ["identity_id"])
    op.create_index("ix_channel_sessions_conversation_id", "channel_sessions", ["conversation_id"])
    op.create_index("ix_channel_sessions_platform_chat_id", "channel_sessions", ["platform_chat_id"])
{%- endif %}


def downgrade() -> None:
{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
    op.drop_table("channel_sessions")
    op.drop_table("channel_identities")
    op.drop_table("channel_bots")
{%- endif %}
{%- if cookiecutter.enable_rag %}
    op.drop_table("sync_logs")
    op.drop_table("sync_sources")
    op.drop_table("rag_documents")
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
    op.drop_table("sessions")
{%- endif %}
{%- if cookiecutter.use_jwt %}
    op.drop_table("message_ratings")
    op.drop_table("conversation_shares")
{%- endif %}
    op.drop_table("chat_files")
    op.drop_table("tool_calls")
    op.drop_table("messages")
    op.drop_table("conversations")


