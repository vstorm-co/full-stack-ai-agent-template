{%- if cookiecutter.use_sqlmodel %}
"""User database model (SQLModel + PostgreSQL)."""

import uuid
from datetime import datetime
from enum import StrEnum
{%- if cookiecutter.enable_session_management %}
from typing import TYPE_CHECKING
{%- endif %}

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel{%- if cookiecutter.enable_session_management %}, Relationship{%- endif %}

from app.db.base import TimestampMixin

{%- if cookiecutter.enable_session_management %}
if TYPE_CHECKING:
    from app.db.models.session import Session
{%- endif %}


class UserRole(StrEnum):
    """User role enumeration.

    Roles hierarchy (higher includes lower permissions):
    - ADMIN: Full system access, can manage users and settings
    - USER: Standard user access
    """

    ADMIN = "admin"
    USER = "user"


class User(TimestampMixin, SQLModel, table=True):
    """User model."""

    __tablename__ = "users"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    email: str = Field(
        sa_column=Column(String(255), unique=True, index=True, nullable=False)
    )
    hashed_password: str | None = Field(default=None, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool = Field(default=True, sa_column=Column(Boolean, default=True, nullable=False))
    role: str = Field(default=UserRole.USER.value, max_length=50)
    is_app_admin: bool = Field(default=False, sa_column=Column(Boolean, default=False, nullable=False))
    avatar_url: str | None = Field(default=None, max_length=500)
    onboarding_completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
{%- if cookiecutter.enable_oauth %}
    oauth_provider: str | None = Field(
        default=None,
        sa_column=Column(String(32), nullable=True, index=True),
    )
    oauth_id: str | None = Field(
        default=None,
        sa_column=Column(String(255), nullable=True, index=True),
    )
{%- endif %}
{%- if cookiecutter.use_delegated_auth %}
    external_user_id: str | None = Field(
        default=None,
        sa_column=Column(String(255), nullable=True, index=True, unique=True),
    )
{%- endif %}

{%- if cookiecutter.enable_session_management %}
    sessions: list["Session"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
{%- endif %}

    @property
    def user_role(self) -> UserRole:
        """Get role as enum."""
        return UserRole(self.role)

    def has_role(self, required_role: UserRole) -> bool:
        """Check if user has the required role or higher."""
        if self.role == UserRole.ADMIN.value:
            return True
        return self.role == required_role.value

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


{%- else %}
"""User database model."""

import uuid
from datetime import datetime
from enum import StrEnum
{%- if cookiecutter.enable_session_management %}
from typing import TYPE_CHECKING
{%- endif %}

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column{%- if cookiecutter.enable_session_management %}, relationship{%- endif %}

from app.db.base import Base, TimestampMixin

{%- if cookiecutter.enable_session_management %}
if TYPE_CHECKING:
    from app.db.models.session import Session
{%- endif %}


class UserRole(StrEnum):
    """User role enumeration.

    Roles hierarchy (higher includes lower permissions):
    - ADMIN: Full system access, can manage users and settings
    - USER: Standard user access
    """

    ADMIN = "admin"
    USER = "user"


class User(Base, TimestampMixin):
    """User model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.USER.value, nullable=False)
    is_app_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
{%- if cookiecutter.enable_oauth %}
    oauth_provider: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
{%- endif %}
{%- if cookiecutter.use_delegated_auth %}
    external_user_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True, unique=True
    )
{%- endif %}

{%- if cookiecutter.enable_session_management %}

    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
{%- endif %}

    @property
    def user_role(self) -> UserRole:
        """Get role as enum."""
        return UserRole(self.role)

    def has_role(self, required_role: UserRole) -> bool:
        """Check if user has the required role or higher.

        Admin role has access to everything.
        """
        if self.role == UserRole.ADMIN.value:
            return True
        return self.role == required_role.value

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


{%- endif %}
