{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
"""Tests for Knowledge Base scoping — personal / org / app access rules."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthorizationError, BadRequestError, NotFoundError
from app.schemas.knowledge_base import KnowledgeBaseCreate
from app.services.knowledge_base import KnowledgeBaseService


def _kb(scope: str, owner_user_id=None, organization_id=None, is_default: bool = False):
    kb = MagicMock()
    kb.id = uuid.uuid4()
    kb.scope = scope
    kb.owner_user_id = owner_user_id
    kb.organization_id = organization_id
    kb.is_default = is_default
    return kb


class TestKBAccessControl:
    """Service-level access checks for all 3 scopes (PostgreSQL async)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.mark.anyio
    async def test_personal_kb_visible_to_owner(self, mock_db):
        user_id = uuid.uuid4()
        kb = _kb("personal", owner_user_id=user_id)

        with patch("app.repositories.knowledge_base_repo.get_by_id", new=AsyncMock(return_value=kb)):
            svc = KnowledgeBaseService(mock_db)
            result = await svc.get(kb.id, user_id=user_id)
            assert result is kb

    @pytest.mark.anyio
    async def test_personal_kb_hidden_from_other_user(self, mock_db):
        owner = uuid.uuid4()
        other = uuid.uuid4()
        kb = _kb("personal", owner_user_id=owner)

        with patch("app.repositories.knowledge_base_repo.get_by_id", new=AsyncMock(return_value=kb)):
            svc = KnowledgeBaseService(mock_db)
            with pytest.raises(NotFoundError):
                await svc.get(kb.id, user_id=other)

    @pytest.mark.anyio
    async def test_org_kb_visible_to_member(self, mock_db):
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        kb = _kb("org", organization_id=org_id)

        with patch("app.repositories.knowledge_base_repo.get_by_id", new=AsyncMock(return_value=kb)):
            svc = KnowledgeBaseService(mock_db)
            result = await svc.get(kb.id, user_id=user_id, organization_id=org_id)
            assert result is kb

    @pytest.mark.anyio
    async def test_org_kb_hidden_from_other_org(self, mock_db):
        org_a = uuid.uuid4()
        org_b = uuid.uuid4()
        user_id = uuid.uuid4()
        kb = _kb("org", organization_id=org_a)

        with patch("app.repositories.knowledge_base_repo.get_by_id", new=AsyncMock(return_value=kb)):
            svc = KnowledgeBaseService(mock_db)
            with pytest.raises(NotFoundError):
                await svc.get(kb.id, user_id=user_id, organization_id=org_b)

    @pytest.mark.anyio
    async def test_app_kb_visible_to_anyone(self, mock_db):
        user_id = uuid.uuid4()
        kb = _kb("app")

        with patch("app.repositories.knowledge_base_repo.get_by_id", new=AsyncMock(return_value=kb)):
            svc = KnowledgeBaseService(mock_db)
            result = await svc.get(kb.id, user_id=user_id)
            assert result is kb

    @pytest.mark.anyio
    async def test_cannot_delete_default_kb(self, mock_db):
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        kb = _kb("org", organization_id=org_id, is_default=True)

        with patch("app.repositories.knowledge_base_repo.get_by_id", new=AsyncMock(return_value=kb)):
            svc = KnowledgeBaseService(mock_db)
            with pytest.raises(BadRequestError):
                await svc.delete(kb.id, user_id=user_id, organization_id=org_id)

    @pytest.mark.anyio
    async def test_non_app_admin_cannot_create_app_kb(self, mock_db):
        user_id = uuid.uuid4()
        data = KnowledgeBaseCreate(name="Global KB", scope="app", collection_name="global")

        svc = KnowledgeBaseService(mock_db)
        with pytest.raises(AuthorizationError):
            await svc.create(data, user_id=user_id, is_app_admin=False)

    @pytest.mark.anyio
    async def test_app_admin_can_create_app_kb(self, mock_db):
        user_id = uuid.uuid4()
        data = KnowledgeBaseCreate(name="Global KB", scope="app", collection_name="global")
        mock_kb = MagicMock()

        with patch("app.repositories.knowledge_base_repo.create", new=AsyncMock(return_value=mock_kb)):
            svc = KnowledgeBaseService(mock_db)
            result = await svc.create(data, user_id=user_id, is_app_admin=True)
            assert result is mock_kb

    @pytest.mark.anyio
    async def test_org_kb_creation_without_org_raises(self, mock_db):
        user_id = uuid.uuid4()
        data = KnowledgeBaseCreate(name="Team KB", scope="org", collection_name="team")

        svc = KnowledgeBaseService(mock_db)
        with pytest.raises(AuthorizationError):
            await svc.create(data, user_id=user_id, organization_id=None)

    @pytest.mark.anyio
    async def test_personal_kb_owner_can_delete(self, mock_db):
        user_id = uuid.uuid4()
        kb = _kb("personal", owner_user_id=user_id)

        with patch("app.repositories.knowledge_base_repo.get_by_id", new=AsyncMock(return_value=kb)), \
             patch("app.repositories.knowledge_base_repo.delete", new=AsyncMock(return_value=True)):
            svc = KnowledgeBaseService(mock_db)
            await svc.delete(kb.id, user_id=user_id)

    @pytest.mark.anyio
    async def test_personal_kb_non_owner_cannot_delete(self, mock_db):
        owner = uuid.uuid4()
        other = uuid.uuid4()
        kb = _kb("personal", owner_user_id=owner)

        with patch("app.repositories.knowledge_base_repo.get_by_id", new=AsyncMock(return_value=kb)):
            svc = KnowledgeBaseService(mock_db)
            with pytest.raises(AuthorizationError):
                await svc.delete(kb.id, user_id=other)

    @pytest.mark.anyio
    async def test_list_accessible_passes_correct_params(self, mock_db):
        user_id = uuid.uuid4()
        org_id = uuid.uuid4()

        with patch(
            "app.repositories.knowledge_base_repo.get_accessible",
            new=AsyncMock(return_value=[]),
        ) as mock_list:
            svc = KnowledgeBaseService(mock_db)
            await svc.list_accessible(user_id=user_id, organization_id=org_id)

            mock_list.assert_called_once()
            _, kwargs = mock_list.call_args
            assert kwargs.get("user_id") == user_id
            assert kwargs.get("organization_id") == org_id


{%- else %}
"""KB scoping tests — not configured (enable_teams, enable_rag, or use_jwt is false)."""
{%- endif %}
