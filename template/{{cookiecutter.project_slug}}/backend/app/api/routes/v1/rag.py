{%- if cookiecutter.enable_rag %}
"""RAG API routes for collection management, search, document upload, and deletion."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any
{%- if (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) and cookiecutter.enable_redis %}
import asyncio
from collections.abc import AsyncIterable

import redis.asyncio as aioredis

from fastapi.sse import EventSourceResponse, ServerSentEvent
{%- endif %}

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, UploadFile, File, status
from fastapi.responses import JSONResponse

from app.api.deps import IngestionSvc, RetrievalSvc, VectorStoreSvc
{%- if cookiecutter.use_jwt %}
from app.api.deps import CurrentAdmin, CurrentUser
{%- endif %}
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
from app.api.deps import RAGDocumentSvc, RAGSyncSvc, SyncSourceSvc
from app.core.config import settings as app_settings
from app.core.exceptions import NotFoundError
from app.rag.config import get_supported_formats
from app.schemas.sync_source import (
    ConnectorList,
    SyncSourceCreate,
    SyncSourceList,
    SyncSourceRead,
    SyncSourceUpdate,
)
from app.services.file_storage import get_file_storage
{%- if not (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) %}
from app.tasks.rag import ingest_document_in_background, sync_local_in_background, sync_source_in_background
{%- endif %}
{%- if cookiecutter.use_celery or cookiecutter.use_taskiq %}
from app.worker.tasks.rag_tasks import ingest_document_task, sync_collection_task, sync_single_source_task
{%- endif %}
{%- if cookiecutter.use_arq %}
from app.worker.arq_app import get_arq_pool
{%- endif %}
from fastapi.responses import FileResponse
{%- endif %}
{%- if cookiecutter.use_mongodb %}
from app.core.config import settings as app_settings
from app.rag.config import get_supported_formats
{%- endif %}
from app.schemas.rag import (
    RAGCollectionInfo,
    RAGCollectionList,
    RAGDocumentList,
    RAGMessageResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGSearchResult,
)
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
from app.schemas.rag import RAGIngestResponse, RAGRetryResponse, RAGTrackedDocumentList
from app.schemas.rag import RAGSyncLogList, RAGSyncRequest, RAGSyncResponse
{%- endif %}

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/supported-formats")
async def get_supported_formats_endpoint() -> Any:
    """Return file formats supported by the current PDF parser configuration."""
{%- if cookiecutter.use_all_pdf_parsers %}
    parser_name = getattr(app_settings, "PDF_PARSER", "pymupdf")
{%- elif cookiecutter.use_llamaparse %}
    parser_name = "llamaparse"
{%- elif cookiecutter.use_liteparse %}
    parser_name = "liteparse"
{%- else %}
    parser_name = "pymupdf"
{%- endif %}
    return {"parser": parser_name, "formats": sorted(get_supported_formats(parser_name))}


@router.get("/collections", response_model=RAGCollectionList)
async def list_collections(
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """List all available collections in the vector store."""
    names = await vector_store.list_collections()
    return RAGCollectionList(items=names)


@router.post("/collections/{name}", status_code=status.HTTP_201_CREATED, response_model=RAGMessageResponse)
async def create_collection(
    name: str,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Create and initialize a new collection."""
    try:
        await vector_store.create_collection(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RAGMessageResponse(message=f"Collection '{name}' created successfully.")


@router.delete("/collections/{name}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def drop_collection(
    name: str,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
    rag_doc_svc: RAGDocumentSvc,
{%- endif %}
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> None:
    """Drop an entire collection — vectors and all SQL document records."""
    await vector_store.delete_collection(name)
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
    await rag_doc_svc.delete_by_collection(name)
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
    current_user: CurrentUser,
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
        collection = (request.collection_names[0] if request.collection_names else request.collection_name)
        results = await retrieval_service.retrieve(
            query=request.query,
            collection_name=collection,
            limit=request.limit,
            min_score=request.min_score,
            filter=request.filter or "",
            use_reranker=use_reranker,
        )
    api_results = [
        RAGSearchResult(**hit.model_dump())
        for hit in results
    ]
    return RAGSearchResponse(results=api_results)


@router.delete("/collections/{name}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}

@router.post("/collections/{name}/ingest", response_model=RAGIngestResponse, response_model_exclude_none=True)
async def ingest_file(
    name: str,
    background_tasks: BackgroundTasks,
    rag_doc_svc: RAGDocumentSvc,
    ingestion_service: IngestionSvc,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
    file: UploadFile = File(...),
    replace: bool = Query(False),
) -> Any:
    """Upload and ingest a file into a collection. Tracks status in DB."""

{%- if cookiecutter.use_all_pdf_parsers %}
    ALLOWED = get_supported_formats(getattr(app_settings, "PDF_PARSER", "pymupdf"))
{%- elif cookiecutter.use_llamaparse %}
    ALLOWED = get_supported_formats("llamaparse")
{%- elif cookiecutter.use_liteparse %}
    ALLOWED = get_supported_formats("liteparse")
{%- else %}
    ALLOWED = get_supported_formats("pymupdf")
{%- endif %}
    max_size = app_settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(sorted(ALLOWED))}",
        )

    data = await file.read()
    if len(data) > max_size:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum {app_settings.MAX_UPLOAD_SIZE_MB}MB.")

    storage = get_file_storage()
    storage_path = await storage.save(f"rag/{name}", filename, data)

{%- if cookiecutter.use_postgresql %}
    rag_doc = await rag_doc_svc.create_document(
        collection_name=name, filename=filename, filesize=len(data),
        filetype=ext.lstrip("."), storage_path=storage_path,
    )
{%- else %}
    rag_doc = rag_doc_svc.create_document(
        collection_name=name, filename=filename, filesize=len(data),
        filetype=ext.lstrip("."), storage_path=storage_path,
    )
{%- endif %}
    doc_id = rag_doc.id

    await vector_store.create_collection(name)
{%- if cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq %}

    # Save to shared media volume (accessible by both app and worker containers)
    tmp_dir = os.path.join(str(app_settings.MEDIA_DIR), "_rag_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, f"{str(doc_id)}{ext}")
    with open(tmp_path, "wb") as f:
        f.write(data)

    # Dispatch async task
{%- if cookiecutter.use_celery %}
    ingest_document_task.delay(
        rag_document_id=str(doc_id), collection_name=name,
        filepath=tmp_path, source_path=filename, replace=replace,
    )
{%- elif cookiecutter.use_taskiq %}
    await ingest_document_task.kiq(
        rag_document_id=str(doc_id), collection_name=name,
        filepath=tmp_path, source_path=filename, replace=replace,
    )
{%- elif cookiecutter.use_arq %}
    pool = await get_arq_pool()
    await pool.enqueue_job("ingest_document_task",
        str(doc_id), name, tmp_path, filename, replace,
    )
{%- endif %}

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "id": str(doc_id),
            "status": "processing",
            "filename": filename,
            "collection": name,
            "message": "File accepted. Processing in background.",
        },
    )
{%- else %}

    tmp_dir = os.path.join(tempfile.gettempdir(), "rag_ingest")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, f"{str(doc_id)}{ext}")
    with open(tmp_path, "wb") as f:
        f.write(data)

    background_tasks.add_task(ingest_document_in_background, str(doc_id), name, tmp_path, filename, replace)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "id": str(doc_id),
            "status": "processing",
            "filename": filename,
            "collection": name,
            "message": "File accepted. Processing in background.",
        },
    )
{%- endif %}


