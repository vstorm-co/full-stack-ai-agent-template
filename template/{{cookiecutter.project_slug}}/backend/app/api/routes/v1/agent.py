{%- if cookiecutter.use_pydantic_ai %}
"""AI Agent WebSocket routes with streaming support (PydanticAI)."""

import logging
from typing import Any
from sqlalchemy import select
{%- if cookiecutter.use_database %}
from datetime import datetime, UTC
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}
{%- endif %}

from fastapi import APIRouter, WebSocket, WebSocketDisconnect{%- if cookiecutter.websocket_auth_jwt %}, Depends{%- endif %}{%- if cookiecutter.websocket_auth_api_key %}, Query{%- endif %}

from pydantic_ai import (
    Agent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPartDelta,
)
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)

from app.agents.assistant import Deps, get_agent
{%- if cookiecutter.websocket_auth_jwt %}
from app.api.deps import get_current_user_ws
from app.db.models.user import User
{%- endif %}
{%- if cookiecutter.websocket_auth_api_key %}
from app.core.config import settings
{%- endif %}
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
from app.db.session import get_db_context{% if cookiecutter.use_sqlite %}, get_db_session
from contextlib import contextmanager{% endif %}
from app.api.deps import ConversationSvc, get_conversation_service
from app.schemas.conversation import ConversationCreate, ConversationUpdate, MessageCreate, ToolCallCreate, ToolCallComplete
{%- elif cookiecutter.use_mongodb %}
from app.api.deps import ConversationSvc, get_conversation_service
from app.schemas.conversation import ConversationCreate, ConversationUpdate, MessageCreate, ToolCallCreate, ToolCallComplete
{%- endif %}

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/agent/models")
async def list_models() -> dict[str, Any]:
    """Return available LLM models and the current default."""
    from app.core.config import settings
    return {
        "default": settings.AI_MODEL,
        "models": settings.AI_AVAILABLE_MODELS,
    }


