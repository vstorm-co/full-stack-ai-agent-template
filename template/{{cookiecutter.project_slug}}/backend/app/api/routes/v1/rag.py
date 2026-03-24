{%- if cookiecutter.enable_rag %}
"""RAG API routes for collection management, search, document upload, and deletion."""

import logging
import tempfile
from pathlib import Path
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) or ((cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) and cookiecutter.enable_redis) %}
import json
{%- endif %}
{%- if (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) and cookiecutter.enable_redis %}
from collections.abc import AsyncIterable
{%- endif %}

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, UploadFile, File, status
from fastapi.responses import JSONResponse
{%- if (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) and cookiecutter.enable_redis %}
from fastapi.sse import EventSourceResponse, ServerSentEvent
{%- endif %}

from app.api.deps import IngestionSvc, RetrievalSvc, VectorStoreSvc
{%- if cookiecutter.use_jwt %}
from app.api.deps import CurrentAdmin, CurrentUser
{%- endif %}
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
from app.api.deps import RAGDocumentSvc, RAGSyncSvc, SyncSourceSvc
from app.core.exceptions import NotFoundError
from app.schemas.sync_source import (
    ConnectorConfigField,
    ConnectorInfo,
    ConnectorList,
    SyncSourceCreate,
    SyncSourceList,
    SyncSourceRead,
    SyncSourceUpdate,
)
{%- endif %}
from app.schemas.rag import (
    RAGCollectionInfo,
    RAGCollectionList,
    RAGDocumentItem,
    RAGDocumentList,
    RAGMessageResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGSearchResult,
)
{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
from app.schemas.rag import RAGIngestResponse, RAGRetryResponse, RAGTrackedDocumentItem, RAGTrackedDocumentList
from app.schemas.rag import RAGSyncLogItem, RAGSyncLogList, RAGSyncRequest, RAGSyncResponse
{%- endif %}

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/supported-formats")
async def get_supported_formats_endpoint():
    """Return file formats supported by the current PDF parser configuration."""
    from app.rag.config import get_supported_formats

{%- if cookiecutter.use_all_pdf_parsers %}
    from app.core.config import settings as app_settings
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
):
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
):
    """Create and initialize a new collection."""
    import re
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{0,63}$', name):
        raise HTTPException(status_code=400, detail="Collection name must start with a letter and contain only letters, numbers, and underscores (max 64 chars)")
    if name.lower() == "all":
        raise HTTPException(status_code=400, detail="'all' is a reserved collection name")
    await vector_store._ensure_collection(name)
    return RAGMessageResponse(message=f"Collection '{name}' created successfully.")


@router.delete("/collections/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def drop_collection(
    name: str,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
    rag_doc_svc: RAGDocumentSvc = None,
{%- endif %}
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
):
    """Drop an entire collection — vectors and all SQL document records."""
    await vector_store.delete_collection(name)
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
    if rag_doc_svc:
        await rag_doc_svc.delete_by_collection(name)
{%- endif %}


@router.get("/collections/{name}/info", response_model=RAGCollectionInfo)
async def get_collection_info(
    name: str,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
):
    """Retrieve stats for a specific collection."""
    return await vector_store.get_collection_info(name)


@router.get("/collections/{name}/documents", response_model=RAGDocumentList)
async def list_documents(
    name: str,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
):
    """List all documents in a specific collection."""
    documents = await vector_store.get_documents(name)
    return RAGDocumentList(
        items=[
            RAGDocumentItem(
                document_id=doc.document_id,
                filename=doc.filename,
                filesize=doc.filesize,
                filetype=doc.filetype,
                chunk_count=doc.chunk_count,
                additional_info=doc.additional_info,
            )
            for doc in documents
        ],
        total=len(documents),
    )


