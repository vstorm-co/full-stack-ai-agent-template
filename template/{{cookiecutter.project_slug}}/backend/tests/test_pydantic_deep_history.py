{%- if cookiecutter.use_pydantic_deep %}
"""A PydanticDeep chat remembers the conversation from one turn to the next.

pydantic-deep keeps no history between runs, and the session builds a new agent
for every turn, so the session carries the conversation itself - and the
in-memory workspace, so files written in one turn are there in the next.
"""

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, DeltaToolCalls, FunctionModel

from app.agents.pydantic_deep_assistant import PydanticDeepAssistant, to_model_messages
from app.services.agent_session import AgentSession

pytestmark = pytest.mark.anyio


def _prompts(messages: list[ModelMessage]) -> list[str]:
    return [
        part.content
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, UserPromptPart) and isinstance(part.content, str)
    ]


class _Script:
    """A model that answers each turn from a script and records what it saw."""

    def __init__(self) -> None:
        self.seen: list[list[str]] = []
        self.tool_results: list[str] = []
        self.turns: dict[str, list[ModelResponse]] = {}

    def respond(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        for message in messages:
            for part in getattr(message, "parts", []):
                if isinstance(part, ToolReturnPart):
                    self.tool_results.append(str(part.content))
        prompt = _prompts(messages)[-1]
        if not self.turns.get(prompt):
            self.seen.append(_prompts(messages))
            return ModelResponse(parts=[TextPart(content=f"answered: {prompt}")])
        return self.turns[prompt].pop(0)

    async def stream(
        self, messages: list[ModelMessage], info: AgentInfo
    ) -> AsyncIterator[str | DeltaToolCalls]:
        """The session streams its runs: the same answers, as deltas."""
        for part in self.respond(messages, info).parts:
            if isinstance(part, TextPart):
                yield part.content
            elif isinstance(part, ToolCallPart):
                yield {0: DeltaToolCall(name=part.tool_name, json_args=json.dumps(part.args))}

    def model(self) -> FunctionModel:
        return FunctionModel(self.respond, stream_function=self.stream)


async def _turn(
    session: AgentSession, script: _Script, text: str, conversation_id: str
) -> None:
    with (
        patch.object(
            PydanticDeepAssistant, "_get_model_string", lambda self: script.model()
        ),
{%- if cookiecutter.use_database %}
        patch(
            "app.services.agent_session.persist_user_turn",
            AsyncMock(return_value=(conversation_id, False, None)),
        ),
        patch("app.services.agent_session.persist_assistant_turn", AsyncMock()),
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        patch("app.services.agent_session.resolve_kb_collections", AsyncMock(return_value=[])),
{%- endif %}
        patch("app.services.agent_session.send_event", AsyncMock()),
    ):
        await session.process_message({"message": text, "conversation_id": conversation_id})


C1, C2 = str(uuid4()), str(uuid4())


def _session() -> AgentSession:
{%- if cookiecutter.websocket_auth_jwt %}
    return AgentSession(MagicMock(), MagicMock(id="u1", email="u@example.com"))
{%- else %}
    return AgentSession(MagicMock())
{%- endif %}


async def test_the_second_turn_sees_the_first():
    session, script = _session(), _Script()

    await _turn(session, script, "my name is Ada", C1)
    await _turn(session, script, "what is my name?", C1)

    assert script.seen[-1] == ["my name is Ada", "what is my name?"]


async def test_a_file_written_in_one_turn_is_there_in_the_next():
    session, script = _session(), _Script()
    script.turns["save a note"] = [
        ModelResponse(
            parts=[ToolCallPart("write_file", {"path": "notes.txt", "content": "remember me"})]
        ),
        ModelResponse(parts=[TextPart(content="saved")]),
    ]
    script.turns["read the note"] = [
        ModelResponse(parts=[ToolCallPart("read_file", {"path": "notes.txt"})]),
        ModelResponse(parts=[TextPart(content="done")]),
    ]

    await _turn(session, script, "save a note", C1)
    await _turn(session, script, "read the note", C1)

    assert any("remember me" in result for result in script.tool_results)

{%- if cookiecutter.use_database %}


async def test_another_conversation_starts_afresh():
    session, script = _session(), _Script()

    await _turn(session, script, "my name is Ada", C1)
    await _turn(session, script, "what is my name?", C2)

    assert script.seen[-1] == ["what is my name?"]
{%- endif %}


def test_persisted_messages_become_model_messages():
    messages = to_model_messages(
        [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "system", "content": "ignored"},
        ]
    )

    assert [type(m) for m in messages] == [ModelRequest, ModelResponse]
    assert _prompts(messages) == ["hi"]


def test_no_history_is_no_messages():
    empty: list[Any] = []
    assert to_model_messages(None) == empty
{%- else %}
"""PydanticDeep history tests - not configured (another AI framework)."""
{%- endif %}