class AgentConnectionManager:
    """WebSocket connection manager for AI agent."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Agent WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Agent WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_event(self, websocket: WebSocket, event_type: str, data: Any) -> bool:
        """Send a JSON event to a specific WebSocket client.

        Returns True if sent successfully, False if connection is closed.
        """
        try:
            await websocket.send_json({"type": event_type, "data": data})
            return True
        except (WebSocketDisconnect, RuntimeError):
            # Connection already closed
            return False


manager = AgentConnectionManager()


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

{%- if cookiecutter.websocket_auth_api_key %}


async def verify_api_key(api_key: str) -> bool:
    """Verify the API key for WebSocket authentication."""
    return api_key == settings.API_KEY
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
    """WebSocket endpoint for AI agent with full event streaming.

    Uses PydanticAI iter() to stream all agent events including:
    - user_prompt: When user input is received
    - model_request_start: When model request begins
    - text_delta: Streaming text from the model
    - tool_call_delta: Streaming tool call arguments
    - tool_call: When a tool is called (with full args)
    - tool_result: When a tool returns a result
    - final_result: When the final result is ready
    - complete: When processing is complete
    - error: When an error occurs

    Expected input message format:
    {
        "message": "user message here",
        "history": [{"role": "user|assistant|system", "content": "..."}]{% if cookiecutter.use_database %},
        "conversation_id": "optional-uuid-to-continue-existing-conversation"{% endif %}
    }
{%- if cookiecutter.websocket_auth_jwt %}

    Authentication: Requires a valid JWT token passed as a query parameter or header.
{%- elif cookiecutter.websocket_auth_api_key %}

    Authentication: Requires a valid API key passed as 'api_key' query parameter.
    Example: ws://localhost:{{ cookiecutter.backend_port }}/api/v1/ws/agent?api_key=your-api-key
{%- endif %}
{%- if cookiecutter.use_database %}

    Persistence: Set 'conversation_id' to continue an existing conversation.
    If not provided, a new conversation is created. The conversation_id is
    returned in the 'conversation_created' event.
{%- endif %}
    """
{%- if cookiecutter.websocket_auth_api_key %}
    # Verify API key before accepting connection
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- endif %}

    await manager.connect(websocket)

    # Conversation state per connection
    conversation_history: list[dict[str, str]] = []
    deps = Deps()
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None = None
{%- endif %}

    try:
        while True:
            # Receive user message
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            file_ids = data.get("file_ids", [])

            if not user_message and not file_ids:
                await manager.send_event(websocket, "error", {"message": "Empty message"})
                continue

{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}

            # Handle conversation persistence
            try:
{%- if cookiecutter.use_postgresql %}
                async with get_db_context() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        # Verify conversation exists and update title if empty
                        conv = await conv_service.get_conversation(UUID(requested_conv_id))
                        if not conv.title and user_message:
                            title = user_message[:50] if len(user_message) > 50 else user_message
                            await conv_service.update_conversation(UUID(requested_conv_id), ConversationUpdate(title=title))
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                            user_id=user.id,
{%- endif %}
                            title=user_message[:50] if len(user_message) > 50 else user_message,
                        )
                        conversation = await conv_service.create_conversation(conv_data)
                        current_conversation_id = str(conversation.id)
                        await manager.send_event(
                            websocket,
                            "conversation_created",
                            {"conversation_id": current_conversation_id},
                        )

                    # Save user message
                    user_msg = await conv_service.add_message(
                        UUID(current_conversation_id),
                        MessageCreate(role="user", content=user_message),
                    )
                    # Link uploaded files to this message
                    if file_ids:
                        try:
                            await conv_service.link_files_to_message(user_msg.id, file_ids)
                        except Exception as e:
                            logger.warning(f"Failed to link files: {e}")
{%- else %}
                with contextmanager(get_db_session)() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        conv = conv_service.get_conversation(requested_conv_id)
                        if not conv.title and user_message:
                            title = user_message[:50] if len(user_message) > 50 else user_message
                            conv_service.update_conversation(requested_conv_id, ConversationUpdate(title=title))
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                            user_id=str(user.id),
{%- endif %}
                            title=user_message[:50] if len(user_message) > 50 else user_message,
                        )
                        conversation = conv_service.create_conversation(conv_data)
                        current_conversation_id = str(conversation.id)
                        await manager.send_event(
                            websocket,
                            "conversation_created",
                            {"conversation_id": current_conversation_id},
                        )

                    # Save user message
                    user_msg = conv_service.add_message(
                        current_conversation_id,
                        MessageCreate(role="user", content=user_message),
                    )
                    # Link uploaded files to this message
                    if file_ids:
                        try:
                            conv_service.link_files_to_message(user_msg.id, file_ids)
                        except Exception as e:
                            logger.warning(f"Failed to link files: {e}")
{%- endif %}
            except Exception as e:
                logger.warning(f"Failed to persist conversation: {e}")
                # Continue without persistence
{%- elif cookiecutter.use_mongodb %}

            # Handle conversation persistence (MongoDB)
            conv_service = get_conversation_service()

            requested_conv_id = data.get("conversation_id")
            if requested_conv_id:
                current_conversation_id = requested_conv_id
                conv = await conv_service.get_conversation(requested_conv_id)
                if not conv.title and user_message:
                    title = user_message[:50] if len(user_message) > 50 else user_message
                    await conv_service.update_conversation(requested_conv_id, ConversationUpdate(title=title))
            elif not current_conversation_id:
                conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                    user_id=str(user.id),
{%- endif %}
                    title=user_message[:50] if len(user_message) > 50 else user_message,
                )
                conversation = await conv_service.create_conversation(conv_data)
                current_conversation_id = str(conversation.id)
                await manager.send_event(
                    websocket,
                    "conversation_created",
                    {"conversation_id": current_conversation_id},
                )

            # Save user message
            await conv_service.add_message(
                current_conversation_id,
                MessageCreate(role="user", content=user_message),
            )
{%- endif %}

            await manager.send_event(websocket, "user_prompt", {"content": user_message})

            try:
                selected_model = data.get("model")
                assistant = get_agent(model_name=selected_model)
                model_history = build_message_history(conversation_history)

                # Collect tool calls during streaming for persistence
                collected_tool_calls: list[dict[str, Any]] = []

{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
                # Load attached files and build multimodal input
                from pydantic_ai.messages import BinaryContent
                from app.db.models.chat_file import ChatFile as ChatFileModel
                from app.services.file_storage import get_file_storage

                user_input: str | list[Any] = user_message
                file_context_parts: list[str] = []

                if file_ids:
                    storage = get_file_storage()
                    image_parts = []
{%- if cookiecutter.use_postgresql %}
                    async with get_db_context() as file_db:
                        for fid in file_ids:
                            try:
                                result = await file_db.execute(select(ChatFileModel).where(ChatFileModel.id == UUID(fid)))
                                chat_file = result.scalar_one_or_none()
                                if not chat_file:
                                    continue
                                if chat_file.file_type == "image":
                                    file_data = await storage.load(chat_file.storage_path)
                                    image_parts.append(BinaryContent(data=file_data, media_type=chat_file.mime_type))
                                elif chat_file.parsed_content:
                                    file_context_parts.append(f"\n---\nAttached file: {chat_file.filename}\n```\n{chat_file.parsed_content}\n```")
                            except Exception as e:
                                logger.warning(f"Failed to load file {fid}: {e}")
{%- else %}
                    with contextmanager(get_db_session)() as file_db:
                        for fid in file_ids:
                            try:
                                result = file_db.execute(select(ChatFileModel).where(ChatFileModel.id == fid))
                                chat_file = result.scalar_one_or_none()
                                if not chat_file:
                                    continue
                                if chat_file.file_type == "image":
                                    file_data = await storage.load(chat_file.storage_path)
                                    image_parts.append(BinaryContent(data=file_data, media_type=chat_file.mime_type))
                                elif chat_file.parsed_content:
                                    file_context_parts.append(f"\n---\nAttached file: {chat_file.filename}\n```\n{chat_file.parsed_content}\n```")
                            except Exception as e:
                                logger.warning(f"Failed to load file {fid}: {e}")
{%- endif %}

                    if image_parts:
                        full_text = user_message + "".join(file_context_parts)
                        user_input = [full_text, *image_parts]
                    elif file_context_parts:
                        user_input = user_message + "".join(file_context_parts)
{%- else %}
                user_input = user_message
{%- endif %}

                # Use iter() on the underlying PydanticAI agent to stream all events
                async with assistant.agent.iter(
                    user_input,
                    deps=deps,
                    message_history=model_history,
                ) as agent_run:
                    async for node in agent_run:
                        if Agent.is_user_prompt_node(node):
                            prompt_text = node.user_prompt if isinstance(node.user_prompt, str) else user_message
                            await manager.send_event(
                                websocket,
                                "user_prompt_processed",
                                {"prompt": prompt_text},
                            )

                        elif Agent.is_model_request_node(node):
                            await manager.send_event(websocket, "model_request_start", {})

                            async with node.stream(agent_run.ctx) as request_stream:
                                async for event in request_stream:
                                    if isinstance(event, PartStartEvent):
                                        await manager.send_event(
                                            websocket,
                                            "part_start",
                                            {
                                                "index": event.index,
                                                "part_type": type(event.part).__name__,
                                            },
                                        )
                                        # Send initial content from TextPart if present
                                        if isinstance(event.part, TextPart) and event.part.content:
                                            await manager.send_event(
                                                websocket,
                                                "text_delta",
                                                {
                                                    "index": event.index,
                                                    "content": event.part.content,
                                                },
                                            )

                                    elif isinstance(event, PartDeltaEvent):
                                        if isinstance(event.delta, TextPartDelta):
                                            await manager.send_event(
                                                websocket,
                                                "text_delta",
                                                {
                                                    "index": event.index,
                                                    "content": event.delta.content_delta,
                                                },
                                            )
                                        elif isinstance(event.delta, ToolCallPartDelta):
                                            await manager.send_event(
                                                websocket,
                                                "tool_call_delta",
                                                {
                                                    "index": event.index,
                                                    "args_delta": event.delta.args_delta,
                                                },
                                            )

                                    elif isinstance(event, FinalResultEvent):
                                        await manager.send_event(
                                            websocket,
                                            "final_result_start",
                                            {"tool_name": event.tool_name},
                                        )

                        elif Agent.is_call_tools_node(node):
                            await manager.send_event(websocket, "call_tools_start", {})

                            async with node.stream(agent_run.ctx) as handle_stream:
                                async for tool_event in handle_stream:
                                    if isinstance(tool_event, FunctionToolCallEvent):
                                        collected_tool_calls.append({
                                            "tool_call_id": tool_event.part.tool_call_id,
                                            "tool_name": tool_event.part.tool_name,
                                            "args": tool_event.part.args,
                                        })
                                        await manager.send_event(
                                            websocket,
                                            "tool_call",
                                            {
                                                "tool_name": tool_event.part.tool_name,
                                                "args": tool_event.part.args,
                                                "tool_call_id": tool_event.part.tool_call_id,
                                            },
                                        )

                                    elif isinstance(tool_event, FunctionToolResultEvent):
                                        for tc in collected_tool_calls:
                                            if tc["tool_call_id"] == tool_event.tool_call_id:
                                                tc["result"] = str(tool_event.result.content)
                                                break
                                        await manager.send_event(
                                            websocket,
                                            "tool_result",
                                            {
                                                "tool_call_id": tool_event.tool_call_id,
                                                "content": str(tool_event.result.content),
                                            },
                                        )

                        elif Agent.is_end_node(node) and agent_run.result is not None:
                            await manager.send_event(
                                websocket,
                                "final_result",
                                {"output": agent_run.result.output},
                            )

                # Update conversation history
                conversation_history.append({"role": "user", "content": user_message})
                if agent_run.result:
                    conversation_history.append(
                        {"role": "assistant", "content": agent_run.result.output}
                    )

{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}

                # Save assistant response to database
                if current_conversation_id and agent_run.result:
                    try:
{%- if cookiecutter.use_postgresql %}
                        async with get_db_context() as db:
                            conv_service = get_conversation_service(db)
                            assistant_msg = await conv_service.add_message(
                                UUID(current_conversation_id),
                                MessageCreate(
                                    role="assistant",
                                    content=agent_run.result.output,
                                    model_name=assistant.model_name if hasattr(assistant, "model_name") else None,
                                ),
                            )
                            # Save tool calls
                            from datetime import datetime, UTC
                            import json
                            for tc in collected_tool_calls:
                                try:
                                    args_dict = tc.get("args", {})
                                    if isinstance(args_dict, str):
                                        args_dict = json.loads(args_dict) if args_dict.strip() else {}
                                    if args_dict is None:
                                        args_dict = {}
                                    tc_obj = await conv_service.start_tool_call(
                                        assistant_msg.id,
                                        ToolCallCreate(tool_call_id=tc["tool_call_id"], tool_name=tc["tool_name"], args=args_dict, started_at=datetime.now(UTC)),
                                    )
                                    if tc.get("result"):
                                        await conv_service.complete_tool_call(tc_obj.id, ToolCallComplete(result=tc["result"], completed_at=datetime.now(UTC), success=True))
                                except Exception as e:
                                    logger.warning(f"Failed to persist tool call: {e}")
{%- else %}
                        with contextmanager(get_db_session)() as db:
                            conv_service = get_conversation_service(db)
                            assistant_msg = conv_service.add_message(
                                current_conversation_id,
                                MessageCreate(
                                    role="assistant",
                                    content=agent_run.result.output,
                                    model_name=assistant.model_name if hasattr(assistant, "model_name") else None,
                                ),
                            )
                            # Save tool calls
                            from datetime import datetime, UTC
                            import json
                            for tc in collected_tool_calls:
                                try:
                                    args_dict = tc.get("args", {})
                                    if isinstance(args_dict, str):
                                        args_dict = json.loads(args_dict) if args_dict.strip() else {}
                                    if args_dict is None:
                                        args_dict = {}
                                    tc_obj = conv_service.start_tool_call(
                                        assistant_msg.id,
                                        ToolCallCreate(tool_call_id=tc["tool_call_id"], tool_name=tc["tool_name"], args=args_dict, started_at=datetime.now(UTC)),
                                    )
                                    if tc.get("result"):
                                        conv_service.complete_tool_call(tc_obj.id, ToolCallComplete(result=tc["result"], completed_at=datetime.now(UTC), success=True))
                                except Exception as e:
                                    logger.warning(f"Failed to persist tool call: {e}")
{%- endif %}
                    except Exception as e:
                        logger.warning(f"Failed to persist assistant response: {e}")
{%- elif cookiecutter.use_mongodb %}

                # Save assistant response to database
                if current_conversation_id and agent_run.result:
                    try:
                        await conv_service.add_message(
                            current_conversation_id,
                            MessageCreate(
                                role="assistant",
                                content=agent_run.result.output,
                                model_name=assistant.model_name if hasattr(assistant, "model_name") else None,
                            ),
                        )
                    except Exception as e:
                        logger.warning(f"Failed to persist assistant response: {e}")
{%- endif %}

                await manager.send_event(websocket, "complete", {
{%- if cookiecutter.use_database %}
                    "conversation_id": current_conversation_id,
{%- endif %}
                })

            except WebSocketDisconnect:
                # Client disconnected during processing - this is normal
                logger.info("Client disconnected during agent processing")
                break
            except Exception as e:
                logger.exception(f"Error processing agent request: {e}")
                # Try to send error, but don't fail if connection is closed
                await manager.send_event(websocket, "error", {"message": str(e)})

    except WebSocketDisconnect:
        pass  # Normal disconnect
    finally:
        manager.disconnect(websocket)
{%- elif cookiecutter.use_langchain %}
"""AI Agent WebSocket routes with streaming support (LangChain)."""

import logging
from typing import Any
{%- if cookiecutter.use_database %}
from datetime import datetime, UTC
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}
{%- endif %}

from fastapi import APIRouter, WebSocket, WebSocketDisconnect{%- if cookiecutter.websocket_auth_jwt %}, Depends{%- endif %}{%- if cookiecutter.websocket_auth_api_key %}, Query{%- endif %}

from langchain.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage

from app.agents.langchain_assistant import AgentContext, get_agent
{%- if cookiecutter.websocket_auth_jwt %}
from app.api.deps import get_current_user_ws
from app.db.models.user import User
{%- endif %}
{%- if cookiecutter.websocket_auth_api_key %}
from app.core.config import settings
{%- endif %}
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
from app.db.session import get_db_context{% if cookiecutter.use_sqlite %}, get_db_session
from contextlib import contextmanager{% endif %}
from app.api.deps import ConversationSvc, get_conversation_service
from app.schemas.conversation import ConversationCreate, ConversationUpdate, MessageCreate, ToolCallCreate, ToolCallComplete
{%- elif cookiecutter.use_mongodb %}
from app.api.deps import ConversationSvc, get_conversation_service
from app.schemas.conversation import ConversationCreate, ConversationUpdate, MessageCreate, ToolCallCreate, ToolCallComplete
{%- endif %}

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/agent/models")
async def list_models() -> dict[str, Any]:
    """Return available LLM models and the current default."""
    from app.core.config import settings
    return {
        "default": settings.AI_MODEL,
        "models": settings.AI_AVAILABLE_MODELS,
    }


class AgentConnectionManager:
    """WebSocket connection manager for AI agent."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Agent WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Agent WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_event(self, websocket: WebSocket, event_type: str, data: Any) -> bool:
        """Send a JSON event to a specific WebSocket client.

        Returns True if sent successfully, False if connection is closed.
        """
        try:
            await websocket.send_json({"type": event_type, "data": data})
            return True
        except (WebSocketDisconnect, RuntimeError):
            # Connection already closed
            return False


