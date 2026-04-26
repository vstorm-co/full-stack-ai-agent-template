"""Message rating service - business logic for ratings."""

{%- if cookiecutter.use_postgresql %}
import csv
from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator
from datetime import UTC, datetime
from io import StringIO

from fastapi.responses import JSONResponse, StreamingResponse

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.repositories import conversation as conversation_repo
from app.repositories import message_rating as rating_repo
from app.schemas.message_rating import (
    MessageRatingCreate,
    MessageRatingRead,
    MessageRatingWithDetails,
    RatingSummary,
    RatingValue,
)


class MessageRatingService:
    """Service for managing message ratings."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_message_role(self, message_id: UUID) -> str:
        """Get the role of a message.

        Raises:
            NotFoundError: If message doesn't exist
        """
        message = await conversation_repo.get_message_by_id(self.db, message_id)
        if not message:
            raise NotFoundError(message="Message not found", details={"message_id": str(message_id)})
        return message.role

    async def _validate_message_in_conversation(
        self, message_id: UUID, conversation_id: UUID
    ) -> None:
        """Validate that a message belongs to the specified conversation.

        Raises:
            NotFoundError: If message doesn't exist or belongs to a different conversation
        """
        message = await conversation_repo.get_message_by_id(self.db, message_id)
        if not message:
            raise NotFoundError(message="Message not found", details={"message_id": str(message_id)})
        if message.conversation_id != conversation_id:
            raise NotFoundError(
                message="Message not found in this conversation",
                details={"message_id": str(message_id), "conversation_id": str(conversation_id)},
            )

    async def _validate_conversation_ownership(
        self, conversation_id: UUID, user_id: UUID
    ) -> None:
        """Validate that the conversation belongs to the specified user.

        Raises:
            NotFoundError: If conversation doesn't exist or belongs to a different user
        """
        conv = await conversation_repo.get_conversation_by_id(self.db, conversation_id)
        if not conv or conv.user_id != user_id:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": str(conversation_id)},
            )

    async def rate_message(
        self,
        conversation_id: UUID,
        message_id: UUID,
        user_id: UUID,
        data: MessageRatingCreate,
    ) -> tuple[MessageRatingRead, bool]:
        """Rate or update rating for a message.

        Args:
            conversation_id: The conversation containing the message
            message_id: The message to rate
            user_id: The user rating the message
            data: Rating data (rating value, optional comment)

        Returns:
            Tuple of (rating, is_new) where is_new is True if created, False if updated

        Raises:
            ValidationError: If trying to rate a non-assistant message
            NotFoundError: If message doesn't exist or not in the specified conversation
        """
        # Validate message belongs to the specified conversation
        await self._validate_conversation_ownership(conversation_id, user_id)
        await self._validate_message_in_conversation(message_id, conversation_id)

        message_role = await self._get_message_role(message_id)
        if message_role != "assistant":
            raise ValidationError(
                message="Only assistant messages can be rated",
                details={"message_role": message_role},
            )

        # Check for existing rating
        existing = await rating_repo.get_rating_by_message_and_user(
            self.db, message_id, user_id
        )

        if existing:
            # Update existing rating
            updated = await rating_repo.update_rating(
                self.db, existing, new_rating=data.rating, comment=data.comment
            )
            return MessageRatingRead.model_validate(updated), False

        # Create new rating with race condition handling
        try:
            rating = await rating_repo.create_rating(
                self.db,
                message_id=message_id,
                user_id=user_id,
                rating=data.rating,
                comment=data.comment,
            )
            return MessageRatingRead.model_validate(rating), True
        except IntegrityError:
            # Race condition: another request created the rating first
            await self.db.rollback()
            existing = await rating_repo.get_rating_by_message_and_user(
                self.db, message_id, user_id
            )
            if existing:
                # Update the existing rating
                updated = await rating_repo.update_rating(
                    self.db, existing, new_rating=data.rating, comment=data.comment
                )
                return MessageRatingRead.model_validate(updated), False
            raise

    async def remove_rating(
        self,
        conversation_id: UUID,
        message_id: UUID,
        user_id: UUID,
    ) -> None:
        """Remove a user's rating from a message.

        Args:
            conversation_id: The conversation containing the message
            message_id: The message to remove rating from
            user_id: The user who owns the rating

        Raises:
            NotFoundError: If message doesn't exist, not in conversation, or no rating exists
        """
        # Validate message belongs to the specified conversation
        await self._validate_conversation_ownership(conversation_id, user_id)
        await self._validate_message_in_conversation(message_id, conversation_id)

        rating = await rating_repo.get_rating_by_message_and_user(
            self.db, message_id, user_id
        )
        if not rating:
            raise NotFoundError(
                message="Rating not found",
                details={"message_id": str(message_id), "user_id": str(user_id)},
            )
        await rating_repo.delete_rating(self.db, rating)

    async def get_message_ratings(
        self,
        message_id: UUID,
    ) -> dict[str, int]:
        """Get aggregate rating counts for a message.

        Returns:
            Dict with likes and dislikes count
        """
        ratings = await rating_repo.get_ratings_for_message(self.db, message_id)
        return {
            "likes": sum(1 for r in ratings if r.rating == 1),
            "dislikes": sum(1 for r in ratings if r.rating == -1),
        }

    async def list_ratings(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        rating_filter: int | None = None,
        with_comments_only: bool = False,
    ) -> tuple[list[MessageRatingWithDetails], int]:
        """List all ratings (admin only)."""
        items, total = await rating_repo.list_ratings(
            self.db,
            skip=skip,
            limit=limit,
            rating_filter=rating_filter,
            with_comments_only=with_comments_only,
        )

        # Enrich with related data
        result = []
        for item in items:
            result.append(
                MessageRatingWithDetails(
                    id=item.id,
                    message_id=item.message_id,
                    user_id=item.user_id,
                    rating=RatingValue(item.rating),
                    comment=item.comment,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    message_content=(item.message.content or "")[:200] if item.message else None,
                    message_role=item.message.role if item.message else None,
                    conversation_id=item.message.conversation_id if item.message else None,
{%- if cookiecutter.use_jwt %}
                    user_email=item.user.email if item.user else None,
                    user_name=item.user.full_name if item.user else None,
{%- else %}
                    user_email=None,
                    user_name=None,
{%- endif %}
                )
            )

        return result, total

    EXPORT_CHUNK_SIZE = 5000

    async def export_all_ratings(
        self,
        *,
        rating_filter: int | None = None,
        with_comments_only: bool = False,
    ) -> AsyncGenerator[list[MessageRatingWithDetails], None]:
        """Yield all ratings in chunks for memory-efficient export.

        Fetches ratings in pages to avoid loading all ORM objects into
        memory at once. Each yielded chunk is a list of lightweight
        Pydantic schemas.
        """
        skip = 0
        while True:
            items, total = await rating_repo.list_ratings(
                self.db,
                skip=skip,
                limit=self.EXPORT_CHUNK_SIZE,
                rating_filter=rating_filter,
                with_comments_only=with_comments_only,
            )
            if not items:
                break
            result = [
                MessageRatingWithDetails(
                    id=item.id,
                    message_id=item.message_id,
                    user_id=item.user_id,
                    rating=RatingValue(item.rating),
                    comment=item.comment,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    message_content=(item.message.content or "")[:200] if item.message else None,
                    message_role=item.message.role if item.message else None,
                    conversation_id=item.message.conversation_id if item.message else None,
{%- if cookiecutter.use_jwt %}
                    user_email=item.user.email if item.user else None,
                    user_name=item.user.full_name if item.user else None,
{%- else %}
                    user_email=None,
                    user_name=None,
{%- endif %}
                )
                for item in items
            ]
            yield result
            skip += self.EXPORT_CHUNK_SIZE
            if skip >= total:
                break

    async def get_summary(self, *, days: int = 30) -> RatingSummary:
        """Get aggregated rating statistics."""
        summary_data = await rating_repo.get_rating_summary(self.db, days=days)
        return RatingSummary(**summary_data)

    _CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
    _CSV_HEADER = [
        "ID", "Message ID", "Conversation ID", "User ID",
        "Rating", "Comment", "Message Content", "Message Role",
        "User Email", "User Name", "Created At", "Updated At",
    ]

    def _csv_escape(self, value: str) -> str:
        if value and value[0] in self._CSV_INJECTION_PREFIXES:
            return "'" + value
        return value

    def _csv_row_values(self, item: MessageRatingWithDetails) -> list[str]:
        return [
            self._csv_escape(str(item.id)),
            self._csv_escape(str(item.message_id)),
            self._csv_escape(str(item.conversation_id)) if item.conversation_id else "",
            self._csv_escape(str(item.user_id)),
            "Like" if item.rating == 1 else "Dislike",
            self._csv_escape(item.comment or ""),
            self._csv_escape(item.message_content or ""),
            self._csv_escape(item.message_role or ""),
            self._csv_escape(item.user_email or ""),
            self._csv_escape(item.user_name or ""),
            item.created_at.isoformat() if item.created_at else "",
            item.updated_at.isoformat() if item.updated_at else "",
        ]

    def _serialize_csv_row(self, values: list[str]) -> str:
        buffer = StringIO()
        csv.writer(buffer).writerow(values)
        return buffer.getvalue()

    def _validate_export_format(self, export_format: str) -> str:
        fmt = export_format.lower()
        if fmt not in ("json", "csv"):
            raise ValidationError(
                message="Invalid export format. Must be 'json' or 'csv'.",
                details={"export_format": export_format},
            )
        return fmt

    def _export_disposition(self, now: datetime, fmt: str) -> str:
        return f'attachment; filename="ratings_export_{now.strftime("%Y%m%d_%H%M%S")}.{fmt}"'

    def _json_export_response(
        self, items: list[MessageRatingWithDetails], now: datetime
    ) -> JSONResponse:
        return JSONResponse(
            content={
                "ratings": [item.model_dump(mode="json") for item in items],
                "total": len(items),
                "exported_at": now.isoformat(),
            },
            headers={"Content-Disposition": self._export_disposition(now, "json")},
        )

    def _stream_csv_async(
        self, chunks: AsyncIterable[list[MessageRatingWithDetails]], now: datetime
    ) -> StreamingResponse:
        async def generate() -> AsyncIterator[str]:
            yield self._serialize_csv_row(self._CSV_HEADER)
            async for chunk in chunks:
                for item in chunk:
                    yield self._serialize_csv_row(self._csv_row_values(item))
        return StreamingResponse(
            generate(),
            media_type="text/csv",
            headers={"Content-Disposition": self._export_disposition(now, "csv")},
        )

    async def export_ratings(
        self,
        *,
        export_format: str,
        rating_filter: int | None = None,
        with_comments_only: bool = False,
    ) -> JSONResponse | StreamingResponse:
        fmt = self._validate_export_format(export_format)
        now = datetime.now(UTC)
        chunks = self.export_all_ratings(
            rating_filter=rating_filter,
            with_comments_only=with_comments_only,
        )
        if fmt == "csv":
            return self._stream_csv_async(chunks, now)
        all_items: list[MessageRatingWithDetails] = []
        async for chunk in chunks:
            all_items.extend(chunk)
        return self._json_export_response(all_items, now)


{%- elif cookiecutter.use_sqlite %}
"""Message rating service (SQLite sync)."""

import csv
from collections.abc import Generator, Iterable, Iterator
from datetime import UTC, datetime
from io import StringIO

from fastapi.responses import JSONResponse, StreamingResponse

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.repositories import conversation as conversation_repo
from app.repositories import message_rating as rating_repo
from app.schemas.message_rating import (
    MessageRatingCreate,
    MessageRatingRead,
    MessageRatingWithDetails,
    RatingSummary,
    RatingValue,
)


class MessageRatingService:
    """Service for managing message ratings."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _get_message_role(self, message_id: str) -> str:
        """Get the role of a message.

        Raises:
            NotFoundError: If message doesn't exist
        """
        message = conversation_repo.get_message_by_id(self.db, message_id)
        if not message:
            raise NotFoundError(message="Message not found", details={"message_id": message_id})
        return message.role

    def _validate_message_in_conversation(
        self, message_id: str, conversation_id: str
    ) -> None:
        """Validate that a message belongs to the specified conversation.

        Raises:
            NotFoundError: If message doesn't exist or belongs to a different conversation
        """
        message = conversation_repo.get_message_by_id(self.db, message_id)
        if not message:
            raise NotFoundError(message="Message not found", details={"message_id": message_id})
        if message.conversation_id != conversation_id:
            raise NotFoundError(
                message="Message not found in this conversation",
                details={"message_id": message_id, "conversation_id": conversation_id},
            )

    def _validate_conversation_ownership(
        self, conversation_id: str, user_id: str
    ) -> None:
        """Validate that the conversation belongs to the specified user.

        Raises:
            NotFoundError: If conversation doesn't exist or belongs to a different user
        """
        conv = conversation_repo.get_conversation_by_id(self.db, conversation_id)
        if not conv or conv.user_id != user_id:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": conversation_id},
            )

    def rate_message(
        self,
        conversation_id: str,
        message_id: str,
        user_id: str,
        data: MessageRatingCreate,
    ) -> tuple[MessageRatingRead, bool]:
        """Rate or update rating for a message.

        Args:
            conversation_id: The conversation containing the message
            message_id: The message to rate
            user_id: The user rating the message
            data: Rating data (rating value, optional comment)

        Returns:
            Tuple of (rating, is_new) where is_new is True if created, False if updated

        Raises:
            ValidationError: If trying to rate a non-assistant message
            NotFoundError: If message doesn't exist or not in the specified conversation
        """
        # Validate message belongs to the specified conversation
        self._validate_conversation_ownership(conversation_id, user_id)
        self._validate_message_in_conversation(message_id, conversation_id)

        message_role = self._get_message_role(message_id)
        if message_role != "assistant":
            raise ValidationError(
                message="Only assistant messages can be rated",
                details={"message_role": message_role},
            )

        # Check for existing rating
        existing = rating_repo.get_rating_by_message_and_user(
            self.db, message_id, user_id
        )

        if existing:
            # Update existing rating
            updated = rating_repo.update_rating(
                self.db, existing, new_rating=data.rating, comment=data.comment
            )
            return MessageRatingRead.model_validate(updated), False

        # Create new rating with race condition handling
        try:
            rating = rating_repo.create_rating(
                self.db,
                message_id=message_id,
                user_id=user_id,
                rating=data.rating,
                comment=data.comment,
            )
            return MessageRatingRead.model_validate(rating), True
        except IntegrityError:
            # Race condition: another request created the rating first
            self.db.rollback()
            existing = rating_repo.get_rating_by_message_and_user(
                self.db, message_id, user_id
            )
            if existing:
                # Update the existing rating
                updated = rating_repo.update_rating(
                    self.db, existing, new_rating=data.rating, comment=data.comment
                )
                return MessageRatingRead.model_validate(updated), False
            raise

    def remove_rating(
        self,
        conversation_id: str,
        message_id: str,
        user_id: str,
    ) -> None:
        """Remove a user's rating from a message.

        Args:
            conversation_id: The conversation containing the message
            message_id: The message to remove rating from
            user_id: The user who owns the rating

        Raises:
            NotFoundError: If message doesn't exist, not in conversation, or no rating exists
        """
        # Validate message belongs to the specified conversation
        self._validate_conversation_ownership(conversation_id, user_id)
        self._validate_message_in_conversation(message_id, conversation_id)

        rating = rating_repo.get_rating_by_message_and_user(
            self.db, message_id, user_id
        )
        if not rating:
            raise NotFoundError(
                message="Rating not found",
                details={"message_id": message_id, "user_id": user_id},
            )
        rating_repo.delete_rating(self.db, rating)

    def get_message_ratings(
        self,
        message_id: str,
    ) -> dict[str, int]:
        """Get aggregate rating counts for a message.

        Returns:
            Dict with likes and dislikes count
        """
        ratings = rating_repo.get_ratings_for_message(self.db, message_id)
        return {
            "likes": sum(1 for r in ratings if r.rating == 1),
            "dislikes": sum(1 for r in ratings if r.rating == -1),
        }

    def list_ratings(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        rating_filter: int | None = None,
        with_comments_only: bool = False,
    ) -> tuple[list[MessageRatingWithDetails], int]:
        """List all ratings (admin only)."""
        items, total = rating_repo.list_ratings(
            self.db,
            skip=skip,
            limit=limit,
            rating_filter=rating_filter,
            with_comments_only=with_comments_only,
        )

        # Enrich with related data
        result = []
        for item in items:
            result.append(
                MessageRatingWithDetails(
                    id=item.id,
                    message_id=item.message_id,
                    user_id=item.user_id,
                    rating=RatingValue(item.rating),
                    comment=item.comment,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    message_content=(item.message.content or "")[:200] if item.message else None,
                    message_role=item.message.role if item.message else None,
                    conversation_id=item.message.conversation_id if item.message else None,
{%- if cookiecutter.use_jwt %}
                    user_email=item.user.email if item.user else None,
                    user_name=item.user.full_name if item.user else None,
{%- else %}
                    user_email=None,
                    user_name=None,
{%- endif %}
                )
            )

        return result, total

    EXPORT_CHUNK_SIZE = 5000

    def export_all_ratings(
        self,
        *,
        rating_filter: int | None = None,
        with_comments_only: bool = False,
    ) -> Generator[list[MessageRatingWithDetails], None, None]:
        """Yield all ratings in chunks for memory-efficient export.

        Fetches ratings in pages to avoid loading all ORM objects into
        memory at once. Each yielded chunk is a list of lightweight
        Pydantic schemas.
        """
        skip = 0
        while True:
            items, total = rating_repo.list_ratings(
                self.db,
                skip=skip,
                limit=self.EXPORT_CHUNK_SIZE,
                rating_filter=rating_filter,
                with_comments_only=with_comments_only,
            )
            if not items:
                break
            result = [
                MessageRatingWithDetails(
                    id=item.id,
                    message_id=item.message_id,
                    user_id=item.user_id,
                    rating=RatingValue(item.rating),
                    comment=item.comment,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    message_content=(item.message.content or "")[:200] if item.message else None,
                    message_role=item.message.role if item.message else None,
                    conversation_id=item.message.conversation_id if item.message else None,
{%- if cookiecutter.use_jwt %}
                    user_email=item.user.email if item.user else None,
                    user_name=item.user.full_name if item.user else None,
{%- else %}
                    user_email=None,
                    user_name=None,
{%- endif %}
                )
                for item in items
            ]
            yield result
            skip += self.EXPORT_CHUNK_SIZE
            if skip >= total:
                break

    def get_summary(self, *, days: int = 30) -> RatingSummary:
        """Get aggregated rating statistics."""
        summary_data = rating_repo.get_rating_summary(self.db, days=days)
        return RatingSummary(**summary_data)

    _CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
    _CSV_HEADER = [
        "ID", "Message ID", "Conversation ID", "User ID",
        "Rating", "Comment", "Message Content", "Message Role",
        "User Email", "User Name", "Created At", "Updated At",
    ]

    def _csv_escape(self, value: str) -> str:
        if value and value[0] in self._CSV_INJECTION_PREFIXES:
            return "'" + value
        return value

    def _csv_row_values(self, item: MessageRatingWithDetails) -> list[str]:
        return [
            self._csv_escape(str(item.id)),
            self._csv_escape(str(item.message_id)),
            self._csv_escape(str(item.conversation_id)) if item.conversation_id else "",
            self._csv_escape(str(item.user_id)),
            "Like" if item.rating == 1 else "Dislike",
            self._csv_escape(item.comment or ""),
            self._csv_escape(item.message_content or ""),
            self._csv_escape(item.message_role or ""),
            self._csv_escape(item.user_email or ""),
            self._csv_escape(item.user_name or ""),
            item.created_at.isoformat() if item.created_at else "",
            item.updated_at.isoformat() if item.updated_at else "",
        ]

    def _serialize_csv_row(self, values: list[str]) -> str:
        buffer = StringIO()
        csv.writer(buffer).writerow(values)
        return buffer.getvalue()

    def _validate_export_format(self, export_format: str) -> str:
        fmt = export_format.lower()
        if fmt not in ("json", "csv"):
            raise ValidationError(
                message="Invalid export format. Must be 'json' or 'csv'.",
                details={"export_format": export_format},
            )
        return fmt

    def _export_disposition(self, now: datetime, fmt: str) -> str:
        return f'attachment; filename="ratings_export_{now.strftime("%Y%m%d_%H%M%S")}.{fmt}"'

    def _json_export_response(
        self, items: list[MessageRatingWithDetails], now: datetime
    ) -> JSONResponse:
        return JSONResponse(
            content={
                "ratings": [item.model_dump(mode="json") for item in items],
                "total": len(items),
                "exported_at": now.isoformat(),
            },
            headers={"Content-Disposition": self._export_disposition(now, "json")},
        )

    def _stream_csv_sync(
        self, chunks: Iterable[list[MessageRatingWithDetails]], now: datetime
    ) -> StreamingResponse:
        def generate() -> Iterator[str]:
            yield self._serialize_csv_row(self._CSV_HEADER)
            for chunk in chunks:
                for item in chunk:
                    yield self._serialize_csv_row(self._csv_row_values(item))
        return StreamingResponse(
            generate(),
            media_type="text/csv",
            headers={"Content-Disposition": self._export_disposition(now, "csv")},
        )

    def export_ratings(
        self,
        *,
        export_format: str,
        rating_filter: int | None = None,
        with_comments_only: bool = False,
    ) -> JSONResponse | StreamingResponse:
        fmt = self._validate_export_format(export_format)
        now = datetime.now(UTC)
        chunks = self.export_all_ratings(
            rating_filter=rating_filter,
            with_comments_only=with_comments_only,
        )
        if fmt == "csv":
            return self._stream_csv_sync(chunks, now)
        all_items: list[MessageRatingWithDetails] = []
        for chunk in chunks:
            all_items.extend(chunk)
        return self._json_export_response(all_items, now)


