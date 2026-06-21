{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
{%- if cookiecutter.use_sqlmodel %}
"""KnowledgeBase model — scoped RAG collections (personal / org / app)."""

import enum
import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class KBScope(enum.StrEnum):
    PERSONAL = "personal"
    ORG = "org"
    APP = "app"


class KnowledgeBase(TimestampMixin, SQLModel, table=True):
    """Named, scoped wrapper around a vector-store collection."""

    __tablename__ = "knowledge_bases"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    name: str = Field(sa_column=Column(String(128), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(String(500), nullable=True))
    scope: str = Field(
        default=KBScope.PERSONAL.value,
        sa_column=Column(String(16), nullable=False, default=KBScope.PERSONAL.value, index=True),
    )
    collection_name: str = Field(sa_column=Column(String(255), nullable=False, index=True))
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, default=False),
    )
    owner_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    organization_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase(id={self.id}, name={self.name!r}, scope={self.scope})>"

{%- elif cookiecutter.use_sqlalchemy %}
"""KnowledgeBase model — scoped RAG collections (personal / org / app)."""

import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class KBScope(enum.StrEnum):
    PERSONAL = "personal"
    ORG = "org"
    APP = "app"


class KnowledgeBase(TimestampMixin, Base):
    """Named, scoped wrapper around a vector-store collection."""

    __tablename__ = "knowledge_bases"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default=KBScope.PERSONAL.value, index=True)
    collection_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase(id={self.id}, name={self.name!r}, scope={self.scope})>"

{%- endif %}
{%- else %}
"""KnowledgeBase model — not configured (enable_teams, enable_rag, or use_jwt is false)."""
{%- endif %}
