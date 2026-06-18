"""RAG ingestion & sync tasks — processes documents asynchronously."""

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, soft_time_limit=300, time_limit=360)  # type: ignore
def ingest_document_task(
    self: Any,
    rag_document_id: str,
    collection_name: str,
    filepath: str,
    source_path: str,
    replace: bool = False,
) -> dict[str, Any]:
    """Process a document: parse, chunk, embed, store in vector DB."""
    logger.info(f"Starting ingestion: {source_path} -> {collection_name}")
    try:
        return asyncio.run(
            _run_ingestion(rag_document_id, collection_name, filepath, source_path, replace)
        )
    except Exception as exc:
        logger.error(f"Ingestion failed: {exc}")
        asyncio.run(_update_status(rag_document_id, "error", error_message=str(exc)))
        raise self.retry(exc=exc, countdown=30) from exc


@shared_task(bind=True, max_retries=1, soft_time_limit=600, time_limit=720)  # type: ignore
def sync_collection_task(
    self: Any, sync_log_id: str, source: str, collection_name: str, mode: str, path: str
) -> dict[str, Any]:
    """Sync a collection from a local directory."""
    logger.info(f"Starting sync: {source} -> {collection_name} (mode={mode})")
    try:
        return asyncio.run(_run_sync(sync_log_id, source, collection_name, mode, path))
    except Exception as exc:
        logger.error(f"Sync failed: {exc}")
        asyncio.run(_update_sync_log(sync_log_id, "error", error_message=str(exc)))
        raise self.retry(exc=exc, countdown=60) from exc


@shared_task(bind=True, max_retries=2, soft_time_limit=600, time_limit=720)  # type: ignore
def sync_single_source_task(
    self: Any, source_id: str, sync_log_id: str | None = None
) -> dict[str, Any]:
    """Sync a single connector source. If sync_log_id provided, use existing log."""
    logger.info(f"Starting source sync: {source_id}")
    try:
        return asyncio.run(_run_source_sync(source_id, sync_log_id=sync_log_id))
    except Exception as exc:
        logger.error(f"Source sync failed: {exc}")
        raise self.retry(exc=exc, countdown=60) from exc


@shared_task  # type: ignore
def check_scheduled_syncs() -> None:
    """Periodic task: find sources due for sync and dispatch individual tasks."""

    async def _check() -> None:
        from app.db.session import get_worker_db_context
        from app.repositories import sync_source as sync_source_repo

        async with get_worker_db_context() as db:
            sources = await sync_source_repo.get_due_for_sync(db)
            for source in sources:
                sync_single_source_task.delay(str(source.id))
            logger.info(f"Scheduled sync check: dispatched {len(sources)} source(s)")

    asyncio.run(_check())


async def _run_ingestion(
    rag_document_id: str, collection_name: str, filepath: str, source_path: str, replace: bool
) -> dict[str, Any]:
    from app.core.config import settings
    from app.db.session import get_worker_db_context
    from app.services.rag.documents import DocumentProcessor
    from app.services.rag.embeddings import EmbeddingService
    from app.services.rag.ingestion import IngestionService
    from app.services.rag.vectorstore import MilvusVectorStore as VectorStore
    from app.services.rag_document import RAGDocumentService

    rag_settings = settings.rag
    embed_service = EmbeddingService(settings=rag_settings)
    vector_store = VectorStore(settings=rag_settings, embedding_service=embed_service)
    processor = DocumentProcessor(settings=rag_settings)
    ingestion_service = IngestionService(processor=processor, vector_store=vector_store)

    file_path = Path(filepath)
    try:
        result = await ingestion_service.ingest_file(
            filepath=file_path,
            collection_name=collection_name,
            replace=replace,
            source_path=source_path,
        )
        async with get_worker_db_context() as db:
            await RAGDocumentService(db).complete_ingestion(
                rag_document_id, vector_document_id=result.document_id
            )
        await _notify_ws(rag_document_id, "done", source_path)
        logger.info(f"Ingestion complete: {source_path}")
        return {"status": "done", "document_id": result.document_id, "filename": source_path}
    except Exception as e:
        await _update_status(rag_document_id, "error", error_message=str(e))
        raise