{%- elif cookiecutter.use_mongodb %}
"""Message rating service (MongoDB async)."""

import csv
from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator
from datetime import UTC, datetime
from io import StringIO

from fastapi.responses import JSONResponse, StreamingResponse

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models.conversation import Message
from app.repositories import message_rating as rating_repo
from app.schemas.message_rating import (
    MessageRatingCreate,
    MessageRatingRead,
    MessageRatingWithDetails,
    RatingSummary,
    RatingValue,
)


class MessageRatingService:
    """Service for managing message ratings."""

    async def _get_message_role(self, message_id: str) -> str:
        """Get the role of a message.

        Raises:
            NotFoundError: If message doesn't exist
        """
        message = await Message.get(message_id)
        if not message:
            raise NotFoundError(message="Message not found", details={"message_id": message_id})
        return message.role

    async def _validate_message_in_conversation(
        self, message_id: str, conversation_id: str
    ) -> None:
        """Validate that a message belongs to the specified conversation.

        Raises:
            NotFoundError: If message doesn't exist or belongs to a different conversation
        """
        message = await Message.get(message_id)
        if not message:
            raise NotFoundError(message="Message not found", details={"message_id": message_id})
        if message.conversation_id != conversation_id:
            raise NotFoundError(
                message="Message not found in this conversation",
                details={"message_id": message_id, "conversation_id": conversation_id},
            )

    async def _validate_conversation_ownership(
        self, conversation_id: str, user_id: str
    ) -> None:
        """Validate that the conversation belongs to the specified user.

        Raises:
            NotFoundError: If conversation doesn't exist or belongs to a different user
        """
        from app.db.models.conversation import Conversation

        conv = await Conversation.get(conversation_id)
        if not conv or conv.user_id != user_id:
            raise NotFoundError(
                message="Conversation not found",
                details={"conversation_id": conversation_id},
            )

    async def rate_message(
        self,
        conversation_id: str,
        message_id: str,
        user_id: str,
        data: MessageRatingCreate,
    ) -> tuple[MessageRatingRead, bool]:
        """Rate or update rating for a message.

        Args:
            conversation_id: The conversation containing the message
            message_id: The message to rate
            user_id: The user rating the message
            data: Rating data (rating value, optional comment)

        Returns:
            Tuple of (rating, is_new) where is_new is True if created, False if updated

        Raises:
            ValidationError: If trying to rate a non-assistant message
            NotFoundError: If message doesn't exist or not in the specified conversation
        """
        # Validate conversation ownership and message belongs to it
        await self._validate_conversation_ownership(conversation_id, user_id)
        await self._validate_message_in_conversation(message_id, conversation_id)

        message_role = await self._get_message_role(message_id)
        if message_role != "assistant":
            raise ValidationError(
                message="Only assistant messages can be rated",
                details={"message_role": message_role},
            )

        # Check for existing rating
        existing = await rating_repo.get_rating_by_message_and_user(
            message_id, user_id
        )

        if existing:
            # Update existing rating
            updated = await rating_repo.update_rating(
                existing, new_rating=data.rating, comment=data.comment
            )
            return MessageRatingRead.model_validate(updated), False

        # Create new rating
        rating = await rating_repo.create_rating(
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
            rating=data.rating,
            comment=data.comment,
        )
        return MessageRatingRead.model_validate(rating), True

    async def remove_rating(
        self,
        conversation_id: str,
        message_id: str,
        user_id: str,
    ) -> None:
        """Remove a user's rating from a message.

        Args:
            conversation_id: The conversation containing the message
            message_id: The message to remove rating from
            user_id: The user who owns the rating

        Raises:
            NotFoundError: If message doesn't exist, not in conversation, or no rating exists
        """
        # Validate conversation ownership and message belongs to it
        await self._validate_conversation_ownership(conversation_id, user_id)
        await self._validate_message_in_conversation(message_id, conversation_id)

        rating = await rating_repo.get_rating_by_message_and_user(
            message_id, user_id
        )
        if not rating:
            raise NotFoundError(
                message="Rating not found",
                details={"message_id": message_id, "user_id": user_id},
            )
        await rating_repo.delete_rating(rating)

    async def get_message_ratings(
        self,
        message_id: str,
    ) -> dict[str, int]:
        """Get aggregate rating counts for a message.

        Returns:
            Dict with likes and dislikes count
        """
        ratings = await rating_repo.get_ratings_for_message(message_id)
        return {
            "likes": sum(1 for r in ratings if r.rating == 1),
            "dislikes": sum(1 for r in ratings if r.rating == -1),
        }

    async def list_ratings(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        rating_filter: int | None = None,
        with_comments_only: bool = False,
    ) -> tuple[list[MessageRatingWithDetails], int]:
        """List all ratings (admin only)."""
        items, total = await rating_repo.list_ratings(
            skip=skip,
            limit=limit,
            rating_filter=rating_filter,
            with_comments_only=with_comments_only,
        )

        if not items:
            return [], total

        # Batch fetch all related messages and users to avoid N+1 queries
{%- if cookiecutter.use_jwt %}
        from app.db.models.user import User

        message_ids = [item.message_id for item in items]
        user_ids = [item.user_id for item in items if item.user_id]

        # Fetch all messages
        messages = {msg.id: msg for msg in await Message.find({"_id": {"$in": message_ids}}).to_list()}

        # Fetch all users
        users = {user.id: user for user in await User.find({"_id": {"$in": user_ids}}).to_list()} if user_ids else {}
{%- else %}
        message_ids = [item.message_id for item in items]
        messages = {msg.id: msg for msg in await Message.find({"_id": {"$in": message_ids}}).to_list()}
        users = {}
{%- endif %}

        result = []
        for item in items:
            message = messages.get(item.message_id)
{%- if cookiecutter.use_jwt %}
            user = users.get(item.user_id) if item.user_id else None
{%- else %}
            user = None
{%- endif %}

            result.append(
                MessageRatingWithDetails(
                    id=item.id,
                    message_id=item.message_id,
                    user_id=item.user_id,
                    rating=RatingValue(item.rating),
                    comment=item.comment,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    message_content=(message.content or "")[:200] if message else None,
                    message_role=message.role if message else None,
                    conversation_id=message.conversation_id if message else None,
                    user_email=user.email if user else None,
                    user_name=user.full_name if user else None,
                )
            )

        return result, total

    EXPORT_CHUNK_SIZE = 5000

    async def export_all_ratings(
        self,
        *,
        rating_filter: int | None = None,
        with_comments_only: bool = False,
    ) -> AsyncGenerator[list[MessageRatingWithDetails], None]:
        """Yield all ratings in chunks for memory-efficient export.

        Fetches ratings in pages to avoid loading all ORM objects into
        memory at once. Each yielded chunk is a list of lightweight
        Pydantic schemas.
        """
        skip = 0
        while True:
            items, total = await rating_repo.list_ratings(
                skip=skip,
                limit=self.EXPORT_CHUNK_SIZE,
                rating_filter=rating_filter,
                with_comments_only=with_comments_only,
            )
            if not items:
                break

            # Batch fetch related messages and users
{%- if cookiecutter.use_jwt %}
            from app.db.models.user import User

            message_ids = [item.message_id for item in items]
            user_ids = [item.user_id for item in items if item.user_id]
            messages = {msg.id: msg for msg in await Message.find({"_id": {"$in": message_ids}}).to_list()}
            users = {user.id: user for user in await User.find({"_id": {"$in": user_ids}}).to_list()} if user_ids else {}
{%- else %}
            message_ids = [item.message_id for item in items]
            messages = {msg.id: msg for msg in await Message.find({"_id": {"$in": message_ids}}).to_list()}
{%- endif %}

            result = []
            for item in items:
                message = messages.get(item.message_id)
{%- if cookiecutter.use_jwt %}
                user = users.get(item.user_id) if item.user_id else None
{%- endif %}
                result.append(
                    MessageRatingWithDetails(
                        id=item.id,
                        message_id=item.message_id,
                        user_id=item.user_id,
                        rating=RatingValue(item.rating),
                        comment=item.comment,
                        created_at=item.created_at,
                        updated_at=item.updated_at,
                        message_content=(message.content or "")[:200] if message else None,
                        message_role=message.role if message else None,
                        conversation_id=message.conversation_id if message else None,
{%- if cookiecutter.use_jwt %}
                        user_email=user.email if user else None,
                        user_name=user.full_name if user else None,
{%- else %}
                        user_email=None,
                        user_name=None,
{%- endif %}
                    )
                )
            yield result
            skip += self.EXPORT_CHUNK_SIZE
            if skip >= total:
                break

    async def get_summary(self, *, days: int = 30) -> RatingSummary:
        """Get aggregated rating statistics."""
        summary_data = await rating_repo.get_rating_summary(days=days)
        return RatingSummary(**summary_data)

    _CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
    _CSV_HEADER = [
        "ID", "Message ID", "Conversation ID", "User ID",
        "Rating", "Comment", "Message Content", "Message Role",
        "User Email", "User Name", "Created At", "Updated At",
    ]

    def _csv_escape(self, value: str) -> str:
        if value and value[0] in self._CSV_INJECTION_PREFIXES:
            return "'" + value
        return value

    def _csv_row_values(self, item: MessageRatingWithDetails) -> list[str]:
        return [
            self._csv_escape(str(item.id)),
            self._csv_escape(str(item.message_id)),
            self._csv_escape(str(item.conversation_id)) if item.conversation_id else "",
            self._csv_escape(str(item.user_id)),
            "Like" if item.rating == 1 else "Dislike",
            self._csv_escape(item.comment or ""),
            self._csv_escape(item.message_content or ""),
            self._csv_escape(item.message_role or ""),
            self._csv_escape(item.user_email or ""),
            self._csv_escape(item.user_name or ""),
            item.created_at.isoformat() if item.created_at else "",
            item.updated_at.isoformat() if item.updated_at else "",
        ]

    def _serialize_csv_row(self, values: list[str]) -> str:
        buffer = StringIO()
        csv.writer(buffer).writerow(values)
        return buffer.getvalue()

    def _validate_export_format(self, export_format: str) -> str:
        fmt = export_format.lower()
        if fmt not in ("json", "csv"):
            raise ValidationError(
                message="Invalid export format. Must be 'json' or 'csv'.",
                details={"export_format": export_format},
            )
        return fmt

    def _export_disposition(self, now: datetime, fmt: str) -> str:
        return f'attachment; filename="ratings_export_{now.strftime("%Y%m%d_%H%M%S")}.{fmt}"'

    def _json_export_response(
        self, items: list[MessageRatingWithDetails], now: datetime
    ) -> JSONResponse:
        return JSONResponse(
            content={
                "ratings": [item.model_dump(mode="json") for item in items],
                "total": len(items),
                "exported_at": now.isoformat(),
            },
            headers={"Content-Disposition": self._export_disposition(now, "json")},
        )

    def _stream_csv_async(
        self, chunks: AsyncIterable[list[MessageRatingWithDetails]], now: datetime
    ) -> StreamingResponse:
        async def generate() -> AsyncIterator[str]:
            yield self._serialize_csv_row(self._CSV_HEADER)
            async for chunk in chunks:
                for item in chunk:
                    yield self._serialize_csv_row(self._csv_row_values(item))
        return StreamingResponse(
            generate(),
            media_type="text/csv",
            headers={"Content-Disposition": self._export_disposition(now, "csv")},
        )

    async def export_ratings(
        self,
        *,
        export_format: str,
        rating_filter: int | None = None,
        with_comments_only: bool = False,
    ) -> JSONResponse | StreamingResponse:
        fmt = self._validate_export_format(export_format)
        now = datetime.now(UTC)
        chunks = self.export_all_ratings(
            rating_filter=rating_filter,
            with_comments_only=with_comments_only,
        )
        if fmt == "csv":
            return self._stream_csv_async(chunks, now)
        all_items: list[MessageRatingWithDetails] = []
        async for chunk in chunks:
            all_items.extend(chunk)
        return self._json_export_response(all_items, now)


{%- endif %}
