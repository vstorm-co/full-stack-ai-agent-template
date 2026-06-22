"""Base Pydantic schemas."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict


def serialize_datetime(dt: datetime) -> str:
    """Serialize datetime to ISO format with timezone.

    Ensures all datetimes have explicit timezone (defaults to UTC).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.isoformat()


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        json_encoders={datetime: serialize_datetime},
    )

    def serializable_dict(self, **kwargs: Any) -> dict[str, Any]:
        """Return a dict with only JSON-serializable fields."""
        result: dict[str, Any] = jsonable_encoder(self.model_dump(**kwargs))
        return result


class TimestampSchema(BaseModel):
    """Schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime | None = None


class BaseResponse(BaseModel):
    """Standard API response."""

    success: bool = True
    message: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = False
    error: str
    detail: str | None = None
    code: str | None = None


class AgentModelsResponse(BaseModel):
    default: str
    models: list[str]


class HealthResponse(BaseModel):
    status: str
    max_upload_size_mb: int | None = None


class HealthDetailResponse(BaseModel):
    status: str
    timestamp: str
    service: str
    checks: dict[str, Any] | None = None
    details: dict[str, Any] | None = None
