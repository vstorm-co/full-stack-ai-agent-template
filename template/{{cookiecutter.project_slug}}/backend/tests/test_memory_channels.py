{%- if cookiecutter.enable_memory and (cookiecutter.use_telegram or cookiecutter.use_slack) %}
"""Channel messages use the user's memory only in a one-to-one chat."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.agent_invocation import AgentInvocationService

pytestmark = pytest.mark.anyio


_CAPABILITY = object()


class _Stop(Exception):
    """Ends the call once the agent has been built."""


async def _memory_given_to_agent(**kwargs) -> object:
    seen: dict[str, object] = {}

    def _get_agent(**agent_kwargs):
        seen.update(agent_kwargs)
        raise _Stop

    with (
        patch(
            "app.services.agent_invocation.build_memory_capability",
            AsyncMock(return_value=_CAPABILITY),
        ),
        patch("app.services.agent_invocation.get_agent", _get_agent),
{%- if cookiecutter.enable_mcp_client %}
        patch("app.services.agent_invocation.build_toolsets_for_user", AsyncMock(return_value=[])),
{%- endif %}
        pytest.raises(_Stop),
    ):
        await AgentInvocationService(MagicMock())._call_pydantic_ai(
            user_message="hi", history=[], **kwargs
        )
    return seen["memory_capability"]


async def test_a_direct_message_from_a_linked_user_uses_memory():
    memory = await _memory_given_to_agent(
        user_id=uuid4(), organization_id=uuid4(), direct_message=True
    )
    assert memory is _CAPABILITY


async def test_a_group_chat_does_not():
    """The user's private notes would be answered into the channel."""
    memory = await _memory_given_to_agent(
        user_id=uuid4(), organization_id=uuid4(), direct_message=False
    )
    assert memory is None


async def test_anonymous_traffic_does_not():
    memory = await _memory_given_to_agent(user_id=None, direct_message=True)
    assert memory is None
{%- else %}
"""Channel memory tests - not configured (needs enable_memory and a channel)."""
{%- endif %}