manager = AgentConnectionManager()


def build_message_history(
    history: list[dict[str, str]]
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

{%- if cookiecutter.websocket_auth_api_key %}


async def verify_api_key(api_key: str) -> bool:
    """Verify the API key for WebSocket authentication."""
    return api_key == settings.API_KEY
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
    """WebSocket endpoint for AI agent with streaming support.

    Uses LangChain stream() to stream agent events including:
    - user_prompt: When user input is received
    - text_delta: Streaming text from the model
    - tool_call: When a tool is called
    - tool_result: When a tool returns a result
    - final_result: When the final result is ready
    - complete: When processing is complete
    - error: When an error occurs

    Expected input message format:
    {
        "message": "user message here",
        "history": [{"role": "user|assistant|system", "content": "..."}]{% if cookiecutter.use_database %},
        "conversation_id": "optional-uuid-to-continue-existing-conversation"{% endif %}
    }
{%- if cookiecutter.websocket_auth_jwt %}

    Authentication: Requires a valid JWT token passed as a query parameter or header.
{%- elif cookiecutter.websocket_auth_api_key %}

    Authentication: Requires a valid API key passed as 'api_key' query parameter.
    Example: ws://localhost:{{ cookiecutter.backend_port }}/api/v1/ws/agent?api_key=your-api-key
{%- endif %}
{%- if cookiecutter.use_database %}

    Persistence: Set 'conversation_id' to continue an existing conversation.
    If not provided, a new conversation is created. The conversation_id is
    returned in the 'conversation_created' event.
{%- endif %}
    """
{%- if cookiecutter.websocket_auth_api_key %}
    # Verify API key before accepting connection
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- endif %}

    await manager.connect(websocket)

    # Conversation state per connection
    conversation_history: list[dict[str, str]] = []
    context: AgentContext = {}
{%- if cookiecutter.websocket_auth_jwt %}
    context["user_id"] = str(user.id) if user else None
    context["user_name"] = user.email if user else None
{%- endif %}
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None = None
{%- endif %}

    try:
        while True:
            # Receive user message
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            file_ids = data.get("file_ids", [])

            if not user_message and not file_ids:
                await manager.send_event(websocket, "error", {"message": "Empty message"})
                continue

{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}

            # Handle conversation persistence
            try:
{%- if cookiecutter.use_postgresql %}
                async with get_db_context() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        # Verify conversation exists and update title if empty
                        conv = await conv_service.get_conversation(UUID(requested_conv_id))
                        if not conv.title and user_message:
                            title = user_message[:50] if len(user_message) > 50 else user_message
                            await conv_service.update_conversation(UUID(requested_conv_id), ConversationUpdate(title=title))
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                            user_id=user.id,
{%- endif %}
                            title=user_message[:50] if len(user_message) > 50 else user_message,
                        )
                        conversation = await conv_service.create_conversation(conv_data)
                        current_conversation_id = str(conversation.id)
                        await manager.send_event(
                            websocket,
                            "conversation_created",
                            {"conversation_id": current_conversation_id},
                        )

                    # Save user message
                    user_msg = await conv_service.add_message(
                        UUID(current_conversation_id),
                        MessageCreate(role="user", content=user_message),
                    )
                    # Link uploaded files to this message
                    if file_ids:
                        try:
                            await conv_service.link_files_to_message(user_msg.id, file_ids)
                        except Exception as e:
                            logger.warning(f"Failed to link files: {e}")
{%- else %}
                with contextmanager(get_db_session)() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        conv = conv_service.get_conversation(requested_conv_id)
                        if not conv.title and user_message:
                            title = user_message[:50] if len(user_message) > 50 else user_message
                            conv_service.update_conversation(requested_conv_id, ConversationUpdate(title=title))
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                            user_id=str(user.id),
{%- endif %}
                            title=user_message[:50] if len(user_message) > 50 else user_message,
                        )
                        conversation = conv_service.create_conversation(conv_data)
                        current_conversation_id = str(conversation.id)
                        await manager.send_event(
                            websocket,
                            "conversation_created",
                            {"conversation_id": current_conversation_id},
                        )

                    # Save user message
                    user_msg = conv_service.add_message(
                        current_conversation_id,
                        MessageCreate(role="user", content=user_message),
                    )
                    # Link uploaded files to this message
                    if file_ids:
                        try:
                            conv_service.link_files_to_message(user_msg.id, file_ids)
                        except Exception as e:
                            logger.warning(f"Failed to link files: {e}")
{%- endif %}
            except Exception as e:
                logger.warning(f"Failed to persist conversation: {e}")
                # Continue without persistence
{%- elif cookiecutter.use_mongodb %}

            # Handle conversation persistence (MongoDB)
            conv_service = get_conversation_service()

            requested_conv_id = data.get("conversation_id")
            if requested_conv_id:
                current_conversation_id = requested_conv_id
                conv = await conv_service.get_conversation(requested_conv_id)
                if not conv.title and user_message:
                    title = user_message[:50] if len(user_message) > 50 else user_message
                    await conv_service.update_conversation(requested_conv_id, ConversationUpdate(title=title))
            elif not current_conversation_id:
                conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                    user_id=str(user.id),
{%- endif %}
                    title=user_message[:50] if len(user_message) > 50 else user_message,
                )
                conversation = await conv_service.create_conversation(conv_data)
                current_conversation_id = str(conversation.id)
                await manager.send_event(
                    websocket,
                    "conversation_created",
                    {"conversation_id": current_conversation_id},
                )

            # Save user message
            await conv_service.add_message(
                current_conversation_id,
                MessageCreate(role="user", content=user_message),
            )
{%- endif %}

            await manager.send_event(websocket, "user_prompt", {"content": user_message})

            try:
                selected_model = data.get("model")
                assistant = get_agent(model_name=selected_model)
                model_history = build_message_history(conversation_history)
                model_history.append(HumanMessage(content=user_message))

                final_output = ""
                tool_events: list[Any] = []
                seen_tool_call_ids: set[str] = set()

                await manager.send_event(websocket, "model_request_start", {})

                for stream_mode, data in assistant.agent.stream(
                    {"messages": model_history},
                    stream_mode=["messages", "updates"],
                    config={"configurable": context} if context else None,
                ):
                    if stream_mode == "messages":
                        token, metadata = data

                        if isinstance(token, AIMessageChunk):
                            if token.content:
                                text_content = ""
                                if isinstance(token.content, str):
                                    text_content = token.content
                                elif isinstance(token.content, list):
                                    for block in token.content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            text_content += block.get("text", "")
                                        elif isinstance(block, str):
                                            text_content += block

                                if text_content:
                                    await manager.send_event(
                                        websocket,
                                        "text_delta",
                                        {"content": text_content},
                                    )
                                    final_output += text_content

                            if token.tool_call_chunks:
                                for tc_chunk in token.tool_call_chunks:
                                    tc_id = tc_chunk.get("id")
                                    tc_name = tc_chunk.get("name")
                                    if tc_id and tc_name and tc_id not in seen_tool_call_ids:
                                        seen_tool_call_ids.add(tc_id)
                                        await manager.send_event(
                                            websocket,
                                            "tool_call",
                                            {
                                                "tool_name": tc_name,
                                                "args": {},
                                                "tool_call_id": tc_id,
                                            },
                                        )

                    elif stream_mode == "updates":
                        for node_name, update in data.items():
                            if node_name == "tools":
                                for msg in update.get("messages", []):
                                    if isinstance(msg, ToolMessage):
                                        await manager.send_event(
                                            websocket,
                                            "tool_result",
                                            {
                                                "tool_call_id": msg.tool_call_id,
                                                "content": msg.content,
                                            },
                                        )
                            elif node_name == "model":
                                for msg in update.get("messages", []):
                                    if isinstance(msg, AIMessage) and msg.tool_calls:
                                        for tc in msg.tool_calls:
                                            tc_id = tc.get("id", "")
                                            if tc_id not in seen_tool_call_ids:
                                                seen_tool_call_ids.add(tc_id)
                                                tool_events.append(tc)
                                                await manager.send_event(
                                                    websocket,
                                                    "tool_call",
                                                    {
                                                        "tool_name": tc.get("name", ""),
                                                        "args": tc.get("args", {}),
                                                        "tool_call_id": tc_id,
                                                    },
                                                )

                await manager.send_event(
                    websocket,
                    "final_result",
                    {"output": final_output},
                )

                # Update conversation history
                conversation_history.append({"role": "user", "content": user_message})
                if final_output:
                    conversation_history.append(
                        {"role": "assistant", "content": final_output}
                    )

