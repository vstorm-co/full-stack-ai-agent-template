"""Message rating model for user feedback on AI responses.

This module is only imported when JWT auth is enabled (see
`app/db/models/__init__.py` and `alembic/env.py`).
"""

{%- if cookiecutter.use_jwt %}

{%- if cookiecutter.use_sqlmodel %}
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from app.db.base import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.conversation import Message
    from app.db.models.user import User


class MessageRating(TimestampMixin, SQLModel, table=True):
    """User rating for AI assistant messages.

    Attributes:
        id: Unique rating identifier
        message_id: The message being rated (assistant messages only)
        user_id: The user who submitted the rating
        rating: 1 for like, -1 for dislike
        comment: Optional feedback comment
        created_at: When the rating was submitted
        updated_at: When the rating was last modified
    """

    __tablename__ = "message_ratings"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_message_user_rating"),
        CheckConstraint("rating IN (1, -1)", name="ck_rating_value"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    message_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    rating: int = Field(sa_column=Column(Integer, nullable=False))  # 1 or -1
    comment: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    message: "Message" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "MessageRating.message_id"}
    )
    user: "User" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "MessageRating.user_id"}
    )

    def __repr__(self) -> str:
        return f"<MessageRating(id={self.id}, rating={self.rating})>"


{%- else %}
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.conversation import Message
    from app.db.models.user import User


class MessageRating(Base, TimestampMixin):
    """User rating for AI assistant messages."""

    __tablename__ = "message_ratings"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_message_user_rating"),
        CheckConstraint("rating IN (1, -1)", name="ck_rating_value"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or -1
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    message: Mapped["Message"] = relationship(
        "Message",
        foreign_keys="MessageRating.message_id",
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys="MessageRating.user_id",
    )

    def __repr__(self) -> str:
        return f"<MessageRating(id={self.id}, rating={self.rating})>"


{%- endif %}

{%- else %}
"""Message rating model - requires JWT auth (not configured)."""
{%- endif %}
