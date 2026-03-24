{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
"""Session management routes."""

from typing import Any

from fastapi import APIRouter, status
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from app.api.deps import CurrentUser, SessionSvc
from app.schemas.session import LogoutAllResponse, SessionListResponse, SessionRead

router = APIRouter()


{%- if cookiecutter.use_postgresql %}


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    current_user: CurrentUser,
    session_service: SessionSvc,
) -> Any:
    """Get all active sessions for the current user."""
    sessions = await session_service.get_user_sessions(current_user.id)
    return SessionListResponse(
        sessions=[
            SessionRead(
                id=s.id,
                device_name=s.device_name,
                device_type=s.device_type,
                ip_address=s.ip_address,
                is_current=False,  # TODO: compare with current session
                created_at=s.created_at,
                last_used_at=s.last_used_at,
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout_session(
    session_id: UUID,
    current_user: CurrentUser,
    session_service: SessionSvc,
) -> None:
    """Logout a specific session."""
    await session_service.logout_session(session_id, current_user.id)


@router.delete("", response_model=LogoutAllResponse)
async def logout_all_sessions(
    current_user: CurrentUser,
    session_service: SessionSvc,
) -> Any:
    """Logout from all sessions (logout from all devices)."""
    count = await session_service.logout_all_sessions(current_user.id)
    return LogoutAllResponse(
        message="Successfully logged out from all sessions",
        sessions_logged_out=count,
    )


{%- elif cookiecutter.use_mongodb %}


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    current_user: CurrentUser,
    session_service: SessionSvc,
) -> Any:
    """Get all active sessions for the current user."""
    sessions = await session_service.get_user_sessions(str(current_user.id))
    return SessionListResponse(
        sessions=[
            SessionRead(
                id=str(s.id),
                device_name=s.device_name,
                device_type=s.device_type,
                ip_address=s.ip_address,
                is_current=False,
                created_at=s.created_at,
                last_used_at=s.last_used_at,
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout_session(
    session_id: str,
    current_user: CurrentUser,
    session_service: SessionSvc,
) -> None:
    """Logout a specific session."""
    await session_service.logout_session(session_id, str(current_user.id))


@router.delete("", response_model=LogoutAllResponse)
async def logout_all_sessions(
    current_user: CurrentUser,
    session_service: SessionSvc,
) -> Any:
    """Logout from all sessions (logout from all devices)."""
    count = await session_service.logout_all_sessions(str(current_user.id))
    return LogoutAllResponse(
        message="Successfully logged out from all sessions",
        sessions_logged_out=count,
    )


{%- elif cookiecutter.use_sqlite %}


@router.get("", response_model=SessionListResponse)
def list_sessions(
    current_user: CurrentUser,
    session_service: SessionSvc,
) -> Any:
    """Get all active sessions for the current user."""
    sessions = session_service.get_user_sessions(current_user.id)
    return SessionListResponse(
        sessions=[
            SessionRead(
                id=s.id,
                device_name=s.device_name,
                device_type=s.device_type,
                ip_address=s.ip_address,
                is_current=False,
                created_at=s.created_at,
                last_used_at=s.last_used_at,
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout_session(
    session_id: str,
    current_user: CurrentUser,
    session_service: SessionSvc,
) -> None:
    """Logout a specific session."""
    session_service.logout_session(session_id, current_user.id)


@router.delete("", response_model=LogoutAllResponse)
def logout_all_sessions(
    current_user: CurrentUser,
    session_service: SessionSvc,
) -> Any:
    """Logout from all sessions (logout from all devices)."""
    count = session_service.logout_all_sessions(current_user.id)
    return LogoutAllResponse(
        message="Successfully logged out from all sessions",
        sessions_logged_out=count,
    )


{%- endif %}
{%- else %}
"""Session routes - not configured."""
{%- endif %}
