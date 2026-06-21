{%- if cookiecutter.enable_teams %}
"""Organization, OrganizationMember and Invitation schemas."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.base import BaseSchema, TimestampSchema
from app.schemas.user import UserRead

_ID = UUID


class OrganizationCreate(BaseSchema):
    name: str = Field(min_length=2, max_length=128)
    slug: str | None = Field(default=None, min_length=2, max_length=64)

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.match(r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$", v):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens, no leading/trailing hyphens")
        return v


class OrganizationUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=128)
    avatar_url: str | None = Field(default=None, max_length=500)


class OrganizationRead(BaseSchema, TimestampSchema):
    id: _ID
    name: str
    slug: str
    is_personal: bool
    avatar_url: str | None = None
    member_count: int = 0
    role: str  # current user's role in this org
{%- if cookiecutter.enable_billing %}
    subscription_tier: str = "free"
    seats_limit: int | None = None
    credits_balance: int = 0
{%- endif %}


class OrganizationList(BaseSchema):
    items: list[OrganizationRead]
    total: int


class OrganizationMemberRead(BaseSchema):
    id: _ID
    organization_id: _ID
    user_id: _ID
    role: str
    email: str
    full_name: str | None = None
    avatar_url: str | None = None
    joined_at: datetime


class OrganizationMemberUpdate(BaseSchema):
    role: str = Field(description="New role for the member")

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        allowed = {"owner", "admin", "member", "viewer"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(sorted(allowed))}")
        return v


class OrganizationMemberList(BaseSchema):
    items: list[OrganizationMemberRead]
    total: int


class InvitationCreate(BaseSchema):
    email: EmailStr
    role: str = "member"

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        allowed = {"admin", "member", "viewer"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(sorted(allowed))}")
        return v


class InvitationRead(BaseSchema):
    id: _ID
    organization_id: _ID
    email: str
    role: str
    status: str
    token: str
    expires_at: datetime
    created_at: datetime
    invited_by: UserRead | None = None


class InvitationList(BaseSchema):
    items: list[InvitationRead]
    total: int


class InvitationAccept(BaseSchema):
    token: str


class TransferOwnershipRequest(BaseSchema):
    new_owner_user_id: _ID


{%- else %}
"""Organization schemas — not configured (enable_teams=false)."""
{%- endif %}
