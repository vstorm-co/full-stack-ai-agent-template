{%- if cookiecutter.enable_rag %}
"""RAG document repository (PostgreSQL async).

Contains database operations for RAGDocument entities.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import delete as sql_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.rag_document import RAGDocument


async def get_by_id(db: AsyncSession, doc_id: UUID) -> RAGDocument | None:
    """Get a RAG document by ID."""
    return await db.get(RAGDocument, doc_id)


async def get_all(
    db: AsyncSession,
    collection_name: str | None = None,
{%- if cookiecutter.enable_teams %}
    organization_id: UUID | None = None,
{%- endif %}
) -> list[RAGDocument]:
    """Get all RAG documents, optionally filtered by collection."""
    query = select(RAGDocument)
    if collection_name:
        query = query.where(RAGDocument.collection_name == collection_name)
{%- if cookiecutter.enable_teams %}
    if organization_id is not None:
        query = query.where(RAGDocument.organization_id == organization_id)
{%- endif %}
    query = query.order_by(RAGDocument.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


{%- if cookiecutter.enable_teams %}


async def get_for_kb(
    db: AsyncSession,
    kb_id: UUID,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[RAGDocument], int]:
    """Page through documents linked to a Knowledge Base. Returns (rows, total)."""
    base = select(RAGDocument).where(RAGDocument.knowledge_base_id == kb_id)
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            base.order_by(RAGDocument.created_at.desc()).offset(skip).limit(limit)
        )
    ).scalars().all()
    return list(rows), int(total)
{%- endif %}


async def create(
    db: AsyncSession,
    *,
    collection_name: str,
    filename: str,
    filesize: int,
    filetype: str,
    storage_path: str,
    status: str = "processing",
{%- if cookiecutter.enable_teams %}
    organization_id: UUID | None = None,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    knowledge_base_id: UUID | None = None,
{%- endif %}
) -> RAGDocument:
    """Create a new RAG document record."""
    doc = RAGDocument(
        collection_name=collection_name,
        filename=filename,
        filesize=filesize,
        filetype=filetype,
        storage_path=storage_path,
        status=status,
{%- if cookiecutter.enable_teams %}
        organization_id=organization_id,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
        knowledge_base_id=knowledge_base_id,
{%- endif %}
    )
    db.add(doc)
    await db.flush()
    return doc


async def update_status(
    db: AsyncSession,
    doc_id: UUID,
    *,
    status: str,
    error_message: str | None = None,
    vector_document_id: str | None = None,
    chunk_count: int | None = None,
    completed_at: Any = None,
) -> RAGDocument | None:
    """Update the processing status of a RAG document."""
    doc = await db.get(RAGDocument, doc_id)
    if not doc:
        return None
    doc.status = status
    if error_message is not None:
        doc.error_message = error_message
    if vector_document_id is not None:
        doc.vector_document_id = vector_document_id
    if chunk_count is not None:
        doc.chunk_count = chunk_count
    if completed_at is not None:
        doc.completed_at = completed_at
    await db.flush()
    return doc


async def delete(db: AsyncSession, doc_id: UUID) -> bool:
    """Delete a RAG document by ID."""
    doc = await db.get(RAGDocument, doc_id)
    if not doc:
        return False
    await db.delete(doc)
    await db.flush()
    return True


async def sum_filesize_for_org(db: AsyncSession, org_id: UUID) -> int:
    """Return total bytes of RAG documents stored for an organization."""
    result = await db.execute(
        select(func.coalesce(func.sum(RAGDocument.filesize), 0)).where(
            RAGDocument.organization_id == org_id
        )
    )
    return int(result.scalar_one())


async def delete_by_collection(db: AsyncSession, collection_name: str) -> int:
    """Delete all RAG document records for a collection. Returns affected row count."""
    result = await db.execute(
        sql_delete(RAGDocument).where(RAGDocument.collection_name == collection_name)
    )
    await db.flush()
    return result.rowcount  # ty: ignore[unresolved-attribute]


{%- else %}
"""RAG document repository - not configured."""
{%- endif %}
