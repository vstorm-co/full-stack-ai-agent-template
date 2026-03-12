{%- if cookiecutter.use_jwt %}
"""User schemas."""

from enum import StrEnum
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema, TimestampSchema


class UserRole(StrEnum):
    """User role enumeration for API schemas."""

    ADMIN = "admin"
    USER = "user"


class UserBase(BaseSchema):
    """Base user schema."""

    email: EmailStr = Field(max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class UserCreate(BaseSchema):
    """Schema for creating a user."""

    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole = UserRole.USER


class UserUpdate(BaseSchema):
    """Schema for updating a user."""

    email: EmailStr | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    role: UserRole | None = None


class UserRead(UserBase, TimestampSchema):
    """Schema for reading a user."""

{%- if cookiecutter.use_postgresql %}
    id: UUID
{%- elif cookiecutter.use_sqlite or cookiecutter.use_mongodb %}
    id: str
{%- endif %}
    is_superuser: bool = False
    role: UserRole = UserRole.USER


class UserInDB(UserRead):
    """User schema with hashed password (internal use)."""

    hashed_password: str
{%- else %}
"""User schemas - not configured."""
{%- endif %}