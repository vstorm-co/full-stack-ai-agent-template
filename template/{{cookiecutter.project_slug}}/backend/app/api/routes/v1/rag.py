{%- if cookiecutter.enable_rag %}
"""RAG API routes — collection management, search, document upload, sync, status stream.

Routes are HTTP plumbing only. Business logic, file I/O, task dispatch, and Redis
pub/sub all live in their respective services. Domain exceptions raised by services are
mapped to HTTP responses by the global exception handlers in
``app.api.exception_handlers``; routes do not catch and re-wrap them.
"""

import contextlib
{%- if cookiecutter.enable_redis %}
from collections.abc import AsyncIterable
{%- endif %}
from typing import Any

from fastapi import APIRouter, File, Query, UploadFile, status
from fastapi.responses import FileResponse
{%- if cookiecutter.enable_redis %}
from fastapi.sse import EventSourceResponse, ServerSentEvent
{%- endif %}

from app.api.deps import IngestionSvc, RAGDocumentSvc, RAGSyncSvc, RetrievalSvc, SyncSourceSvc, VectorStoreSvc
{%- if cookiecutter.use_jwt %}
from app.api.deps import CurrentAdmin, CurrentUser
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
from app.api.deps import ActiveOrg, KnowledgeBaseSvc
{%- endif %}
{%- if cookiecutter.enable_redis %}
from app.api.deps import RAGStatusSvc
{%- endif %}
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.services.rag.config import get_supported_formats
from app.schemas.rag import (
    RAGCollectionInfo,
    RAGCollectionList,
    RAGDocumentList,
    RAGIngestResponse,
    RAGMessageResponse,
    RAGRetryResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGSearchResult,
    RAGSyncLogList,
    RAGSyncRequest,
    RAGSyncResponse,
    RAGTrackedDocumentList,
    SupportedFormatsResponse,
)
from app.schemas.sync_source import (
    ConnectorList,
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    SyncSourceClone,
{%- endif %}
    SyncSourceCreate,
    SyncSourceList,
    SyncSourceRead,
    SyncSourceUpdate,
)

router = APIRouter()


@router.get("/supported-formats", response_model=SupportedFormatsResponse)
async def get_supported_formats_endpoint() -> Any:
    """Return file formats supported by the current PDF parser configuration."""
    parser_name = getattr(settings, "PDF_PARSER", "pymupdf")
    return {"parser": parser_name, "formats": sorted(get_supported_formats(parser_name))}


@router.get("/collections", response_model=RAGCollectionList)
async def list_collections(
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    kb_svc: KnowledgeBaseSvc,
    admin: CurrentAdmin,
    active_org: ActiveOrg,
{%- else %}
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
{%- endif %}
) -> Any:
    """List collections derived from Knowledge Base records.

    Single source of truth = KnowledgeBase rows, so /rag and /kb stay
    consistent: a freshly-created KB (whose Milvus collection only materializes
    after the first document is ingested) still appears here, and dropping a
    collection here removes the KB too.
    """
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    names = await kb_svc.list_accessible_collection_names(
        user_id=admin.id, organization_id=active_org.id
    )
    return RAGCollectionList(items=names)
{%- else %}
    names = await vector_store.list_collections()
    return RAGCollectionList(items=names)
{%- endif %}


@router.post(
    "/collections/{name}",
    status_code=status.HTTP_201_CREATED,
    response_model=RAGMessageResponse,
)
async def create_collection(
    name: str,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    kb_svc: KnowledgeBaseSvc,
    admin: CurrentAdmin,
    active_org: ActiveOrg,
{%- endif %}
) -> Any:
    """Create and initialize a new collection.

    Also creates a matching KnowledgeBase row (idempotent) so the collection
    shows up on /kb as well as /rag.
    """
    await vector_store.create_collection(name)
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    await kb_svc.create_for_rag_collection(
        name, user_id=admin.id, organization_id=active_org.id
    )
{%- endif %}
    return RAGMessageResponse(message=f"Collection '{name}' created successfully.")


@router.delete(
    "/collections/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def drop_collection(
    name: str,
    vector_store: VectorStoreSvc,
    rag_doc_svc: RAGDocumentSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    kb_svc: KnowledgeBaseSvc,
{%- endif %}
) -> None:
    """Drop a collection — vectors, SQL document records, and the KB row.

    The Milvus collection may not exist yet for a zero-document KB, so the
    vector-store drop is best-effort; the KB + SQL cleanup still runs.
    """
    with contextlib.suppress(Exception):
        await vector_store.delete_collection(name)
    await rag_doc_svc.delete_by_collection(name)
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    await kb_svc.delete_by_collection_name(name)
{%- endif %}