@router.post("/search", response_model=RAGSearchResponse)
async def search_documents(
    request: RAGSearchRequest,
    retrieval_service: RetrievalSvc,
    {%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
    {%- endif %}
    use_reranker: bool = Query(False, description="Whether to use reranking (if configured)"),
):
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


@router.delete("/collections/{name}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    name: str,
    document_id: str,
    ingestion_service: IngestionSvc,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin,
{%- endif %}
):
    """Delete a specific document by its ID from a collection."""
    success = await ingestion_service.remove_document(name, document_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


{%- if (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}

@router.post("/collections/{name}/ingest", response_model=RAGIngestResponse, response_model_exclude_none=True)
async def ingest_file(
    name: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    rag_doc_svc: RAGDocumentSvc = None,
    ingestion_service: IngestionSvc = None,
    vector_store: VectorStoreSvc = None,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
    replace: bool = Query(False),
):
    """Upload and ingest a file into a collection. Tracks status in DB."""
    from app.core.config import settings as app_settings
    from app.rag.config import get_supported_formats

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

    from app.services.file_storage import get_file_storage
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

    await vector_store._ensure_collection(name)
{%- if cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq %}

    # Save to shared media volume (accessible by both app and worker containers)
    import os
    tmp_dir = os.path.join(str(app_settings.MEDIA_DIR), "_rag_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, f"{str(doc_id)}{ext}")
    with open(tmp_path, "wb") as f:
        f.write(data)

    # Dispatch async task
    from app.worker.tasks.rag_tasks import ingest_document_task
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
    from app.worker.arq_app import get_arq_pool
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

    import os
    tmp_dir = os.path.join(tempfile.gettempdir(), "rag_ingest")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, f"{str(doc_id)}{ext}")
    with open(tmp_path, "wb") as f:
        f.write(data)

    async def _ingest_in_background(doc_id_str: str, collection: str, fpath: str, source: str, do_replace: bool) -> None:
        """Run ingestion via FastAPI BackgroundTasks."""
        from app.db.session import get_db_context
        from app.rag.ingestion import IngestionService
        from app.services.rag_document import RAGDocumentService

        try:
            svc = IngestionService()
            result = await svc.ingest_file(filepath=Path(fpath), collection_name=collection, replace=do_replace, source_path=source)
            async with get_db_context() as bg_db:
                bg_doc_svc = RAGDocumentService(bg_db)
                await bg_doc_svc.complete_ingestion(doc_id_str, vector_document_id=result.document_id)
        except Exception as exc:
            logger.error(f"Background ingestion failed: {exc}")
            async with get_db_context() as bg_db:
                bg_doc_svc = RAGDocumentService(bg_db)
                await bg_doc_svc.fail_ingestion(doc_id_str, error_message=str(exc))
        finally:
            Path(fpath).unlink(missing_ok=True)

    background_tasks.add_task(_ingest_in_background, str(doc_id), name, tmp_path, filename, replace)

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
    rag_doc_svc: RAGDocumentSvc = None,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
    collection_name: str | None = Query(None),
):
    """List tracked RAG documents."""
{%- if cookiecutter.use_postgresql %}
    docs = await rag_doc_svc.list_documents(collection_name)
{%- else %}
    docs = rag_doc_svc.list_documents(collection_name)
{%- endif %}
    return RAGTrackedDocumentList(
        items=[
            RAGTrackedDocumentItem(
                id=str(d.id), collection_name=d.collection_name, filename=d.filename,
                filesize=d.filesize, filetype=d.filetype, status=d.status,
                error_message=d.error_message, vector_document_id=d.vector_document_id,
                chunk_count=d.chunk_count, has_file=bool(d.storage_path),
                created_at=d.created_at.isoformat() if d.created_at else None,
                completed_at=d.completed_at.isoformat() if d.completed_at else None,
            )
            for d in docs
        ],
        total=len(docs),
    )


@router.get("/documents/{doc_id}/download")
{%- if cookiecutter.use_postgresql %}
async def download_rag_document(
{%- else %}
def download_rag_document(
{%- endif %}
    doc_id: str,
    rag_doc_svc: RAGDocumentSvc = None,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
):
    """Download the original file."""
    from fastapi.responses import FileResponse

    try:
{%- if cookiecutter.use_postgresql %}
        file_path, filename, mime_type = await rag_doc_svc.get_download_info(doc_id)
{%- else %}
        file_path, filename, mime_type = rag_doc_svc.get_download_info(doc_id)
{%- endif %}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    return FileResponse(path=file_path, filename=filename, media_type=mime_type)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
{%- if cookiecutter.use_postgresql %}
async def delete_rag_document(
{%- else %}
def delete_rag_document(
{%- endif %}
    doc_id: str,
    rag_doc_svc: RAGDocumentSvc = None,
    ingestion_service: IngestionSvc = None,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
):
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
    rag_doc_svc: RAGDocumentSvc = None,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
):
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
    rag_sync_svc: RAGSyncSvc = None,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
    collection_name: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """List sync operation logs."""
{%- if cookiecutter.use_postgresql %}
    logs = await rag_sync_svc.list_sync_logs(collection_name=collection_name, limit=limit)
{%- else %}
    logs = rag_sync_svc.list_sync_logs(collection_name=collection_name, limit=limit)
{%- endif %}
    return RAGSyncLogList(
        items=[
            RAGSyncLogItem(
                id=str(log.id), source=log.source, collection_name=log.collection_name,
                status=log.status, mode=log.mode, total_files=log.total_files,
                ingested=log.ingested, updated=log.updated, skipped=log.skipped, failed=log.failed,
                error_message=log.error_message,
                started_at=log.started_at.isoformat() if log.started_at else None,
                completed_at=log.completed_at.isoformat() if log.completed_at else None,
            )
            for log in logs
        ],
        total=len(logs),
    )


@router.post("/sync/local", response_model=RAGSyncResponse)
async def trigger_local_sync(
    request: RAGSyncRequest,
    background_tasks: BackgroundTasks,
    rag_sync_svc: RAGSyncSvc = None,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
):
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
    from app.worker.tasks.rag_tasks import sync_collection_task
    sync_collection_task.delay(
        sync_log_id=str(sync_log.id), source="local",
        collection_name=request.collection_name, mode=request.mode, path=request.path,
    )
{%- elif cookiecutter.use_taskiq %}
    from app.worker.tasks.rag_tasks import sync_collection_task
    await sync_collection_task.kiq(
        sync_log_id=str(sync_log.id), source="local",
        collection_name=request.collection_name, mode=request.mode, path=request.path,
    )
{%- elif cookiecutter.use_arq %}
    from app.worker.arq_app import get_arq_pool
    pool = await get_arq_pool()
    await pool.enqueue_job("sync_collection_task",
        str(sync_log.id), "local", request.collection_name, request.mode, request.path,
    )
{%- else %}
    from app.db.session import get_db_context

    async def _sync_in_background(log_id: str, collection: str, mode: str, path: str) -> None:
        """Run sync via FastAPI BackgroundTasks."""
        from app.rag.ingestion import IngestionService
        from app.services.rag_sync import RAGSyncService

        svc = IngestionService()
        ingested = skipped = failed = total = 0

        try:
            target = Path(path)
            files = list(target.rglob("*")) if target.is_dir() else [target]
            files = [f for f in files if f.is_file()]
            total = len(files)

            for filepath in files:
                try:
                    await svc.ingest_file(filepath=filepath, collection_name=collection, replace=(mode == "full"), source_path=str(filepath))
                    ingested += 1
                except Exception as e:
                    logger.warning(f"Failed to ingest {filepath}: {e}")
                    failed += 1
        except Exception as e:
            logger.error(f"Sync failed: {e}")

        async with get_db_context() as bg_db:
            bg_sync_svc = RAGSyncService(bg_db)
            try:
                await bg_sync_svc.complete_sync(
                    log_id,
                    status="done" if not failed else "error",
                    total_files=total,
                    ingested=ingested,
                    skipped=skipped,
                    failed=failed,
                )
            except NotFoundError:
                logger.error(f"Sync log {log_id} not found during background update")

    background_tasks.add_task(_sync_in_background, str(sync_log.id), request.collection_name, request.mode, request.path)
{%- endif %}

    return RAGSyncResponse(id=str(sync_log.id), status="running", message=f"Sync started for '{request.collection_name}' (mode={request.mode})")


@router.delete("/sync/{sync_id}", response_model=RAGMessageResponse)
{%- if cookiecutter.use_postgresql %}
async def cancel_sync(
{%- else %}
def cancel_sync(
{%- endif %}
    sync_id: str,
    rag_sync_svc: RAGSyncSvc = None,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
):
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


# --- Sync Source CRUD ---


@router.get("/sync/sources", response_model=SyncSourceList)
{%- if cookiecutter.use_postgresql %}
async def list_sync_sources(
{%- else %}
def list_sync_sources(
{%- endif %}
    sync_source_svc: SyncSourceSvc = None,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
):
    """List all configured sync sources."""
{%- if cookiecutter.use_postgresql %}
    sources = await sync_source_svc.list_sources()
{%- else %}
    sources = sync_source_svc.list_sources()
{%- endif %}
    return SyncSourceList(
        items=[SyncSourceRead(
            id=str(s.id), name=s.name, connector_type=s.connector_type,
            collection_name=s.collection_name,
            config=s.config if isinstance(s.config, dict) else json.loads(s.config) if s.config else {},
            sync_mode=s.sync_mode, schedule_minutes=s.schedule_minutes,
            is_active=s.is_active,
            last_sync_at=s.last_sync_at.isoformat() if s.last_sync_at else None,
            last_sync_status=s.last_sync_status, last_error=s.last_error,
            created_at=s.created_at.isoformat() if s.created_at else None,
        ) for s in sources],
        total=len(sources),
    )


@router.post("/sync/sources", response_model=SyncSourceRead, status_code=status.HTTP_201_CREATED)
{%- if cookiecutter.use_postgresql %}
async def create_sync_source(
{%- else %}
def create_sync_source(
{%- endif %}
    data: SyncSourceCreate,
    sync_source_svc: SyncSourceSvc = None,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
):
    """Create a new sync source configuration."""
    try:
{%- if cookiecutter.use_postgresql %}
        source = await sync_source_svc.create_source(data)
{%- else %}
        source = sync_source_svc.create_source(data)
{%- endif %}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return SyncSourceRead(
        id=str(source.id), name=source.name, connector_type=source.connector_type,
        collection_name=source.collection_name,
        config=source.config if isinstance(source.config, dict) else json.loads(source.config) if source.config else {},
        sync_mode=source.sync_mode, schedule_minutes=source.schedule_minutes,
        is_active=source.is_active,
        last_sync_at=None, last_sync_status=None, last_error=None,
        created_at=source.created_at.isoformat() if source.created_at else None,
    )


@router.patch("/sync/sources/{source_id}", response_model=SyncSourceRead)
{%- if cookiecutter.use_postgresql %}
async def update_sync_source(
{%- else %}
def update_sync_source(
{%- endif %}
    source_id: str,
    data: SyncSourceUpdate,
    sync_source_svc: SyncSourceSvc = None,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
):
    """Update an existing sync source configuration."""
    try:
{%- if cookiecutter.use_postgresql %}
        source = await sync_source_svc.update_source(source_id, data)
{%- else %}
        source = sync_source_svc.update_source(source_id, data)
{%- endif %}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    return SyncSourceRead(
        id=str(source.id), name=source.name, connector_type=source.connector_type,
        collection_name=source.collection_name,
        config=source.config if isinstance(source.config, dict) else json.loads(source.config) if source.config else {},
        sync_mode=source.sync_mode, schedule_minutes=source.schedule_minutes,
        is_active=source.is_active,
        last_sync_at=source.last_sync_at.isoformat() if source.last_sync_at else None,
        last_sync_status=source.last_sync_status, last_error=source.last_error,
        created_at=source.created_at.isoformat() if source.created_at else None,
    )


@router.delete("/sync/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
{%- if cookiecutter.use_postgresql %}
async def delete_sync_source(
{%- else %}
def delete_sync_source(
{%- endif %}
    source_id: str,
    sync_source_svc: SyncSourceSvc = None,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
):
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
    sync_source_svc: SyncSourceSvc = None,
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
):
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
    from app.worker.tasks.rag_tasks import sync_single_source_task
    sync_single_source_task.delay(source_id, str(sync_log.id))
{%- elif cookiecutter.use_taskiq %}
    from app.worker.tasks.rag_tasks import sync_single_source_task
    await sync_single_source_task.kiq(source_id, str(sync_log.id))
{%- elif cookiecutter.use_arq %}
    from app.worker.arq_app import get_arq_pool
    pool = await get_arq_pool()
    await pool.enqueue_job("sync_single_source_task", source_id, str(sync_log.id))
{%- else %}
    async def _run_source_sync_bg(src_id: str, log_id: str) -> None:
        """Execute sync via FastAPI BackgroundTasks."""
        from app.db.session import get_db_context
        from app.services.sync_source import SyncSourceService
        from app.rag.connectors import CONNECTOR_REGISTRY
        from app.rag.ingestion import IngestionService
        import tempfile
        from pathlib import Path

        async with get_db_context() as bg_db:
            svc = SyncSourceService(bg_db)
            try:
                source = await svc.get_source(src_id)
                connector_cls = CONNECTOR_REGISTRY.get(source.connector_type)
                if not connector_cls:
                    await svc.complete_sync(log_id, status="error", error_message=f"Unknown connector: {source.connector_type}")
                    return
                connector = connector_cls()
                config = source.config if isinstance(source.config, dict) else {}
                files = await connector.list_files(config)
                ingestion = IngestionService()
                ingested = failed = 0
                with tempfile.TemporaryDirectory() as tmp_dir:
                    for f in files:
                        try:
                            local_path = await connector.download_file(f, Path(tmp_dir))
                            await ingestion.ingest_file(
                                filepath=local_path, collection_name=source.collection_name,
                                replace=(source.sync_mode == "full"), source_path=f.source_path,
                            )
                            ingested += 1
                        except Exception as e:
                            logger.warning(f"Sync file failed {f.name}: {e}")
                            failed += 1
                await svc.complete_sync(log_id, status="done" if not failed else "error",
                    total_files=len(files), ingested=ingested, failed=failed)
            except Exception as e:
                logger.error(f"Source sync failed: {e}")
                await svc.complete_sync(log_id, status="error", error_message=str(e))

    background_tasks.add_task(_run_source_sync_bg, source_id, str(sync_log.id))
{%- endif %}

    return RAGSyncResponse(
        id=str(sync_log.id),
        status="running",
        message=f"Sync triggered for source '{source_id}'",
    )


@router.get("/sync/connectors", response_model=ConnectorList)
async def list_connectors(
{%- if cookiecutter.use_jwt %}
    _: CurrentAdmin = None,
{%- endif %}
):
    """List available sync connector types with their config schemas."""
    from app.rag.connectors import CONNECTOR_REGISTRY

    items = []
    for _connector_type, connector_cls in CONNECTOR_REGISTRY.items():
        schema_fields = {}
        for field_name, field_spec in connector_cls.CONFIG_SCHEMA.items():
            schema_fields[field_name] = ConnectorConfigField(**field_spec)
        items.append(ConnectorInfo(
            type=connector_cls.CONNECTOR_TYPE,
            name=connector_cls.DISPLAY_NAME,
            config_schema=schema_fields,
            enabled=True,
        ))
    return ConnectorList(items=items)
{%- endif %}

{%- if (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) and cookiecutter.enable_redis %}


# SSE for RAG status updates (auto-reconnect via EventSource API)
@router.get("/status/stream", response_class=EventSourceResponse)
async def rag_status_stream() -> AsyncIterable[ServerSentEvent]:
    """SSE endpoint for real-time RAG ingestion status updates.

    Subscribes to Redis pub/sub channel 'rag_status' and streams events.
    Browser auto-reconnects via EventSource API.
    """
    import asyncio

    import redis.asyncio as aioredis
    from app.core.config import settings

    r = aioredis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}")
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
