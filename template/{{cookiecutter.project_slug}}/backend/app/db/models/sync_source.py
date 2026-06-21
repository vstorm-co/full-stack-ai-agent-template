{%- if cookiecutter.enable_rag %}
{%- if cookiecutter.use_sqlmodel %}
"""SyncSource model — stores RAG sync source configurations."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class SyncSource(TimestampMixin, SQLModel, table=True):
    """Configurable connector source for RAG document synchronization.

    Belongs to an organization. ``collection_name`` is nullable — a source
    without a collection is an org-level "integration template" not yet
    assigned to a specific knowledge base.
    """

    __tablename__ = "sync_sources"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    organization_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    name: str = Field(sa_column=Column(String(255), nullable=False))
    connector_type: str = Field(sa_column=Column(String(20), nullable=False))
    collection_name: str | None = Field(default=None, sa_column=Column(String(255), nullable=True, index=True))
    config: dict[str, object] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}"))
    sync_mode: str = Field(default="new_only", sa_column=Column(String(20), nullable=False, default="new_only"))
    schedule_minutes: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True))
    last_sync_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    last_sync_status: str | None = Field(default=None, sa_column=Column(String(20), nullable=True))
    last_error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
{%- elif cookiecutter.use_sqlalchemy %}
"""SyncSource model — stores RAG sync source configurations."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SyncSource(TimestampMixin, Base):
    """Configurable connector source for RAG document synchronization.

    Belongs to an organization. ``collection_name`` is nullable — a source
    without a collection is an org-level "integration template" not yet
    assigned to a specific knowledge base.
    """

    __tablename__ = "sync_sources"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(20), nullable=False)
    collection_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    config: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, server_default="{}")
    sync_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="new_only")
    schedule_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
{%- endif %}
{%- endif %}
