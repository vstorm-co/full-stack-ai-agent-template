{%- if cookiecutter.use_pydantic_ai %}
# Thin session wrapper — the route is lifecycle plumbing only; orchestration lives here.
import asyncio
import contextlib
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
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
    BinaryContent,
    TextPart,
    ThinkingPart,
    ThinkingPartDelta,
{%- if cookiecutter.enable_deep_research %}
    ToolCallPart,
{%- endif %}
)

from app.agents.assistant import Deps, get_agent
from app.services.agent import (
    build_message_history,
{%- if cookiecutter.use_database %}
    persist_assistant_turn,
    persist_user_turn,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    resolve_kb_collections,
{%- endif %}
    send_event,
)
{%- if cookiecutter.websocket_auth_jwt %}
from app.db.models.user import User
{%- endif %}
from app.api.deps import get_conversation_service
from app.db.session import get_db_context
from app.services.file_storage import get_file_storage
{%- if cookiecutter.enable_billing and cookiecutter.enable_teams and cookiecutter.enable_credits_system %}
from app.services.usage import UsageService
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
from app.core.config import settings
from app.services.research import RESEARCH_TOOL_NAMES, ResearchToolkit
{%- endif %}

logger = logging.getLogger(__name__)


class AgentSession:
    """One WebSocket session with the AI agent."""

    def __init__(
        self,
        websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
        user: User,
{%- endif %}
    ) -> None:
        self.websocket = websocket
{%- if cookiecutter.websocket_auth_jwt %}
        self.user = user
{%- endif %}
        self.conversation_history: list[dict[str, str]] = []
        self.deps = Deps(kb_collection_names=[])
        self.deps.ask_user = self._ask_user
{%- if cookiecutter.use_database %}
        self.current_conversation_id: str | None = None
{%- endif %}
        self._turn_task: asyncio.Task[None] | None = None
        self._ask_user_future: asyncio.Future[list[dict[str, Any]]] | None = None
{%- if cookiecutter.enable_deep_research %}
        self._research: ResearchToolkit | None = None
{%- endif %}
{%- if cookiecutter.enable_subagents %}
        self._subagent_task_manager: Any | None = None
{%- endif %}

    async def handle_frame(self, data: dict[str, Any]) -> None:
        """Dispatch one incoming WebSocket frame.

        A ``stop`` cancels the running turn; an ``ask_user_response`` unblocks a
        paused run; any other control frame is ignored; a bare message starts a
        new turn as a cancellable background task.
        """
        msg_type = data.get("type")

        if msg_type == "stop":
            await self._cancel_turn()
            return

        if msg_type == "ask_user_response":
            fut = self._ask_user_future
            if fut is not None and not fut.done():
                answers = data.get("answers")
                fut.set_result(answers if isinstance(answers, list) else [])
            return

        if msg_type is not None:
            return

        if self._turn_task is not None and not self._turn_task.done():
            logger.warning("Ignoring message received while a turn is already in progress")
            return
        task = asyncio.create_task(self._run_turn(data))
        self._turn_task = task
        task.add_done_callback(self._on_turn_done)

    def _on_turn_done(self, task: asyncio.Task[None]) -> None:
        """Clear the turn slot and surface unexpected crashes."""
        if self._turn_task is task:
            self._turn_task = None
        if not task.cancelled():
            exc = task.exception()
            if isinstance(exc, WebSocketDisconnect):
                logger.info("Client disconnected during agent turn")
            elif exc is not None:
                logger.error("Agent turn task crashed", exc_info=exc)

    async def _run_turn(self, data: dict[str, Any]) -> None:
        """Run one turn, emitting a terminal ``complete`` even when stopped."""
        try:
            await self.process_message(data)
        except asyncio.CancelledError:
            await send_event(
                self.websocket,
                "complete",
                {
{%- if cookiecutter.use_database %}
                    "conversation_id": self.current_conversation_id,
{%- endif %}
                    "stopped": True,
                },
            )
            raise

    async def _cancel_turn(self) -> None:
        """Cancel the in-flight turn task and wait for it to unwind."""
        task = self._turn_task
        if task is None or task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def shutdown(self) -> None:
        """Cancel any in-flight turn."""
        await self._cancel_turn()

    async def process_message(self, data: dict[str, Any]) -> None:
        """Process one user turn: persist input, run the agent, stream events, persist output."""
        user_message = data.get("message", "")
        file_ids = data.get("file_ids", [])

        if not user_message and not file_ids:
            await send_event(self.websocket, "error", {"message": "Empty message"})
            return

{%- if cookiecutter.use_database %}
        self.current_conversation_id, newly_created, organization_id = await persist_user_turn(
{%- if cookiecutter.websocket_auth_jwt %}
            self.user,
{%- endif %}
            user_message,
            file_ids,
            requested_conversation_id=data.get("conversation_id"),
            current_conversation_id=self.current_conversation_id,
        )
        if newly_created and self.current_conversation_id:
            await send_event(
                self.websocket,
                "conversation_created",
                {"conversation_id": self.current_conversation_id},
            )
{%- endif %}

        await send_event(self.websocket, "user_prompt", {"content": user_message})

        try:
{%- if cookiecutter.enable_deep_research %}
            deep_research = settings.ENABLE_DEEP_RESEARCH and bool(data.get("deep_research", False))
            self._research = None
{%- if cookiecutter.enable_todo %}
            todo_cap = None
{%- endif %}
{%- if cookiecutter.enable_subagents %}
            subagent_cap = None
{%- endif %}
            ctx_manager_cap = None
            if deep_research and self.current_conversation_id:
                self._research = ResearchToolkit(self._send, model_name=data.get("model"))
                caps = await self._research.build(self.current_conversation_id)
{%- if cookiecutter.enable_todo %}
                todo_cap = caps.todo
{%- endif %}
{%- if cookiecutter.enable_subagents %}
                subagent_cap = caps.subagents
{%- endif %}
                ctx_manager_cap = caps.context_manager
            else:
                deep_research = False
{%- endif %}
            assistant = get_agent(
                model_name=data.get("model"),
                thinking_effort=data.get("thinking_effort"),
{%- if cookiecutter.enable_deep_research %}
                deep_research=deep_research,
{%- endif %}
{%- if cookiecutter.enable_todo %}
                todo_capability=todo_cap,
{%- endif %}
{%- if cookiecutter.enable_subagents %}
                subagent_capability=subagent_cap,
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
                context_manager_capability=ctx_manager_cap,
{%- endif %}
            )
            model_history = build_message_history(self.conversation_history)
            user_input = await self._build_multimodal_input(user_message, file_ids)
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
            self.deps.kb_collection_names = await resolve_kb_collections(
{%- if cookiecutter.use_database %}
                self.current_conversation_id,
{%- else %}
                None,
{%- endif %}
{%- if cookiecutter.websocket_auth_jwt %}
                self.user.id,
{%- endif %}
                override_kb_ids=(
                    [str(i) for i in (data.get("active_knowledge_base_ids") or [])]
                    if "active_knowledge_base_ids" in data and isinstance(data.get("active_knowledge_base_ids"), list)
                    else None
                ),
{%- if cookiecutter.enable_teams and cookiecutter.use_database %}
                organization_id=str(organization_id) if organization_id else None,
{%- endif %}
            )
{%- endif %}

            collected_tool_calls: list[dict[str, Any]] = []
{%- if cookiecutter.enable_deep_research %}
{%- if cookiecutter.enable_subagents %}
            self._subagent_task_manager = (
                self._research.subagent_capability.task_manager
                if self._research and self._research.subagent_capability
                else None
            )
            if self._subagent_task_manager is not None:
                self._subagent_task_manager.message_bus.add_handler(
                    self._on_subagent_message
                )
{%- endif %}
            poller = (
{%- if cookiecutter.enable_subagents %}
                asyncio.create_task(self._poll_subagent_status())
                if self._research is not None
                else None
{%- else %}
                None
{%- endif %}
            )
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
            try:
                async with assistant.agent.iter(
                    user_input, deps=self.deps, message_history=model_history
                ) as agent_run:
                    await self._stream_agent_run(agent_run, user_message, collected_tool_calls)
            finally:
                if poller is not None:
                    poller.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await poller
{%- if cookiecutter.enable_subagents %}
                if self._subagent_task_manager is not None:
                    self._subagent_task_manager.message_bus.remove_handler(
                        self._on_subagent_message
                    )
                    self._subagent_task_manager = None
{%- endif %}
                if self._research is not None:
                    await self._research.flush()
{%- else %}
            async with assistant.agent.iter(
                user_input, deps=self.deps, message_history=model_history
            ) as agent_run:
                await self._stream_agent_run(agent_run, user_message, collected_tool_calls)
{%- endif %}

            # Update in-memory history only after a complete agent run
            if agent_run.result is not None:
                self.conversation_history.append({"role": "user", "content": user_message})
                self.conversation_history.append(
                    {"role": "assistant", "content": agent_run.result.output}
                )

{%- if cookiecutter.use_database %}
            assistant_msg_id: str | None = None
            if self.current_conversation_id and agent_run.result is not None:
                assistant_msg_id = await persist_assistant_turn(
                    self.current_conversation_id,
                    agent_run.result.output,
                    getattr(assistant, "model_name", None),
                    collected_tool_calls,
                )

