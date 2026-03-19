"""Schemas for file upload operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Response after successful file upload."""

    id: UUID
    filename: str
    mime_type: str
    size: int
    file_type: str  # image, text, pdf, docx


class FileInfo(FileUploadResponse):
    """Full file metadata."""

    created_at: datetime
    user_id: UUID


class FileReference(BaseModel):
    """Lightweight file reference for embedding in messages."""

    id: UUID
    filename: str
    file_type: str
    mime_type: str
