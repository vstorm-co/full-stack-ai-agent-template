{%- if cookiecutter.enable_rag %}
{%- if cookiecutter.use_sqlmodel %}
"""RAGDocument model — tracks documents ingested into RAG collections."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class RAGDocument(TimestampMixin, SQLModel, table=True):
    """Tracks ingested documents with processing status."""

    __tablename__ = "rag_documents"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    collection_name: str = Field(sa_column=Column(String(255), nullable=False, index=True))
    filename: str = Field(sa_column=Column(String(255), nullable=False))
    filesize: int = Field(sa_column=Column(Integer, nullable=False, default=0))
    filetype: str = Field(sa_column=Column(String(20), nullable=False))
    storage_path: str | None = Field(default=None, sa_column=Column(String(500), nullable=True))
    status: str = Field(default="processing", sa_column=Column(String(20), nullable=False, default="processing"))
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    vector_document_id: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    chunk_count: int = Field(default=0, sa_column=Column(Integer, nullable=False, default=0))
    started_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    completed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
{%- if cookiecutter.enable_teams %}
    organization_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    knowledge_base_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
{%- endif %}
{%- elif cookiecutter.use_sqlalchemy %}
"""RAGDocument model — tracks documents ingested into RAG collections."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RAGDocument(TimestampMixin, Base):
    """Tracks ingested documents with processing status."""

    __tablename__ = "rag_documents"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filesize: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filetype: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="processing")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    vector_document_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
{%- if cookiecutter.enable_teams %}
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
{%- endif %}
{%- endif %}
{%- endif %}