{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}

                # Save assistant response to database
                if current_conversation_id and final_output:
                    try:
{%- if cookiecutter.use_postgresql %}
                        async with get_db_context() as db:
                            conv_service = get_conversation_service(db)
                            await conv_service.add_message(
                                UUID(current_conversation_id),
                                MessageCreate(
                                    role="assistant",
                                    content=final_output,
                                    model_name=assistant.model_name if hasattr(assistant, "model_name") else None,
                                ),
                            )
{%- else %}
                        with contextmanager(get_db_session)() as db:
                            conv_service = get_conversation_service(db)
                            conv_service.add_message(
                                current_conversation_id,
                                MessageCreate(
                                    role="assistant",
                                    content=final_output,
                                    model_name=assistant.model_name if hasattr(assistant, "model_name") else None,
                                ),
                            )
{%- endif %}
                    except Exception as e:
                        logger.warning(f"Failed to persist assistant response: {e}")
{%- elif cookiecutter.use_mongodb %}

                # Save assistant response to database
                if current_conversation_id and final_output:
                    try:
                        await conv_service.add_message(
                            current_conversation_id,
                            MessageCreate(
                                role="assistant",
                                content=final_output,
                                model_name=assistant.model_name if hasattr(assistant, "model_name") else None,
                            ),
                        )
                    except Exception as e:
                        logger.warning(f"Failed to persist assistant response: {e}")
{%- endif %}

                await manager.send_event(websocket, "complete", {
{%- if cookiecutter.use_database %}
                    "conversation_id": current_conversation_id,
{%- endif %}
                })

            except WebSocketDisconnect:
                # Client disconnected during processing - this is normal
                logger.info("Client disconnected during agent processing")
                break
            except Exception as e:
                logger.exception(f"Error processing agent request: {e}")
                # Try to send error, but don't fail if connection is closed
                await manager.send_event(websocket, "error", {"message": str(e)})

    except WebSocketDisconnect:
        pass  # Normal disconnect
    finally:
        manager.disconnect(websocket)
{%- elif cookiecutter.use_langgraph %}
"""AI Agent WebSocket routes with streaming support (LangGraph ReAct Agent)."""

import logging
from typing import Any
{%- if cookiecutter.use_database %}
from datetime import datetime, UTC
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}
{%- endif %}

from fastapi import APIRouter, WebSocket, WebSocketDisconnect{%- if cookiecutter.websocket_auth_jwt %}, Depends{%- endif %}{%- if cookiecutter.websocket_auth_api_key %}, Query{%- endif %}

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage

from app.agents.langgraph_assistant import AgentContext, get_agent
{%- if cookiecutter.websocket_auth_jwt %}
from app.api.deps import get_current_user_ws
from app.db.models.user import User
{%- endif %}
{%- if cookiecutter.websocket_auth_api_key %}
from app.core.config import settings
{%- endif %}
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
from app.db.session import get_db_context{% if cookiecutter.use_sqlite %}, get_db_session
from contextlib import contextmanager{% endif %}
from app.api.deps import ConversationSvc, get_conversation_service
from app.schemas.conversation import ConversationCreate, ConversationUpdate, MessageCreate, ToolCallCreate, ToolCallComplete
{%- elif cookiecutter.use_mongodb %}
from app.api.deps import ConversationSvc, get_conversation_service
from app.schemas.conversation import ConversationCreate, ConversationUpdate, MessageCreate, ToolCallCreate, ToolCallComplete
{%- endif %}

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/agent/models")
async def list_models() -> dict[str, Any]:
    """Return available LLM models and the current default."""
    from app.core.config import settings
    return {
        "default": settings.AI_MODEL,
        "models": settings.AI_AVAILABLE_MODELS,
    }


