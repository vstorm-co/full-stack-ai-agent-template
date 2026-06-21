"""Shared agent service utilities.

Houses framework-agnostic helpers used by every WebSocket agent route:
  - ``AgentConnectionManager`` + ``send_event`` — WebSocket fan-out
  - ``build_message_history`` — convert dicts to provider-native messages
  - ``persist_user_turn`` / ``persist_assistant_turn`` — DB persistence
  - ``resolve_kb_collections`` — Teams+RAG collection lookup
  - ``normalize_tool_args`` / ``truncate_title`` — small utilities

Framework-specific concerns (multimodal input, streaming events) stay in the route.
"""

import logging
from typing import Any
{%- if cookiecutter.use_database %}
import json
from datetime import UTC, datetime
from uuid import UUID
{%- endif %}

from fastapi import WebSocket, WebSocketDisconnect
{%- if cookiecutter.use_pydantic_ai %}
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
{%- elif cookiecutter.use_langchain or cookiecutter.use_langgraph or cookiecutter.use_deepagents %}
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
{%- endif %}

{%- if cookiecutter.use_database %}
from app.api.deps import get_conversation_service
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
    ToolCallComplete,
    ToolCallCreate,
)
from app.db.session import get_db_context
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
from app.services.knowledge_base import KnowledgeBaseService
{%- endif %}
{%- if cookiecutter.enable_teams %}
from app.repositories import organization_repo
{%- endif %}

logger = logging.getLogger(__name__)


async def send_event(websocket: WebSocket, event_type: str, data: Any) -> bool:
    """Send a JSON event to a WebSocket client.

    Returns True if sent successfully, False if the connection is already closed.
    """
    try:
        await websocket.send_json({"type": event_type, "data": data})
        return True
    except (WebSocketDisconnect, RuntimeError):
        return False


class AgentConnectionManager:
    """WebSocket connection manager for AI agent."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a new WebSocket connection."""
        # Echo back the application subprotocol chosen during auth (if any)
        subprotocol = getattr(websocket.state, "accept_subprotocol", None)
        await websocket.accept(subprotocol=subprotocol)
        self.active_connections.append(websocket)
        logger.info("Agent WebSocket connected. Total connections: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("Agent WebSocket disconnected. Total connections: %d", len(self.active_connections))

    async def send_event(self, websocket: WebSocket, event_type: str, data: Any) -> bool:
        """Forward to the module-level :func:`send_event`."""
        return await send_event(websocket, event_type, data)


{%- if cookiecutter.use_pydantic_ai %}


def build_message_history(history: list[dict[str, str]]) -> list[ModelRequest | ModelResponse]:
    """Convert conversation history to PydanticAI message format."""
    model_history: list[ModelRequest | ModelResponse] = []

    for msg in history:
        if msg["role"] == "user":
            model_history.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
        elif msg["role"] == "assistant":
            model_history.append(ModelResponse(parts=[TextPart(content=msg["content"])]))
        elif msg["role"] == "system":
            model_history.append(ModelRequest(parts=[SystemPromptPart(content=msg["content"])]))

    return model_history
{%- elif cookiecutter.use_langchain or cookiecutter.use_langgraph or cookiecutter.use_deepagents %}


def build_message_history(
    history: list[dict[str, str]],
) -> list[HumanMessage | AIMessage | SystemMessage]:
    """Convert conversation history to LangChain message format."""
    messages: list[HumanMessage | AIMessage | SystemMessage] = []

    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
        elif msg["role"] == "system":
            messages.append(SystemMessage(content=msg["content"]))

    return messages
{%- endif %}

{%- if cookiecutter.use_database %}


def truncate_title(text: str, limit: int = 50) -> str:
    """Return text truncated to ``limit`` characters."""
    return text[:limit] if len(text) > limit else text


async def persist_user_turn(
{%- if cookiecutter.websocket_auth_jwt %}
    user: Any,
{%- endif %}
    user_message: str,
    file_ids: list[Any],
    requested_conversation_id: str | None,
    current_conversation_id: str | None,
) -> tuple[str | None, bool, str | None]:
    """Resolve the conversation, persist the user message, and link any uploaded files.

    Returns ``(conversation_id, was_newly_created, organization_id)``. When
    ``was_newly_created`` is True the caller should emit a ``conversation_created``
    WebSocket event. ``organization_id`` is the conversation's owning org (the user's
    Personal org for new conversations) so usage events can be billed correctly;
    None when teams are disabled or no org context is available.
    """
    newly_created = False
    organization_id: str | None = None
    try:
        async with get_db_context() as db:
            conv_service = get_conversation_service(db)

            if requested_conversation_id:
                current_conversation_id = requested_conversation_id
                conv = await conv_service.get_conversation(UUID(requested_conversation_id){% if cookiecutter.websocket_auth_jwt %}, user_id=user.id{% endif %})
                if not conv.title and user_message:
                    await conv_service.update_conversation(
                        UUID(requested_conversation_id),
                        ConversationUpdate(title=truncate_title(user_message)),
{%- if cookiecutter.websocket_auth_jwt %}
                        user_id=user.id,
{%- endif %}
                    )
{%- if cookiecutter.enable_teams %}
                if getattr(conv, "organization_id", None) is not None:
                    organization_id = str(conv.organization_id)
{%- endif %}
            elif not current_conversation_id:
{%- if cookiecutter.enable_teams and cookiecutter.websocket_auth_jwt %}
                personal_org = await organization_repo.get_personal_for_user(db, user.id)
                if personal_org is not None:
                    organization_id = str(personal_org.id)
{%- endif %}
                conversation = await conv_service.create_conversation(
                    ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                        user_id=user.id,
{%- endif %}
{%- if cookiecutter.use_external_user_id_in_conversations and cookiecutter.websocket_auth_jwt %}
                        external_user_id=getattr(user, "external_user_id", None),
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.websocket_auth_jwt %}
                        organization_id=personal_org.id if personal_org else None,
{%- endif %}
                        title=truncate_title(user_message),
                    )
                )
                current_conversation_id = str(conversation.id)
                newly_created = True

            user_msg = await conv_service.add_message(
                UUID(current_conversation_id),
                MessageCreate(role="user", content=user_message),
            )
            if file_ids:
                try:
                    await conv_service.link_files_to_message(user_msg.id, file_ids)
                except Exception as e:
                    logger.warning("Failed to link files: %s", e)
    except Exception as e:
        logger.warning("Failed to persist conversation: %s", e)

    return current_conversation_id, newly_created, organization_id


