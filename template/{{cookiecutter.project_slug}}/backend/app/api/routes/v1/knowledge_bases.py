{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
"""Knowledge Base routes — CRUD + per-KB document upload + sync sources.

Document upload and sync-source management are wired here (rather than under
``/rag``) so non-admin owners can manage their own KB without needing the
app-admin role required by the bulk ``/rag`` endpoints.
"""

from typing import Any

from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import ActiveOrg, CurrentUser, DBSession, KnowledgeBaseSvc
from app.api.deps import RAGDocumentSvc, SyncSourceSvc, VectorStoreSvc
from app.core.exceptions import NotFoundError
from app.repositories import sync_log as sync_log_repo
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseList,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
)
from app.schemas.rag import RAGIngestResponse, RAGSyncLogItem, RAGSyncLogList, RAGSyncResponse, RAGTrackedDocumentList
from app.schemas.sync_source import (
    ConnectorList,
    SyncSourceClone,
    SyncSourceCreate,
    SyncSourceList,
    SyncSourceRead,
)

router = APIRouter()


@router.get("", response_model=KnowledgeBaseList)
async def list_knowledge_bases(
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """List all Knowledge Bases accessible to the current user in this org context."""
    items = await service.list_accessible(
        user_id=current_user.id,
        organization_id=active_org.id,
    )
    return KnowledgeBaseList(items=items, total=len(items))


@router.post("", response_model=KnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Create a new Knowledge Base.

    - ``personal`` scope: visible only to you
    - ``org`` scope: visible to all members of the active org (admin/owner only)
    - ``app`` scope: visible to all users (app admin only)
    """
    return await service.create(
        data,
        user_id=current_user.id,
        organization_id=active_org.id,
        is_app_admin=current_user.is_app_admin,
    )


@router.get("/{kb_id}", response_model=KnowledgeBaseRead)
async def get_knowledge_base(
    kb_id: UUID,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Get a Knowledge Base by ID."""
    return await service.get(
        kb_id,
        user_id=current_user.id,
        organization_id=active_org.id,
    )


@router.patch("/{kb_id}", response_model=KnowledgeBaseRead)
async def update_knowledge_base(
    kb_id: UUID,
    data: KnowledgeBaseUpdate,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Update name or description of a Knowledge Base."""
    return await service.update(
        kb_id,
        data,
        user_id=current_user.id,
        organization_id=active_org.id,
        is_app_admin=current_user.is_app_admin,
    )


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_knowledge_base(
    kb_id: UUID,
    service: KnowledgeBaseSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> None:
    """Delete a Knowledge Base. Default KBs cannot be deleted."""
    await service.delete(
        kb_id,
        user_id=current_user.id,
        organization_id=active_org.id,
        is_app_admin=current_user.is_app_admin,
    )


@router.get("/{kb_id}/documents", response_model=RAGTrackedDocumentList)
async def list_kb_documents(
    kb_id: UUID,
    service: KnowledgeBaseSvc,
    rag_doc_service: RAGDocumentSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List documents ingested into a Knowledge Base."""
    await service.get(kb_id, user_id=current_user.id, organization_id=active_org.id)
    return await rag_doc_service.list_for_kb(kb_id=kb_id, skip=skip, limit=limit)


@router.post(
    "/{kb_id}/documents",
    response_model=RAGIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_kb_document(
    kb_id: UUID,
    service: KnowledgeBaseSvc,
    rag_doc_service: RAGDocumentSvc,
    vector_store: VectorStoreSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    file: UploadFile = File(...),
    replace: bool = Query(False),
) -> Any:
    """Upload a file into the KB's underlying vector collection.

    Auth is per-KB (owner / org member / admin) — unlike the bulk
    ``/rag/{collection}/documents`` endpoint which is admin-only — so a
    workspace user can manage their own KB without elevation.
    """
    kb = await service.get(
        kb_id, user_id=current_user.id, organization_id=active_org.id
    )
    data = await file.read()
    return await rag_doc_service.dispatch_upload(
        collection_name=kb.collection_name,
        file_data=data,
        filename=file.filename or "unknown",
        replace=replace,
        vector_store=vector_store,
        organization_id=active_org.id,
        knowledge_base_id=kb.id,
    )


@router.get("/{kb_id}/documents/{doc_id}/download", response_model=None)
async def download_kb_document(
    kb_id: UUID,
    doc_id: UUID,
    service: KnowledgeBaseSvc,
    rag_doc_svc: RAGDocumentSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> FileResponse:
    """Download (or open inline) the original file for a KB document."""
    kb = await service.get(
        kb_id, user_id=current_user.id, organization_id=active_org.id
    )
    doc = await rag_doc_svc.get_document(str(doc_id))
    if doc.collection_name != kb.collection_name:
        raise NotFoundError(
            message="Document not found in this knowledge base",
            details={"kb_id": str(kb_id), "doc_id": str(doc_id)},
        )
    file_path, filename, mime_type = await rag_doc_svc.get_download_info(str(doc_id))
    return FileResponse(path=file_path, filename=filename, media_type=mime_type)


@router.delete(
    "/{kb_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_kb_document(
    kb_id: UUID,
    doc_id: UUID,
    service: KnowledgeBaseSvc,
    rag_doc_service: RAGDocumentSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> None:
    """Remove a document from the KB (cascades to vectors + file storage).

    Verifies the doc actually belongs to this KB's collection — without that
    check a KB owner could pass any doc_id and remove docs from KBs they
    don't own.
    """
    kb = await service.get(
        kb_id, user_id=current_user.id, organization_id=active_org.id
    )
    doc = await rag_doc_service.get_document(str(doc_id))
    if doc.collection_name != kb.collection_name:
        raise NotFoundError(
            message="Document not found in this knowledge base",
            details={"kb_id": str(kb_id), "doc_id": str(doc_id)},
        )
    await rag_doc_service.delete_document(str(doc_id))


# These mirror /rag/sync/sources but with per-KB auth (a personal KB owner
# can wire up a Google Drive folder without admin role) and automatically
# pin the source to ``kb.collection_name`` so the user can't accidentally
# point a sync at a different collection.


@router.get("/{kb_id}/sync-sources", response_model=SyncSourceList)
async def list_kb_sync_sources(
    kb_id: UUID,
    service: KnowledgeBaseSvc,
    sync_source_svc: SyncSourceSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """List sync sources feeding this KB's collection (org-scoped)."""
    kb = await service.get(kb_id, user_id=current_user.id, organization_id=active_org.id)
    return await sync_source_svc.list_sources(
        organization_id=active_org.id,
        collection_name=kb.collection_name,
    )


@router.get("/{kb_id}/sync-sources/org-integrations", response_model=SyncSourceList)
async def list_org_integrations_for_kb(
    kb_id: UUID,
    service: KnowledgeBaseSvc,
    sync_source_svc: SyncSourceSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """List org integrations that are NOT yet assigned to this KB.

    Used by the wizard's 'pick existing' step so the user can clone an
    existing integration's credentials into this knowledge base.
    """
    kb = await service.get(kb_id, user_id=current_user.id, organization_id=active_org.id)
    all_org = await sync_source_svc.list_sources(organization_id=active_org.id)
    others = [s for s in all_org.items if s.collection_name != kb.collection_name]
    return SyncSourceList(items=others, total=len(others))


@router.get("/{kb_id}/sync-sources/connectors", response_model=ConnectorList)
async def list_kb_connectors(
    kb_id: UUID,
    service: KnowledgeBaseSvc,
    sync_source_svc: SyncSourceSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """List available connector types (Google Drive, S3, …) for this KB."""
    await service.get(kb_id, user_id=current_user.id, organization_id=active_org.id)
    return sync_source_svc.list_connectors()


@router.post(
    "/{kb_id}/sync-sources",
    response_model=SyncSourceRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_kb_sync_source(
    kb_id: UUID,
    data: SyncSourceCreate,
    service: KnowledgeBaseSvc,
    sync_source_svc: SyncSourceSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Wire up a sync source (Google Drive, S3, …) feeding this KB.

    The ``collection_name`` field on the request body is overridden with the
    KB's own collection — clients should not need to know that detail.
    """
    kb = await service.get(kb_id, user_id=current_user.id, organization_id=active_org.id)
    payload = data.model_copy(update={"collection_name": kb.collection_name})
    return await sync_source_svc.create_source(payload, organization_id=active_org.id)


@router.post(
    "/{kb_id}/sync-sources/{source_id}/clone",
    response_model=SyncSourceRead,
    status_code=status.HTTP_201_CREATED,
)
async def clone_kb_sync_source(
    kb_id: UUID,
    source_id: UUID,
    data: SyncSourceClone,
    service: KnowledgeBaseSvc,
    sync_source_svc: SyncSourceSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Clone an existing org integration into this KB.

    Decrypts credentials from the source and re-encrypts them for the clone,
    pinning it to this KB's collection_name. The clone is independent.
    """
    kb = await service.get(kb_id, user_id=current_user.id, organization_id=active_org.id)
    clone_data = data.model_copy(update={"collection_name": kb.collection_name})
    return await sync_source_svc.clone_source(
        str(source_id), clone_data, organization_id=active_org.id
    )


@router.post(
    "/{kb_id}/sync-sources/{source_id}/trigger",
    response_model=RAGSyncResponse,
)
async def trigger_kb_sync_source(
    kb_id: UUID,
    source_id: UUID,
    service: KnowledgeBaseSvc,
    sync_source_svc: SyncSourceSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> Any:
    """Manually trigger a sync run for one of this KB's sources."""
    kb = await service.get(
        kb_id, user_id=current_user.id, organization_id=active_org.id
    )
    source = await sync_source_svc.get_source(str(source_id))
    if source.collection_name != kb.collection_name:
        raise NotFoundError(
            message="Sync source not found in this knowledge base",
            details={"kb_id": str(kb_id), "source_id": str(source_id)},
        )
    sync_log = await sync_source_svc.trigger_sync(str(source_id))
    return RAGSyncResponse(
        id=str(sync_log.id),
        status="running",
        message=f"Sync triggered for source '{source_id}'",
    )


@router.get("/{kb_id}/sync-sources/{source_id}/logs", response_model=RAGSyncLogList)
async def list_kb_sync_source_logs(
    kb_id: UUID,
    source_id: UUID,
    service: KnowledgeBaseSvc,
    db: DBSession,
    current_user: CurrentUser,
    active_org: ActiveOrg,
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    """List sync run history for a specific KB sync source."""
    kb = await service.get(kb_id, user_id=current_user.id, organization_id=active_org.id)
    logs = await sync_log_repo.get_all(db, sync_source_id=source_id, limit=limit)
    # Verify source belongs to this KB's collection (security: don't leak other KBs' logs).
    items = [
        RAGSyncLogItem(
            id=str(log.id),
            source=log.source,
            collection_name=log.collection_name,
            status=log.status,
            mode=log.mode,
            total_files=log.total_files,
            ingested=log.ingested,
            updated=log.updated,
            skipped=log.skipped,
            failed=log.failed,
            error_message=log.error_message,
            started_at=log.started_at,
            completed_at=log.completed_at,
        )
        for log in logs
        if log.collection_name == kb.collection_name
    ]
    return RAGSyncLogList(items=items, total=len(items))


@router.delete(
    "/{kb_id}/sync-sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_kb_sync_source(
    kb_id: UUID,
    source_id: UUID,
    service: KnowledgeBaseSvc,
    sync_source_svc: SyncSourceSvc,
    current_user: CurrentUser,
    active_org: ActiveOrg,
) -> None:
    """Remove a sync source from this KB."""
    kb = await service.get(
        kb_id, user_id=current_user.id, organization_id=active_org.id
    )
    source = await sync_source_svc.get_source(str(source_id))
    if source.collection_name != kb.collection_name:
        raise NotFoundError(
            message="Sync source not found in this knowledge base",
            details={"kb_id": str(kb_id), "source_id": str(source_id)},
        )
    await sync_source_svc.delete_source(str(source_id))


{%- else %}
"""Knowledge Base routes — not configured."""
{%- endif %}
