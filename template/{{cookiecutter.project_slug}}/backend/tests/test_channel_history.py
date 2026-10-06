{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
"""A channel message reaches the model once, not once as prompt and once as history."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.agent_invocation import AgentInvocationService

pytestmark = pytest.mark.anyio


async def test_history_is_what_came_before_the_new_message():
    stored = [{"role": "user", "content": "earlier"}, {"role": "assistant", "content": "reply"}]
    service = AgentInvocationService(MagicMock())

    async def _persist(_conversation_id, content):
        stored.append({"role": "user", "content": content})

    call_agent = AsyncMock(return_value=("ok", []))
    with (
        patch.object(service, "_load_history", AsyncMock(side_effect=lambda _id: list(stored))),
        patch.object(service, "_persist_user_message", AsyncMock(side_effect=_persist)),
        patch.object(service, "_persist_assistant_message", AsyncMock()),
        patch.object(service, "_load_active_kb_collection_names", AsyncMock(return_value=[])),
        patch.object(service, "_call_agent", call_agent),
    ):
        await service.invoke(user_message="now", conversation_id=uuid4())

    history = call_agent.call_args.kwargs["history"]
    assert history == [
        {"role": "user", "content": "earlier"},
        {"role": "assistant", "content": "reply"},
    ]
{%- else %}
"""Channel history tests - not configured (no Telegram or Slack)."""
{%- endif %}
