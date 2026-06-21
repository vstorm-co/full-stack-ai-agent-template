{%- if cookiecutter.enable_rag %}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""RAG sync service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.sync_log import SyncLog
from app.repositories import sync_log_repo
from app.schemas.rag import RAGSyncLogItem, RAGSyncLogList
{%- if cookiecutter.use_celery or cookiecutter.use_taskiq %}
from app.worker.tasks.rag_tasks import sync_collection_task
{%- elif cookiecutter.use_arq %}
from app.worker.arq_app import get_arq_pool
{%- elif cookiecutter.use_prefect %}
from app.worker.tasks.rag_tasks import sync_collection_flow
{%- else %}
from app.worker.background import fire_and_forget
from app.worker.background.rag import sync_local_in_background
{%- endif %}


class RAGSyncService:
    """Service for RAG sync operation management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_sync_logs(
        self,
        collection_name: str | None = None,
        limit: int = 20,
    ) -> RAGSyncLogList:
        """Return up to `limit` sync log entries ordered newest-first.

        When `collection_name` is None all collections are included; pass a
        collection name to restrict results to that collection only.  The
        caller is responsible for choosing an appropriate `limit` — no
        server-side cap beyond `limit` is applied.
        """
        logs = await sync_log_repo.get_all(self.db, collection_name=collection_name, limit=limit)
        return RAGSyncLogList(
            items=[RAGSyncLogItem.model_validate(log) for log in logs],
            total=len(logs),
        )

    async def get_sync_log(self, sync_id: str) -> SyncLog:
        """Get a sync log by ID.

        Raises:
            NotFoundError: If sync log does not exist.
        """
        log = await sync_log_repo.get_by_id(self.db, UUID(sync_id))
        if not log:
            raise NotFoundError(
                message="Sync log not found",
                details={"sync_id": sync_id},
            )
        return log

    async def create_sync_log(
        self,
        *,
        source: str,
        collection_name: str,
        mode: str,
    ) -> SyncLog:
        """Create a new sync log entry."""
        return await sync_log_repo.create(
            self.db,
            source=source,
            collection_name=collection_name,
            mode=mode,
        )

    async def start_local_sync(
        self,
        *,
        collection_name: str,
        mode: str,
        path: str | None,
    ) -> SyncLog:
        """Persist a sync log and dispatch the local-sync task on the configured backend."""
        sync_log = await self.create_sync_log(
            source="local",
            collection_name=collection_name,
            mode=mode,
        )
{%- if cookiecutter.use_celery %}
        sync_collection_task.delay(
            sync_log_id=str(sync_log.id),
            source="local",
            collection_name=collection_name,
            mode=mode,
            path=path,
        )
{%- elif cookiecutter.use_taskiq %}
        await sync_collection_task.kiq(
            sync_log_id=str(sync_log.id),
            source="local",
            collection_name=collection_name,
            mode=mode,
            path=path,
        )
{%- elif cookiecutter.use_arq %}
        pool = await get_arq_pool()
        await pool.enqueue_job(
            "sync_collection",
            str(sync_log.id),
            "local",
            collection_name,
            mode,
            path,
        )
{%- elif cookiecutter.use_prefect %}
        import asyncio
        asyncio.create_task(sync_collection_flow(
            sync_log_id=str(sync_log.id),
            source="local",
            collection_name=collection_name,
            mode=mode,
            path=path,
        ))
{%- else %}
        fire_and_forget(
            sync_local_in_background(
                sync_log_id=str(sync_log.id),
                collection_name=collection_name,
                mode=mode,
                path=path,
            ),
            label="rag.sync_local",
        )
{%- endif %}
        return sync_log

    async def complete_sync(
        self,
        sync_id: str,
        *,
        status: str,
        total_files: int = 0,
        ingested: int = 0,
        updated: int = 0,
        skipped: int = 0,
        failed: int = 0,
        error_message: str | None = None,
    ) -> None:
        """Mark a sync operation as completed (done or error)."""
        log = await self.get_sync_log(sync_id)
        await sync_log_repo.update_status(
            self.db,
            log.id,
            status=status,
            total_files=total_files,
            ingested=ingested,
            updated=updated,
            skipped=skipped,
            failed=failed,
            error_message=error_message,
            completed_at=datetime.now(UTC),
        )

    async def cancel_sync(self, sync_id: str) -> SyncLog:
        """Cancel a running sync operation.

        Raises:
            NotFoundError: If sync log does not exist.
            BadRequestError: If sync is not in 'running' state.
        """
        log = await self.get_sync_log(sync_id)
        if log.status != "running":
            raise BadRequestError(
                message="Sync is not in running state",
                details={"sync_id": sync_id, "current_status": log.status},
            )
        cancelled = await sync_log_repo.update_status(
            self.db,
            log.id,
            status="cancelled",
            completed_at=datetime.now(UTC),
        )
        if cancelled is None:
            raise NotFoundError(message="Sync log not found", details={"sync_id": sync_id})
        return cancelled


{%- else %}
"""RAG sync service - not configured."""
{%- endif %}
