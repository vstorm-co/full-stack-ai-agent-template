"""Schemas for user-scoped slash command settings."""

from __future__ import annotations

from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema, TimestampSchema

# Slug-style names: lowercase letters, digits, hyphens. Matches the palette
# matcher in the frontend; rejects anything that wouldn't survive `/<name>`.
NAME_PATTERN = r"^[a-z0-9][a-z0-9-]{0,31}$"


class UserSlashCommandBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=32, pattern=NAME_PATTERN)
    is_enabled: bool = True


class UserSlashCommandCustomCreate(UserSlashCommandBase):
    """Create a user-defined custom command (with prompt body)."""

    prompt: str = Field(..., min_length=1, max_length=10_000)

    @field_validator("prompt")
    @classmethod
    def _strip_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("prompt must not be empty")
        return v


class UserSlashCommandUpdate(BaseSchema):
    """Patch a custom command. ``prompt`` only applies to custom commands;
    built-in overrides accept just ``is_enabled``."""

    name: str | None = Field(default=None, min_length=1, max_length=32, pattern=NAME_PATTERN)
    prompt: str | None = Field(default=None, min_length=1, max_length=10_000)
    is_enabled: bool | None = None


class BuiltinOverrideUpsert(BaseSchema):
    """Upsert an override row for a built-in command (controls is_enabled)."""

    name: str = Field(..., min_length=1, max_length=32, pattern=NAME_PATTERN)
    is_enabled: bool


class UserSlashCommandRead(UserSlashCommandBase, TimestampSchema):
    id: UUID
    # NULL = override of a built-in (controls is_enabled only). Otherwise
    # this is a user-defined custom command.
    prompt: str | None = None


class UserSlashCommandList(BaseSchema):
    items: list[UserSlashCommandRead]
    total: int
