"""AI Agent WebSocket routes with streaming support (PydanticAI)."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
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
from app.api.deps import get_conversation_service, get_current_user_ws
from app.db.models.user import User
from app.db.session import get_db_context
from app.schemas.conversation import (
    ConversationCreate,
    MessageCreate,
    ToolCallCreate,
    ToolCallComplete,
)

logger = logging.getLogger(__name__)

router = APIRouter()


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
        logger.info(
            f"Agent WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

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


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
    user: User = Depends(get_current_user_ws),
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
        "history": [{"role": "user|assistant|system", "content": "..."}],
        "conversation_id": "optional-uuid-to-continue-existing-conversation"
    }

    Authentication: Requires a valid JWT token passed as a query parameter or header.

    Persistence: Set 'conversation_id' to continue an existing conversation.
    If not provided, a new conversation is created. The conversation_id is
    returned in the 'conversation_created' event.
    """

    await manager.connect(websocket)

    # Conversation state per connection
    conversation_history: list[dict[str, str]] = []
    deps = Deps()
    current_conversation_id: str | None = None

    try:
        while True:
            # Receive user message
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            file_ids = data.get("file_ids", [])
            # Optionally accept history from client (or use server-side tracking)
            if "history" in data:
                conversation_history = data["history"]

            if not user_message and not file_ids:
                await manager.send_event(websocket, "error", {"message": "Empty message"})
                continue

            # Handle conversation persistence
            try:
                async with get_db_context() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        # Verify conversation exists
                        await conv_service.get_conversation(UUID(requested_conv_id))
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
                            user_id=user.id,
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

                    # Link uploaded files to this message (same transaction)
                    if file_ids:
                        from sqlalchemy import update as sa_update
                        from app.db.models.chat_file import ChatFile as ChatFileModel
                        try:
                            file_uuids = [UUID(fid) for fid in file_ids]
                            await db.execute(
                                sa_update(ChatFileModel)
                                .where(
                                    ChatFileModel.id.in_(file_uuids),
                                    ChatFileModel.user_id == user.id,
                                )
                                .values(message_id=user_msg.id)
                            )
                            await db.commit()
                        except Exception as e:
                            logger.warning(f"Failed to link files to message: {e}")
            except Exception as e:
                logger.warning(f"Failed to persist conversation: {e}")
                # Continue without persistence

            await manager.send_event(websocket, "user_prompt", {"content": user_message})

            try:
                assistant = get_agent()
                model_history = build_message_history(conversation_history)

                # Collect tool calls during streaming for persistence
                collected_tool_calls: list[dict] = []

                # Load attached files and build multimodal input
                from pydantic_ai.messages import BinaryContent
                from sqlalchemy import select
                from app.db.models.chat_file import ChatFile
                from app.services.file_storage import get_file_storage

                user_input: str | list = user_message
                file_context_parts: list[str] = []

                if file_ids:
                    storage = get_file_storage()
                    image_parts = []

                    async with get_db_context() as file_db:
                        for fid in file_ids:
                            try:
                                result = await file_db.execute(
                                    select(ChatFile).where(ChatFile.id == UUID(fid))
                                )
                                chat_file = result.scalar_one_or_none()
                                if not chat_file or chat_file.user_id != user.id:
                                    continue

                                if chat_file.file_type == "image":
                                    file_data = await storage.load(chat_file.storage_path)
                                    image_parts.append(
                                        BinaryContent(data=file_data, media_type=chat_file.mime_type)
                                    )
                                elif chat_file.parsed_content:
                                    file_context_parts.append(
                                        f"\n---\nAttached file: {chat_file.filename}\n```\n{chat_file.parsed_content}\n```"
                                    )
                            except Exception as e:
                                logger.warning(f"Failed to load file {fid}: {e}")

                    # Build multimodal input if images present
                    if image_parts:
                        full_text = user_message + "".join(file_context_parts)
                        user_input = [full_text, *image_parts]
                    elif file_context_parts:
                        user_input = user_message + "".join(file_context_parts)

                # Use iter() on the underlying PydanticAI agent to stream all events
                async with assistant.agent.iter(
                    user_input,
                    deps=deps,
                    message_history=model_history,
                ) as agent_run:
                    async for node in agent_run:
                        if Agent.is_user_prompt_node(node):
                            # Send only text portion (BinaryContent is not JSON serializable)
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
                                        # Update collected tool call with result
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

                # Save assistant response and tool calls to database
                if current_conversation_id and agent_run.result:
                    try:
                        async with get_db_context() as db:
                            conv_service = get_conversation_service(db)
                            assistant_msg = await conv_service.add_message(
                                UUID(current_conversation_id),
                                MessageCreate(
                                    role="assistant",
                                    content=agent_run.result.output,
                                    model_name=assistant.model_name
                                    if hasattr(assistant, "model_name")
                                    else None,
                                ),
                            )

                            # Save tool calls associated with this assistant message
                            from datetime import datetime, UTC
                            import json
                            for tc in collected_tool_calls:
                                try:
                                    args_dict = tc.get("args", {})
                                    if isinstance(args_dict, str):
                                        args_dict = json.loads(args_dict) if args_dict.strip() else {}
                                    if args_dict is None:
                                        args_dict = {}
                                    tool_call_obj = await conv_service.start_tool_call(
                                        assistant_msg.id,
                                        ToolCallCreate(
                                            tool_call_id=tc["tool_call_id"],
                                            tool_name=tc["tool_name"],
                                            args=args_dict,
                                            started_at=datetime.now(UTC),
                                        ),
                                    )
                                    if tc.get("result"):
                                        await conv_service.complete_tool_call(
                                            tool_call_obj.id,
                                            ToolCallComplete(
                                                result=tc["result"],
                                                completed_at=datetime.now(UTC),
                                                success=True,
                                            ),
                                        )
                                except Exception as e:
                                    logger.warning(f"Failed to persist tool call: {e}")
                    except Exception as e:
                        logger.warning(f"Failed to persist assistant response: {e}")

                await manager.send_event(
                    websocket,
                    "complete",
                    {
                        "conversation_id": current_conversation_id,
                    },
                )

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