@router.get("/collections/{name}/info", response_model=RAGCollectionInfo)
async def get_collection_info(
    name: str,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Retrieve stats for a specific collection."""
    return await vector_store.get_collection_info(name)


@router.get("/collections/{name}/documents", response_model=RAGDocumentList)
async def list_documents(
    name: str,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """List all documents in a specific collection."""
    return await vector_store.get_document_list(name)


@router.post("/search", response_model=RAGSearchResponse)
async def search_documents(
    request: RAGSearchRequest,
    retrieval_service: RetrievalSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentUser,
{%- endif %}
    use_reranker: bool = Query(False, description="Whether to use reranking (if configured)"),
) -> Any:
    """Search for relevant document chunks. Supports multi-collection search."""
    if request.collection_names and len(request.collection_names) > 1:
        results = await retrieval_service.retrieve_multi(
            query=request.query,
            collection_names=request.collection_names,
            limit=request.limit,
            min_score=request.min_score,
            use_reranker=use_reranker,
        )
    else:
        collection = (
            request.collection_names[0] if request.collection_names else request.collection_name
        )
        results = await retrieval_service.retrieve(
            query=request.query,
            collection_name=collection,
            limit=request.limit,
            min_score=request.min_score,
            filter=request.filter or "",
            use_reranker=use_reranker,
        )
    api_results = [RAGSearchResult(**hit.model_dump()) for hit in results]
    return RAGSearchResponse(results=api_results)


@router.delete(
    "/collections/{name}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_document(
    name: str,
    document_id: str,
    ingestion_service: IngestionSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> None:
    """Delete a specific document by its ID from a collection."""
    success = await ingestion_service.remove_document(name, document_id)
    if not success:
        raise NotFoundError(
            message="Document not found",
            details={"collection": name, "document_id": document_id},
        )


@router.post(
    "/collections/{name}/ingest",
    response_model=RAGIngestResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_file(
    name: str,
    rag_doc_svc: RAGDocumentSvc,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    active_org: ActiveOrg,
{%- endif %}
    file: UploadFile = File(...),
    replace: bool = Query(False),
) -> Any:
    """Upload and queue a file for ingestion into a collection."""
    data = await file.read()
    return await rag_doc_svc.dispatch_upload(
        collection_name=name,
        file_data=data,
        filename=file.filename or "unknown",
        replace=replace,
        vector_store=vector_store,
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
        organization_id=active_org.id,
{%- endif %}
    )


@router.get("/documents", response_model=RAGTrackedDocumentList)
async def list_rag_documents(
    rag_doc_svc: RAGDocumentSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
    collection_name: str | None = Query(None),
) -> Any:
    """List tracked RAG documents."""
    return await rag_doc_svc.list_documents(collection_name)


@router.get("/documents/{doc_id}/download", response_model=None)
async def download_rag_document(
    doc_id: str,
    rag_doc_svc: RAGDocumentSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    file_path, filename, mime_type = await rag_doc_svc.get_download_info(doc_id)
    return FileResponse(path=file_path, filename=filename, media_type=mime_type)


@router.delete(
    "/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_rag_document(
    doc_id: str,
    rag_doc_svc: RAGDocumentSvc,
    ingestion_service: IngestionSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> None:
    """Delete a document from SQL, vector store, and file storage."""
    await rag_doc_svc.delete_document(doc_id, ingestion_service)


@router.post("/documents/{doc_id}/retry", response_model=RAGRetryResponse)
async def retry_ingestion(
    doc_id: str,
    rag_doc_svc: RAGDocumentSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Retry a failed document ingestion."""
    doc = await rag_doc_svc.retry_ingestion(doc_id)
    return RAGRetryResponse(id=str(doc.id), status="processing", message="Retry queued")


@router.get("/sync/logs", response_model=RAGSyncLogList)
async def list_sync_logs(
    rag_sync_svc: RAGSyncSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
    collection_name: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    """List sync operation logs."""
    return await rag_sync_svc.list_sync_logs(collection_name=collection_name, limit=limit)


@router.post("/sync/local", response_model=RAGSyncResponse)
async def trigger_local_sync(
    request: RAGSyncRequest,
    rag_sync_svc: RAGSyncSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Trigger a local directory sync via background task."""
    sync_log = await rag_sync_svc.start_local_sync(
        collection_name=request.collection_name,
        mode=request.mode,
        path=request.path,
    )
    return RAGSyncResponse(
        id=str(sync_log.id),
        status="running",
        message=f"Sync started for '{request.collection_name}' (mode={request.mode})",
    )


@router.delete("/sync/{sync_id}", response_model=RAGMessageResponse)
async def cancel_sync(
    sync_id: str,
    rag_sync_svc: RAGSyncSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Cancel a running sync operation."""
    await rag_sync_svc.cancel_sync(sync_id)
    return RAGMessageResponse(message="Sync cancelled")


@router.get("/sync/sources", response_model=SyncSourceList)
async def list_sync_sources(
    sync_source_svc: SyncSourceSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    active_org: ActiveOrg,
{%- endif %}
    collection_name: str | None = Query(None, description="Filter by KB collection name"),
) -> Any:
    """List sync sources for the active organization.

    Pass ``collection_name`` to see only sources assigned to a specific KB.
    Omit it to list all org-level integrations (assigned and unassigned).
    """
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    return await sync_source_svc.list_sources(
        organization_id=active_org.id,
        collection_name=collection_name,
    )
{%- else %}
    return await sync_source_svc.list_sources()
{%- endif %}


@router.post(
    "/sync/sources",
    response_model=SyncSourceRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_sync_source(
    data: SyncSourceCreate,
    sync_source_svc: SyncSourceSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    active_org: ActiveOrg,
{%- endif %}
) -> Any:
    """Create a new sync source configuration.

    Omit ``collection_name`` to create an org-level integration template
    that can later be cloned into one or more knowledge bases.
    """
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    return await sync_source_svc.create_source(data, organization_id=active_org.id)
{%- else %}
    return await sync_source_svc.create_source(data)
{%- endif %}


{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}


@router.post(
    "/sync/sources/{source_id}/clone",
    response_model=SyncSourceRead,
    status_code=status.HTTP_201_CREATED,
)
async def clone_sync_source(
    source_id: str,
    data: SyncSourceClone,
    sync_source_svc: SyncSourceSvc,
    _: CurrentAdmin,
    active_org: ActiveOrg,
) -> Any:
    """Clone an existing integration into a different knowledge base.

    Credentials are decrypted from the source and re-encrypted for the clone.
    The clone is independent — its own schedule and sync history.
    """
    return await sync_source_svc.clone_source(source_id, data, organization_id=active_org.id)
{%- endif %}


@router.patch("/sync/sources/{source_id}", response_model=SyncSourceRead)
async def update_sync_source(
    source_id: str,
    data: SyncSourceUpdate,
    sync_source_svc: SyncSourceSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Update an existing sync source configuration."""
    return await sync_source_svc.update_source(source_id, data)


@router.delete(
    "/sync/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_sync_source(
    source_id: str,
    sync_source_svc: SyncSourceSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> None:
    """Delete a sync source configuration."""
    await sync_source_svc.delete_source(source_id)


@router.post("/sync/sources/{source_id}/trigger", response_model=RAGSyncResponse)
async def trigger_sync_source(
    source_id: str,
    sync_source_svc: SyncSourceSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Trigger a manual sync for a configured source."""
    sync_log = await sync_source_svc.trigger_sync(source_id)
    return RAGSyncResponse(
        id=str(sync_log.id),
        status="running",
        message=f"Sync triggered for source '{source_id}'",
    )


@router.get("/sync/connectors", response_model=ConnectorList)
async def list_connectors(
    sync_source_svc: SyncSourceSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """List available sync connector types with their config schemas."""
    return sync_source_svc.list_connectors()

{%- if cookiecutter.enable_redis %}


@router.get("/status/stream", response_class=EventSourceResponse)
async def rag_status_stream(
    rag_status_svc: RAGStatusSvc,
) -> AsyncIterable[ServerSentEvent]:
    """SSE endpoint for real-time RAG ingestion status updates.

    Subscribes to the ``rag_status`` Redis pub/sub channel; the browser auto-reconnects
    via the EventSource API.

    The endpoint is itself an async generator: FastAPI's native SSE producer
    streams what it yields. Returning the generator object instead (with
    ``response_class``) makes the producer mis-iterate it → HTTP 500.
    """
    async for event in rag_status_svc.stream_events():
        yield event
{%- endif %}
{%- else %}
"""RAG routes — not enabled."""
{%- endif %}