async def _run_sync(
    sync_log_id: str, source: str, collection_name: str, mode: str, path: str
) -> dict[str, Any]:
    import hashlib

    from app.core.config import settings
    from app.db.session import get_worker_db_context
    from app.services.rag.config import DocumentExtensions
    from app.services.rag.documents import DocumentProcessor
    from app.services.rag.embeddings import EmbeddingService
    from app.services.rag.ingestion import IngestionService
    from app.services.rag.vectorstore import MilvusVectorStore as VectorStore
    from app.services.rag_document import RAGDocumentService
    from app.services.rag_sync import RAGSyncService

    rag_settings = settings.rag
    embed_service = EmbeddingService(settings=rag_settings)
    vector_store = VectorStore(settings=rag_settings, embedding_service=embed_service)
    processor = DocumentProcessor(settings=rag_settings)
    ingestion_service = IngestionService(processor=processor, vector_store=vector_store)

    target_path = Path(path).resolve()
    if not target_path.exists():
        await _update_sync_log(sync_log_id, "error", error_message=f"Path not found: {path}")
        return {"status": "error", "message": f"Path not found: {path}"}

    if target_path.is_file():
        files = [target_path]
    else:
        files = [f for f in target_path.rglob("*") if f.is_file() and not f.name.startswith(".")]

    allowed = {ext.value for ext in DocumentExtensions}
    files = [f for f in files if f.suffix.lower() in allowed]
    ingested = updated = skipped = failed = 0

    for filepath in files:
        # Check if sync was cancelled
        async with get_worker_db_context() as db:
            sync_log_check = await RAGSyncService(db).get_sync_log(sync_log_id)
            if sync_log_check.status == "cancelled":
                logger.info(f"Sync {sync_log_id} cancelled by user")
                return {
                    "status": "cancelled",
                    "ingested": ingested,
                    "updated": updated,
                    "skipped": skipped,
                    "failed": failed,
                }

        source_path = str(filepath.resolve())
        if mode in ("new_only", "update_only"):
            existing_id = await ingestion_service.find_existing(collection_name, source_path)

            if mode == "new_only":
                if existing_id:
                    # File exists — check if content changed via hash
                    file_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()
                    existing_hash = await ingestion_service.get_existing_hash(
                        collection_name, source_path
                    )
                    if existing_hash and file_hash == existing_hash:
                        skipped += 1
                        continue
                    # Hash changed — will re-ingest below

            elif mode == "update_only":
                if not existing_id:
                    skipped += 1
                    continue
                file_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()
                existing_hash = await ingestion_service.get_existing_hash(
                    collection_name, source_path
                )
                if existing_hash and file_hash == existing_hash:
                    skipped += 1
                    continue
        try:
            result = await ingestion_service.ingest_file(
                filepath=filepath, collection_name=collection_name, replace=True
            )
            if result.status.value == "done":
                if result.message and "replaced" in result.message:
                    updated += 1
                else:
                    ingested += 1
                async with get_worker_db_context() as db:
                    doc = await RAGDocumentService(db).create_document(
                        collection_name=collection_name,
                        filename=filepath.name,
                        filesize=filepath.stat().st_size,
                        filetype=filepath.suffix.lstrip(".").lower(),
                    )
                    await RAGDocumentService(db).complete_ingestion(
                        str(doc.id), vector_document_id=result.document_id
                    )
            else:
                failed += 1
        except Exception as e:
            logger.warning(f"Sync file error {filepath.name}: {e}")
            failed += 1

    async with get_worker_db_context() as db:
        await RAGSyncService(db).complete_sync(
            sync_log_id,
            status="done" if failed == 0 else "error",
            total_files=len(files),
            ingested=ingested,
            updated=updated,
            skipped=skipped,
            failed=failed,
        )

    return {
        "status": "done",
        "ingested": ingested,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
    }


async def _update_status(
    rag_document_id: str, status: str, error_message: str | None = None
) -> None:
    from app.db.session import get_worker_db_context
    from app.services.rag_document import RAGDocumentService

    try:
        async with get_worker_db_context() as db:
            doc_svc = RAGDocumentService(db)
            if status == "error":
                await doc_svc.fail_ingestion(
                    rag_document_id, error_message=error_message or "Unknown error"
                )
            elif status == "done":
                # vector_document_id required for complete_ingestion; callers
                # set status="done" directly in _run_ingestion with the ID.
                pass
    except Exception as e:
        logger.warning(f"Failed to update RAGDocument status: {e}")