class AgentConnectionManager:
    """WebSocket connection manager for AI agent."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Agent WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Agent WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_event(self, websocket: WebSocket, event_type: str, data: Any) -> bool:
        """Send a JSON event to a specific WebSocket client.

        Returns True if sent successfully, False if connection is closed.
        """
        try:
            await websocket.send_json({"type": event_type, "data": data})
            return True
        except (WebSocketDisconnect, RuntimeError):
            # Connection already closed
            return False


manager = AgentConnectionManager()


def build_message_history(
    history: list[dict[str, str]]
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

{%- if cookiecutter.websocket_auth_api_key %}


async def verify_api_key(api_key: str) -> bool:
    """Verify the API key for WebSocket authentication."""
    return api_key == settings.API_KEY
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
    """WebSocket endpoint for LangGraph ReAct agent with streaming support.

    Uses LangGraph astream_events() to stream all agent events including:
    - user_prompt: When user input is received
    - model_request_start: When model request begins
    - text_delta: Streaming text from the model
    - tool_call: When a tool is called
    - tool_result: When a tool returns a result
    - final_result: When the final result is ready
    - complete: When processing is complete
    - error: When an error occurs

    Expected input message format:
    {
        "message": "user message here",
        "history": [{"role": "user|assistant|system", "content": "..."}]{% if cookiecutter.use_database %},
        "conversation_id": "optional-uuid-to-continue-existing-conversation"{% endif %}
    }
{%- if cookiecutter.websocket_auth_jwt %}

    Authentication: Requires a valid JWT token passed as a query parameter or header.
{%- elif cookiecutter.websocket_auth_api_key %}

    Authentication: Requires a valid API key passed as 'api_key' query parameter.
    Example: ws://localhost:{{ cookiecutter.backend_port }}/api/v1/ws/agent?api_key=your-api-key
{%- endif %}
{%- if cookiecutter.use_database %}

    Persistence: Set 'conversation_id' to continue an existing conversation.
    If not provided, a new conversation is created. The conversation_id is
    returned in the 'conversation_created' event.
{%- endif %}
    """
{%- if cookiecutter.websocket_auth_api_key %}
    # Verify API key before accepting connection
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- endif %}

    await manager.connect(websocket)

    # Conversation state per connection
    conversation_history: list[dict[str, str]] = []
    context: AgentContext = {}
{%- if cookiecutter.websocket_auth_jwt %}
    context["user_id"] = str(user.id) if user else None
    context["user_name"] = user.email if user else None
{%- endif %}
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None = None
{%- endif %}

    try:
        while True:
            # Receive user message
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            file_ids = data.get("file_ids", [])

            if not user_message and not file_ids:
                await manager.send_event(websocket, "error", {"message": "Empty message"})
                continue

{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}

            # Handle conversation persistence
            try:
{%- if cookiecutter.use_postgresql %}
                async with get_db_context() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        # Verify conversation exists and update title if empty
                        conv = await conv_service.get_conversation(UUID(requested_conv_id))
                        if not conv.title and user_message:
                            title = user_message[:50] if len(user_message) > 50 else user_message
                            await conv_service.update_conversation(UUID(requested_conv_id), ConversationUpdate(title=title))
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                            user_id=user.id,
{%- endif %}
                            title=user_message[:50] if len(user_message) > 50 else user_message,
                        )
                        conversation = await conv_service.create_conversation(conv_data)
                        current_conversation_id = str(conversation.id)
                        await manager.send_event(
                            websocket,
                            "conversation_created",
                            {"conversation_id": current_conversation_id},
                        )

                    # Save user message
                    user_msg = await conv_service.add_message(
                        UUID(current_conversation_id),
                        MessageCreate(role="user", content=user_message),
                    )
                    # Link uploaded files to this message
                    if file_ids:
                        try:
                            await conv_service.link_files_to_message(user_msg.id, file_ids)
                        except Exception as e:
                            logger.warning(f"Failed to link files: {e}")
{%- else %}
                with contextmanager(get_db_session)() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        conv = conv_service.get_conversation(requested_conv_id)
                        if not conv.title and user_message:
                            title = user_message[:50] if len(user_message) > 50 else user_message
                            conv_service.update_conversation(requested_conv_id, ConversationUpdate(title=title))
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                            user_id=str(user.id),
{%- endif %}
                            title=user_message[:50] if len(user_message) > 50 else user_message,
                        )
                        conversation = conv_service.create_conversation(conv_data)
                        current_conversation_id = str(conversation.id)
                        await manager.send_event(
                            websocket,
                            "conversation_created",
                            {"conversation_id": current_conversation_id},
                        )

                    # Save user message
                    user_msg = conv_service.add_message(
                        current_conversation_id,
                        MessageCreate(role="user", content=user_message),
                    )
                    # Link uploaded files to this message
                    if file_ids:
                        try:
                            conv_service.link_files_to_message(user_msg.id, file_ids)
                        except Exception as e:
                            logger.warning(f"Failed to link files: {e}")
{%- endif %}
            except Exception as e:
                logger.warning(f"Failed to persist conversation: {e}")
                # Continue without persistence
{%- elif cookiecutter.use_mongodb %}

            # Handle conversation persistence (MongoDB)
            conv_service = get_conversation_service()

            requested_conv_id = data.get("conversation_id")
            if requested_conv_id:
                current_conversation_id = requested_conv_id
                conv = await conv_service.get_conversation(requested_conv_id)
                if not conv.title and user_message:
                    title = user_message[:50] if len(user_message) > 50 else user_message
                    await conv_service.update_conversation(requested_conv_id, ConversationUpdate(title=title))
            elif not current_conversation_id:
                conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                    user_id=str(user.id),
{%- endif %}
                    title=user_message[:50] if len(user_message) > 50 else user_message,
                )
                conversation = await conv_service.create_conversation(conv_data)
                current_conversation_id = str(conversation.id)
                await manager.send_event(
                    websocket,
                    "conversation_created",
                    {"conversation_id": current_conversation_id},
                )

            # Save user message
            await conv_service.add_message(
                current_conversation_id,
                MessageCreate(role="user", content=user_message),
            )
{%- endif %}

            await manager.send_event(websocket, "user_prompt", {"content": user_message})

            try:
                selected_model = data.get("model")
                assistant = get_agent(model_name=selected_model)

                final_output = ""
                tool_events: list[Any] = []
                seen_tool_call_ids: set[str] = set()

                await manager.send_event(websocket, "model_request_start", {})

                # Use LangGraph's astream with messages and updates modes
                async for stream_mode, data in assistant.stream(
                    user_message,
                    history=conversation_history,
                    context=context,
                ):
                    if stream_mode == "messages":
                        chunk, _metadata = data

                        if isinstance(chunk, AIMessageChunk):
                            if chunk.content:
                                text_content = ""
                                if isinstance(chunk.content, str):
                                    text_content = chunk.content
                                elif isinstance(chunk.content, list):
                                    for block in chunk.content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            text_content += block.get("text", "")
                                        elif isinstance(block, str):
                                            text_content += block

                                if text_content:
                                    await manager.send_event(
                                        websocket,
                                        "text_delta",
                                        {"content": text_content},
                                    )
                                    final_output += text_content

                            # Handle tool call chunks
                            if chunk.tool_call_chunks:
                                for tc_chunk in chunk.tool_call_chunks:
                                    tc_id = tc_chunk.get("id")
                                    tc_name = tc_chunk.get("name")
                                    if tc_id and tc_name and tc_id not in seen_tool_call_ids:
                                        seen_tool_call_ids.add(tc_id)
                                        await manager.send_event(
                                            websocket,
                                            "tool_call",
                                            {
                                                "tool_name": tc_name,
                                                "args": {},
                                                "tool_call_id": tc_id,
                                            },
                                        )

                    elif stream_mode == "updates":
                        # Handle state updates from nodes
                        for node_name, update in data.items():
                            if node_name == "tools":
                                # Tool node completed - extract tool results
                                for msg in update.get("messages", []):
                                    if isinstance(msg, ToolMessage):
                                        await manager.send_event(
                                            websocket,
                                            "tool_result",
                                            {
                                                "tool_call_id": msg.tool_call_id,
                                                "content": msg.content,
                                            },
                                        )
                            elif node_name == "agent":
                                # Agent node completed - check for tool calls
                                for msg in update.get("messages", []):
                                    if isinstance(msg, AIMessage) and msg.tool_calls:
                                        for tc in msg.tool_calls:
                                            tc_id = tc.get("id", "")
                                            if tc_id not in seen_tool_call_ids:
                                                seen_tool_call_ids.add(tc_id)
                                                tool_events.append(tc)
                                                await manager.send_event(
                                                    websocket,
                                                    "tool_call",
                                                    {
                                                        "tool_name": tc.get("name", ""),
                                                        "args": tc.get("args", {}),
                                                        "tool_call_id": tc_id,
                                                    },
                                                )

                await manager.send_event(
                    websocket,
                    "final_result",
                    {"output": final_output},
                )

                # Update conversation history
                conversation_history.append({"role": "user", "content": user_message})
                if final_output:
                    conversation_history.append(
                        {"role": "assistant", "content": final_output}
                    )

{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}

                # Save assistant response to database
                if current_conversation_id and final_output:
                    try:
{%- if cookiecutter.use_postgresql %}
                        async with get_db_context() as db:
                            conv_service = get_conversation_service(db)
                            await conv_service.add_message(
                                UUID(current_conversation_id),
                                MessageCreate(
                                    role="assistant",
                                    content=final_output,
                                    model_name=assistant.model_name if hasattr(assistant, "model_name") else None,
                                ),
                            )
{%- else %}
                        with contextmanager(get_db_session)() as db:
                            conv_service = get_conversation_service(db)
                            conv_service.add_message(
                                current_conversation_id,
                                MessageCreate(
                                    role="assistant",
                                    content=final_output,
                                    model_name=assistant.model_name if hasattr(assistant, "model_name") else None,
                                ),
                            )
{%- endif %}
                    except Exception as e:
                        logger.warning(f"Failed to persist assistant response: {e}")
{%- elif cookiecutter.use_mongodb %}

                # Save assistant response to database
                if current_conversation_id and final_output:
                    try:
                        await conv_service.add_message(
                            current_conversation_id,
                            MessageCreate(
                                role="assistant",
                                content=final_output,
                                model_name=assistant.model_name if hasattr(assistant, "model_name") else None,
                            ),
                        )
                    except Exception as e:
                        logger.warning(f"Failed to persist assistant response: {e}")
{%- endif %}

                await manager.send_event(websocket, "complete", {
{%- if cookiecutter.use_database %}
                    "conversation_id": current_conversation_id,
{%- endif %}
                })

            except WebSocketDisconnect:
                # Client disconnected during processing - this is normal
                logger.info("Client disconnected during agent processing")
                break
            except Exception as e:
                logger.exception(f"Error processing agent request: {e}")
                # Try to send error, but don't fail if connection is closed
                await manager.send_event(websocket, "error", {"message": str(e)})

    except WebSocketDisconnect:
        pass  # Normal disconnect
    finally:
        manager.disconnect(websocket)
{%- elif cookiecutter.use_crewai %}
"""AI Agent WebSocket routes with streaming support (CrewAI Multi-Agent)."""

import logging
from typing import Any
{%- if cookiecutter.use_database %}
from datetime import datetime, UTC
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}
{%- endif %}

from fastapi import APIRouter, WebSocket, WebSocketDisconnect{%- if cookiecutter.websocket_auth_jwt %}, Depends{%- endif %}{%- if cookiecutter.websocket_auth_api_key %}, Query{%- endif %}

from app.agents.crewai_assistant import CrewContext, get_crew
{%- if cookiecutter.websocket_auth_jwt %}
from app.api.deps import get_current_user_ws
from app.db.models.user import User
{%- endif %}
{%- if cookiecutter.websocket_auth_api_key %}
from app.core.config import settings
{%- endif %}
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
from app.db.session import get_db_context{% if cookiecutter.use_sqlite %}, get_db_session
from contextlib import contextmanager{% endif %}
from app.api.deps import ConversationSvc, get_conversation_service
from app.schemas.conversation import ConversationCreate, MessageCreate
{%- elif cookiecutter.use_mongodb %}
from app.api.deps import ConversationSvc, get_conversation_service
from app.schemas.conversation import ConversationCreate, MessageCreate
{%- endif %}

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/agent/models")
async def list_models() -> dict[str, Any]:
    """Return available LLM models and the current default."""
    from app.core.config import settings
    return {
        "default": settings.AI_MODEL,
        "models": settings.AI_AVAILABLE_MODELS,
    }


class AgentConnectionManager:
    """WebSocket connection manager for AI agent."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Agent WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Agent WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_event(self, websocket: WebSocket, event_type: str, data: Any) -> bool:
        """Send a JSON event to a specific WebSocket client.

        Returns True if sent successfully, False if connection is closed.
        """
        try:
            await websocket.send_json({"type": event_type, "data": data})
            return True
        except (WebSocketDisconnect, RuntimeError):
            # Connection already closed
            return False


manager = AgentConnectionManager()

{%- if cookiecutter.websocket_auth_api_key %}


