{%- if cookiecutter.enable_rag and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Check RAG permissions before searching, writing, or copying credentials."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.api.routes.v1.rag import search_documents
{%- if cookiecutter.enable_redis %}
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.v1.rag import router
{%- endif %}
from app.core.exceptions import AuthorizationError, NotFoundError
from app.schemas.rag import RAGSearchRequest
from app.schemas.sync_source import SyncSourceClone
from app.services.knowledge_base import KnowledgeBaseService
from app.services.sync_source import SyncSourceService

pytestmark = pytest.mark.anyio


async def test_search_requires_access_to_every_collection() -> None:
    retrieval = SimpleNamespace(retrieve_multi=AsyncMock())
    kb_service = SimpleNamespace(list_accessible_collection_names=AsyncMock(return_value=["shared"]))
    with pytest.raises(NotFoundError):
        await search_documents(
            RAGSearchRequest(query="sample", collection_names=["shared", "restricted"]),
            retrieval, SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4()), kb_service, False,
        )
    retrieval.retrieve_multi.assert_not_awaited()


async def test_org_member_has_read_access_but_cannot_modify_the_kb() -> None:
    service = KnowledgeBaseService(MagicMock())
    org, user, kb_id = uuid4(), uuid4(), uuid4()
    kb = SimpleNamespace(id=kb_id, scope="org", organization_id=org)
    with (
        patch("app.services.knowledge_base.knowledge_base_repo.get_by_id", AsyncMock(return_value=kb)),
        patch("app.services.knowledge_base.member_repo.get", AsyncMock(return_value=SimpleNamespace(role="member"))),
    ):
        assert await service.get(kb_id, user_id=user, organization_id=org) is kb
        with pytest.raises(AuthorizationError):
            await service.get_for_write(kb_id, user_id=user, organization_id=org)


@pytest.mark.parametrize("same_org", [False, True])
async def test_credentials_are_only_cloned_from_manageable_sources(same_org: bool) -> None:
    service = SyncSourceService(MagicMock())
    org = uuid4()
    source = SimpleNamespace(organization_id=org if same_org else uuid4(), collection_name="restricted")
    with (
        patch.object(service, "get_source", AsyncMock(return_value=source)),
        patch("app.services.sync_source._decrypt_config") as decrypt,
    ):
        with pytest.raises(NotFoundError):
            await service.clone_source(
                str(uuid4()), SyncSourceClone(collection_name="shared"),
                organization_id=org, allowed_source_collections={"shared"}, allow_org_integrations=True,
            )
    decrypt.assert_not_called()
{%- if cookiecutter.enable_redis %}


def test_status_stream_requires_authentication() -> None:
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.get("/status/stream")
    assert response.status_code == 401
{%- endif %}
{%- endif %}
