{%- if cookiecutter.enable_rag %}
{%- if cookiecutter.use_sqlmodel %}
"""SyncLog model — tracks document synchronization history."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class SyncLog(TimestampMixin, SQLModel, table=True):
    __tablename__ = "sync_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    source: str = Field(sa_column=Column(String(20), nullable=False))
    collection_name: str = Field(sa_column=Column(String(255), nullable=False, index=True))
    sync_source_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("sync_sources.id", ondelete="SET NULL"), nullable=True),
    )
    status: str = Field(default="running", sa_column=Column(String(20), nullable=False, default="running"))
    mode: str = Field(default="full", sa_column=Column(String(20), nullable=False, default="full"))
    total_files: int = Field(default=0, sa_column=Column(Integer, nullable=False, default=0))
    ingested: int = Field(default=0, sa_column=Column(Integer, nullable=False, default=0))
    updated: int = Field(default=0, sa_column=Column(Integer, nullable=False, default=0))
    skipped: int = Field(default=0, sa_column=Column(Integer, nullable=False, default=0))
    failed: int = Field(default=0, sa_column=Column(Integer, nullable=False, default=0))
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    started_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
{%- elif cookiecutter.use_sqlalchemy %}
"""SyncLog model — tracks document synchronization history."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SyncLog(TimestampMixin, Base):
    __tablename__ = "sync_logs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    collection_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sync_source_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sync_sources.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="full")
    total_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ingested: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
{%- endif %}
{%- endif %}
