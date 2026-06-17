{%- if cookiecutter.use_pydantic_ai or cookiecutter.use_langchain or cookiecutter.use_langgraph or cookiecutter.use_crewai or cookiecutter.use_deepagents or cookiecutter.use_pydantic_deep %}
"""AI Agent WebSocket route.

The route is just lifecycle plumbing — auth, accept, dispatch loop, disconnect.
Per-turn orchestration lives in :class:`app.services.agent_session.AgentSession`.
"""

import logging
import secrets
from typing import Any
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt and cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from fastapi import APIRouter, WebSocket, WebSocketDisconnect{%- if cookiecutter.websocket_auth_jwt %}, Depends{%- endif %}{%- if cookiecutter.websocket_auth_api_key %}, Query{%- endif %}

from app.core.config import settings
from app.services.agent import AgentConnectionManager, send_event
from app.services.agent_session import AgentSession
{%- if cookiecutter.websocket_auth_jwt %}
from app.api.deps import get_current_user_ws
from app.db.models.user import User
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt and cookiecutter.use_postgresql %}
from app.agents.pydantic_deep_assistant import PydanticDeepContext, get_agent
from app.api.deps import get_conversation_service, get_project_service
from app.db.session import get_db_context
from app.schemas.conversation import ConversationCreate, MessageCreate
from pydantic_ai import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
)
from pydantic_ai.messages import TextPart
from pydantic_ai_backends import StateBackend
{%- endif %}

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

{%- if cookiecutter.websocket_auth_api_key %}


