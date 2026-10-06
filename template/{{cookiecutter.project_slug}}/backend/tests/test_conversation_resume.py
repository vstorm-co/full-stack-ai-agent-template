{%- if cookiecutter.use_database and (cookiecutter.use_pydantic_ai or cookiecutter.use_pydantic_deep) %}
"""A conversation resumed on a new connection keeps its context.

The session holds the conversation in memory only while the WebSocket lasts, so
a reconnect - or switching to another conversation - loads that conversation's
stored messages instead of starting the model from nothing, or from the
previous conversation's.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCalls, FunctionModel

from app.services import agent as agent_service
from app.services.agent import HISTORY_REPLAY_LIMIT, load_conversation_history
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


class _Recorder:
    """A streaming model that records the prompts each request carried."""

    def __init__(self) -> None:
        self.seen: list[list[str]] = []

    def respond(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        self.seen.append(_prompts(messages))
        return ModelResponse(parts=[TextPart(content="ok")])

    async def stream(
        self, messages: list[ModelMessage], info: AgentInfo
    ) -> AsyncIterator[str | DeltaToolCalls]:
        self.respond(messages, info)
        yield "ok"

    def model(self) -> FunctionModel:
        return FunctionModel(self.respond, stream_function=self.stream)


def _session() -> AgentSession:
{%- if cookiecutter.websocket_auth_jwt %}
    return AgentSession(MagicMock(), MagicMock(id=uuid4(), email="u@example.com"))
{%- else %}
    return AgentSession(MagicMock())
{%- endif %}


async def _turn(
    session: AgentSession,
    model: _Recorder,
    text: str,
    conversation_id: str,
    *,
    stored: list[dict[str, str]],
    newly_created: bool = False,
) -> None:
    with (
{%- if cookiecutter.use_pydantic_ai %}
        patch("app.agents.assistant._build_model", lambda _name: model.model()),
{%- else %}
        patch(
            "app.agents.pydantic_deep_assistant.PydanticDeepAssistant._get_model_string",
            lambda self: model.model(),
        ),
{%- endif %}
        patch(
            "app.services.agent_session.persist_user_turn",
            AsyncMock(return_value=(conversation_id, newly_created, None)),
        ),
        patch(
            "app.services.agent_session.load_conversation_history",
            AsyncMock(return_value=list(stored)),
        ),
        patch("app.services.agent_session.persist_assistant_turn", AsyncMock(return_value=None)),
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
        patch("app.services.agent_session.resolve_kb_collections", AsyncMock(return_value=[])),
{%- endif %}
{%- if cookiecutter.enable_mcp_client %}
        patch("app.services.agent_session.build_toolsets_for_user", AsyncMock(return_value=[])),
{%- endif %}
        patch("app.services.agent_session.send_event", AsyncMock()),
    ):
        await session.process_message({"message": text, "conversation_id": conversation_id})


STORED = [
    {"role": "user", "content": "my name is Ada"},
    {"role": "assistant", "content": "Hello Ada"},
]


async def test_a_resumed_conversation_starts_from_its_stored_history():
    """A new connection: nothing in memory, the conversation in the database."""
    model = _Recorder()

    await _turn(_session(), model, "what is my name?", str(uuid4()), stored=STORED)

    assert model.seen[-1] == ["my name is Ada", "what is my name?"]


async def test_a_new_conversation_starts_empty():
    model = _Recorder()

    await _turn(_session(), model, "hello", str(uuid4()), stored=STORED, newly_created=True)

    assert model.seen[-1] == ["hello"]


async def test_switching_conversations_does_not_carry_the_previous_one_over():
    session, model = _session(), _Recorder()
    first, second = str(uuid4()), str(uuid4())

    await _turn(session, model, "the secret is 42", first, stored=[])
    await _turn(session, model, "what is the secret?", second, stored=[])

    assert model.seen[-1] == ["what is the secret?"]


def _stored_messages(count: int) -> list[MagicMock]:
    return [
        MagicMock(role="user" if i % 2 == 0 else "assistant", content=f"m{i}") for i in range(count)
    ]


@asynccontextmanager
async def _db():
    yield MagicMock()


async def _load(messages: list[MagicMock], current_prompt: str) -> list[dict[str, str]]:
    service = MagicMock()

    async def list_messages(_conversation_id, *, skip: int = 0, limit: int = 100):
        return messages[skip : skip + limit], len(messages)

    service.list_messages = list_messages
    with (
        patch.object(agent_service, "get_db_context", _db),
        patch.object(agent_service, "get_conversation_service", return_value=service),
    ):
        return await load_conversation_history(str(uuid4()), current_prompt=current_prompt)


async def test_the_current_prompt_is_not_replayed_as_history():
    messages = [*_stored_messages(2), MagicMock(role="user", content="now")]

    history = await _load(messages, "now")

    assert history == [{"role": "user", "content": "m0"}, {"role": "assistant", "content": "m1"}]


async def test_only_the_most_recent_messages_are_replayed():
    messages = [*_stored_messages(HISTORY_REPLAY_LIMIT + 10), MagicMock(role="user", content="now")]

    history = await _load(messages, "now")

    assert len(history) == HISTORY_REPLAY_LIMIT
    assert history[-1]["content"] == f"m{HISTORY_REPLAY_LIMIT + 9}"
{%- else %}
"""Conversation resume tests - not configured (needs a database and Pydantic AI or PydanticDeep)."""
{%- endif %}
