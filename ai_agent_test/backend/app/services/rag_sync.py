"""RAG sync service (PostgreSQL async).

Contains business logic for managing RAG synchronization operations
and their associated log entries.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.sync_log import SyncLog
from app.repositories import sync_log_repo
from app.schemas.rag import RAGSyncLogItem, RAGSyncLogList


class RAGSyncService:
    """Service for RAG sync operation management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_sync_logs(
        self,
        collection_name: str | None = None,
        limit: int = 20,
    ) -> RAGSyncLogList:
        """List sync operation logs, optionally filtered by collection."""
        logs = await sync_log_repo.get_all(self.db, collection_name=collection_name, limit=limit)
        return RAGSyncLogList(
            items=[
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
                    started_at=log.started_at.isoformat() if log.started_at else None,
                    completed_at=log.completed_at.isoformat() if log.completed_at else None,
                )
                for log in logs
            ],
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
        from app.worker.tasks.rag_tasks import sync_collection_task

        sync_collection_task.delay(
            sync_log_id=str(sync_log.id),
            source="local",
            collection_name=collection_name,
            mode=mode,
            path=path,
        )
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
            ValueError: If sync is not in 'running' state.
        """
        log = await self.get_sync_log(sync_id)
        if log.status != "running":
            raise ValueError("Sync is not running")
        cancelled = await sync_log_repo.update_status(
            self.db,
            log.id,
            status="cancelled",
            completed_at=datetime.now(UTC),
        )
        if cancelled is None:
            raise NotFoundError(message="Sync log not found", details={"sync_id": sync_id})
        return cancelled
