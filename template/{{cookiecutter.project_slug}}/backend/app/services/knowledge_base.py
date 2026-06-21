{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
import logging
import re
import secrets
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.db.models.knowledge_base import KBScope, KnowledgeBase
from app.repositories import conversation_repo, knowledge_base_repo
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate

logger = logging.getLogger(__name__)


def _derive_collection_name(name: str) -> str:
    """Slugify the KB name and append a short random suffix to avoid collisions."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "kb"
    return f"{slug[:48]}_{secrets.token_hex(3)}"


class KnowledgeBaseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_accessible(
        self,
        user_id: UUID,
        organization_id: UUID | None = None,
    ) -> list[KnowledgeBase]:
        return await knowledge_base_repo.get_accessible(
            self.db, user_id=user_id, organization_id=organization_id
        )

    async def list_accessible_collection_names(
        self,
        user_id: UUID,
        organization_id: UUID | None = None,
    ) -> list[str]:
        """Return the distinct collection names of all KBs visible to this user.

        Drives the ``/rag/collections`` listing so it stays consistent with
        ``/kb`` — every KB (even one with zero documents, whose Milvus
        collection doesn't exist yet) shows up.
        """
        kbs = await knowledge_base_repo.get_accessible(
            self.db, user_id=user_id, organization_id=organization_id
        )
        seen: set[str] = set()
        names: list[str] = []
        for kb in kbs:
            if kb.collection_name not in seen:
                seen.add(kb.collection_name)
                names.append(kb.collection_name)
        return names

    async def create_for_rag_collection(
        self,
        collection_name: str,
        *,
        user_id: UUID,
        organization_id: UUID | None = None,
    ) -> KnowledgeBase:
        """Create a KB backed by an explicit ``collection_name`` (idempotent).

        Used by ``POST /rag/collections/{name}`` so a collection created on the
        /rag page also appears on /kb. The collection name is used verbatim
        (the /rag endpoint already validates it) rather than slug-derived, and
        the KB is org-scoped so it is visible to the workspace. Returns the
        existing KB unchanged if one already maps to this collection.
        """
        existing = await knowledge_base_repo.get_by_collection_name(self.db, collection_name)
        if existing:
            return existing
        scope = KBScope.ORG.value if organization_id else KBScope.PERSONAL.value
        return await knowledge_base_repo.create(
            self.db,
            name=collection_name,
            collection_name=collection_name,
            scope=scope,
            owner_user_id=user_id if scope == KBScope.PERSONAL.value else None,
            organization_id=organization_id,
        )

    async def delete_by_collection_name(self, collection_name: str) -> None:
        """Delete the KB row mapped to a collection, if any.

        Best-effort: keeps the KB table in sync when a collection is dropped via
        ``DELETE /rag/collections/{name}``. A default KB is left intact so the
        org keeps a usable knowledge base.
        """
        kb = await knowledge_base_repo.get_by_collection_name(self.db, collection_name)
        if kb and not kb.is_default:
            await knowledge_base_repo.delete(self.db, kb.id)

    async def resolve_active_collection_names(
        self,
        conversation_id: UUID,
        user_id: UUID | None,
    ) -> list[str]:
        """Return active KB collection names for a conversation.

        Always resolved server-side from `Conversation.active_knowledge_base_ids`,
        intersected with KBs the user can access. Falls back to the org default
        KB when no KBs are explicitly active. Never trust collection names from
        the LLM or client.
        """
        try:
            conv = await conversation_repo.get_conversation_by_id(self.db, conversation_id)
            if not conv:
                return []
            org_id = getattr(conv, "organization_id", None)
            active: list[UUID] = conv.active_knowledge_base_ids or []
            if not active:
                if org_id:
                    default_kb = await knowledge_base_repo.get_default_for_org(self.db, org_id)
                    if default_kb:
                        return [default_kb.collection_name]
                return []
            accessible = await knowledge_base_repo.get_accessible(
                self.db,
                user_id=user_id,
                organization_id=org_id,
            )
            active_set = {str(i) for i in active}
            return [kb.collection_name for kb in accessible if str(kb.id) in active_set]
        except Exception as exc:
            logger.warning("KB collection resolution failed: %s", exc)
            return []

    async def resolve_collection_names_for_ids(
        self,
        *,
        kb_ids: list[UUID],
        user_id: UUID | None,
        organization_id: UUID | None,
    ) -> list[str]:
        """Resolve a client-supplied list of KB IDs to collection names.

        Used when the conversation hasn't been saved yet so we can't read
        ``Conversation.active_knowledge_base_ids`` from DB. Intersects with
        the caller's accessible KBs — clients can never reach a KB they
        don't own (or that isn't shared with their org).
        """
        if not kb_ids:
            return []
        try:
            accessible = await knowledge_base_repo.get_accessible(
                self.db,
                user_id=user_id,
                organization_id=organization_id,
            )
            wanted = {str(i) for i in kb_ids}
            return [kb.collection_name for kb in accessible if str(kb.id) in wanted]
        except Exception as exc:
            logger.warning("KB collection override resolution failed: %s", exc)
            return []

    async def get(
        self,
        kb_id: UUID,
        *,
        user_id: UUID,
        organization_id: UUID | None = None,
    ) -> KnowledgeBase:
        kb = await knowledge_base_repo.get_by_id(self.db, kb_id)
        if not kb:
            raise NotFoundError(message="Knowledge base not found", details={"kb_id": str(kb_id)})
        self._check_read_access(kb, user_id=user_id, organization_id=organization_id)
        return kb

    async def create(
        self,
        data: KnowledgeBaseCreate,
        *,
        user_id: UUID,
        organization_id: UUID | None = None,
        is_app_admin: bool = False,
    ) -> KnowledgeBase:
        self._check_create_permission(
            scope=data.scope,
            user_id=user_id,
            organization_id=organization_id,
            is_app_admin=is_app_admin,
        )
        owner_user_id = user_id if data.scope == KBScope.PERSONAL.value else None
        org_id = (
            organization_id if data.scope in (KBScope.ORG.value, KBScope.PERSONAL.value) else None
        )
        return await knowledge_base_repo.create(
            self.db,
            name=data.name,
            collection_name=data.collection_name or _derive_collection_name(data.name),
            scope=data.scope,
            description=data.description,
            owner_user_id=owner_user_id,
            organization_id=org_id,
        )

    async def create_default_for_org(
        self,
        organization_id: UUID,
        collection_name: str,
    ) -> KnowledgeBase:
        existing = await knowledge_base_repo.get_default_for_org(self.db, organization_id)
        if existing:
            return existing
        return await knowledge_base_repo.create(
            self.db,
            name="Default",
            collection_name=collection_name,
            scope=KBScope.ORG.value,
            description="Default knowledge base",
            organization_id=organization_id,
            is_default=True,
        )

    async def update(
        self,
        kb_id: UUID,
        data: KnowledgeBaseUpdate,
        *,
        user_id: UUID,
        organization_id: UUID | None = None,
        is_app_admin: bool = False,
    ) -> KnowledgeBase:
        kb = await knowledge_base_repo.get_by_id(self.db, kb_id)
        if not kb:
            raise NotFoundError(message="Knowledge base not found", details={"kb_id": str(kb_id)})
        self._check_write_access(
            kb, user_id=user_id, organization_id=organization_id, is_app_admin=is_app_admin
        )
        return await knowledge_base_repo.update(
            self.db,
            db_kb=kb,
            name=data.name,
            description=data.description,
        )

    async def delete(
        self,
        kb_id: UUID,
        *,
        user_id: UUID,
        organization_id: UUID | None = None,
        is_app_admin: bool = False,
    ) -> None:
        kb = await knowledge_base_repo.get_by_id(self.db, kb_id)
        if not kb:
            raise NotFoundError(message="Knowledge base not found", details={"kb_id": str(kb_id)})
        if kb.is_default:
            from app.core.exceptions import BadRequestError

            raise BadRequestError(message="Cannot delete the default knowledge base")
        self._check_write_access(
            kb, user_id=user_id, organization_id=organization_id, is_app_admin=is_app_admin
        )
        await knowledge_base_repo.delete(self.db, kb_id)

    def _check_read_access(
        self,
        kb: KnowledgeBase,
        *,
        user_id: UUID,
        organization_id: UUID | None,
    ) -> None:
        if kb.scope == KBScope.APP.value:
            return
        if kb.scope == KBScope.PERSONAL.value and str(kb.owner_user_id) == str(user_id):
            return
        if (
            kb.scope == KBScope.ORG.value
            and organization_id
            and str(kb.organization_id) == str(organization_id)
        ):
            return
        raise NotFoundError(message="Knowledge base not found", details={"kb_id": str(kb.id)})

    def _check_write_access(
        self,
        kb: KnowledgeBase,
        *,
        user_id: UUID,
        organization_id: UUID | None,
        is_app_admin: bool,
    ) -> None:
        if kb.scope == KBScope.APP.value and not is_app_admin:
            raise AuthorizationError(
                message="App admin required to modify app-scoped knowledge base"
            )
        if kb.scope == KBScope.PERSONAL.value and str(kb.owner_user_id) != str(user_id):
            raise AuthorizationError(message="Only the owner can modify this knowledge base")
        if kb.scope == KBScope.ORG.value and (
            not organization_id or str(kb.organization_id) != str(organization_id)
        ):
            raise AuthorizationError(message="Not a member of this knowledge base's organization")

    def _check_create_permission(
        self,
        *,
        scope: str,
        user_id: UUID,
        organization_id: UUID | None,
        is_app_admin: bool,
    ) -> None:
        if scope == KBScope.APP.value and not is_app_admin:
            raise AuthorizationError(
                message="App admin required to create app-scoped knowledge base"
            )
        if scope == KBScope.ORG.value and not organization_id:
            raise AuthorizationError(
                message="Organization context required to create org-scoped knowledge base"
            )

{%- else %}
"""Knowledge Base service — not configured."""
{%- endif %}
