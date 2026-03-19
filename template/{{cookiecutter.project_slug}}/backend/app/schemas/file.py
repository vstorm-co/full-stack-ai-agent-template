{%- if cookiecutter.enable_ai_agent and cookiecutter.enable_conversation_persistence %}
"""Schemas for file upload operations."""

from datetime import datetime
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    """Response after successful file upload."""

{%- if cookiecutter.use_postgresql %}
    id: UUID
{%- else %}
    id: str
{%- endif %}
    filename: str
    mime_type: str
    size: int
    file_type: str


class FileInfo(FileUploadResponse):
    """Full file metadata."""

    created_at: datetime
{%- if cookiecutter.use_postgresql %}
    user_id: UUID
{%- else %}
    user_id: str
{%- endif %}
{%- endif %}