async def verify_api_key(api_key: str) -> bool:
    """Verify the API key for WebSocket authentication."""
    return api_key == settings.API_KEY
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
    """WebSocket endpoint for CrewAI multi-agent with streaming support.

    Uses CrewAI to stream crew execution events including:
    - user_prompt: When user input is received
    - task_start: When a task begins execution
    - agent_action: When an agent takes an action
    - task_complete: When a task finishes
    - crew_complete: When all tasks are done
    - final_result: When the final result is ready
    - complete: When processing is complete
    - error: When an error occurs

    Expected input message format:
    {
        "message": "user message here",
        "history": [{"role": "user|assistant|system", "content": "..."}]{% if cookiecutter.use_database %},
        "conversation_id": "optional-uuid-to-continue-existing-conversation"{% endif %}
    }
{%- if cookiecutter.websocket_auth_jwt %}

    Authentication: Requires a valid JWT token passed as a query parameter or header.
{%- elif cookiecutter.websocket_auth_api_key %}

    Authentication: Requires a valid API key passed as 'api_key' query parameter.
    Example: ws://localhost:{{ cookiecutter.backend_port }}/api/v1/ws/agent?api_key=your-api-key
{%- endif %}
{%- if cookiecutter.use_database %}

    Persistence: Set 'conversation_id' to continue an existing conversation.
    If not provided, a new conversation is created. The conversation_id is
    returned in the 'conversation_created' event.
{%- endif %}
    """
{%- if cookiecutter.websocket_auth_api_key %}
    # Verify API key before accepting connection
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- endif %}

    await manager.connect(websocket)

    # Conversation state per connection
    conversation_history: list[dict[str, str]] = []
    context: CrewContext = {}
{%- if cookiecutter.websocket_auth_jwt %}
    context["user_id"] = str(user.id) if user else None
    context["user_name"] = user.email if user else None
{%- endif %}
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None = None
{%- endif %}

    try:
        while True:
            # Receive user message
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            file_ids = data.get("file_ids", [])

            if not user_message and not file_ids:
                await manager.send_event(websocket, "error", {"message": "Empty message"})
                continue

{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}

            # Handle conversation persistence
            try:
{%- if cookiecutter.use_postgresql %}
                async with get_db_context() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        # Verify conversation exists and update title if empty
                        conv = await conv_service.get_conversation(UUID(requested_conv_id))
                        if not conv.title and user_message:
                            title = user_message[:50] if len(user_message) > 50 else user_message
                            await conv_service.update_conversation(UUID(requested_conv_id), ConversationUpdate(title=title))
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                            user_id=user.id,
{%- endif %}
                            title=user_message[:50] if len(user_message) > 50 else user_message,
                        )
                        conversation = await conv_service.create_conversation(conv_data)
                        current_conversation_id = str(conversation.id)
                        await manager.send_event(
                            websocket,
                            "conversation_created",
                            {"conversation_id": current_conversation_id},
                        )

                    # Save user message
                    user_msg = await conv_service.add_message(
                        UUID(current_conversation_id),
                        MessageCreate(role="user", content=user_message),
                    )
                    # Link uploaded files to this message
                    if file_ids:
                        try:
                            await conv_service.link_files_to_message(user_msg.id, file_ids)
                        except Exception as e:
                            logger.warning(f"Failed to link files: {e}")
{%- else %}
                with contextmanager(get_db_session)() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        conv = conv_service.get_conversation(requested_conv_id)
                        if not conv.title and user_message:
                            title = user_message[:50] if len(user_message) > 50 else user_message
                            conv_service.update_conversation(requested_conv_id, ConversationUpdate(title=title))
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                            user_id=str(user.id),
{%- endif %}
                            title=user_message[:50] if len(user_message) > 50 else user_message,
                        )
                        conversation = conv_service.create_conversation(conv_data)
                        current_conversation_id = str(conversation.id)
                        await manager.send_event(
                            websocket,
                            "conversation_created",
                            {"conversation_id": current_conversation_id},
                        )

                    # Save user message
                    user_msg = conv_service.add_message(
                        current_conversation_id,
                        MessageCreate(role="user", content=user_message),
                    )
                    # Link uploaded files to this message
                    if file_ids:
                        try:
                            conv_service.link_files_to_message(user_msg.id, file_ids)
                        except Exception as e:
                            logger.warning(f"Failed to link files: {e}")
{%- endif %}
            except Exception as e:
                logger.warning(f"Failed to persist conversation: {e}")
                # Continue without persistence
{%- elif cookiecutter.use_mongodb %}

            # Handle conversation persistence (MongoDB)
            conv_service = get_conversation_service()

            requested_conv_id = data.get("conversation_id")
            if requested_conv_id:
                current_conversation_id = requested_conv_id
                conv = await conv_service.get_conversation(requested_conv_id)
                if not conv.title and user_message:
                    title = user_message[:50] if len(user_message) > 50 else user_message
                    await conv_service.update_conversation(requested_conv_id, ConversationUpdate(title=title))
            elif not current_conversation_id:
                conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                    user_id=str(user.id),
{%- endif %}
                    title=user_message[:50] if len(user_message) > 50 else user_message,
                )
                conversation = await conv_service.create_conversation(conv_data)
                current_conversation_id = str(conversation.id)
                await manager.send_event(
                    websocket,
                    "conversation_created",
                    {"conversation_id": current_conversation_id},
                )

            # Save user message
            await conv_service.add_message(
                current_conversation_id,
                MessageCreate(role="user", content=user_message),
            )
{%- endif %}

            await manager.send_event(websocket, "user_prompt", {"content": user_message})

            try:
                crew_assistant = get_crew()

                final_output = ""

                await manager.send_event(websocket, "crew_start", {
                    "crew_name": crew_assistant.config.name,
                    "process": crew_assistant.config.process,
                })

                # Stream crew execution events
                async for event in crew_assistant.stream(
                    user_message,
                    history=conversation_history,
                    context=context,
                ):
                    event_type = event.get("type", "unknown")

                    # Crew lifecycle events
                    if event_type == "crew_started":
                        await manager.send_event(
                            websocket,
                            "crew_started",
                            {
                                "crew_name": event.get("crew_name", ""),
                                "crew_id": event.get("crew_id", ""),
                            },
                        )

                    # Agent events
                    elif event_type == "agent_started":
                        await manager.send_event(
                            websocket,
                            "agent_started",
                            {
                                "agent": event.get("agent", ""),
                                "task": event.get("task", ""),
                            },
                        )

                    elif event_type == "agent_completed":
                        agent_name = event.get("agent", "")
                        agent_output = event.get("output", "")
                        await manager.send_event(
                            websocket,
                            "agent_completed",
                            {
                                "agent": agent_name,
                                "output": agent_output,
                            },
                        )
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
                        # Save agent's output as a separate message
                        if current_conversation_id and agent_output:
                            try:
{%- if cookiecutter.use_postgresql %}
                                async with get_db_context() as db:
                                    conv_service = get_conversation_service(db)
                                    await conv_service.add_message(
                                        UUID(current_conversation_id),
                                        MessageCreate(
                                            role="assistant",
                                            content=f"✅ **{agent_name}**\n\n{agent_output}",
                                        ),
                                    )
{%- else %}
                                with contextmanager(get_db_session)() as db:
                                    conv_service = get_conversation_service(db)
                                    conv_service.add_message(
                                        current_conversation_id,
                                        MessageCreate(
                                            role="assistant",
                                            content=f"✅ **{agent_name}**\n\n{agent_output}",
                                        ),
                                    )
{%- endif %}
                            except Exception as e:
                                logger.warning(f"Failed to persist agent response: {e}")
{%- elif cookiecutter.use_mongodb %}
                        # Save agent's output as a separate message
                        if current_conversation_id and agent_output:
                            try:
                                await conv_service.add_message(
                                    current_conversation_id,
                                    MessageCreate(
                                        role="assistant",
                                        content=f"✅ **{agent_name}**\n\n{agent_output}",
                                    ),
                                )
                            except Exception as e:
                                logger.warning(f"Failed to persist agent response: {e}")
{%- endif %}

                    # Task events
                    elif event_type == "task_started":
                        await manager.send_event(
                            websocket,
                            "task_started",
                            {
                                "task_id": event.get("task_id", ""),
                                "description": event.get("description", ""),
                                "agent": event.get("agent", ""),
                            },
                        )

                    elif event_type == "task_completed":
                        await manager.send_event(
                            websocket,
                            "task_completed",
                            {
                                "task_id": event.get("task_id", ""),
                                "output": event.get("output", ""),
                                "agent": event.get("agent", ""),
                            },
                        )

                    # Tool events
                    elif event_type == "tool_started":
                        await manager.send_event(
                            websocket,
                            "tool_started",
                            {
                                "tool_name": event.get("tool_name", ""),
                                "tool_args": event.get("tool_args", ""),
                                "agent": event.get("agent", ""),
                            },
                        )

                    elif event_type == "tool_finished":
                        await manager.send_event(
                            websocket,
                            "tool_finished",
                            {
                                "tool_name": event.get("tool_name", ""),
                                "tool_result": event.get("tool_result", ""),
                                "agent": event.get("agent", ""),
                            },
                        )

                    # LLM events
                    elif event_type == "llm_started":
                        await manager.send_event(
                            websocket,
                            "llm_started",
                            {
                                "agent": event.get("agent", ""),
                            },
                        )

                    elif event_type == "llm_completed":
                        await manager.send_event(
                            websocket,
                            "llm_completed",
                            {
                                "agent": event.get("agent", ""),
                                "response": event.get("response", ""),
                            },
                        )

                    # Final result
                    elif event_type == "crew_complete":
                        final_output = event.get("result", "")
                        await manager.send_event(
                            websocket,
                            "final_result",
                            {"output": final_output},
                        )

                    # Error
                    elif event_type == "error":
                        await manager.send_event(
                            websocket,
                            "error",
                            {"message": event.get("error", "Unknown error")},
                        )

                # Update conversation history
                conversation_history.append({"role": "user", "content": user_message})
                if final_output:
                    conversation_history.append(
                        {"role": "assistant", "content": final_output}
                    )

