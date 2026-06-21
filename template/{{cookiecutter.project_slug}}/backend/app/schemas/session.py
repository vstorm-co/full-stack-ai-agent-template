{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
"""Session schemas."""

from datetime import datetime
from uuid import UUID

from app.schemas.base import BaseSchema


class SessionRead(BaseSchema):
    """Session response schema."""

    id: UUID
    device_name: str | None = None
    device_type: str | None = None
    ip_address: str | None = None
    is_current: bool = False
    created_at: datetime
    last_used_at: datetime


class SessionListResponse(BaseSchema):
    """Response for list of sessions."""

    sessions: list[SessionRead]
    total: int


class LogoutAllResponse(BaseSchema):
    """Response for logout all sessions."""

    message: str
    sessions_logged_out: int
{%- else %}
"""Session schemas - not configured."""
{%- endif %}
