{%- if cookiecutter.use_pydantic_ai and cookiecutter.enable_deep_research %}
"""Deep research releases withheld narration when a run ends on it.

Text sent with a planning or delegation tool call is held back as narration.
Pydantic AI continues the run after such a step, so that text is normally not
the answer - but if a run does end there, it was, and must reach the chat
before ``final_result``.
"""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.agent_session import AgentSession

pytestmark = pytest.mark.anyio


class _Request:
    @asynccontextmanager
    async def stream(self, _ctx):
        yield MagicMock()


class _End:
    pass


class _Run:
    """An agent run of one model request followed by the end of the run."""

    def __init__(self, output: str) -> None:
        self.ctx = MagicMock()
        self.result = SimpleNamespace(output=output)

    async def __aiter__(self):
        yield _Request()
        yield _End()


async def _events_for(withheld: list[tuple[int, str]]) -> list[tuple[str, dict]]:
{%- if cookiecutter.websocket_auth_jwt %}
    session = AgentSession(MagicMock(), MagicMock(id=uuid4(), email="u@example.com"))
{%- else %}
    session = AgentSession(MagicMock())
{%- endif %}
    events: list[tuple[str, dict]] = []

    async def _send(_websocket, event_type, data):
        events.append((event_type, data))

    with (
        patch("app.services.agent_session.send_event", _send),
        patch.object(session, "_stream_request_events", AsyncMock(return_value=withheld)),
        patch("app.services.agent_session.Agent.is_user_prompt_node", lambda node: False),
        patch(
            "app.services.agent_session.Agent.is_model_request_node",
            lambda node: isinstance(node, _Request),
        ),
        patch("app.services.agent_session.Agent.is_call_tools_node", lambda node: False),
        patch("app.services.agent_session.Agent.is_end_node", lambda node: isinstance(node, _End)),
    ):
        await session._stream_agent_run(_Run("the report"), "go", [], [])
    return events


async def test_text_withheld_from_the_last_step_is_sent_before_the_result():
    events = await _events_for([(0, "the report")])

    assert events[-2:] == [
        ("text_delta", {"index": 0, "content": "the report"}),
        ("final_result", {"output": "the report"}),
    ]


async def test_nothing_extra_is_sent_when_nothing_was_withheld():
    events = await _events_for([])

    assert [event for event, _ in events] == ["model_request_start", "final_result"]
{%- else %}
"""Deep research streaming tests - not configured (needs Pydantic AI deep research)."""
{%- endif %}