{%- if cookiecutter.use_database %}
                # Note: Agent outputs are saved individually in agent_completed events above
{%- endif %}

                await manager.send_event(websocket, "complete", {
{%- if cookiecutter.use_database %}
                    "conversation_id": current_conversation_id,
{%- endif %}
                })

            except WebSocketDisconnect:
                # Client disconnected during processing - this is normal
                logger.info("Client disconnected during agent processing")
                break
            except Exception as e:
                logger.exception(f"Error processing agent request: {e}")
                # Try to send error, but don't fail if connection is closed
                await manager.send_event(websocket, "error", {"message": str(e)})

    except WebSocketDisconnect:
        pass  # Normal disconnect
    finally:
        manager.disconnect(websocket)
{%- elif cookiecutter.use_deepagents %}
"""AI Agent WebSocket routes with streaming and human-in-the-loop support (DeepAgents)."""

import logging
import uuid
from typing import Any
{%- if cookiecutter.use_database %}
from datetime import datetime, UTC
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}
{%- endif %}

from fastapi import APIRouter, WebSocket, WebSocketDisconnect{%- if cookiecutter.websocket_auth_jwt %}, Depends{%- endif %}{%- if cookiecutter.websocket_auth_api_key %}, Query{%- endif %}

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage

from app.agents.deepagents_assistant import AgentContext, Decision, InterruptData, get_agent
{%- if cookiecutter.websocket_auth_jwt %}
from app.api.deps import get_current_user_ws
from app.db.models.user import User
{%- endif %}
{%- if cookiecutter.websocket_auth_api_key %}
from app.core.config import settings
{%- endif %}
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
from app.db.session import get_db_context{% if cookiecutter.use_sqlite %}, get_db_session
from contextlib import contextmanager{% endif %}
from app.api.deps import ConversationSvc, get_conversation_service
from app.schemas.conversation import ConversationCreate, ConversationUpdate, MessageCreate, ToolCallCreate, ToolCallComplete
{%- elif cookiecutter.use_mongodb %}
from app.api.deps import ConversationSvc, get_conversation_service
from app.schemas.conversation import ConversationCreate, ConversationUpdate, MessageCreate, ToolCallCreate, ToolCallComplete
{%- endif %}

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/agent/models")
async def list_models() -> dict[str, Any]:
    """Return available LLM models and the current default."""
    from app.core.config import settings
    return {
        "default": settings.AI_MODEL,
        "models": settings.AI_AVAILABLE_MODELS,
    }


