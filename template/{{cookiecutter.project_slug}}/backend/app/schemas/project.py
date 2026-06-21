{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
"""Project schemas for DeepAgents project management."""

from datetime import datetime
from typing import Literal

from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class ProjectCreate(BaseSchema):
    """Schema for creating a project."""

    name: str = Field(..., max_length=255, description="Project name")
    description: str | None = Field(default=None, description="Optional project description")
    image: str = Field(
        default="python:3.12-slim",
        max_length=255,
        description="Docker image used for the sandbox container",
    )


class ProjectUpdate(BaseSchema):
    """Schema for updating a project."""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    image: str | None = Field(default=None, max_length=255)


class ProjectRead(BaseSchema, TimestampSchema):
    """Schema for reading a project (API response)."""

    id: UUID
    owner_id: UUID
    name: str
    description: str | None = None
    image: str
    container_name: str
    volume_name: str
    archived_at: datetime | None = None


class ProjectList(BaseSchema):
    """Schema for listing projects."""

    items: list[ProjectRead]
    total: int


class ProjectMemberCreate(BaseSchema):
    """Schema for adding a member to a project."""

    user_id: UUID = Field(..., description="ID of the user to add")
    role: Literal["viewer", "editor", "admin"] = Field(
        default="viewer", description="Member role"
    )


class ProjectMemberUpdate(BaseSchema):
    """Schema for updating a member's role."""

    role: Literal["viewer", "editor", "admin"] = Field(..., description="New role")


class ProjectMemberRead(BaseSchema):
    """Schema for reading a project member."""

    project_id: UUID
    user_id: UUID
    invited_by: UUID | None = None
    role: str
    created_at: datetime


class ProjectMemberList(BaseSchema):
    """Schema for listing project members."""

    items: list[ProjectMemberRead]
    total: int
{%- else %}
"""Project schemas - requires use_pydantic_deep and use_jwt."""
{%- endif %}
