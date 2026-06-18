"""ConversationShare model — sharing conversations between users (PostgreSQL async)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ConversationShare(Base):
    """Share record granting a user access to another user's conversation."""

    __tablename__ = "conversation_shares"
    __table_args__ = (
        UniqueConstraint("conversation_id", "shared_with", name="uq_share_conv_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shared_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    shared_with: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    permission: Mapped[str] = mapped_column(
        String(10), nullable=False, default="view"
    )  # view | edit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ConversationShare(id={self.id}, conv={self.conversation_id}, with={self.shared_with})>"
