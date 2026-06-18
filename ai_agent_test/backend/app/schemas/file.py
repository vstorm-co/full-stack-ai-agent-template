"""Schemas for file upload operations."""

from datetime import datetime
from uuid import UUID

from app.schemas.base import BaseSchema


class FileUploadResponse(BaseSchema):
    """Response after successful file upload."""

    id: UUID
    filename: str
    mime_type: str
    size: int
    file_type: str


class FileInfo(FileUploadResponse):
    """Full file metadata."""

    created_at: datetime
    user_id: UUID
