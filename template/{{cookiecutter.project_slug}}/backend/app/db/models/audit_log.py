{%- if cookiecutter.enable_teams %}
{%- if cookiecutter.use_sqlmodel %}
"""App admin audit log model (PostgreSQL/SQLModel)."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class AppAdminAuditLog(TimestampMixin, SQLModel, table=True):
    """Records privileged actions performed by app admins or org owners."""

    __tablename__ = "app_admin_audit_logs"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    actor_user_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    )
    organization_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), nullable=True, index=True),
    )
    action: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    target_type: str | None = Field(default=None, sa_column=Column(String(100), nullable=True))
    target_id: str | None = Field(default=None, sa_column=Column(String(36), nullable=True))
    details: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    ip_address: str | None = Field(default=None, sa_column=Column(String(45), nullable=True))

    def __repr__(self) -> str:
        return f"<AppAdminAuditLog(id={self.id}, action={self.action}, actor={self.actor_user_id})>"


{%- else %}
"""App admin audit log model (PostgreSQL/SQLAlchemy)."""

import uuid
from typing import Any

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AppAdminAuditLog(Base, TimestampMixin):
    """Records privileged actions performed by app admins or org owners."""

    __tablename__ = "app_admin_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    def __repr__(self) -> str:
        return f"<AppAdminAuditLog(id={self.id}, action={self.action}, actor={self.actor_user_id})>"


{%- endif %}
{%- else %}
"""Audit log — not configured (enable_teams=false)."""
{%- endif %}