async def verify_api_key(api_key: str) -> bool:
    """Constant-time API key check. `==` would leak the key over WebSocket
    timings — `compare_digest` rejects in fixed time regardless of how much
    of the prefix matches."""
    return secrets.compare_digest(api_key, settings.API_KEY)
{%- endif %}


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User = Depends(get_current_user_ws),
{%- elif cookiecutter.websocket_auth_api_key %}
    api_key: str = Query(..., alias="api_key"),
{%- endif %}
) -> None:
    """WebSocket endpoint for the AI agent.

    Streams agent events to the client. Each incoming JSON message is forwarded to
    :class:`AgentSession.process_message`{% if cookiecutter.use_deepagents %}; ``{"type": "resume"}`` payloads are handled
    transparently by the session for human-in-the-loop tool approvals{% endif %}.

    Expected input format::

        {
            "message": "user message here",
            "file_ids": ["..."]{% if cookiecutter.use_database %},
            "conversation_id": "optional-uuid"{% endif %},
            "model": "optional-model-override",
            "thinking_effort": "optional"
        }
{%- if cookiecutter.websocket_auth_jwt %}

    Authentication: handled by ``get_current_user_ws`` (JWT).
{%- elif cookiecutter.websocket_auth_api_key %}

    Authentication: pass ``api_key`` as a query parameter.
{%- endif %}
    """
{%- if cookiecutter.websocket_auth_api_key %}
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- elif cookiecutter.websocket_auth_jwt %}
    if user is None:
        return
{%- endif %}

    await manager.connect(websocket)
    session = AgentSession(
        websocket,
{%- if cookiecutter.websocket_auth_jwt %}
        user,
{%- endif %}
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

{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt and cookiecutter.use_postgresql %}


@router.websocket("/ws/projects/{project_id}/chats/{conversation_id}")
async def project_chat_websocket(
    project_id: UUID,
    conversation_id: UUID,
    websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
    user: User = Depends(get_current_user_ws),
{%- elif cookiecutter.websocket_auth_api_key %}
    api_key: str = Query(..., alias="api_key"),
{%- endif %}
) -> None:
    """WebSocket endpoint for project-scoped PydanticDeep chat.

    One Docker container per project is shared across all chats.
    Chat history is stored per-chat inside the project volume at:
      .pydantic-deep/sessions/{conversation_id}/messages.json
    """
{%- if cookiecutter.websocket_auth_api_key %}
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- endif %}

    await manager.connect(websocket)

    context: PydanticDeepContext = {}
{%- if cookiecutter.websocket_auth_jwt %}
    context["user_id"] = str(user.id) if user else None
    context["user_name"] = user.email if user else None
{%- endif %}

    try:
        # Verify project access
        async with get_db_context() as db:
            project_service = get_project_service(db)
            try:
{%- if cookiecutter.websocket_auth_jwt %}
                await project_service.get(project_id, user_id=user.id)
{%- else %}
                await project_service.get(project_id)
{%- endif %}
            except Exception as exc:
                await websocket.close(code=4003, reason=str(exc))
                return

        backend: Any = StateBackend()

        assistant = get_agent(
            conversation_id=str(conversation_id),
            backend_override=backend,
            history_messages_path=f".pydantic-deep/sessions/{conversation_id}/messages.json",
        )

        # Ensure the conversation record exists and is linked to the project
        async with get_db_context() as db:
            conv_service = get_conversation_service(db)
            try:
                await conv_service.get_conversation(
                    conversation_id{% if cookiecutter.websocket_auth_jwt %}, user_id=user.id{% endif %}
                )
            except Exception:
                conv = await conv_service.create_conversation(
                    ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                        user_id=user.id,
{%- endif %}
                        project_id=project_id,
                    )
                )
                await send_event(
                    websocket,
                    "conversation_created",
                    {"conversation_id": str(conv.id), "project_id": str(project_id)},
                )

        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")

            if not user_message:
                await send_event(websocket, "error", {"message": "Empty message"})
                continue

            await send_event(websocket, "user_prompt", {"content": user_message})

            async with get_db_context() as db:
                conv_service = get_conversation_service(db)
                try:
                    await conv_service.add_message(
                        conversation_id,
                        MessageCreate(role="user", content=user_message),
                    )
                except Exception as exc:
                    logger.warning("Failed to persist user message: %s", exc)

            try:
                await send_event(websocket, "model_request_start", {})

                async with assistant.agent.run_stream(
                    user_message, deps=assistant.deps
                ) as stream:
                    async for event in stream.stream_events():
                        if isinstance(event, PartDeltaEvent) and isinstance(
                            event.delta, TextPartDelta
                        ):
                            await send_event(
                                websocket, "text_delta", {"delta": event.delta.content_delta}
                            )
                        elif isinstance(event, PartStartEvent) and isinstance(
                            event.part, TextPart
                        ):
                            pass
                        elif isinstance(event, FunctionToolCallEvent):
                            await send_event(
                                websocket,
                                "tool_call",
                                {
                                    "tool_name": event.part.tool_name,
                                    "args": str(event.part.args),
                                },
                            )
                        elif isinstance(event, FunctionToolResultEvent):
                            await send_event(
                                websocket,
                                "tool_result",
                                {
                                    "tool_name": event.result.tool_name,
                                    "content": str(event.result.content),
                                },
                            )
                        elif isinstance(event, FinalResultEvent):
                            await send_event(
                                websocket, "final_result", {"content": str(event.output)}
                            )

                    result = stream.result()

                async with get_db_context() as db:
                    conv_service = get_conversation_service(db)
                    try:
                        await conv_service.add_message(
                            conversation_id,
                            MessageCreate(
                                role="assistant",
                                content=getattr(result, "output", ""),
                                model_name=getattr(assistant, "model_name", None),
                            ),
                        )
                    except Exception as exc:
                        logger.warning("Failed to persist assistant response: %s", exc)

                await send_event(
                    websocket,
                    "complete",
                    {
                        "conversation_id": str(conversation_id),
                        "project_id": str(project_id),
                    },
                )

            except WebSocketDisconnect:
                logger.info("Client disconnected during project chat")
                break
            except Exception as exc:
                logger.exception("Error in project chat: %s", exc)
                await send_event(websocket, "error", {"message": str(exc)})

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
{%- endif %}
{%- else %}
"""AI Agent routes - not configured."""
{%- endif %}
