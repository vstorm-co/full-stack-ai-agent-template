"""Session schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SessionRead(BaseModel):
    """Session response schema."""

    id: UUID
    device_name: str | None = None
    device_type: str | None = None
    ip_address: str | None = None
    is_current: bool = False
    created_at: datetime
    last_used_at: datetime


class SessionListResponse(BaseModel):
    """Response for list of sessions."""

    sessions: list[SessionRead]
    total: int


class LogoutAllResponse(BaseModel):
    """Response for logout all sessions."""

    message: str
    sessions_logged_out: int
