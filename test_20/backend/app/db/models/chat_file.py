"""ChatFile database model - stores metadata for files uploaded in chat."""

import uuid

from sqlalchemy import Column, ForeignKey, String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class ChatFile(TimestampMixin, SQLModel, table=True):
    """Tracks files uploaded by users in chat conversations."""

    __tablename__ = "chat_files"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True),
    )
    message_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True),
    )
    filename: str = Field(sa_column=Column(String(255), nullable=False))
    mime_type: str = Field(sa_column=Column(String(100), nullable=False))
    size: int = Field(sa_column=Column(Integer, nullable=False))
    storage_path: str = Field(sa_column=Column(String(500), nullable=False))
    file_type: str = Field(sa_column=Column(String(20), nullable=False))  # image, text, pdf, docx
    parsed_content: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    def __repr__(self) -> str:
        return f"<ChatFile(id={self.id}, filename={self.filename}, type={self.file_type})>"
