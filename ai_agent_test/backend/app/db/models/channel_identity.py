"""ChannelIdentity model — maps platform user → app user (PostgreSQL async)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ChannelIdentity(Base, TimestampMixin):
    """Mapping between a platform user and an app user account."""

    __tablename__ = "channel_identities"
    __table_args__ = (
        UniqueConstraint("platform", "platform_user_id", name="uq_channel_identity_platform_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    platform_user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    platform_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    platform_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    link_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    link_code_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<ChannelIdentity(id={self.id}, platform={self.platform}, platform_user_id={self.platform_user_id})>"
