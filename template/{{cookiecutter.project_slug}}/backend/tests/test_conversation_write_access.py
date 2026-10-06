{%- if cookiecutter.use_database and cookiecutter.websocket_auth_jwt and (cookiecutter.use_pydantic_ai or cookiecutter.use_langchain or cookiecutter.use_langgraph or cookiecutter.use_deepagents or cookiecutter.use_pydantic_deep) %}
"""A chat turn over the WebSocket may only write to a conversation the user can edit.

The REST route checks this in ``ConversationService.add_message``; the WebSocket
path reaches the same method through ``persist_user_turn``, which logs and
carries on after a failure to persist. An access refusal must not be treated as
one: the turn would go on, and the agent's reply would be written into a
conversation the user may only read, or may not see at all.
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthorizationError, NotFoundError
from app.services.agent import persist_user_turn
from app.services.agent_session import AgentSession


def _service(*, get_conversation: AsyncMock, add_message: AsyncMock) -> MagicMock:
    service = MagicMock()
    service.get_conversation = get_conversation
    service.add_message = add_message
    service.update_conversation = AsyncMock()
    return service


async def _persist(service: MagicMock, user: MagicMock) -> tuple[str | None, bool, str | None]:
    @asynccontextmanager
    async def _db():
        yield MagicMock()

    with (
        patch("app.services.agent.get_db_context", _db),
        patch("app.services.agent.get_conversation_service", return_value=service),
    ):
        return await persist_user_turn(
            user,
            "hello",
            [],
            requested_conversation_id=str(uuid.uuid4()),
            current_conversation_id=None,
        )


class TestPersistUserTurn:
    @pytest.mark.anyio
    async def test_a_conversation_the_user_cannot_see_is_refused(self):
        service = _service(
            get_conversation=AsyncMock(side_effect=NotFoundError(message="Conversation not found")),
            add_message=AsyncMock(),
        )

        with pytest.raises(NotFoundError):
            await _persist(service, MagicMock(id=uuid.uuid4()))

        service.add_message.assert_not_called()

    @pytest.mark.anyio
    async def test_a_view_only_share_is_refused(self):
        user = MagicMock(id=uuid.uuid4())
        service = _service(
            get_conversation=AsyncMock(return_value=MagicMock(title="t")),
            add_message=AsyncMock(
                side_effect=AuthorizationError(
                    message="You do not have edit permission for this conversation"
                )
            ),
        )

        with pytest.raises(AuthorizationError):
            await _persist(service, user)

        assert service.add_message.call_args.kwargs["user_id"] == user.id

    @pytest.mark.anyio
    async def test_other_failures_are_still_logged_and_the_turn_goes_on(self):
        service = _service(
            get_conversation=AsyncMock(return_value=MagicMock(title="t")),
            add_message=AsyncMock(side_effect=RuntimeError("database hiccup")),
        )

        conversation_id, newly_created, _ = await _persist(service, MagicMock(id=uuid.uuid4()))

        assert conversation_id is not None
        assert newly_created is False


class TestRefusedTurn:
    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "refusal",
        [
            NotFoundError(message="Conversation not found"),
            AuthorizationError(message="You do not have edit permission for this conversation"),
        ],
        ids=["not-visible", "view-only"],
    )
    async def test_the_agent_never_runs(self, refusal):
        session = AgentSession(MagicMock(), MagicMock(id=uuid.uuid4()))
        events: list[tuple[str, dict]] = []

        async def _send_event(_websocket, event_type, data):
            events.append((event_type, data))

        with (
            patch("app.services.agent_session.persist_user_turn", AsyncMock(side_effect=refusal)),
            patch("app.services.agent_session.send_event", _send_event),
            patch("app.services.agent_session.persist_assistant_turn", AsyncMock()) as persisted,
        ):
            await session.process_message(
                {"message": "hello", "conversation_id": str(uuid.uuid4())}
            )

        assert events == [("error", {"message": refusal.message})]
        persisted.assert_not_called()
{%- else %}
"""Conversation write access over the WebSocket - needs a database and JWT auth."""
{%- endif %}
