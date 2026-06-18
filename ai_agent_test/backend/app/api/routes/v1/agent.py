"""AI Agent WebSocket route.

The route is just lifecycle plumbing — auth, accept, dispatch loop, disconnect.
Per-turn orchestration lives in :class:`app.services.agent_session.AgentSession`.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.deps import get_current_user_ws
from app.core.config import settings
from app.db.models.user import User
from app.services.agent import AgentConnectionManager
from app.services.agent_session import AgentSession

logger = logging.getLogger(__name__)

router = APIRouter()

manager = AgentConnectionManager()


@router.get("/agent/models")
async def list_models() -> dict[str, Any]:
    """Return available LLM models and the current default."""
    return {
        "default": settings.AI_MODEL,
        "models": settings.AI_AVAILABLE_MODELS,
    }


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
    user: User = Depends(get_current_user_ws),
) -> None:
    """WebSocket endpoint for the AI agent.

    Streams agent events to the client. Each incoming JSON message is forwarded to
    :class:`AgentSession.process_message`.

    Expected input format::

        {
            "message": "user message here",
            "file_ids": ["..."],
            "conversation_id": "optional-uuid",
            "model": "optional-model-override",
            "thinking_effort": "optional"
        }

    Authentication: handled by ``get_current_user_ws`` (JWT).
    """
    if user is None:
        return

    await manager.connect(websocket)
    session = AgentSession(
        websocket,
        user,
    )

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            await session.handle_frame(data)
    finally:
        await session.shutdown()
        manager.disconnect(websocket)