@router.get("/documents", response_model=RAGTrackedDocumentList)
{%- if cookiecutter.use_postgresql %}
async def list_rag_documents(
{%- else %}
def list_rag_documents(
{%- endif %}
    rag_doc_svc: RAGDocumentSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
    collection_name: str | None = Query(None),
) -> Any:
    """List tracked RAG documents."""

{%- if cookiecutter.use_postgresql %}
    return await rag_doc_svc.list_documents(collection_name)
{%- else %}
    return rag_doc_svc.list_documents(collection_name)
{%- endif %}


@router.get("/documents/{doc_id}/download")
{%- if cookiecutter.use_postgresql %}
async def download_rag_document(
{%- else %}
def download_rag_document(
{%- endif %}
    doc_id: str,
    rag_doc_svc: RAGDocumentSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Download the original file."""
    try:
{%- if cookiecutter.use_postgresql %}
        file_path, filename, mime_type = await rag_doc_svc.get_download_info(doc_id)
{%- else %}
        file_path, filename, mime_type = rag_doc_svc.get_download_info(doc_id)
{%- endif %}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    return FileResponse(path=file_path, filename=filename, media_type=mime_type)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
{%- if cookiecutter.use_postgresql %}
async def delete_rag_document(
{%- else %}
def delete_rag_document(
{%- endif %}
    doc_id: str,
    rag_doc_svc: RAGDocumentSvc,
    ingestion_service: IngestionSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> None:
    """Delete a document from SQL, vector store, and file storage."""

    try:
{%- if cookiecutter.use_postgresql %}
        await rag_doc_svc.delete_document(doc_id, ingestion_service)
{%- else %}
        rag_doc_svc.delete_document(doc_id, ingestion_service)
{%- endif %}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e



@router.post("/documents/{doc_id}/retry", response_model=RAGRetryResponse)
{%- if cookiecutter.use_postgresql %}
async def retry_ingestion(
{%- else %}
def retry_ingestion(
{%- endif %}
    doc_id: str,
    rag_doc_svc: RAGDocumentSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Retry a failed document ingestion."""

    try:
{%- if cookiecutter.use_postgresql %}
        doc = await rag_doc_svc.retry_ingestion(doc_id)
{%- else %}
        doc = rag_doc_svc.retry_ingestion(doc_id)
{%- endif %}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RAGRetryResponse(id=str(doc.id), status="processing", message="Retry queued")


@router.get("/sync/logs", response_model=RAGSyncLogList)
{%- if cookiecutter.use_postgresql %}
async def list_sync_logs(
{%- else %}
def list_sync_logs(
{%- endif %}
    rag_sync_svc: RAGSyncSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
    collection_name: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    """List sync operation logs."""

{%- if cookiecutter.use_postgresql %}
    return await rag_sync_svc.list_sync_logs(collection_name=collection_name, limit=limit)
{%- else %}
    return rag_sync_svc.list_sync_logs(collection_name=collection_name, limit=limit)
{%- endif %}


@router.post("/sync/local", response_model=RAGSyncResponse)
async def trigger_local_sync(
    request: RAGSyncRequest,
    background_tasks: BackgroundTasks,
    rag_sync_svc: RAGSyncSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Trigger a local directory sync via background task."""

{%- if cookiecutter.use_postgresql %}
    sync_log = await rag_sync_svc.create_sync_log(
        source="local", collection_name=request.collection_name, mode=request.mode,
    )
{%- else %}
    sync_log = rag_sync_svc.create_sync_log(
        source="local", collection_name=request.collection_name, mode=request.mode,
    )
{%- endif %}

{%- if cookiecutter.use_celery %}
    sync_collection_task.delay(
        sync_log_id=str(sync_log.id), source="local",
        collection_name=request.collection_name, mode=request.mode, path=request.path,
    )
{%- elif cookiecutter.use_taskiq %}
    await sync_collection_task.kiq(
        sync_log_id=str(sync_log.id), source="local",
        collection_name=request.collection_name, mode=request.mode, path=request.path,
    )
{%- elif cookiecutter.use_arq %}
    pool = await get_arq_pool()
    await pool.enqueue_job("sync_collection_task",
        str(sync_log.id), "local", request.collection_name, request.mode, request.path,
    )
{%- else %}
    background_tasks.add_task(sync_local_in_background, str(sync_log.id), request.collection_name, request.mode, request.path)
{%- endif %}

    return RAGSyncResponse(id=str(sync_log.id), status="running", message=f"Sync started for '{request.collection_name}' (mode={request.mode})")


@router.delete("/sync/{sync_id}", response_model=RAGMessageResponse)
{%- if cookiecutter.use_postgresql %}
async def cancel_sync(
{%- else %}
def cancel_sync(
{%- endif %}
    sync_id: str,
    rag_sync_svc: RAGSyncSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Cancel a running sync operation."""

    try:
{%- if cookiecutter.use_postgresql %}
        await rag_sync_svc.cancel_sync(sync_id)
{%- else %}
        rag_sync_svc.cancel_sync(sync_id)
{%- endif %}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RAGMessageResponse(message="Sync cancelled")


@router.get("/sync/sources", response_model=SyncSourceList)
{%- if cookiecutter.use_postgresql %}
async def list_sync_sources(
{%- else %}
def list_sync_sources(
{%- endif %}
    sync_source_svc: SyncSourceSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """List all configured sync sources."""

{%- if cookiecutter.use_postgresql %}
    return await sync_source_svc.list_sources()
{%- else %}
    return sync_source_svc.list_sources()
{%- endif %}


@router.post("/sync/sources", response_model=SyncSourceRead, status_code=status.HTTP_201_CREATED)
{%- if cookiecutter.use_postgresql %}
async def create_sync_source(
{%- else %}
def create_sync_source(
{%- endif %}
    data: SyncSourceCreate,
    sync_source_svc: SyncSourceSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Create a new sync source configuration."""

    try:
{%- if cookiecutter.use_postgresql %}
        return await sync_source_svc.create_source(data)
{%- else %}
        return sync_source_svc.create_source(data)
{%- endif %}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/sync/sources/{source_id}", response_model=SyncSourceRead)
{%- if cookiecutter.use_postgresql %}
async def update_sync_source(
{%- else %}
def update_sync_source(
{%- endif %}
    source_id: str,
    data: SyncSourceUpdate,
    sync_source_svc: SyncSourceSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Update an existing sync source configuration."""

    try:
{%- if cookiecutter.use_postgresql %}
        return await sync_source_svc.update_source(source_id, data)
{%- else %}
        return sync_source_svc.update_source(source_id, data)
{%- endif %}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.delete("/sync/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
{%- if cookiecutter.use_postgresql %}
async def delete_sync_source(
{%- else %}
def delete_sync_source(
{%- endif %}
    source_id: str,
    sync_source_svc: SyncSourceSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> None:
    """Delete a sync source configuration."""

    try:
{%- if cookiecutter.use_postgresql %}
        await sync_source_svc.delete_source(source_id)
{%- else %}
        sync_source_svc.delete_source(source_id)
{%- endif %}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.post("/sync/sources/{source_id}/trigger", response_model=RAGSyncResponse)
async def trigger_sync_source(
    source_id: str,
    background_tasks: BackgroundTasks,
    sync_source_svc: SyncSourceSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
) -> Any:
    """Trigger a manual sync for a configured source."""

    try:
{%- if cookiecutter.use_postgresql %}
        sync_log = await sync_source_svc.trigger_sync(source_id)
{%- else %}
        sync_log = sync_source_svc.trigger_sync(source_id)
{%- endif %}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e

    # Dispatch background task to execute the sync
{%- if cookiecutter.use_celery %}
    sync_single_source_task.delay(source_id, str(sync_log.id))
{%- elif cookiecutter.use_taskiq %}
    await sync_single_source_task.kiq(source_id, str(sync_log.id))
{%- elif cookiecutter.use_arq %}
    pool = await get_arq_pool()
    await pool.enqueue_job("sync_single_source_task", source_id, str(sync_log.id))
{%- else %}
    background_tasks.add_task(sync_source_in_background, source_id, str(sync_log.id))
{%- endif %}

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
{%- endif %}

{%- if (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) and cookiecutter.enable_redis %}


# SSE for RAG status updates (auto-reconnect via EventSource API)
@router.get("/status/stream", response_class=EventSourceResponse)
async def rag_status_stream() -> AsyncIterable[ServerSentEvent]:
    """SSE endpoint for real-time RAG ingestion status updates.

    Subscribes to Redis pub/sub channel 'rag_status' and streams events.
    Browser auto-reconnects via EventSource API.
    """
    r = aioredis.from_url(f"redis://{app_settings.REDIS_HOST}:{app_settings.REDIS_PORT}/{app_settings.REDIS_DB}")  # type: ignore[no-untyped-call]
    pubsub = r.pubsub()
    await pubsub.subscribe("rag_status")
    event_id = 0

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"].decode() if isinstance(message["data"], bytes) else message["data"]
                event_id += 1
                yield ServerSentEvent(raw_data=data, event="status", id=str(event_id))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning(f"RAG SSE error: {e}")
    finally:
        try:
            await pubsub.unsubscribe("rag_status")
            await r.aclose()
        except Exception:
            pass
{%- endif %}

{%- else %}
"""RAG routes - not configured."""
{%- endif %}