{%- if cookiecutter.enable_billing and cookiecutter.enable_teams and cookiecutter.enable_credits_system %}
            # Record usage + debit credits (best-effort).
            if agent_run.result is not None and organization_id:
                await self._record_usage(
                    agent_run=agent_run,
                    assistant=assistant,
                    organization_id=organization_id,
                )
{%- endif %}

            if assistant_msg_id:
                await send_event(
                    self.websocket,
                    "message_saved",
                    {
                        "message_id": assistant_msg_id,
                        "conversation_id": self.current_conversation_id,
                    },
                )

            await send_event(
                self.websocket,
                "complete",
                {"conversation_id": self.current_conversation_id},
            )
{%- else %}
            await send_event(self.websocket, "complete", {})
{%- endif %}
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.exception("Error processing agent request")
            await send_event(self.websocket, "error", {"message": str(e)})

    async def _ask_user(self, questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Pause the run: ask the client questions and block until they answer.

        Emits an ``ask_user`` event with the whole batch, then awaits a future the
        frame dispatcher completes when the matching ``ask_user_response`` arrives.
        The client returns a list of answers parallel to the questions.
        """
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[list[dict[str, Any]]] = loop.create_future()
        self._ask_user_future = fut
        try:
            await send_event(self.websocket, "ask_user", {"questions": questions})
            return await fut
        finally:
            self._ask_user_future = None
{%- if cookiecutter.enable_subagents %}

    async def _send(self, event_type: str, data: Any) -> bool:
        """Emit a WebSocket event on this session's socket (bound for callbacks)."""
        return await send_event(self.websocket, event_type, data)

    async def _poll_subagent_status(self) -> None:
        """Emit ``subagent_status`` frames for changing async subagent tasks.

        Polls the subagent capability's task manager ~1/s and forwards a frame
        whenever a task's status changes (or is first seen). Cancelled in the
        run's ``finally``.
        """
        seen: dict[str, str] = {}
        cap = self._research.subagent_capability if self._research else None
        if cap is None:
            return
        try:
            while True:
                task_manager = cap.task_manager
                if task_manager is not None:
                    for handle in task_manager.list_handles():
                        status = getattr(handle.status, "value", str(handle.status))
                        task_id = handle.task_id
                        if seen.get(task_id) == status:
                            continue
                        seen[task_id] = status
                        await self._send(
                            "subagent_status",
                            {
                                "task_id": task_id,
                                "subagent_name": handle.subagent_name,
                                "description": handle.description,
                                "status": status,
                                "error": handle.error,
                            },
                        )
                        ts = datetime.utcnow().isoformat()
                        if status == "running":
                            await self._send(
                                "subagent_message",
                                {
                                    "task_id": task_id,
                                    "type": "info",
                                    "text": "Task started — running in background",
                                    "timestamp": ts,
                                },
                            )
                        elif status == "waiting_for_answer" and handle.pending_question:
                            await self._send(
                                "subagent_message",
                                {
                                    "task_id": task_id,
                                    "type": "question",
                                    "text": handle.pending_question,
                                    "timestamp": ts,
                                },
                            )
                        elif status == "completed" and handle.result:
                            await self._send(
                                "subagent_message",
                                {
                                    "task_id": task_id,
                                    "type": "result",
                                    "text": handle.result[:1500],
                                    "timestamp": ts,
                                },
                            )
                        elif status == "failed" and handle.error:
                            await self._send(
                                "subagent_message",
                                {
                                    "task_id": task_id,
                                    "type": "error",
                                    "text": handle.error,
                                    "timestamp": ts,
                                },
                            )
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            task_manager = cap.task_manager
            if task_manager is not None:
                for handle in task_manager.list_handles():
                    status = getattr(handle.status, "value", str(handle.status))
                    if seen.get(handle.task_id) == status:
                        continue
                    await self._send(
                        "subagent_status",
                        {
                            "task_id": handle.task_id,
                            "subagent_name": handle.subagent_name,
                            "description": handle.description,
                            "status": status,
                            "error": handle.error,
                        },
                    )
                    ts = datetime.utcnow().isoformat()
                    if status == "completed" and handle.result:
                        await self._send(
                            "subagent_message",
                            {
                                "task_id": handle.task_id,
                                "type": "result",
                                "text": handle.result[:1500],
                                "timestamp": ts,
                            },
                        )
                    elif status == "failed" and handle.error:
                        await self._send(
                            "subagent_message",
                            {
                                "task_id": handle.task_id,
                                "type": "error",
                                "text": handle.error,
                                "timestamp": ts,
                            },
                        )
            raise

    async def _on_subagent_message(self, msg: Any) -> None:
        """Forward TASK_UPDATE (steering) messages from the message bus as SSE events."""
        try:
            from subagents_pydantic_ai.types import MessageType
            if msg.type != MessageType.TASK_UPDATE:
                return
            payload = msg.payload
            text = payload.get("message") if isinstance(payload, dict) else str(payload)
            if not text:
                return
            await self._send(
                "subagent_message",
                {
                    "task_id": msg.task_id,
                    "type": "steering",
                    "text": text,
                    "timestamp": msg.timestamp.isoformat(),
                },
            )
        except Exception:
            pass
{%- endif %}

{%- if cookiecutter.enable_billing and cookiecutter.enable_teams and cookiecutter.enable_credits_system %}
    async def _record_usage(
        self,
        *,
        agent_run: Any,
        assistant: Any,
        organization_id: Any,
    ) -> None:
        """Persist a UsageEvent + debit credits for the just-finished agent run."""
        try:
            usage = agent_run.usage()
        except Exception:
            logger.exception("usage_extract_failed")
            return


        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        cached_tokens = int(getattr(usage, "cache_read_tokens", 0) or 0)
        if input_tokens == 0 and output_tokens == 0:
            return

        try:
            org_uuid = (
                organization_id
                if isinstance(organization_id, UUID)
                else UUID(str(organization_id))
            )
        except Exception:
            logger.warning("usage_record_skipped_invalid_org_id", extra={"org": organization_id})
            return

        conv_uuid: UUID | None = None
        if self.current_conversation_id:
            try:
                conv_uuid = UUID(self.current_conversation_id)
            except Exception:
                conv_uuid = None

        try:
            async with get_db_context() as db:
                svc = UsageService(db)
                await svc.record(
                    organization_id=org_uuid,
                    actor_user_id=self.user.id,
                    conversation_id=conv_uuid,
                    model=getattr(assistant, "model_name", "") or "",
                    provider="{{ cookiecutter.llm_provider }}",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=cached_tokens,
                    ai_framework="pydantic_ai",
                )
        except Exception:
            logger.exception("usage_record_failed", extra={"org_id": str(org_uuid)})
{%- endif %}


    async def _build_multimodal_input(
        self, user_message: str, file_ids: list[Any]
    ) -> str | list[Any]:
        """Fold attached images and parsed file text into the user message."""
        if not file_ids:
            return user_message

        storage = get_file_storage()
        image_parts: list[BinaryContent] = []
        file_context_parts: list[str] = []
        async with get_db_context() as file_db:
            attached_files = await get_conversation_service(file_db).list_attached_files(file_ids)
            for chat_file in attached_files:
                try:
                    if chat_file.file_type == "image":
                        file_data = await storage.load(chat_file.storage_path)
                        image_parts.append(
                            BinaryContent(data=file_data, media_type=chat_file.mime_type)
                        )
                    elif chat_file.parsed_content:
                        file_context_parts.append(
                            f"\n---\nAttached file: {chat_file.filename}\n```\n{chat_file.parsed_content}\n```"
                        )
                except Exception:
                    logger.warning("Failed to load file %s", chat_file.id, exc_info=True)

        full_text = user_message + "".join(file_context_parts)
        if image_parts:
            return [full_text, *image_parts]
        return full_text

    async def _stream_agent_run(
        self,
        agent_run: Any,
        user_message: str,
        collected_tool_calls: list[dict[str, Any]],
    ) -> None:
        """Drive the agent_run iterator, dispatching each node to its streaming helper."""
        async for node in agent_run:
            if Agent.is_user_prompt_node(node):
                prompt_text = (
                    node.user_prompt if isinstance(node.user_prompt, str) else user_message
                )
                await send_event(
                    self.websocket, "user_prompt_processed", {"prompt": prompt_text}
                )
            elif Agent.is_model_request_node(node):
                await send_event(self.websocket, "model_request_start", {})
                async with node.stream(agent_run.ctx) as request_stream:
                    await self._stream_request_events(request_stream)
            elif Agent.is_call_tools_node(node):
                await send_event(self.websocket, "call_tools_start", {})
                async with node.stream(agent_run.ctx) as handle_stream:
                    await self._stream_tool_events(handle_stream, collected_tool_calls)
            elif Agent.is_end_node(node) and agent_run.result is not None:
                await send_event(
                    self.websocket, "final_result", {"output": agent_run.result.output}
                )

    async def _stream_request_events(self, request_stream: Any) -> None:
        """Forward model-request events (text/thinking/tool deltas + final-result start).
{%- if cookiecutter.enable_deep_research %}

        During a deep research turn the model narrates every delegation step.
        A plain-text response ends a PydanticAI run, so a step that issues a
        planning/delegation tool call (``RESEARCH_TOOL_NAMES``) is interstitial:
        its text is buffered and dropped. A step with only content tools (charts,
        RAG) or no tool calls is the final answer and its text is released.
        Reasoning and tool events are always forwarded.
{%- endif %}
        """
{%- if cookiecutter.enable_deep_research %}
        deep_research = self._research is not None
        buffered_text: list[tuple[int, str]] = []
        tool_names: dict[int, str] = {}

        async def emit_text(index: int, content: str) -> None:
            if not content:
                return
            if deep_research:
                buffered_text.append((index, content))
            else:
                await send_event(
                    self.websocket, "text_delta", {"index": index, "content": content}
                )
{%- endif %}
        async for event in request_stream:
            if isinstance(event, PartStartEvent):
                await send_event(
                    self.websocket,
                    "part_start",
                    {"index": event.index, "part_type": type(event.part).__name__},
                )
{%- if cookiecutter.enable_deep_research %}
                if isinstance(event.part, ToolCallPart):
                    if event.part.tool_name:
                        tool_names[event.index] = event.part.tool_name
                elif isinstance(event.part, TextPart) and event.part.content:
                    await emit_text(event.index, event.part.content)
{%- else %}
                if isinstance(event.part, TextPart) and event.part.content:
                    await send_event(
                        self.websocket,
                        "text_delta",
                        {"index": event.index, "content": event.part.content},
                    )
{%- endif %}
                elif isinstance(event.part, ThinkingPart) and event.part.content:
                    await send_event(
                        self.websocket,
                        "thinking_delta",
                        {"index": event.index, "content": event.part.content},
                    )
            elif isinstance(event, PartDeltaEvent):
                if isinstance(event.delta, TextPartDelta):
{%- if cookiecutter.enable_deep_research %}
                    await emit_text(event.index, event.delta.content_delta)
{%- else %}
                    await send_event(
                        self.websocket,
                        "text_delta",
                        {"index": event.index, "content": event.delta.content_delta},
                    )
{%- endif %}
                elif isinstance(event.delta, ThinkingPartDelta):
                    if event.delta.content_delta:
                        await send_event(
                            self.websocket,
                            "thinking_delta",
                            {"index": event.index, "content": event.delta.content_delta},
                        )
                elif isinstance(event.delta, ToolCallPartDelta):
{%- if cookiecutter.enable_deep_research %}
                    if event.delta.tool_name_delta:
                        tool_names[event.index] = (
                            tool_names.get(event.index, "") + event.delta.tool_name_delta
                        )
{%- endif %}
                    await send_event(
                        self.websocket,
                        "tool_call_delta",
                        {"index": event.index, "args_delta": event.delta.args_delta},
                    )
            elif isinstance(event, FinalResultEvent):
                await send_event(
                    self.websocket,
                    "final_result_start",
                    {"tool_name": event.tool_name},
                )
{%- if cookiecutter.enable_deep_research %}

        made_research_call = any(name in RESEARCH_TOOL_NAMES for name in tool_names.values())
        if deep_research and buffered_text and not made_research_call:
            for index, content in buffered_text:
                await send_event(
                    self.websocket, "text_delta", {"index": index, "content": content}
                )
{%- endif %}

    async def _stream_tool_events(
        self,
        handle_stream: Any,
        collected_tool_calls: list[dict[str, Any]],
    ) -> None:
        """Forward tool-call/result events; collect tool calls (with results) for persistence."""
        pending: dict[str, dict[str, Any]] = {}
        async for tool_event in handle_stream:
            if isinstance(tool_event, FunctionToolCallEvent):
                tc = {
                    "tool_call_id": tool_event.part.tool_call_id,
                    "tool_name": tool_event.part.tool_name,
                    "args": tool_event.part.args_as_dict(raise_if_invalid=False),
                }
                collected_tool_calls.append(tc)
                pending[tool_event.part.tool_call_id] = tc
                await send_event(self.websocket, "tool_call", tc)
            elif isinstance(tool_event, FunctionToolResultEvent):
                tc = pending.get(tool_event.tool_call_id)
                if tc is not None:
                    tc["result"] = str(tool_event.result.content)
                await send_event(
                    self.websocket,
                    "tool_result",
                    {
                        "tool_call_id": tool_event.tool_call_id,
                        "content": str(tool_event.result.content),
                    },
                )
{%- elif cookiecutter.use_langchain %}
"""Per-connection AI agent session (LangChain)."""

import asyncio
import contextlib
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from langchain.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.messages.ai import add_usage

from app.agents.langchain_assistant import AgentContext, get_agent
from app.services.agent import (
    build_message_history,
{%- if cookiecutter.use_database %}
    persist_assistant_turn,
    persist_user_turn,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    resolve_kb_collections,
{%- endif %}
    send_event,
)
{%- if cookiecutter.websocket_auth_jwt %}
from app.db.models.user import User
{%- endif %}
{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
from app.db.session import get_db_context
{%- endif %}
{%- if cookiecutter.enable_billing and cookiecutter.enable_teams and cookiecutter.enable_credits_system %}
from app.services.usage import UsageService
{%- endif %}

logger = logging.getLogger(__name__)


class AgentSession:
    """One WebSocket session with the LangChain agent."""

    def __init__(
        self,
        websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
        user: User,
{%- endif %}
    ) -> None:
        self.websocket = websocket
{%- if cookiecutter.websocket_auth_jwt %}
        self.user = user
{%- endif %}
        self.conversation_history: list[dict[str, str]] = []
        self.context: AgentContext = {}
{%- if cookiecutter.websocket_auth_jwt %}
        self.context["user_id"] = str(user.id) if user else None
        self.context["user_name"] = user.email if user else None
{%- endif %}
{%- if cookiecutter.use_database %}
        self.current_conversation_id: str | None = None
{%- endif %}
        self._last_usage_metadata: Any = None
        self._thinking_streamed: bool = False
        self._turn_task: asyncio.Task[None] | None = None

    async def handle_frame(self, data: dict[str, Any]) -> None:
        """Dispatch one incoming WebSocket frame.

        A ``stop`` cancels the running turn; any other frame starts a new turn as
        a cancellable background task. Clients serialize turns, so a frame that
        arrives while a turn is running is ignored.
        """
        if data.get("type") == "stop":
            await self._cancel_turn()
            return

        if self._turn_task is not None and not self._turn_task.done():
            logger.warning("Ignoring message received while a turn is already in progress")
            return
        task = asyncio.create_task(self._run_turn(data))
        self._turn_task = task
        task.add_done_callback(self._on_turn_done)

    def _on_turn_done(self, task: asyncio.Task[None]) -> None:
        """Clear the turn slot and surface unexpected crashes."""
        if self._turn_task is task:
            self._turn_task = None
        if not task.cancelled():
            exc = task.exception()
            if isinstance(exc, WebSocketDisconnect):
                logger.info("Client disconnected during agent turn")
            elif exc is not None:
                logger.error("Agent turn task crashed", exc_info=exc)

    async def _run_turn(self, data: dict[str, Any]) -> None:
        """Run one turn, emitting a terminal ``complete`` even when stopped."""
        try:
            await self.process_message(data)
        except asyncio.CancelledError:
            await send_event(
                self.websocket,
                "complete",
                {
{%- if cookiecutter.use_database %}
                    "conversation_id": self.current_conversation_id,
{%- endif %}
                    "stopped": True,
                },
            )
            raise

    async def _cancel_turn(self) -> None:
        """Cancel the in-flight turn task and wait for it to unwind."""
        task = self._turn_task
        if task is None or task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def shutdown(self) -> None:
        """Cancel any in-flight turn."""
        await self._cancel_turn()

    async def process_message(self, data: dict[str, Any]) -> None:
        """Process one user turn: persist input, run the agent, stream events, persist output."""
        user_message = data.get("message", "")
        file_ids = data.get("file_ids", [])

        if not user_message and not file_ids:
            await send_event(self.websocket, "error", {"message": "Empty message"})
            return

{%- if cookiecutter.use_database %}
        self.current_conversation_id, newly_created, organization_id = await persist_user_turn(
{%- if cookiecutter.websocket_auth_jwt %}
            self.user,
{%- endif %}
            user_message,
            file_ids,
            requested_conversation_id=data.get("conversation_id"),
            current_conversation_id=self.current_conversation_id,
        )
        if newly_created and self.current_conversation_id:
            await send_event(
                self.websocket,
                "conversation_created",
                {"conversation_id": self.current_conversation_id},
            )
{%- endif %}

        await send_event(self.websocket, "user_prompt", {"content": user_message})

        try:
            assistant = get_agent(
                model_name=data.get("model"),
                thinking_effort=data.get("thinking_effort"),
            )
            model_history = build_message_history(self.conversation_history)
            model_history.append(HumanMessage(content=user_message))

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
            from app.agents.tools.rag_tool import _active_kb_collections
            kb_names = await resolve_kb_collections(
{%- if cookiecutter.use_database %}
                self.current_conversation_id,
{%- else %}
                None,
{%- endif %}
{%- if cookiecutter.websocket_auth_jwt %}
                self.user.id,
{%- endif %}
                override_kb_ids=(
                    [str(i) for i in (data.get("active_knowledge_base_ids") or [])]
                    if "active_knowledge_base_ids" in data and isinstance(data.get("active_knowledge_base_ids"), list)
                    else None
                ),
{%- if cookiecutter.enable_teams and cookiecutter.use_database %}
                organization_id=str(organization_id) if organization_id else None,
{%- endif %}
            )
            kb_token = _active_kb_collections.set(kb_names)
            try:
                collected_tool_calls: list[dict[str, Any]] = []
                final_output = await self._stream_agent_response(
                    assistant, model_history, collected_tool_calls
                )
            finally:
                _active_kb_collections.reset(kb_token)
{%- else %}
            collected_tool_calls: list[dict[str, Any]] = []
            final_output = await self._stream_agent_response(
                assistant, model_history, collected_tool_calls
            )
{%- endif %}

            # Update in-memory history only after the agent produced output
            if final_output:
                self.conversation_history.append({"role": "user", "content": user_message})
                self.conversation_history.append(
                    {"role": "assistant", "content": final_output}
                )

{%- if cookiecutter.use_database %}
            assistant_msg_id: str | None = None
            if self.current_conversation_id and final_output:
                assistant_msg_id = await persist_assistant_turn(
                    self.current_conversation_id,
                    final_output,
                    getattr(assistant, "model_name", None),
                    collected_tool_calls,
                )

{%- if cookiecutter.enable_billing and cookiecutter.enable_teams and cookiecutter.enable_credits_system %}
            # Record usage + debit credits (best-effort).
            if final_output and organization_id and self._last_usage_metadata:
                await self._record_usage(
                    assistant=assistant,
                    organization_id=organization_id,
                    usage_metadata=self._last_usage_metadata,
                )
{%- endif %}

            if assistant_msg_id:
                await send_event(
                    self.websocket,
                    "message_saved",
                    {
                        "message_id": assistant_msg_id,
                        "conversation_id": self.current_conversation_id,
                    },
                )

            await send_event(
                self.websocket,
                "complete",
                {"conversation_id": self.current_conversation_id},
            )
{%- else %}
            await send_event(self.websocket, "complete", {})
{%- endif %}
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.exception("Error processing agent request")
            await send_event(self.websocket, "error", {"message": str(e)})

{%- if cookiecutter.enable_billing and cookiecutter.enable_teams and cookiecutter.enable_credits_system %}
    async def _record_usage(
        self,
        *,
        assistant: Any,
        organization_id: Any,
        usage_metadata: Any,
    ) -> None:
        """Persist a UsageEvent + debit credits using LangChain UsageMetadata."""

        if not usage_metadata:
            return
        input_tokens = int(usage_metadata.get("input_tokens") or 0)
        output_tokens = int(usage_metadata.get("output_tokens") or 0)
        cached_tokens = int(
            (usage_metadata.get("input_token_details") or {}).get("cache_read") or 0
        )
        if input_tokens == 0 and output_tokens == 0:
            return

        try:
            org_uuid = (
                organization_id
                if isinstance(organization_id, UUID)
                else UUID(str(organization_id))
            )
        except Exception:
            return

        conv_uuid: UUID | None = None
        if self.current_conversation_id:
            try:
                conv_uuid = UUID(self.current_conversation_id)
            except Exception:
                conv_uuid = None

        try:
            async with get_db_context() as db:
                await UsageService(db).record(
                    organization_id=org_uuid,
                    actor_user_id=self.user.id,
                    conversation_id=conv_uuid,
                    model=getattr(assistant, "model_name", "") or "",
                    provider="{{ cookiecutter.llm_provider }}",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=cached_tokens,
                    ai_framework="langchain",
                )
        except Exception:
            logger.exception("usage_record_failed")
{%- endif %}

    async def _stream_agent_response(
        self,
        assistant: Any,
        model_history: list[Any],
        collected_tool_calls: list[dict[str, Any]],
    ) -> str:
        """Run ``assistant.agent.astream`` and forward all events; return accumulated text."""
        final_output = ""
        seen_tool_call_ids: set[str] = set()
        pending: dict[str, dict[str, Any]] = {}
        # Sum usage_metadata across the turn's model calls. We add only the
        # usage dicts (via add_usage), never whole chunks — merging full
        # AIMessageChunks via `+` crashes on scalar additional_kwargs like the
        # OpenAI Responses API's float ``created_at``.
        self._last_usage_metadata = None
        # Per-turn flag: did we already stream reasoning from token chunks?
        # If not, _stream_update_event falls back to the final message's
        # reasoning so thinking is shown for providers that don't stream it.
        self._thinking_streamed = False

        await send_event(self.websocket, "model_request_start", {})

        async for stream_mode, data in assistant.agent.astream(
            {"messages": model_history},
            stream_mode=["messages", "updates"],
            config={"configurable": self.context} if self.context else None,
        ):
            if stream_mode == "messages":
                token, _metadata = data
                if isinstance(token, AIMessageChunk):
                    if token.usage_metadata:
                        self._last_usage_metadata = (
                            token.usage_metadata
                            if self._last_usage_metadata is None
                            else add_usage(self._last_usage_metadata, token.usage_metadata)
                        )
                    final_output += await self._stream_message_chunk(token)
            elif stream_mode == "updates":
                await self._stream_update_event(
                    data, seen_tool_call_ids, pending, collected_tool_calls
                )

        await send_event(self.websocket, "final_result", {"output": final_output})
        return final_output

    @staticmethod
    def _extract_reasoning(message: Any) -> str:
        """Pull reasoning/thinking text from a LangChain message or chunk.

        Covers three shapes:
          * Anthropic extended thinking — ``{"type":"thinking","thinking":"..."}``
          * OpenAI Responses API — ``{"type":"reasoning","summary":[{"type":"summary_text","text":"..."}]}``
          * Legacy providers — ``additional_kwargs.reasoning_content`` (string)
        """
        out = ""
        content = getattr(message, "content", None)
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "thinking":
                    out += block.get("thinking", "") or ""
                elif btype == "reasoning":
                    for summary in block.get("summary", []) or []:
                        if (
                            isinstance(summary, dict)
                            and summary.get("type") == "summary_text"
                        ):
                            out += summary.get("text", "") or ""
        legacy = (getattr(message, "additional_kwargs", None) or {}).get(
            "reasoning_content"
        )
        if isinstance(legacy, str):
            out += legacy
        return out

    async def _stream_message_chunk(self, token: AIMessageChunk) -> str:
        """Emit text + reasoning deltas from a streaming chunk.

        Tool calls are intentionally NOT emitted here. Streamed
        ``tool_call_chunks`` carry only partial JSON-string argument
        fragments, not a usable args dict — emitting from here produced
        ``tool_call`` events with empty ``args`` (and, because they were
        deduped against the same id set, suppressed the complete event).
        The canonical tool call, with full args, is emitted from the
        ``updates`` stream in ``_stream_update_event``.
        """
        text_content = ""
        if token.content:
            if isinstance(token.content, str):
                text_content = token.content
            elif isinstance(token.content, list):
                for block in token.content:
                    if isinstance(block, str):
                        text_content += block
                    elif isinstance(block, dict) and block.get("type") == "text":
                        text_content += block.get("text", "")
            if text_content:
                await send_event(self.websocket, "text_delta", {"content": text_content})

        reasoning_content = self._extract_reasoning(token)
        if reasoning_content:
            self._thinking_streamed = True
            await send_event(
                self.websocket, "thinking_delta", {"content": reasoning_content}
            )
        return text_content

    async def _stream_update_event(
        self,
        update_data: dict[str, Any],
        seen_tool_call_ids: set[str],
        pending: dict[str, dict[str, Any]],
        collected_tool_calls: list[dict[str, Any]],
    ) -> None:
        """Process ``updates`` stream events — the source of truth for tools.

        Tool calls here carry the complete name + parsed ``args`` from
        ``AIMessage.tool_calls`` (unlike the partial streamed chunks). Also
        emits a reasoning fallback for providers that attach the chain of
        thought to the final message instead of streaming it.
        """
        for node_name, update in update_data.items():
            if node_name == "tools":
                for msg in update.get("messages", []):
                    if isinstance(msg, ToolMessage):
                        tc = pending.get(msg.tool_call_id)
                        if tc is not None:
                            tc["result"] = str(msg.content)
                        await send_event(
                            self.websocket,
                            "tool_result",
                            {"tool_call_id": msg.tool_call_id, "content": msg.content},
                        )
            elif node_name == "model":
                for msg in update.get("messages", []):
                    if not isinstance(msg, AIMessage):
                        continue
                    if not self._thinking_streamed:
                        reasoning = self._extract_reasoning(msg)
                        if reasoning:
                            self._thinking_streamed = True
                            await send_event(
                                self.websocket,
                                "thinking_delta",
                                {"content": reasoning},
                            )
                    for tc_in in msg.tool_calls or []:
                        tc_id = tc_in.get("id", "")
                        if not tc_id:
                            continue
                        tc = {
                            "tool_call_id": tc_id,
                            "tool_name": tc_in.get("name", ""),
                            "args": tc_in.get("args", {}),
                        }
                        pending[tc_id] = tc
                        collected_tool_calls.append(tc)
                        if tc_id not in seen_tool_call_ids:
                            seen_tool_call_ids.add(tc_id)
                            await send_event(self.websocket, "tool_call", tc)
{%- elif cookiecutter.use_langgraph %}
"""Per-connection AI agent session (LangGraph)."""

import asyncio
import contextlib
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_core.messages.ai import add_usage

from app.agents.langgraph_assistant import AgentContext, get_agent
from app.services.agent import (
{%- if cookiecutter.use_database %}
    persist_assistant_turn,
    persist_user_turn,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    resolve_kb_collections,
{%- endif %}
    send_event,
)
{%- if cookiecutter.websocket_auth_jwt %}
from app.db.models.user import User
{%- endif %}
{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
from app.db.session import get_db_context
{%- endif %}
{%- if cookiecutter.enable_billing and cookiecutter.enable_teams and cookiecutter.enable_credits_system %}
from app.services.usage import UsageService
{%- endif %}

logger = logging.getLogger(__name__)


class AgentSession:
    """One WebSocket session with the LangGraph ReAct agent."""

    def __init__(
        self,
        websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
        user: User,
{%- endif %}
    ) -> None:
        self.websocket = websocket
{%- if cookiecutter.websocket_auth_jwt %}
        self.user = user
{%- endif %}
        self.conversation_history: list[dict[str, str]] = []
        self.context: AgentContext = {}
{%- if cookiecutter.websocket_auth_jwt %}
        self.context["user_id"] = str(user.id) if user else None
        self.context["user_name"] = user.email if user else None
{%- endif %}
{%- if cookiecutter.use_database %}
        self.current_conversation_id: str | None = None
{%- endif %}
        self._last_usage_metadata: Any = None
        self._thinking_streamed: bool = False
        self._turn_task: asyncio.Task[None] | None = None

    async def handle_frame(self, data: dict[str, Any]) -> None:
        """Dispatch one incoming WebSocket frame.

        A ``stop`` cancels the running turn; any other frame starts a new turn as
        a cancellable background task. Clients serialize turns, so a frame that
        arrives while a turn is running is ignored.
        """
        if data.get("type") == "stop":
            await self._cancel_turn()
            return

        if self._turn_task is not None and not self._turn_task.done():
            logger.warning("Ignoring message received while a turn is already in progress")
            return
        task = asyncio.create_task(self._run_turn(data))
        self._turn_task = task
        task.add_done_callback(self._on_turn_done)

    def _on_turn_done(self, task: asyncio.Task[None]) -> None:
        """Clear the turn slot and surface unexpected crashes."""
        if self._turn_task is task:
            self._turn_task = None
        if not task.cancelled():
            exc = task.exception()
            if isinstance(exc, WebSocketDisconnect):
                logger.info("Client disconnected during agent turn")
            elif exc is not None:
                logger.error("Agent turn task crashed", exc_info=exc)

    async def _run_turn(self, data: dict[str, Any]) -> None:
        """Run one turn, emitting a terminal ``complete`` even when stopped."""
        try:
            await self.process_message(data)
        except asyncio.CancelledError:
            await send_event(
                self.websocket,
                "complete",
                {
{%- if cookiecutter.use_database %}
                    "conversation_id": self.current_conversation_id,
{%- endif %}
                    "stopped": True,
                },
            )
            raise

    async def _cancel_turn(self) -> None:
        """Cancel the in-flight turn task and wait for it to unwind."""
        task = self._turn_task
        if task is None or task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def shutdown(self) -> None:
        """Cancel any in-flight turn."""
        await self._cancel_turn()

    async def process_message(self, data: dict[str, Any]) -> None:
        """Process one user turn: persist input, run the agent, stream events, persist output."""
        user_message = data.get("message", "")
        file_ids = data.get("file_ids", [])

        if not user_message and not file_ids:
            await send_event(self.websocket, "error", {"message": "Empty message"})
            return

{%- if cookiecutter.use_database %}
        self.current_conversation_id, newly_created, organization_id = await persist_user_turn(
{%- if cookiecutter.websocket_auth_jwt %}
            self.user,
{%- endif %}
            user_message,
            file_ids,
            requested_conversation_id=data.get("conversation_id"),
            current_conversation_id=self.current_conversation_id,
        )
        if newly_created and self.current_conversation_id:
            await send_event(
                self.websocket,
                "conversation_created",
                {"conversation_id": self.current_conversation_id},
            )
{%- endif %}

        await send_event(self.websocket, "user_prompt", {"content": user_message})

        try:
            assistant = get_agent(
                model_name=data.get("model"),
                thinking_effort=data.get("thinking_effort"),
            )

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
            from app.agents.tools.rag_tool import _active_kb_collections
            kb_names = await resolve_kb_collections(
{%- if cookiecutter.use_database %}
                self.current_conversation_id,
{%- else %}
                None,
{%- endif %}
{%- if cookiecutter.websocket_auth_jwt %}
                self.user.id,
{%- endif %}
                override_kb_ids=(
                    [str(i) for i in (data.get("active_knowledge_base_ids") or [])]
                    if "active_knowledge_base_ids" in data and isinstance(data.get("active_knowledge_base_ids"), list)
                    else None
                ),
{%- if cookiecutter.enable_teams and cookiecutter.use_database %}
                organization_id=str(organization_id) if organization_id else None,
{%- endif %}
            )
            kb_token = _active_kb_collections.set(kb_names)
            try:
                collected_tool_calls: list[dict[str, Any]] = []
                final_output = await self._stream_agent_response(
                    assistant, user_message, collected_tool_calls
                )
            finally:
                _active_kb_collections.reset(kb_token)
{%- else %}
            collected_tool_calls: list[dict[str, Any]] = []
            final_output = await self._stream_agent_response(
                assistant, user_message, collected_tool_calls
            )
{%- endif %}

            if final_output:
                self.conversation_history.append({"role": "user", "content": user_message})
                self.conversation_history.append(
                    {"role": "assistant", "content": final_output}
                )

{%- if cookiecutter.use_database %}
            assistant_msg_id: str | None = None
            if self.current_conversation_id and final_output:
                assistant_msg_id = await persist_assistant_turn(
                    self.current_conversation_id,
                    final_output,
                    getattr(assistant, "model_name", None),
                    collected_tool_calls,
                )

{%- if cookiecutter.enable_billing and cookiecutter.enable_teams and cookiecutter.enable_credits_system %}
            # Record usage + debit credits (best-effort).
            if final_output and organization_id and self._last_usage_metadata:
                await self._record_usage(
                    assistant=assistant,
                    organization_id=organization_id,
                    usage_metadata=self._last_usage_metadata,
                )
{%- endif %}

            if assistant_msg_id:
                await send_event(
                    self.websocket,
                    "message_saved",
                    {
                        "message_id": assistant_msg_id,
                        "conversation_id": self.current_conversation_id,
                    },
                )

            await send_event(
                self.websocket,
                "complete",
                {"conversation_id": self.current_conversation_id},
            )
{%- else %}
            await send_event(self.websocket, "complete", {})
{%- endif %}
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.exception("Error processing agent request")
            await send_event(self.websocket, "error", {"message": str(e)})

{%- if cookiecutter.enable_billing and cookiecutter.enable_teams and cookiecutter.enable_credits_system %}
    async def _record_usage(
        self,
        *,
        assistant: Any,
        organization_id: Any,
        usage_metadata: Any,
    ) -> None:
        """Persist a UsageEvent + debit credits using LangChain UsageMetadata."""

        if not usage_metadata:
            return
        input_tokens = int(usage_metadata.get("input_tokens") or 0)
        output_tokens = int(usage_metadata.get("output_tokens") or 0)
        cached_tokens = int(
            (usage_metadata.get("input_token_details") or {}).get("cache_read") or 0
        )
        if input_tokens == 0 and output_tokens == 0:
            return

        try:
            org_uuid = (
                organization_id
                if isinstance(organization_id, UUID)
                else UUID(str(organization_id))
            )
        except Exception:
            return

        conv_uuid: UUID | None = None
        if self.current_conversation_id:
            try:
                conv_uuid = UUID(self.current_conversation_id)
            except Exception:
                conv_uuid = None

        try:
            async with get_db_context() as db:
                await UsageService(db).record(
                    organization_id=org_uuid,
                    actor_user_id=self.user.id,
                    conversation_id=conv_uuid,
                    model=getattr(assistant, "model_name", "") or "",
                    provider="{{ cookiecutter.llm_provider }}",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=cached_tokens,
                    ai_framework="langgraph",
                )
        except Exception:
            logger.exception("usage_record_failed")
{%- endif %}

    async def _stream_agent_response(
        self,
        assistant: Any,
        user_message: str,
        collected_tool_calls: list[dict[str, Any]],
    ) -> str:
        """Run the LangGraph agent stream and forward all events; return accumulated text."""
        final_output = ""
        seen_tool_call_ids: set[str] = set()
        pending: dict[str, dict[str, Any]] = {}
        # Sum usage_metadata across the turn's model calls. We add only the
        # usage dicts (via add_usage), never whole chunks — merging full
        # AIMessageChunks via `+` crashes on scalar additional_kwargs like the
        # OpenAI Responses API's float ``created_at``.
        self._last_usage_metadata = None
        # Per-turn flag: did we already stream reasoning from token chunks?
        # If not, _stream_update_event falls back to the final message's
        # reasoning so thinking is shown for providers that don't stream it.
        self._thinking_streamed = False

        await send_event(self.websocket, "model_request_start", {})

        async for stream_mode, data in assistant.stream(
            user_message, history=self.conversation_history, context=self.context
        ):
            if stream_mode == "messages":
                chunk, _metadata = data
                if isinstance(chunk, AIMessageChunk):
                    if chunk.usage_metadata:
                        self._last_usage_metadata = (
                            chunk.usage_metadata
                            if self._last_usage_metadata is None
                            else add_usage(self._last_usage_metadata, chunk.usage_metadata)
                        )
                    final_output += await self._stream_message_chunk(chunk)
            elif stream_mode == "updates":
                await self._stream_update_event(
                    data, seen_tool_call_ids, pending, collected_tool_calls
                )

        await send_event(self.websocket, "final_result", {"output": final_output})
        return final_output

    @staticmethod
    def _extract_reasoning(message: Any) -> str:
        """Pull reasoning/thinking text from a LangChain message or chunk.

        Covers three shapes:
          * Anthropic extended thinking — ``{"type":"thinking","thinking":"..."}``
          * OpenAI Responses API — ``{"type":"reasoning","summary":[{"type":"summary_text","text":"..."}]}``
          * Legacy providers — ``additional_kwargs.reasoning_content`` (string)
        """
        out = ""
        content = getattr(message, "content", None)
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "thinking":
                    out += block.get("thinking", "") or ""
                elif btype == "reasoning":
                    for summary in block.get("summary", []) or []:
                        if (
                            isinstance(summary, dict)
                            and summary.get("type") == "summary_text"
                        ):
                            out += summary.get("text", "") or ""
        legacy = (getattr(message, "additional_kwargs", None) or {}).get(
            "reasoning_content"
        )
        if isinstance(legacy, str):
            out += legacy
        return out

    async def _stream_message_chunk(self, chunk: AIMessageChunk) -> str:
        """Emit text + reasoning deltas from a streaming chunk.

        Tool calls are intentionally NOT emitted here. Streamed
        ``tool_call_chunks`` carry only partial JSON-string argument
        fragments, not a usable args dict — emitting from here produced
        ``tool_call`` events with empty ``args`` (and, because they were
        deduped against the same id set, suppressed the complete event).
        The canonical tool call, with full args, is emitted from the
        ``updates`` stream in ``_stream_update_event``.
        """
        text_content = ""
        if chunk.content:
            if isinstance(chunk.content, str):
                text_content = chunk.content
            elif isinstance(chunk.content, list):
                for block in chunk.content:
                    if isinstance(block, str):
                        text_content += block
                    elif isinstance(block, dict) and block.get("type") == "text":
                        text_content += block.get("text", "")
            if text_content:
                await send_event(self.websocket, "text_delta", {"content": text_content})

        reasoning_content = self._extract_reasoning(chunk)
        if reasoning_content:
            self._thinking_streamed = True
            await send_event(
                self.websocket, "thinking_delta", {"content": reasoning_content}
            )
        return text_content

    async def _stream_update_event(
        self,
        update_data: dict[str, Any],
        seen_tool_call_ids: set[str],
        pending: dict[str, dict[str, Any]],
        collected_tool_calls: list[dict[str, Any]],
    ) -> None:
        """Process LangGraph ``updates`` events — the source of truth for tools.

        Tool calls here carry the complete name + parsed ``args`` from
        ``AIMessage.tool_calls`` (unlike the partial streamed chunks). Also
        emits a reasoning fallback for providers that attach the chain of
        thought to the final message instead of streaming it.
        """
        for node_name, update in update_data.items():
            if node_name == "tools":
                for msg in update.get("messages", []):
                    if isinstance(msg, ToolMessage):
                        tc = pending.get(msg.tool_call_id)
                        if tc is not None:
                            tc["result"] = str(msg.content)
                        await send_event(
                            self.websocket,
                            "tool_result",
                            {"tool_call_id": msg.tool_call_id, "content": msg.content},
                        )
            elif node_name == "agent":
                for msg in update.get("messages", []):
                    if not isinstance(msg, AIMessage):
                        continue
                    if not self._thinking_streamed:
                        reasoning = self._extract_reasoning(msg)
                        if reasoning:
                            self._thinking_streamed = True
                            await send_event(
                                self.websocket,
                                "thinking_delta",
                                {"content": reasoning},
                            )
                    for tc_in in msg.tool_calls or []:
                        tc_id = tc_in.get("id", "")
                        if not tc_id:
                            continue
                        tc = {
                            "tool_call_id": tc_id,
                            "tool_name": tc_in.get("name", ""),
                            "args": tc_in.get("args", {}),
                        }
                        pending[tc_id] = tc
                        collected_tool_calls.append(tc)
                        if tc_id not in seen_tool_call_ids:
                            seen_tool_call_ids.add(tc_id)
                            await send_event(self.websocket, "tool_call", tc)
{%- elif cookiecutter.use_deepagents %}
"""Per-connection AI agent session (DeepAgents) with human-in-the-loop support."""

import asyncio
import contextlib
import logging
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_core.messages.ai import add_usage

from app.agents.deepagents_assistant import (
    AgentContext,
    Decision,
    InterruptData,
    get_agent,
)
from app.services.agent import (
{%- if cookiecutter.use_database %}
    persist_assistant_turn,
    persist_user_turn,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    resolve_kb_collections,
{%- endif %}
    send_event,
)
{%- if cookiecutter.websocket_auth_jwt %}
from app.db.models.user import User
{%- endif %}
from app.api.deps import get_conversation_service
from app.db.session import get_db_context
{%- if cookiecutter.enable_billing and cookiecutter.enable_teams and cookiecutter.enable_credits_system %}
from app.services.usage import UsageService
{%- endif %}

logger = logging.getLogger(__name__)


class AgentSession:
    """One WebSocket session with a DeepAgents agent (with optional HITL).

    Tracks ``pending_interrupt`` across turns so that ``{"type": "resume"}`` messages
    from the client can be matched to the in-flight agent run.
    """

    def __init__(
        self,
        websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
        user: User,
{%- endif %}
    ) -> None:
        self.websocket = websocket
{%- if cookiecutter.websocket_auth_jwt %}
        self.user = user
{%- endif %}
        self.conversation_history: list[dict[str, str]] = []
        self.context: AgentContext = {}
{%- if cookiecutter.websocket_auth_jwt %}
        self.context["user_id"] = str(user.id) if user else None
        self.context["user_name"] = user.email if user else None
{%- endif %}
        self.thread_id: str = str(uuid.uuid4())
        self.pending_interrupt: InterruptData | None = None
        self.assistant = get_agent()
        # Track the thinking effort baked into ``self.assistant``; if the
        # client toggles it between turns we rebuild the assistant so the new
        # setting takes effect (HITL state is per-graph and changing it would
        # invalidate any pending interrupt anyway).
        self._current_thinking_effort: str | None = None
        self._last_usage_metadata: Any = None
        self._thinking_streamed: bool = False
{%- if cookiecutter.use_database %}
        self.current_conversation_id: str | None = None
{%- endif %}
        self._turn_task: asyncio.Task[None] | None = None

    async def handle_frame(self, data: dict[str, Any]) -> None:
        """Dispatch one incoming WebSocket frame.

        A ``stop`` cancels the running turn; any other frame (a message or a
        ``resume``) starts a new turn as a cancellable background task. Clients
        serialize turns, so a frame that arrives while a turn is running is ignored.
        """
        if data.get("type") == "stop":
            await self._cancel_turn()
            return

        if self._turn_task is not None and not self._turn_task.done():
            logger.warning("Ignoring message received while a turn is already in progress")
            return
        task = asyncio.create_task(self._run_turn(data))
        self._turn_task = task
        task.add_done_callback(self._on_turn_done)

    def _on_turn_done(self, task: asyncio.Task[None]) -> None:
        """Clear the turn slot and surface unexpected crashes."""
        if self._turn_task is task:
            self._turn_task = None
        if not task.cancelled():
            exc = task.exception()
            if isinstance(exc, WebSocketDisconnect):
                logger.info("Client disconnected during agent turn")
            elif exc is not None:
                logger.error("Agent turn task crashed", exc_info=exc)

    async def _run_turn(self, data: dict[str, Any]) -> None:
        """Run one turn, emitting a terminal ``complete`` even when stopped."""
        try:
            await self.process_message(data)
        except asyncio.CancelledError:
            await send_event(
                self.websocket,
                "complete",
                {
{%- if cookiecutter.use_database %}
                    "conversation_id": self.current_conversation_id,
{%- endif %}
                    "stopped": True,
                },
            )
            raise

    async def _cancel_turn(self) -> None:
        """Cancel the in-flight turn task and wait for it to unwind."""
        task = self._turn_task
        if task is None or task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def shutdown(self) -> None:
        """Cancel any in-flight turn."""
        await self._cancel_turn()

    async def process_message(self, data: dict[str, Any]) -> None:
        """Dispatch incoming WebSocket payload to the appropriate handler."""
        if data.get("type", "message") == "resume":
            await self._handle_resume(data)
        else:
            await self._handle_message(data)

    async def _handle_resume(self, data: dict[str, Any]) -> None:
        """Resume an interrupted agent run with user decisions."""
        if not self.pending_interrupt:
            await send_event(
                self.websocket, "error", {"message": "No pending interrupt to resume"}
            )
            return

        decisions: list[Decision] = data.get("decisions", [])
        if len(decisions) != len(self.pending_interrupt["action_requests"]):
            await send_event(
                self.websocket,
                "error",
                {
                    "message": (
                        f"Expected {len(self.pending_interrupt['action_requests'])} decisions, "
                        f"got {len(decisions)}"
                    )
                },
            )
            return

        try:
            await send_event(self.websocket, "resume_start", {})
            collected_tool_calls: list[dict[str, Any]] = []
            final_output, new_interrupt = await self._drive_stream(
                self.assistant.stream_resume(
                    decisions=decisions,
                    thread_id=self.thread_id,
                    context=self.context,
                ),
                collected_tool_calls,
            )
            self.pending_interrupt = new_interrupt
            if new_interrupt:
                return

            if final_output:
                self.conversation_history.append(
                    {"role": "assistant", "content": final_output}
                )
{%- if cookiecutter.use_database %}
            if self.current_conversation_id and final_output:
                await persist_assistant_turn(
                    self.current_conversation_id,
                    final_output,
                    getattr(self.assistant, "model_name", None),
                    collected_tool_calls,
                )
{%- endif %}
            await send_event(
                self.websocket, "final_result", {"output": final_output}
            )
            await send_event(self.websocket, "complete", {})
        except Exception as e:
            logger.exception("Error processing agent request")
            await send_event(self.websocket, "error", {"message": str(e)})

    async def _handle_message(self, data: dict[str, Any]) -> None:
        """Process a regular user message (may produce an interrupt)."""
        user_message = data.get("message", "")
        file_ids = data.get("file_ids", [])

        if "history" in data:
            self.conversation_history[:] = data["history"]

        if not user_message and not file_ids:
            await send_event(self.websocket, "error", {"message": "Empty message"})
            return

        # Reset usage tracking for the new turn (drive_stream accumulates across resumes).
        self._last_usage_metadata = None
        # Per-turn flag for the reasoning fallback in _stream_update_event.
        self._thinking_streamed = False

        # Re-instantiate the assistant if the client toggled thinking effort
        # between turns. The graph caches the model with thinking baked in, so
        # we rebuild lazily to honor the new setting.
        new_thinking_effort = data.get("thinking_effort")
        if new_thinking_effort != self._current_thinking_effort:
            self.assistant = get_agent(thinking_effort=new_thinking_effort)
            self._current_thinking_effort = new_thinking_effort

{%- if cookiecutter.use_database %}
        self.current_conversation_id, newly_created, organization_id = await persist_user_turn(
{%- if cookiecutter.websocket_auth_jwt %}
            self.user,
{%- endif %}
            user_message,
            file_ids,
            requested_conversation_id=data.get("conversation_id"),
            current_conversation_id=self.current_conversation_id,
        )
        if newly_created and self.current_conversation_id:
            await send_event(
                self.websocket,
                "conversation_created",
                {"conversation_id": self.current_conversation_id},
            )
{%- endif %}

        await send_event(self.websocket, "user_prompt", {"content": user_message})

        try:
            agent_input = await self._build_agent_input(user_message, file_ids)

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
            from app.agents.tools.rag_tool import _active_kb_collections
            kb_names = await resolve_kb_collections(
{%- if cookiecutter.use_database %}
                self.current_conversation_id,
{%- else %}
                None,
{%- endif %}
{%- if cookiecutter.websocket_auth_jwt %}
                self.user.id,
{%- endif %}
                override_kb_ids=(
                    [str(i) for i in (data.get("active_knowledge_base_ids") or [])]
                    if "active_knowledge_base_ids" in data and isinstance(data.get("active_knowledge_base_ids"), list)
                    else None
                ),
{%- if cookiecutter.enable_teams and cookiecutter.use_database %}
                organization_id=str(organization_id) if organization_id else None,
{%- endif %}
            )
            kb_token = _active_kb_collections.set(kb_names)
            try:
                await send_event(self.websocket, "model_request_start", {})
                collected_tool_calls: list[dict[str, Any]] = []
                final_output, pending_interrupt = await self._drive_stream(
                    self.assistant.stream(
                        agent_input,
                        history=self.conversation_history,
                        context=self.context,
                        thread_id=self.thread_id,
                    ),
                    collected_tool_calls,
                )
            finally:
                _active_kb_collections.reset(kb_token)
{%- else %}
            await send_event(self.websocket, "model_request_start", {})
            collected_tool_calls: list[dict[str, Any]] = []
            final_output, pending_interrupt = await self._drive_stream(
                self.assistant.stream(
                    agent_input,
                    history=self.conversation_history,
                    context=self.context,
                    thread_id=self.thread_id,
                ),
                collected_tool_calls,
            )
{%- endif %}

            self.pending_interrupt = pending_interrupt
            if pending_interrupt:
                return

            await send_event(self.websocket, "final_result", {"output": final_output})

            if final_output:
                self.conversation_history.append({"role": "user", "content": user_message})
                self.conversation_history.append(
                    {"role": "assistant", "content": final_output}
                )

{%- if cookiecutter.use_database %}
            assistant_msg_id: str | None = None
            if self.current_conversation_id and final_output:
                assistant_msg_id = await persist_assistant_turn(
                    self.current_conversation_id,
                    final_output,
                    getattr(self.assistant, "model_name", None),
                    collected_tool_calls,
                )

{%- if cookiecutter.enable_billing and cookiecutter.enable_teams and cookiecutter.enable_credits_system %}
            # Record usage + debit credits (best-effort).
            if final_output and organization_id and self._last_usage_metadata:
                await self._record_usage(
                    organization_id=organization_id,
                    usage_metadata=self._last_usage_metadata,
                )
{%- endif %}

            if assistant_msg_id:
                await send_event(
                    self.websocket,
                    "message_saved",
                    {
                        "message_id": assistant_msg_id,
                        "conversation_id": self.current_conversation_id,
                    },
                )

            await send_event(
                self.websocket,
                "complete",
                {"conversation_id": self.current_conversation_id},
            )
{%- else %}
            await send_event(self.websocket, "complete", {})
{%- endif %}
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.exception("Error processing agent request")
            await send_event(self.websocket, "error", {"message": str(e)})

{%- if cookiecutter.enable_billing and cookiecutter.enable_teams and cookiecutter.enable_credits_system %}
    async def _record_usage(
        self,
        *,
        organization_id: Any,
        usage_metadata: Any,
    ) -> None:
        """Persist a UsageEvent + debit credits using LangChain UsageMetadata."""

        if not usage_metadata:
            return
        input_tokens = int(usage_metadata.get("input_tokens") or 0)
        output_tokens = int(usage_metadata.get("output_tokens") or 0)
        cached_tokens = int(
            (usage_metadata.get("input_token_details") or {}).get("cache_read") or 0
        )
        if input_tokens == 0 and output_tokens == 0:
            return

        try:
            org_uuid = (
                organization_id
                if isinstance(organization_id, UUID)
                else UUID(str(organization_id))
            )
        except Exception:
            return

        conv_uuid: UUID | None = None
        if self.current_conversation_id:
            try:
                conv_uuid = UUID(self.current_conversation_id)
            except Exception:
                conv_uuid = None

        try:
            async with get_db_context() as db:
                await UsageService(db).record(
                    organization_id=org_uuid,
                    actor_user_id=self.user.id,
                    conversation_id=conv_uuid,
                    model=getattr(self.assistant, "model_name", "") or "",
                    provider="{{ cookiecutter.llm_provider }}",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=cached_tokens,
                    ai_framework="deepagents",
                )
        except Exception:
            logger.exception("usage_record_failed")
{%- endif %}

    async def _drive_stream(
        self,
        stream_iter: Any,
        collected_tool_calls: list[dict[str, Any]],
    ) -> tuple[str, InterruptData | None]:
        """Drive a DeepAgents stream iterator. Returns ``(final_output, pending_interrupt)``."""
        final_output = ""
        seen_tool_call_ids: set[str] = set()
        pending: dict[str, dict[str, Any]] = {}
        pending_interrupt: InterruptData | None = None
        # Sum usage_metadata across the turn's model calls (and across HITL
        # resumes — `_drive_stream` runs multiple times per turn). We add only
        # the usage dicts (via add_usage), never whole chunks: merging full
        # AIMessageChunks via `+` crashes on scalar additional_kwargs like the
        # OpenAI Responses API's float ``created_at``.

        async for stream_mode, stream_data in stream_iter:
            if stream_mode == "interrupt":
                pending_interrupt = stream_data
                await send_event(
                    self.websocket,
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
                    if chunk.usage_metadata:
                        self._last_usage_metadata = (
                            chunk.usage_metadata
                            if self._last_usage_metadata is None
                            else add_usage(self._last_usage_metadata, chunk.usage_metadata)
                        )
                    final_output += await self._stream_message_chunk(chunk)
            elif stream_mode == "updates":
                await self._stream_update_event(
                    stream_data, seen_tool_call_ids, pending, collected_tool_calls
                )

        return final_output, pending_interrupt

    @staticmethod
    def _extract_reasoning(message: Any) -> str:
        """Pull reasoning/thinking text from a LangChain message or chunk.

        Covers three shapes:
          * Anthropic extended thinking — ``{"type":"thinking","thinking":"..."}``
          * OpenAI Responses API — ``{"type":"reasoning","summary":[{"type":"summary_text","text":"..."}]}``
          * Legacy providers — ``additional_kwargs.reasoning_content`` (string)
        """
        out = ""
        content = getattr(message, "content", None)
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "thinking":
                    out += block.get("thinking", "") or ""
                elif btype == "reasoning":
                    for summary in block.get("summary", []) or []:
                        if (
                            isinstance(summary, dict)
                            and summary.get("type") == "summary_text"
                        ):
                            out += summary.get("text", "") or ""
        legacy = (getattr(message, "additional_kwargs", None) or {}).get(
            "reasoning_content"
        )
        if isinstance(legacy, str):
            out += legacy
        return out

    async def _stream_message_chunk(self, chunk: AIMessageChunk) -> str:
        """Emit text + reasoning deltas from a streaming chunk.

        Tool calls are intentionally NOT emitted here. Streamed
        ``tool_call_chunks`` carry only partial JSON-string argument
        fragments, not a usable args dict — emitting from here produced
        ``tool_call`` events with empty ``args`` (and, because they were
        deduped against the same id set, suppressed the complete event).
        The canonical tool call, with full args, is emitted from the
        ``updates`` stream in ``_stream_update_event``.
        """
        text_content = ""
        if chunk.content:
            if isinstance(chunk.content, str):
                text_content = chunk.content
            elif isinstance(chunk.content, list):
                for block in chunk.content:
                    if isinstance(block, str):
                        text_content += block
                    elif isinstance(block, dict) and block.get("type") == "text":
                        text_content += block.get("text", "")
            if text_content:
                await send_event(self.websocket, "text_delta", {"content": text_content})

        reasoning_content = self._extract_reasoning(chunk)
        if reasoning_content:
            self._thinking_streamed = True
            await send_event(
                self.websocket, "thinking_delta", {"content": reasoning_content}
            )
        return text_content

    async def _stream_update_event(
        self,
        update_data: dict[str, Any],
        seen_tool_call_ids: set[str],
        pending: dict[str, dict[str, Any]],
        collected_tool_calls: list[dict[str, Any]],
    ) -> None:
        """Process LangGraph ``updates`` events — the source of truth for tools.

        Tool calls here carry the complete name + parsed ``args`` from
        ``AIMessage.tool_calls`` (unlike the partial streamed chunks). Also
        emits a reasoning fallback for providers that attach the chain of
        thought to the final message instead of streaming it.
        """
        for node_name, update in update_data.items():
            if node_name == "tools":
                for msg in update.get("messages", []):
                    if isinstance(msg, ToolMessage):
                        tc = pending.get(msg.tool_call_id)
                        if tc is not None:
                            tc["result"] = str(msg.content)
                        await send_event(
                            self.websocket,
                            "tool_result",
                            {"tool_call_id": msg.tool_call_id, "content": msg.content},
                        )
            # DeepAgents' create_deep_agent delegates to LangChain
            # create_agent, whose model node is named "model" (not "agent"
            # like the hand-built LangGraph graph). Middleware nodes
            # (TodoListMiddleware.after_model, ...) are ignored.
            elif node_name == "model":
                for msg in update.get("messages", []):
                    if not isinstance(msg, AIMessage):
                        continue
                    if not self._thinking_streamed:
                        reasoning = self._extract_reasoning(msg)
                        if reasoning:
                            self._thinking_streamed = True
                            await send_event(
                                self.websocket,
                                "thinking_delta",
                                {"content": reasoning},
                            )
                    for tc_in in msg.tool_calls or []:
                        tc_id = tc_in.get("id", "")
                        if not tc_id:
                            continue
                        tc = {
                            "tool_call_id": tc_id,
                            "tool_name": tc_in.get("name", ""),
                            "args": tc_in.get("args", {}),
                        }
                        pending[tc_id] = tc
                        collected_tool_calls.append(tc)
                        if tc_id not in seen_tool_call_ids:
                            seen_tool_call_ids.add(tc_id)
                            await send_event(self.websocket, "tool_call", tc)


    async def _build_agent_input(self, user_message: str, file_ids: list[Any]) -> str:
        """Fold attached file content into the user message as a plain-text suffix."""
        if not file_ids:
            return user_message

        file_refs: list[str] = []
        async with get_db_context() as file_db:
            attached_files = await get_conversation_service(file_db).list_attached_files(file_ids)
            for chat_file in attached_files:
                if chat_file.parsed_content:
                    file_refs.append(
                        f"- {chat_file.filename}:\n```\n{chat_file.parsed_content}\n```"
                    )
                elif chat_file.file_type == "image":
                    file_refs.append(f"- {chat_file.filename} (image file)")
                else:
                    file_refs.append(f"- {chat_file.filename} (binary file)")

        if file_refs:
            return user_message + "\n\nAttached files:\n" + "\n".join(file_refs)
        return user_message
{%- elif cookiecutter.use_pydantic_deep %}
"""Per-connection AI agent session (PydanticDeep).

PydanticDeep manages conversation history internally via the backend
(history_messages_path), so this session does not maintain ``conversation_history``.
"""

import asyncio
import contextlib
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
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
from pydantic_ai.messages import BinaryContent, TextPart, ThinkingPart, ThinkingPartDelta

from app.agents.pydantic_deep_assistant import PydanticDeepContext, get_agent
from app.services.agent import (
{%- if cookiecutter.use_database %}
    persist_assistant_turn,
    persist_user_turn,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    resolve_kb_collections,
{%- endif %}
    send_event,
)
{%- if cookiecutter.websocket_auth_jwt %}
from app.db.models.user import User
{%- endif %}
from app.api.deps import get_conversation_service
from app.db.session import get_db_context
from app.services.file_storage import get_file_storage

logger = logging.getLogger(__name__)


class AgentSession:
    """One WebSocket session with the PydanticDeep agent."""

    def __init__(
        self,
        websocket: WebSocket,
{%- if cookiecutter.websocket_auth_jwt %}
        user: User,
{%- endif %}
    ) -> None:
        self.websocket = websocket
{%- if cookiecutter.websocket_auth_jwt %}
        self.user = user
{%- endif %}
        self.context: PydanticDeepContext = {}
{%- if cookiecutter.websocket_auth_jwt %}
        self.context["user_id"] = str(user.id) if user else None
        self.context["user_name"] = user.email if user else None
{%- endif %}
{%- if cookiecutter.use_database %}
        self.current_conversation_id: str | None = None
{%- endif %}
        self._turn_task: asyncio.Task[None] | None = None

    async def handle_frame(self, data: dict[str, Any]) -> None:
        """Dispatch one incoming WebSocket frame.

        A ``stop`` cancels the running turn; any other frame starts a new turn as
        a cancellable background task. Clients serialize turns, so a frame that
        arrives while a turn is running is ignored.
        """
        if data.get("type") == "stop":
            await self._cancel_turn()
            return

        if self._turn_task is not None and not self._turn_task.done():
            logger.warning("Ignoring message received while a turn is already in progress")
            return
        task = asyncio.create_task(self._run_turn(data))
        self._turn_task = task
        task.add_done_callback(self._on_turn_done)

    def _on_turn_done(self, task: asyncio.Task[None]) -> None:
        """Clear the turn slot and surface unexpected crashes."""
        if self._turn_task is task:
            self._turn_task = None
        if not task.cancelled():
            exc = task.exception()
            if isinstance(exc, WebSocketDisconnect):
                logger.info("Client disconnected during agent turn")
            elif exc is not None:
                logger.error("Agent turn task crashed", exc_info=exc)

    async def _run_turn(self, data: dict[str, Any]) -> None:
        """Run one turn, emitting a terminal ``complete`` even when stopped."""
        try:
            await self.process_message(data)
        except asyncio.CancelledError:
            await send_event(
                self.websocket,
                "complete",
                {
{%- if cookiecutter.use_database %}
                    "conversation_id": self.current_conversation_id,
{%- endif %}
                    "stopped": True,
                },
            )
            raise

    async def _cancel_turn(self) -> None:
        """Cancel the in-flight turn task and wait for it to unwind."""
        task = self._turn_task
        if task is None or task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def shutdown(self) -> None:
        """Cancel any in-flight turn."""
        await self._cancel_turn()

    async def process_message(self, data: dict[str, Any]) -> None:
        """Process one user turn: persist input, run the agent, stream events, persist output."""
        user_message = data.get("message", "")
        file_ids = data.get("file_ids", [])

        if not user_message and not file_ids:
            await send_event(self.websocket, "error", {"message": "Empty message"})
            return

{%- if cookiecutter.use_database %}
        self.current_conversation_id, newly_created, organization_id = await persist_user_turn(
{%- if cookiecutter.websocket_auth_jwt %}
            self.user,
{%- endif %}
            user_message,
            file_ids,
            requested_conversation_id=data.get("conversation_id"),
            current_conversation_id=self.current_conversation_id,
        )
        if newly_created and self.current_conversation_id:
            await send_event(
                self.websocket,
                "conversation_created",
                {"conversation_id": self.current_conversation_id},
            )
{%- endif %}

        await send_event(self.websocket, "user_prompt", {"content": user_message})

        try:
            assistant = get_agent(
                model_name=data.get("model"),
                thinking_effort=data.get("thinking_effort"),
{%- if cookiecutter.use_database %}
                conversation_id=self.current_conversation_id or "default",
{%- else %}
                conversation_id="default",
{%- endif %}
{%- if cookiecutter.websocket_auth_jwt %}
                user_id=self.context.get("user_id"),
                user_name=self.context.get("user_name"),
{%- endif %}
            )

            user_input = await self._build_agent_input(user_message, file_ids, assistant)

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
            from app.agents.tools.rag_tool import _active_kb_collections
            kb_names = await resolve_kb_collections(
{%- if cookiecutter.use_database %}
                self.current_conversation_id,
{%- else %}
                None,
{%- endif %}
{%- if cookiecutter.websocket_auth_jwt %}
                self.user.id,
{%- endif %}
                override_kb_ids=(
                    [str(i) for i in (data.get("active_knowledge_base_ids") or [])]
                    if "active_knowledge_base_ids" in data and isinstance(data.get("active_knowledge_base_ids"), list)
                    else None
                ),
{%- if cookiecutter.enable_teams and cookiecutter.use_database %}
                organization_id=str(organization_id) if organization_id else None,
{%- endif %}
            )
            kb_token = _active_kb_collections.set(kb_names)
            try:
                collected_tool_calls: list[dict[str, Any]] = []
                async with assistant.agent.iter(user_input, deps=assistant.deps) as agent_run:
                    await self._stream_agent_run(
                        agent_run, user_message, collected_tool_calls
                    )
            finally:
                _active_kb_collections.reset(kb_token)
{%- else %}
            collected_tool_calls: list[dict[str, Any]] = []
            async with assistant.agent.iter(user_input, deps=assistant.deps) as agent_run:
                await self._stream_agent_run(
                    agent_run, user_message, collected_tool_calls
                )
{%- endif %}

{%- if cookiecutter.use_database %}
            if self.current_conversation_id and agent_run.result is not None:
                await persist_assistant_turn(
                    self.current_conversation_id,
                    agent_run.result.output,
                    getattr(assistant, "model_name", None),
                    collected_tool_calls,
                )

            await send_event(
                self.websocket,
                "complete",
                {"conversation_id": self.current_conversation_id},
            )
{%- else %}
            await send_event(self.websocket, "complete", {})
{%- endif %}
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.exception("Error processing agent request")
            await send_event(self.websocket, "error", {"message": str(e)})


    async def _build_agent_input(
        self, user_message: str, file_ids: list[Any], assistant: Any
    ) -> str | list[Any]:
        """Fold attached files into the agent input.

        Sandbox backends (Docker/Daytona) get files written to the workspace and a path
        reference appended. ``StateBackend`` falls back to inline content. Images are
        always attached as ``BinaryContent`` parts for vision models.
        """
        if not file_ids:
            return user_message

        storage = get_file_storage()
        file_refs: list[str] = []
        image_parts: list[Any] = []

        backend = assistant.deps.backend
        has_sandbox = (
            hasattr(backend, "container_name")
            or hasattr(backend, "upload_bytes")
            or hasattr(backend, "workspace_id")
        )

        async def _process_files(attached_files: Any) -> None:
            for chat_file in attached_files:
                try:
                    rel_path = f"uploads/{chat_file.filename}"

                    if chat_file.file_type == "image":
                        file_data = await storage.load(chat_file.storage_path)
                        image_parts.append(
                            BinaryContent(data=file_data, media_type=chat_file.mime_type)
                        )
                        if has_sandbox:
                            await assistant.write_file_to_workspace(rel_path, file_data)
                            file_refs.append(
                                f"- {rel_path} (image, also attached inline for vision)"
                            )
                        else:
                            file_refs.append(
                                f"- {chat_file.filename} (image attached inline)"
                            )
                    elif chat_file.parsed_content:
                        if has_sandbox:
                            await assistant.write_file_to_workspace(
                                rel_path, chat_file.parsed_content
                            )
                            file_refs.append(f"- {rel_path}")
                        else:
                            file_refs.append(
                                f"- {chat_file.filename}:\n```\n{chat_file.parsed_content}\n```"
                            )
                    else:
                        file_data = await storage.load(chat_file.storage_path)
                        if has_sandbox:
                            await assistant.write_file_to_workspace(rel_path, file_data)
                            file_refs.append(f"- {rel_path}")
                        else:
                            file_refs.append(
                                f"- {chat_file.filename} (binary, not readable as text)"
                            )
                except Exception:
                    logger.warning("Failed to load file %s", chat_file.id, exc_info=True)

        async with get_db_context() as file_db:
            attached_files = await get_conversation_service(file_db).list_attached_files(file_ids)
            await _process_files(attached_files)

        if not file_refs:
            return user_message

        header = (
            "\n\nFiles uploaded to your sandbox workspace (use read_file to access):\n"
            if has_sandbox
            else "\n\nAttached files:\n"
        )
        augmented = user_message + header + "\n".join(file_refs)
        return [augmented, *image_parts] if image_parts else augmented

    async def _stream_agent_run(
        self,
        agent_run: Any,
        user_message: str,
        collected_tool_calls: list[dict[str, Any]],
    ) -> None:
        """Drive the pydantic-ai agent_run iterator, forwarding all events."""
        async for node in agent_run:
            if Agent.is_user_prompt_node(node):
                prompt_text = (
                    node.user_prompt if isinstance(node.user_prompt, str) else user_message
                )
                await send_event(
                    self.websocket, "user_prompt_processed", {"prompt": prompt_text}
                )
            elif Agent.is_model_request_node(node):
                await send_event(self.websocket, "model_request_start", {})
                async with node.stream(agent_run.ctx) as request_stream:
                    await self._stream_request_events(request_stream)
            elif Agent.is_call_tools_node(node):
                await send_event(self.websocket, "call_tools_start", {})
                async with node.stream(agent_run.ctx) as handle_stream:
                    await self._stream_tool_events(handle_stream, collected_tool_calls)
            elif Agent.is_end_node(node) and agent_run.result is not None:
                await send_event(
                    self.websocket, "final_result", {"output": agent_run.result.output}
                )

    async def _stream_request_events(self, request_stream: Any) -> None:
        """Forward model-request events (text/thinking/tool deltas + final-result start)."""
        async for event in request_stream:
            if isinstance(event, PartStartEvent):
                await send_event(
                    self.websocket,
                    "part_start",
                    {"index": event.index, "part_type": type(event.part).__name__},
                )
                if isinstance(event.part, TextPart) and event.part.content:
                    await send_event(
                        self.websocket,
                        "text_delta",
                        {"index": event.index, "content": event.part.content},
                    )
                elif isinstance(event.part, ThinkingPart) and event.part.content:
                    # Surface the model's reasoning trace to the UI. Anthropic +
                    # OpenAI-reasoning models emit these as the model "thinks".
                    await send_event(
                        self.websocket,
                        "thinking_delta",
                        {"index": event.index, "content": event.part.content},
                    )
            elif isinstance(event, PartDeltaEvent):
                if isinstance(event.delta, TextPartDelta):
                    await send_event(
                        self.websocket,
                        "text_delta",
                        {"index": event.index, "content": event.delta.content_delta},
                    )
                elif isinstance(event.delta, ThinkingPartDelta):
                    if event.delta.content_delta:
                        await send_event(
                            self.websocket,
                            "thinking_delta",
                            {"index": event.index, "content": event.delta.content_delta},
                        )
                elif isinstance(event.delta, ToolCallPartDelta):
                    await send_event(
                        self.websocket,
                        "tool_call_delta",
                        {"index": event.index, "args_delta": event.delta.args_delta},
                    )
            elif isinstance(event, FinalResultEvent):
                await send_event(
                    self.websocket,
                    "final_result_start",
                    {"tool_name": event.tool_name},
                )

    async def _stream_tool_events(
        self,
        handle_stream: Any,
        collected_tool_calls: list[dict[str, Any]],
    ) -> None:
        """Forward tool-call/result events; collect tool calls (with results) for persistence."""
        pending: dict[str, dict[str, Any]] = {}
        async for tool_event in handle_stream:
            if isinstance(tool_event, FunctionToolCallEvent):
                tc = {
                    "tool_call_id": tool_event.part.tool_call_id,
                    "tool_name": tool_event.part.tool_name,
                    "args": tool_event.part.args_as_dict(raise_if_invalid=False),
                }
                collected_tool_calls.append(tc)
                pending[tool_event.part.tool_call_id] = tc
                await send_event(self.websocket, "tool_call", tc)
            elif isinstance(tool_event, FunctionToolResultEvent):
                tc = pending.get(tool_event.tool_call_id)
                if tc is not None:
                    tc["result"] = str(tool_event.result.content)
                await send_event(
                    self.websocket,
                    "tool_result",
                    {
                        "tool_call_id": tool_event.tool_call_id,
                        "content": str(tool_event.result.content),
                    },
                )
{%- else %}
"""AI Agent session - not configured."""
{%- endif %}
