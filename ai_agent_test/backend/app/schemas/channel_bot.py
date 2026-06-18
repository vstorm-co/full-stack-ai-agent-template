"""Channel bot, identity, and session schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema

# Access policy


class AccessPolicy(BaseModel):
    """Bot access control policy."""

    mode: Literal["open", "whitelist", "jwt_linked", "group_only"] = "open"
    whitelist: list[str] = []
    allowed_groups: list[str] = []
    require_link: bool = False
    rate_limit_rpm: int = 10
    denied_message: str = "You are not authorised to use this bot."


# ChannelBot schemas


class ChannelBotCreate(BaseSchema):
    """Schema for creating a channel bot."""

    platform: str = Field("telegram", max_length=20)
    name: str = Field(..., max_length=255)
    token: str = Field(..., min_length=10, max_length=500)
    webhook_mode: bool = False
    webhook_url: str | None = None
    access_policy: AccessPolicy = Field(default_factory=AccessPolicy)
    ai_model_override: str | None = None
    system_prompt_override: str | None = None


class ChannelBotUpdate(BaseSchema):
    """Schema for updating a channel bot (all fields optional)."""

    name: str | None = Field(default=None, max_length=255)
    token: str | None = Field(default=None, min_length=10, max_length=500)
    webhook_mode: bool | None = None
    webhook_url: str | None = None
    access_policy: AccessPolicy | None = None
    ai_model_override: str | None = None
    system_prompt_override: str | None = None
    is_active: bool | None = None


class ChannelBotRead(BaseSchema):
    """Schema for reading a channel bot (token_encrypted is never returned)."""

    id: UUID
    platform: str
    name: str
    is_active: bool
    webhook_mode: bool
    webhook_url: str | None
    access_policy: AccessPolicy
    ai_model_override: str | None
    system_prompt_override: str | None
    created_at: datetime
    updated_at: datetime | None = None


class ChannelBotList(BaseSchema):
    """Paginated list of channel bots."""

    items: list[ChannelBotRead]
    total: int


# ChannelIdentity schemas


class ChannelIdentityRead(BaseSchema):
    """Schema for reading a channel identity."""

    id: UUID
    user_id: UUID | None = None
    platform: str
    platform_user_id: str
    platform_username: str | None = None
    platform_display_name: str | None = None
    is_active: bool
    created_at: datetime


# ChannelSession schemas


class ChannelSessionRead(BaseSchema):
    """Schema for reading a channel session."""

    id: UUID
    bot_id: UUID
    identity_id: UUID
    conversation_id: UUID | None = None
    platform_chat_id: str
    chat_type: str
    is_active: bool
    last_message_at: datetime | None = None
    created_at: datetime


class ChannelSessionList(BaseSchema):
    """Paginated list of channel sessions."""

    items: list[ChannelSessionRead]
    total: int
