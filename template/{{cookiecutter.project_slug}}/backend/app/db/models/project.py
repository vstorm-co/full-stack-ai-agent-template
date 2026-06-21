{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
{%- if cookiecutter.use_sqlmodel %}
"""Project and ProjectMember models for multi-user project management (SQLModel)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from app.db.base import TimestampMixin


class Project(TimestampMixin, SQLModel, table=True):
    """Project model — represents an isolated workspace (Docker volume + container).

    Each project has a stable container_name and volume_name generated at creation.
    The Docker container is started lazily on first chat within the project.
    """

    __tablename__ = "projects"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    owner_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    image: str = Field(default="python:3.12-slim", max_length=255)
    # Stable Docker identifiers — pd-{id} and pd-vol-{id}
    container_name: str = Field(
        sa_column=Column(String(255), unique=True, nullable=False),
    )
    volume_name: str = Field(
        sa_column=Column(String(255), unique=True, nullable=False),
    )
    archived_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    members: list["ProjectMember"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name})>"


class ProjectMember(SQLModel, table=True):
    """ProjectMember — role-based membership in a project.

    Roles: viewer (read-only), editor (read + write chats), admin (invite + manage).
    The project owner has implicit full access and is not in this table.
    """

    __tablename__ = "project_members"

    project_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    role: str = Field(default="viewer", max_length=20)  # viewer | editor | admin
    invited_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id"),
            nullable=True,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    project: "Project" = Relationship(back_populates="members")

    def __repr__(self) -> str:
        return f"<ProjectMember(project_id={self.project_id}, user_id={self.user_id}, role={self.role})>"


{%- else %}
"""Project and ProjectMember models for multi-user project management."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base, TimestampMixin


class Project(Base, TimestampMixin):
    """Project model — represents an isolated workspace (Docker volume + container).

    Each project has a stable container_name and volume_name generated at creation.
    The Docker container is started lazily on first chat within the project.
    """

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image: Mapped[str] = mapped_column(
        String(255), nullable=False, default="python:3.12-slim"
    )
    # Stable Docker identifiers — pd-{id} and pd-vol-{id}
    container_name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    volume_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name})>"


class ProjectMember(Base):
    """ProjectMember — role-based membership in a project.

    Roles: viewer (read-only), editor (read + write chats), admin (invite + manage).
    The project owner has implicit full access and is not in this table.
    """

    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="viewer"
    )  # viewer | editor | admin
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="members")

    def __repr__(self) -> str:
        return f"<ProjectMember(project_id={self.project_id}, user_id={self.user_id}, role={self.role})>"


{%- endif %}
{%- else %}
"""Project models - requires use_pydantic_deep and use_jwt."""
{%- endif %}