def normalize_tool_args(args: Any) -> dict[str, Any]:
    """Coerce a tool-call ``args`` payload to a dict (handles JSON strings + None)."""
    if isinstance(args, str):
        return json.loads(args) if args.strip() else {}
    if args is None:
        return {}
    return args


async def persist_assistant_turn(
    conversation_id: str,
    output: str,
    model_name: str | None,
    collected_tool_calls: list[dict[str, Any]],
) -> str | None:
    """Persist the assistant message and any tool calls. Returns the saved message id."""
    try:
        async with get_db_context() as db:
            conv_service = get_conversation_service(db)
            assistant_msg = await conv_service.add_message(
                UUID(conversation_id),
                MessageCreate(role="assistant", content=output, model_name=model_name),
            )
            for tc in collected_tool_calls:
                try:
                    tc_obj = await conv_service.start_tool_call(
                        assistant_msg.id,
                        ToolCallCreate(
                            tool_call_id=tc["tool_call_id"],
                            tool_name=tc["tool_name"],
                            args=normalize_tool_args(tc.get("args")),
                            started_at=datetime.now(UTC),
                        ),
                    )
                    if tc.get("result"):
                        await conv_service.complete_tool_call(
                            tc_obj.id,
                            ToolCallComplete(
                                result=tc["result"],
                                completed_at=datetime.now(UTC),
                                success=True,
                            ),
                        )
                except Exception as e:
                    logger.warning("Failed to persist tool call: %s", e)
            return str(assistant_msg.id)
    except Exception as e:
        logger.warning("Failed to persist assistant response: %s", e)
        return None
{%- endif %}

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}


async def resolve_kb_collections(
    conversation_id: str | None,
{%- if cookiecutter.websocket_auth_jwt %}
    user_id: Any,
{%- endif %}
    override_kb_ids: list[str] | None = None,
    organization_id: str | None = None,
) -> list[str]:
    """Return active KB collection names for the conversation.

    When ``override_kb_ids`` is provided (e.g. the client included a draft
    selection in the WS payload before the conversation was saved), those IDs
    are intersected with KBs the user can access and returned directly. Only
    IDs come from the client — collection names are always resolved against
    the user's accessible KBs server-side.
    """
    if override_kb_ids is not None:
        async with get_db_context() as db:
            kb_service = KnowledgeBaseService(db)
            org_uuid = UUID(organization_id) if organization_id else None
            return await kb_service.resolve_collection_names_for_ids(
                kb_ids=[UUID(i) for i in override_kb_ids if i],
{%- if cookiecutter.websocket_auth_jwt %}
                user_id=user_id,
{%- else %}
                user_id=None,
{%- endif %}
                organization_id=org_uuid,
            )
    if not conversation_id:
        return []
    async with get_db_context() as db:
        kb_service = KnowledgeBaseService(db)
        return await kb_service.resolve_active_collection_names(
            UUID(conversation_id),
{%- if cookiecutter.websocket_auth_jwt %}
            user_id,
{%- else %}
            None,
{%- endif %}
        )
{%- endif %}
