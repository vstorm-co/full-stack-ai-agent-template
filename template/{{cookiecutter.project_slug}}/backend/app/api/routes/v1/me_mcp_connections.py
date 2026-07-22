"""User-scoped MCP server connections (Settings → Integrations).

Routes are nested under ``/me/mcp-connections`` because they always operate
on the current user — there's no cross-user view of these. The stored bearer
token never appears in any response (only ``has_auth_token``).
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.agents.mcp_oauth import OAuthError
from app.api.deps import CurrentUser, McpConnectionSvc
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.schemas.mcp_connection import (
    McpConnectionCreate,
    McpConnectionList,
    McpConnectionRead,
    McpConnectionTestResult,
    McpConnectionUpdate,
    McpOAuthCallback,
    McpOAuthCallbackResult,
    McpOAuthStart,
    McpOAuthStartResult,
    McpToolRead,
    WorkspaceMcpServerList,
    WorkspaceMcpServerRead,
)

router = APIRouter()


@router.get("/workspace", response_model=WorkspaceMcpServerList)
async def list_workspace_mcp_servers(user: CurrentUser) -> Any:
    """Deployment-managed MCP servers (MCP_SERVERS) — always-on, read-only."""
    items = [
        WorkspaceMcpServerRead(name=cfg.name, allowed_tools=cfg.allowed_tools)
        for cfg in settings.MCP_SERVERS
    ]
    return WorkspaceMcpServerList(items=items, total=len(items))


@router.get("", response_model=McpConnectionList)
async def list_mcp_connections(service: McpConnectionSvc, user: CurrentUser) -> Any:
    """List the current user's MCP server connections."""
    items, total = await service.list_for_user(user_id=user.id)
    return McpConnectionList(
        items=[McpConnectionRead.from_model(c) for c in items],
        total=total,
    )


@router.post("", response_model=McpConnectionRead, status_code=status.HTTP_201_CREATED)
async def create_mcp_connection(
    data: McpConnectionCreate,
    service: McpConnectionSvc,
    user: CurrentUser,
) -> Any:
    """Add an MCP server connection. The URL is SSRF-validated."""
    db_connection = await service.create(user_id=user.id, data=data)
    return McpConnectionRead.from_model(db_connection)


@router.patch("/{connection_id}", response_model=McpConnectionRead)
async def update_mcp_connection(
    connection_id: UUID,
    data: McpConnectionUpdate,
    service: McpConnectionSvc,
    user: CurrentUser,
) -> Any:
    """Patch a connection. ``auth_token: ""`` clears the stored token."""
    db_connection = await service.update(user_id=user.id, connection_id=connection_id, data=data)
    return McpConnectionRead.from_model(db_connection)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_mcp_connection(
    connection_id: UUID,
    service: McpConnectionSvc,
    user: CurrentUser,
) -> Any:
    """Remove a connection."""
    await service.delete(user_id=user.id, connection_id=connection_id)
    return None


@router.post("/oauth/start", response_model=McpOAuthStartResult)
async def start_mcp_oauth(
    data: McpOAuthStart,
    service: McpConnectionSvc,
    user: CurrentUser,
) -> Any:
    """Begin the OAuth flow; returns the provider consent URL to redirect to."""
    try:
        authorization_url = await service.oauth_start(
            user_id=user.id, name=data.name, url=data.url
        )
    except OAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return McpOAuthStartResult(authorization_url=authorization_url)


@router.post("/oauth/callback", response_model=McpOAuthCallbackResult)
async def complete_mcp_oauth(
    data: McpOAuthCallback,
    service: McpConnectionSvc,
) -> Any:
    """Finish the OAuth flow. Authenticated by the ``state`` token (no session),
    so the provider redirect can reach it without our auth cookie."""
    try:
        connection = await service.oauth_callback(state=data.state, code=data.code)
    except (OAuthError, NotFoundError) as exc:
        return McpOAuthCallbackResult(ok=False, error=str(exc))
    return McpOAuthCallbackResult(ok=True, connection_name=connection.name)


@router.post("/{connection_id}/test", response_model=McpConnectionTestResult)
async def test_mcp_connection(
    connection_id: UUID,
    service: McpConnectionSvc,
    user: CurrentUser,
) -> Any:
    """Probe the server and return its tool list; persists last_status."""
    _connection, tools, error = await service.test(user_id=user.id, connection_id=connection_id)
    return McpConnectionTestResult(
        ok=error is None,
        error=error,
        tools=[McpToolRead(name=t.name, description=t.description) for t in tools],
    )