class AgentConnectionManager:
    """WebSocket connection manager for AI agent."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Agent WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Agent WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_event(self, websocket: WebSocket, event_type: str, data: Any) -> bool:
        """Send a JSON event to a specific WebSocket client.

        Returns True if sent successfully, False if connection is closed.
        """
        try:
            await websocket.send_json({"type": event_type, "data": data})
            return True
        except (WebSocketDisconnect, RuntimeError):
            # Connection already closed
            return False


manager = AgentConnectionManager()


def build_message_history(
    history: list[dict[str, str]]
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

{%- if cookiecutter.websocket_auth_api_key %}


async def verify_api_key(api_key: str) -> bool:
    """Verify the API key for WebSocket authentication."""
    return api_key == settings.API_KEY
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
    """WebSocket endpoint for DeepAgents with streaming and human-in-the-loop support.

    Uses DeepAgents (LangGraph-based) to stream agent events including:
    - user_prompt: When user input is received
    - model_request_start: When model request begins
    - text_delta: Streaming text from the model
    - tool_call: When a tool is called (ls, read_file, write_file, edit_file, etc.)
    - tool_result: When a tool returns a result
    - tool_approval_required: When human approval is needed for tool execution
    - final_result: When the final result is ready
    - complete: When processing is complete
    - error: When an error occurs

    Human-in-the-loop:
    When DEEPAGENTS_INTERRUPT_TOOLS is configured, certain tools will require
    approval before execution. The frontend receives a 'tool_approval_required'
    event and should respond with a 'resume' message containing decisions.

    Expected input message formats:

    Regular message:
    {
        "type": "message",  // optional, default
        "message": "user message here",
        "history": [{"role": "user|assistant|system", "content": "..."}]{% if cookiecutter.use_database %},
        "conversation_id": "optional-uuid"{% endif %}
    }

    Resume after interrupt:
    {
        "type": "resume",
        "decisions": [
            {"type": "approve"},
            {"type": "reject"},
            {"type": "edit", "edited_action": {"name": "tool_name", "args": {...}}}
        ]
    }
{%- if cookiecutter.websocket_auth_jwt %}

    Authentication: Requires a valid JWT token passed as a query parameter or header.
{%- elif cookiecutter.websocket_auth_api_key %}

    Authentication: Requires a valid API key passed as 'api_key' query parameter.
    Example: ws://localhost:{{ cookiecutter.backend_port }}/api/v1/ws/agent?api_key=your-api-key
{%- endif %}
{%- if cookiecutter.use_database %}

    Persistence: Set 'conversation_id' to continue an existing conversation.
    If not provided, a new conversation is created. The conversation_id is
    returned in the 'conversation_created' event.
{%- endif %}
    """
{%- if cookiecutter.websocket_auth_api_key %}
    # Verify API key before accepting connection
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
{%- endif %}

    await manager.connect(websocket)

    # Conversation state per connection
    conversation_history: list[dict[str, str]] = []
    context: AgentContext = {}
    # Thread ID for LangGraph state persistence (required for HITL)
    thread_id: str = str(uuid.uuid4())
    # Track pending interrupt for resume
    pending_interrupt: InterruptData | None = None
{%- if cookiecutter.websocket_auth_jwt %}
    context["user_id"] = str(user.id) if user else None
    context["user_name"] = user.email if user else None
{%- endif %}
{%- if cookiecutter.use_database %}
    current_conversation_id: str | None = None
{%- endif %}

    # Create assistant instance (reused for the connection)
    assistant = get_agent()

    try:
        while True:
            # Receive message from client
            raw_data = await websocket.receive_json()
            message_type = raw_data.get("type", "message")

            # Handle resume after interrupt
            if message_type == "resume":
                if not pending_interrupt:
                    await manager.send_event(websocket, "error", {"message": "No pending interrupt to resume"})
                    continue

                decisions: list[Decision] = raw_data.get("decisions", [])
                if len(decisions) != len(pending_interrupt["action_requests"]):
                    await manager.send_event(
                        websocket,
                        "error",
                        {"message": f"Expected {len(pending_interrupt['action_requests'])} decisions, got {len(decisions)}"},
                    )
                    continue

                # Clear pending interrupt
                pending_interrupt = None

                try:
                    await manager.send_event(websocket, "resume_start", {})

                    final_output = ""
                    seen_tool_call_ids: set[str] = set()

                    # Stream resume
                    async for stream_mode, stream_data in assistant.stream_resume(
                        decisions=decisions,
                        thread_id=thread_id,
                        context=context,
                    ):
                        if stream_mode == "interrupt":
                            # Another interrupt occurred
                            pending_interrupt = stream_data
                            await manager.send_event(
                                websocket,
                                "tool_approval_required",
                                {
                                    "action_requests": pending_interrupt["action_requests"],
                                    "review_configs": pending_interrupt["review_configs"],
                                },
                            )
                            break

                        if stream_mode == "messages":
                            chunk, _metadata = stream_data
                            if isinstance(chunk, AIMessageChunk) and chunk.content:
                                text_content = ""
                                if isinstance(chunk.content, str):
                                    text_content = chunk.content
                                elif isinstance(chunk.content, list):
                                    for block in chunk.content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            text_content += block.get("text", "")
                                        elif isinstance(block, str):
                                            text_content += block
                                if text_content:
                                    await manager.send_event(websocket, "text_delta", {"content": text_content})
                                    final_output += text_content

                        elif stream_mode == "updates":
                            for node_name, update in stream_data.items():
                                if node_name == "tools":
                                    for msg in update.get("messages", []):
                                        if isinstance(msg, ToolMessage):
                                            await manager.send_event(
                                                websocket,
                                                "tool_result",
                                                {"tool_call_id": msg.tool_call_id, "content": msg.content},
                                            )

                    if not pending_interrupt:
                        # No interrupt, send final result
                        if final_output:
                            conversation_history.append({"role": "assistant", "content": final_output})
                        await manager.send_event(websocket, "final_result", {"output": final_output})
                        await manager.send_event(websocket, "complete", {})

                except Exception as e:
                    logger.exception(f"Error resuming agent: {e}")
                    await manager.send_event(websocket, "error", {"message": str(e)})

                continue

            # Regular message handling
            user_message = raw_data.get("message", "")
            # Optionally accept history from client (or use server-side tracking)
            if "history" in raw_data:
                conversation_history = raw_data["history"]

            if not user_message:
                await manager.send_event(websocket, "error", {"message": "Empty message"})
                continue

{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}

            # Handle conversation persistence
            try:
{%- if cookiecutter.use_postgresql %}
                async with get_db_context() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = raw_data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        # Verify conversation exists and update title if empty
                        conv = await conv_service.get_conversation(UUID(requested_conv_id))
                        if not conv.title and user_message:
                            title = user_message[:50] if len(user_message) > 50 else user_message
                            await conv_service.update_conversation(UUID(requested_conv_id), ConversationUpdate(title=title))
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                            user_id=user.id,
{%- endif %}
                            title=user_message[:50] if len(user_message) > 50 else user_message,
                        )
                        conversation = await conv_service.create_conversation(conv_data)
                        current_conversation_id = str(conversation.id)
                        await manager.send_event(
                            websocket,
                            "conversation_created",
                            {"conversation_id": current_conversation_id},
                        )

                    # Save user message
                    user_msg = await conv_service.add_message(
                        UUID(current_conversation_id),
                        MessageCreate(role="user", content=user_message),
                    )
                    # Link uploaded files to this message
                    if file_ids:
                        try:
                            await conv_service.link_files_to_message(user_msg.id, file_ids)
                        except Exception as e:
                            logger.warning(f"Failed to link files: {e}")
{%- else %}
                with contextmanager(get_db_session)() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = raw_data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        conv = conv_service.get_conversation(requested_conv_id)
                        if not conv.title and user_message:
                            title = user_message[:50] if len(user_message) > 50 else user_message
                            conv_service.update_conversation(requested_conv_id, ConversationUpdate(title=title))
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                            user_id=str(user.id),
{%- endif %}
                            title=user_message[:50] if len(user_message) > 50 else user_message,
                        )
                        conversation = conv_service.create_conversation(conv_data)
                        current_conversation_id = str(conversation.id)
                        await manager.send_event(
                            websocket,
                            "conversation_created",
                            {"conversation_id": current_conversation_id},
                        )

                    # Save user message
                    user_msg = conv_service.add_message(
                        current_conversation_id,
                        MessageCreate(role="user", content=user_message),
                    )
                    # Link uploaded files to this message
                    if file_ids:
                        try:
                            conv_service.link_files_to_message(user_msg.id, file_ids)
                        except Exception as e:
                            logger.warning(f"Failed to link files: {e}")
{%- endif %}
            except Exception as e:
                logger.warning(f"Failed to persist conversation: {e}")
                # Continue without persistence
{%- elif cookiecutter.use_mongodb %}

            # Handle conversation persistence (MongoDB)
            conv_service = get_conversation_service()

            requested_conv_id = raw_data.get("conversation_id")
            if requested_conv_id:
                current_conversation_id = requested_conv_id
                conv = await conv_service.get_conversation(requested_conv_id)
                if not conv.title and user_message:
                    title = user_message[:50] if len(user_message) > 50 else user_message
                    await conv_service.update_conversation(requested_conv_id, ConversationUpdate(title=title))
            elif not current_conversation_id:
                conv_data = ConversationCreate(
{%- if cookiecutter.websocket_auth_jwt %}
                    user_id=str(user.id),
{%- endif %}
                    title=user_message[:50] if len(user_message) > 50 else user_message,
                )
                conversation = await conv_service.create_conversation(conv_data)
                current_conversation_id = str(conversation.id)
                await manager.send_event(
                    websocket,
                    "conversation_created",
                    {"conversation_id": current_conversation_id},
                )

            # Save user message
            await conv_service.add_message(
                current_conversation_id,
                MessageCreate(role="user", content=user_message),
            )
{%- endif %}

            await manager.send_event(websocket, "user_prompt", {"content": user_message})

            try:
                final_output = ""
                tool_events: list[Any] = []
                seen_tool_call_ids: set[str] = set()

                await manager.send_event(websocket, "model_request_start", {})

                # Use DeepAgents' stream() which wraps LangGraph's astream
                async for stream_mode, stream_data in assistant.stream(
                    user_message,
                    history=conversation_history,
                    context=context,
                    thread_id=thread_id,
                ):
                    # Handle interrupt - human approval required
                    if stream_mode == "interrupt":
                        pending_interrupt = stream_data
                        await manager.send_event(
                            websocket,
                            "tool_approval_required",
                            {
                                "action_requests": pending_interrupt["action_requests"],
                                "review_configs": pending_interrupt["review_configs"],
                            },
                        )
                        break

                    if stream_mode == "messages":
                        chunk, _metadata = stream_data

                        if isinstance(chunk, AIMessageChunk):
                            if chunk.content:
                                text_content = ""
                                if isinstance(chunk.content, str):
                                    text_content = chunk.content
                                elif isinstance(chunk.content, list):
                                    for block in chunk.content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            text_content += block.get("text", "")
                                        elif isinstance(block, str):
                                            text_content += block

                                if text_content:
                                    await manager.send_event(
                                        websocket,
                                        "text_delta",
                                        {"content": text_content},
                                    )
                                    final_output += text_content

                            # Handle tool call chunks
                            if chunk.tool_call_chunks:
                                for tc_chunk in chunk.tool_call_chunks:
                                    tc_id = tc_chunk.get("id")
                                    tc_name = tc_chunk.get("name")
                                    if tc_id and tc_name and tc_id not in seen_tool_call_ids:
                                        seen_tool_call_ids.add(tc_id)
                                        await manager.send_event(
                                            websocket,
                                            "tool_call",
                                            {
                                                "tool_name": tc_name,
                                                "args": {},
                                                "tool_call_id": tc_id,
                                            },
                                        )

                    elif stream_mode == "updates":
                        # Handle state updates from nodes
                        for node_name, update in stream_data.items():
                            if node_name == "tools":
                                # Tool node completed - extract tool results
                                for msg in update.get("messages", []):
                                    if isinstance(msg, ToolMessage):
                                        await manager.send_event(
                                            websocket,
                                            "tool_result",
                                            {
                                                "tool_call_id": msg.tool_call_id,
                                                "content": msg.content,
                                            },
                                        )
                            elif node_name == "agent":
                                # Agent node completed - check for tool calls
                                for msg in update.get("messages", []):
                                    if isinstance(msg, AIMessage) and msg.tool_calls:
                                        for tc in msg.tool_calls:
                                            tc_id = tc.get("id", "")
                                            if tc_id not in seen_tool_call_ids:
                                                seen_tool_call_ids.add(tc_id)
                                                tool_events.append(tc)
                                                await manager.send_event(
                                                    websocket,
                                                    "tool_call",
                                                    {
                                                        "tool_name": tc.get("name", ""),
                                                        "args": tc.get("args", {}),
                                                        "tool_call_id": tc_id,
                                                    },
                                                )

                # Only send final result if not interrupted
                if not pending_interrupt:
                    await manager.send_event(
                        websocket,
                        "final_result",
                        {"output": final_output},
                    )

                    # Update conversation history
                    conversation_history.append({"role": "user", "content": user_message})
                    if final_output:
                        conversation_history.append(
                            {"role": "assistant", "content": final_output}
                        )

{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}

                    # Save assistant response to database
                    if current_conversation_id and final_output:
                        try:
{%- if cookiecutter.use_postgresql %}
                            async with get_db_context() as db:
                                conv_service = get_conversation_service(db)
                                await conv_service.add_message(
                                    UUID(current_conversation_id),
                                    MessageCreate(
                                        role="assistant",
                                        content=final_output,
                                        model_name=assistant.model_name if hasattr(assistant, "model_name") else None,
                                    ),
                                )
{%- else %}
                            with contextmanager(get_db_session)() as db:
                                conv_service = get_conversation_service(db)
                                conv_service.add_message(
                                    current_conversation_id,
                                    MessageCreate(
                                        role="assistant",
                                        content=final_output,
                                        model_name=assistant.model_name if hasattr(assistant, "model_name") else None,
                                    ),
                                )
{%- endif %}
                        except Exception as e:
                            logger.warning(f"Failed to persist assistant response: {e}")
{%- elif cookiecutter.use_mongodb %}

                    # Save assistant response to database
                    if current_conversation_id and final_output:
                        try:
                            await conv_service.add_message(
                                current_conversation_id,
                                MessageCreate(
                                    role="assistant",
                                    content=final_output,
                                    model_name=assistant.model_name if hasattr(assistant, "model_name") else None,
                                ),
                            )
                        except Exception as e:
                            logger.warning(f"Failed to persist assistant response: {e}")
{%- endif %}

                    await manager.send_event(websocket, "complete", {
{%- if cookiecutter.use_database %}
                        "conversation_id": current_conversation_id,
{%- endif %}
                    })

            except WebSocketDisconnect:
                # Client disconnected during processing - this is normal
                logger.info("Client disconnected during agent processing")
                break
            except Exception as e:
                logger.exception(f"Error processing agent request: {e}")
                # Try to send error, but don't fail if connection is closed
                await manager.send_event(websocket, "error", {"message": str(e)})

    except WebSocketDisconnect:
        pass  # Normal disconnect
    finally:
        manager.disconnect(websocket)
{%- else %}
"""AI Agent routes - not configured."""
{%- endif %}
