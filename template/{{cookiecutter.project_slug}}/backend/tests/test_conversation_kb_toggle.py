{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
"""Tests for Conversation KB toggle — active_knowledge_base_ids semantics."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.services.conversation import ConversationService


def _conv(active_kb_ids=None):
    conv = MagicMock()
    conv.id = "conv-1"
    conv.active_knowledge_base_ids = active_kb_ids
    conv.user_id = "user-1"
    return conv


class TestConversationKBToggle:
    """Service-level tests for KB toggle (PostgreSQL async)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.mark.anyio
    async def test_update_sets_explicit_kb_list(self, mock_db):
        conv = _conv()
        updated = _conv(active_kb_ids=["kb-1", "kb-2"])

        with patch("app.repositories.conversation_repo.get_conversation_by_id", new=AsyncMock(return_value=conv)), \
             patch("app.repositories.conversation_repo.update_conversation", new=AsyncMock(return_value=updated)):
            svc = ConversationService(mock_db)
            result = await svc.update_kb_settings("conv-1", ["kb-1", "kb-2"], user_id="user-1")
            assert result.active_knowledge_base_ids == ["kb-1", "kb-2"]

    @pytest.mark.anyio
    async def test_update_to_none_restores_defaults(self, mock_db):
        conv = _conv(active_kb_ids=["kb-1"])
        updated = _conv(active_kb_ids=None)

        with patch("app.repositories.conversation_repo.get_conversation_by_id", new=AsyncMock(return_value=conv)), \
             patch("app.repositories.conversation_repo.update_conversation", new=AsyncMock(return_value=updated)):
            svc = ConversationService(mock_db)
            result = await svc.update_kb_settings("conv-1", None, user_id="user-1")
            assert result.active_knowledge_base_ids is None

    @pytest.mark.anyio
    async def test_update_to_empty_disables_rag(self, mock_db):
        conv = _conv(active_kb_ids=["kb-1"])
        updated = _conv(active_kb_ids=[])

        with patch("app.repositories.conversation_repo.get_conversation_by_id", new=AsyncMock(return_value=conv)), \
             patch("app.repositories.conversation_repo.update_conversation", new=AsyncMock(return_value=updated)):
            svc = ConversationService(mock_db)
            result = await svc.update_kb_settings("conv-1", [], user_id="user-1")
            assert result.active_knowledge_base_ids == []

    @pytest.mark.anyio
    async def test_update_kb_settings_passes_correct_update_data(self, mock_db):
        conv = _conv()

        with patch("app.repositories.conversation_repo.get_conversation_by_id", new=AsyncMock(return_value=conv)) as _get, \
             patch("app.repositories.conversation_repo.update_conversation", new=AsyncMock(return_value=conv)) as mock_update:
            svc = ConversationService(mock_db)
            await svc.update_kb_settings("conv-1", ["kb-x"], user_id="user-1")

            mock_update.assert_called_once()
            _, kwargs = mock_update.call_args
            assert kwargs["update_data"] == {"active_knowledge_base_ids": ["kb-x"]}

    @pytest.mark.anyio
    async def test_update_kb_settings_other_user_raises(self, mock_db):
        conv = _conv()
        conv.user_id = "owner"

        with patch("app.repositories.conversation_repo.get_conversation_by_id", new=AsyncMock(return_value=conv)), \
             patch("app.services.conversation.conversation_share_repo.get_share", new=AsyncMock(return_value=None)):
            svc = ConversationService(mock_db)
            with pytest.raises(NotFoundError):
                await svc.update_kb_settings("conv-1", ["kb-1"], user_id="other")


{%- else %}
"""Conversation KB toggle tests — not configured (enable_teams, enable_rag, or use_jwt is false)."""
{%- endif %}
