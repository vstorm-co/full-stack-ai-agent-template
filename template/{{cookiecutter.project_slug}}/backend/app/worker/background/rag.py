{%- if cookiecutter.enable_rag and not (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) %}
"""In-process RAG ingestion / sync handlers (FastAPI BackgroundTasks fallback).

Used when no distributed task queue (Celery/Taskiq/ARQ) is configured. Each handler
performs a single ingestion or sync operation in the API process, updating the
appropriate tracking record (``RAGDocument`` / ``SyncLog``) on completion.
"""

import logging
import tempfile
from pathlib import Path

from app.db.session import get_db_context
from app.services.rag.connectors import CONNECTOR_REGISTRY
from app.services.rag.ingestion import IngestionService

logger = logging.getLogger(__name__)


async def ingest_document_in_background(
    *,
    rag_document_id: str,
    collection_name: str,
    filepath: str,
    source_path: str,
    replace: bool,
) -> None:
    """Ingest a single document into the vector store and update its DB record."""
    from app.services.rag_document import RAGDocumentService

    try:
        result = await IngestionService.from_settings().ingest_file(
            filepath=Path(filepath),
            collection_name=collection_name,
            replace=replace,
            source_path=source_path,
        )
        async with get_db_context() as db:
            await RAGDocumentService(db).complete_ingestion(
                rag_document_id, vector_document_id=result.document_id
            )
    except Exception as exc:
        logger.error("background_ingestion_failed: %s", exc)
        async with get_db_context() as db:
            await RAGDocumentService(db).fail_ingestion(rag_document_id, error_message=str(exc))
    finally:
        Path(filepath).unlink(missing_ok=True)


async def sync_local_in_background(
    *,
    sync_log_id: str,
    collection_name: str,
    mode: str,
    path: str,
) -> None:
    """Sync a local directory into a collection and update the sync log."""
    from app.services.rag_sync import RAGSyncService

    svc = IngestionService.from_settings()
    ingested = skipped = failed = total = 0

    try:
        target = Path(path)
        files = list(target.rglob("*")) if target.is_dir() else [target]
        files = [f for f in files if f.is_file()]
        total = len(files)
        for filepath in files:
            try:
                await svc.ingest_file(
                    filepath=filepath,
                    collection_name=collection_name,
                    replace=(mode == "full"),
                    source_path=str(filepath),
                )
                ingested += 1
            except Exception as exc:
                logger.warning("sync_file_failed: %s — %s", filepath, exc)
                failed += 1
    except Exception as exc:
        logger.error("local_sync_failed: %s", exc)

    async with get_db_context() as db:
        try:
            await RAGSyncService(db).complete_sync(
                sync_log_id,
                status="done" if not failed else "error",
                total_files=total,
                ingested=ingested,
                skipped=skipped,
                failed=failed,
            )
        except Exception:
            logger.warning("sync_log_update_failed", extra={"sync_log_id": sync_log_id})


async def sync_source_in_background(source_id: str, sync_log_id: str) -> None:
    """Execute a configured connector source and update the sync log."""
    from app.services.rag_sync import RAGSyncService
    from app.services.sync_source import SyncSourceService

    async with get_db_context() as db:
        source_svc = SyncSourceService(db)
        sync_svc = RAGSyncService(db)
        try:
            source = await source_svc.get_source(source_id)
            connector_cls = CONNECTOR_REGISTRY.get(source.connector_type)
            if not connector_cls:
                await sync_svc.complete_sync(
                    sync_log_id,
                    status="error",
                    error_message=f"Unknown connector: {source.connector_type}",
                )
                return
            connector = connector_cls()
            config = source.config if isinstance(source.config, dict) else {}
            files = await connector.list_files(config)
            ingestion = IngestionService.from_settings()
            ingested = failed = 0
            with tempfile.TemporaryDirectory() as tmp_dir:
                for f in files:
                    try:
                        local_path = await connector.download_file(f, Path(tmp_dir))
                        await ingestion.ingest_file(
                            filepath=local_path,
                            collection_name=source.collection_name,
                            replace=(source.sync_mode == "full"),
                            source_path=f.source_path,
                        )
                        ingested += 1
                    except Exception as exc:
                        logger.warning("connector_file_failed: %s — %s", f.name, exc)
                        failed += 1
            await sync_svc.complete_sync(
                sync_log_id,
                status="done" if not failed else "error",
                total_files=len(files),
                ingested=ingested,
                failed=failed,
            )
        except Exception as exc:
            logger.error("source_sync_failed: %s", exc)
            await sync_svc.complete_sync(sync_log_id, status="error", error_message=str(exc))
{%- else %}
"""RAG background tasks — not configured."""
{%- endif %}
