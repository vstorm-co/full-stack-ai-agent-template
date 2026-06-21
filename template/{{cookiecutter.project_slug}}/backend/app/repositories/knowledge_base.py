{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
"""Knowledge Base repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge_base import KBScope, KnowledgeBase
from app.db.models.rag_document import RAGDocument


async def get_by_id(db: AsyncSession, kb_id: UUID) -> KnowledgeBase | None:
    return await db.get(KnowledgeBase, kb_id)


async def get_accessible(
    db: AsyncSession,
    *,
    user_id: UUID,
    organization_id: UUID | None = None,
) -> list[KnowledgeBase]:
    """All KBs visible to this user: personal + org (if org given) + app."""
    conditions = [
        (KnowledgeBase.scope == KBScope.PERSONAL.value) & (KnowledgeBase.owner_user_id == user_id),
        KnowledgeBase.scope == KBScope.APP.value,
    ]
    if organization_id is not None:
        conditions.append(
            (KnowledgeBase.scope == KBScope.ORG.value) & (KnowledgeBase.organization_id == organization_id)
        )
    result = await db.execute(
        select(KnowledgeBase).where(or_(*conditions)).order_by(KnowledgeBase.created_at)
    )
    return list(result.scalars().all())


async def get_default_for_org(db: AsyncSession, organization_id: UUID) -> KnowledgeBase | None:
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.organization_id == organization_id,
            KnowledgeBase.scope == KBScope.ORG.value,
            KnowledgeBase.is_default.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def get_documents_count(db: AsyncSession, kb_id: UUID) -> int:
    result = await db.execute(
        select(func.count(RAGDocument.id)).where(RAGDocument.knowledge_base_id == kb_id)
    )
    return result.scalar() or 0


async def create(
    db: AsyncSession,
    *,
    name: str,
    collection_name: str,
    scope: str,
    description: str | None = None,
    owner_user_id: UUID | None = None,
    organization_id: UUID | None = None,
    is_default: bool = False,
) -> KnowledgeBase:
    kb = KnowledgeBase(
        name=name,
        collection_name=collection_name,
        scope=scope,
        description=description,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
        is_default=is_default,
    )
    db.add(kb)
    await db.flush()
    await db.refresh(kb)
    return kb


async def update(
    db: AsyncSession,
    *,
    db_kb: KnowledgeBase,
    name: str | None = None,
    description: str | None = None,
) -> KnowledgeBase:
    if name is not None:
        db_kb.name = name
    if description is not None:
        db_kb.description = description
    await db.flush()
    await db.refresh(db_kb)
    return db_kb


async def delete(db: AsyncSession, kb_id: UUID) -> bool:
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        return False
    await db.delete(kb)
    await db.flush()
    return True


async def get_by_collection_name(
    db: AsyncSession, collection_name: str
) -> KnowledgeBase | None:
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.collection_name == collection_name)
    )
    return result.scalars().first()

{%- else %}
"""Knowledge Base repository — not configured."""
{%- endif %}
