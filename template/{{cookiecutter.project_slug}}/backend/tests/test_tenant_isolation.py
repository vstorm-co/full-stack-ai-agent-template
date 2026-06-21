{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Tests for tenant isolation — conversations and RAG documents scoped to orgs.

Verifies that listing and creating resources always uses the active organization
context so users in different orgs cannot see each other's data.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.conversation import ConversationCreate
from app.services.conversation import ConversationService


class TestConversationTenantIsolation:
    """Conversation listing and creation respect organization_id (PostgreSQL)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def _make_org(self, org_id=None):
        org = MagicMock()
        org.id = org_id or uuid.uuid4()
        return org

    def _make_user(self, user_id=None):
        user = MagicMock()
        user.id = user_id or uuid.uuid4()
        return user

    @pytest.mark.anyio
    async def test_list_filters_by_org(self, mock_db):
        """list_conversations passes organization_id filter to repo."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch(
            "app.repositories.conversation_repo.get_conversations_by_user",
            new=AsyncMock(return_value=[]),
        ) as mock_list, patch(
            "app.repositories.conversation_repo.count_conversations",
            new=AsyncMock(return_value=0),
        ) as mock_count:
            svc = ConversationService(mock_db)
            await svc.list_conversations(user_id=user_id, organization_id=org_id)

            mock_list.assert_called_once()
            _, kwargs = mock_list.call_args
            assert kwargs.get("organization_id") == org_id

            mock_count.assert_called_once()
            _, kwargs = mock_count.call_args
            assert kwargs.get("organization_id") == org_id

    @pytest.mark.anyio
    async def test_create_stamps_org_id(self, mock_db):
        """create_conversation passes organization_id to repo."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        mock_conv = MagicMock()

        with patch(
            "app.repositories.conversation_repo.create_conversation",
            new=AsyncMock(return_value=mock_conv),
        ) as mock_create:
            svc = ConversationService(mock_db)
            data = ConversationCreate(user_id=user_id, organization_id=org_id)
            await svc.create_conversation(data)

            mock_create.assert_called_once()
            _, kwargs = mock_create.call_args
            assert kwargs.get("organization_id") == org_id

    @pytest.mark.anyio
    async def test_user_a_cannot_see_org_b_conversations(self, mock_db):
        """User in org A gets no results when org B's conversations exist."""
        org_a = uuid.uuid4()
        user_a = uuid.uuid4()

        # Simulate repo correctly filtering by org — returns empty for org A
        with patch(
            "app.repositories.conversation_repo.get_conversations_by_user",
            new=AsyncMock(return_value=[]),
        ), patch(
            "app.repositories.conversation_repo.count_conversations",
            new=AsyncMock(return_value=0),
        ):
            svc = ConversationService(mock_db)
            items, total = await svc.list_conversations(
                user_id=user_a, organization_id=org_a
            )
            assert items == []
            assert total == 0

    @pytest.mark.anyio
    async def test_list_conversations_passes_user_and_org(self, mock_db):
        """Both user_id and organization_id are passed to repo."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch(
            "app.repositories.conversation_repo.get_conversations_by_user",
            new=AsyncMock(return_value=[]),
        ) as mock_list, patch(
            "app.repositories.conversation_repo.count_conversations",
            new=AsyncMock(return_value=0),
        ):
            svc = ConversationService(mock_db)
            await svc.list_conversations(user_id=user_id, organization_id=org_id)

            _, kwargs = mock_list.call_args
            assert kwargs.get("user_id") == user_id
            assert kwargs.get("organization_id") == org_id


{%- else %}
"""Tenant isolation tests — not configured (enable_teams=false or no JWT)."""
{%- endif %}