async def _notify_ws(rag_document_id: str, status: str, filename: str) -> None:
    try:
        import json

        import redis.asyncio as aioredis

        from app.core.config import settings

        r = aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        )  # type: ignore[no-untyped-call]
        await r.publish(
            "rag_status",
            json.dumps(
                {
                    "document_id": rag_document_id,
                    "status": status,
                    "filename": filename,
                }
            ),
        )
        await r.aclose()
    except Exception as e:
        logger.warning(f"Failed to send WS notification: {e}")


async def _update_sync_log(sync_log_id: str, status: str, error_message: str | None = None) -> None:
    from app.db.session import get_worker_db_context
    from app.services.rag_sync import RAGSyncService

    try:
        async with get_worker_db_context() as db:
            await RAGSyncService(db).complete_sync(
                sync_log_id, status=status, error_message=error_message
            )
    except Exception as e:
        logger.warning(f"Failed to update SyncLog: {e}")


async def _run_source_sync(source_id: str, sync_log_id: str | None = None) -> dict[str, Any]:
    """Core sync logic for connector-based sources (shared between all task frameworks).

    Fetches files from a remote connector (e.g. Google Drive, S3), downloads them
    to a temporary directory, and ingests each into the vector store.
    """
    from app.core.config import settings
    from app.db.session import get_worker_db_context
    from app.services.rag.connectors import CONNECTOR_REGISTRY
    from app.services.rag.documents import DocumentProcessor
    from app.services.rag.embeddings import EmbeddingService
    from app.services.rag.ingestion import IngestionService
    from app.services.rag.vectorstore import MilvusVectorStore as VectorStore
    from app.services.rag_sync import RAGSyncService
    from app.services.sync_source import SyncSourceService

    async with get_worker_db_context() as db:
        source_svc = SyncSourceService(db)

        source = await source_svc.get_source(source_id)
        connector_cls = CONNECTOR_REGISTRY.get(source.connector_type)
        if not connector_cls:
            await source_svc.update_after_sync(
                source_id, "error", f"Unknown connector: {source.connector_type}"
            )
            return {"status": "error", "message": f"Unknown connector: {source.connector_type}"}

        config = source.config if isinstance(source.config, dict) else json.loads(source.config)
        collection_name = source.collection_name
        sync_mode = source.sync_mode

        # Use existing SyncLog (from API trigger) or create new one (from scheduler)
        if sync_log_id:
            log_id = sync_log_id
        else:
            log = await source_svc.trigger_sync(source_id)
            log_id = str(log.id)

    connector = connector_cls()
    rag_settings = settings.rag
    embed_service = EmbeddingService(settings=rag_settings)
    vector_store = VectorStore(settings=rag_settings, embedding_service=embed_service)
    processor = DocumentProcessor(settings=rag_settings)
    ingestion_svc = IngestionService(processor=processor, vector_store=vector_store)

    ingested = skipped = failed = total = 0

    try:
        files = await connector.list_files(config)
        total = len(files)

        with tempfile.TemporaryDirectory() as tmp_dir:
            for remote_file in files:
                try:
                    local_path = await connector.download_file(remote_file, Path(tmp_dir))
                    await ingestion_svc.ingest_file(
                        filepath=local_path,
                        collection_name=collection_name,
                        replace=(sync_mode == "full"),
                        source_path=remote_file.source_path,
                    )
                    ingested += 1
                except Exception as e:
                    logger.warning(f"Failed to sync {remote_file.name}: {e}")
                    failed += 1
    except Exception as e:
        logger.error(f"Source sync failed for {source_id}: {e}")
        failed = max(failed, 1)

    async with get_worker_db_context() as db:
        sync_svc = RAGSyncService(db)
        source_svc = SyncSourceService(db)
        try:
            await sync_svc.complete_sync(
                log_id,
                status="done" if not failed else "error",
                total_files=total,
                ingested=ingested,
                skipped=skipped,
                failed=failed,
            )
            await source_svc.update_after_sync(
                source_id,
                status="done" if not failed else "error",
                error=f"{failed} files failed" if failed else None,
            )
        except Exception:
            logger.error(f"Failed to update sync status for source {source_id}")

    logger.info(
        f"Source sync complete: {source_id} — "
        f"total={total}, ingested={ingested}, skipped={skipped}, failed={failed}"
    )
    return {
        "status": "done" if not failed else "error",
        "total": total,
        "ingested": ingested,
        "skipped": skipped,
        "failed": failed,
    }
