"""RAG document service (PostgreSQL async).

Contains business logic for tracking RAG document ingestion, status updates,
file downloads, cascading deletions across DB+vector store+file storage, and
upload-and-dispatch orchestration for the Celery/Taskiq/ARQ worker.
"""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.rag_document import RAGDocument
from app.repositories import rag_document_repo
from app.schemas.rag import RAGIngestResponse, RAGTrackedDocumentItem, RAGTrackedDocumentList
from app.services.file_storage import get_file_storage
from app.services.rag.config import get_supported_formats

logger = logging.getLogger(__name__)


class RAGDocumentService:
    """Service for RAG document tracking and lifecycle management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_documents(
        self,
        collection_name: str | None = None,
    ) -> RAGTrackedDocumentList:
        """List tracked RAG documents, optionally filtered by collection."""
        docs = await rag_document_repo.get_all(self.db, collection_name)
        return RAGTrackedDocumentList(
            items=[
                RAGTrackedDocumentItem(
                    id=str(d.id),
                    collection_name=d.collection_name,
                    filename=d.filename,
                    filesize=d.filesize,
                    filetype=d.filetype,
                    status=d.status,
                    error_message=d.error_message,
                    vector_document_id=d.vector_document_id,
                    chunk_count=d.chunk_count,
                    has_file=bool(d.storage_path),
                    created_at=d.created_at.isoformat() if d.created_at else None,
                    completed_at=d.completed_at.isoformat() if d.completed_at else None,
                )
                for d in docs
            ],
            total=len(docs),
        )

    async def get_document(self, doc_id: str) -> RAGDocument:
        """Get a RAG document by ID.

        Raises:
            NotFoundError: If document does not exist.
        """
        doc = await rag_document_repo.get_by_id(self.db, UUID(doc_id))
        if not doc:
            raise NotFoundError(
                message="Document not found",
                details={"doc_id": doc_id},
            )
        return doc

    async def create_document(
        self,
        *,
        collection_name: str,
        filename: str,
        filesize: int,
        filetype: str,
        storage_path: str | None = None,
    ) -> RAGDocument:
        """Create a new RAG document tracking record."""
        return await rag_document_repo.create(
            self.db,
            collection_name=collection_name,
            filename=filename,
            filesize=filesize,
            filetype=filetype,
            storage_path=storage_path or "",
        )

    async def dispatch_upload(
        self,
        *,
        collection_name: str,
        file_data: bytes,
        filename: str,
        replace: bool,
        vector_store: Any,
    ) -> RAGIngestResponse:
        """Validate, persist, and queue an uploaded file for ingestion.

        Performs:
          1. file-extension and size validation (against ``settings``);
          2. permanent storage via ``FileStorage``;
          3. RAGDocument tracking-record creation;
          4. lazy creation of the target vector collection;
          5. tmp-copy under ``MEDIA_DIR/_rag_tmp`` (shared with worker container);
          6. dispatch of the ingestion task on the configured task backend.
        """
        allowed = get_supported_formats(getattr(settings, "PDF_PARSER", "pymupdf"))
        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        ext = Path(filename).suffix.lower()
        if ext not in allowed:
            raise BadRequestError(
                message=f"File type '{ext}' not supported",
                details={"ext": ext, "allowed": sorted(allowed)},
            )
        if len(file_data) > max_size:
            raise BadRequestError(
                message=f"File too large. Maximum {settings.MAX_UPLOAD_SIZE_MB}MB.",
                details={"size": len(file_data), "max_mb": settings.MAX_UPLOAD_SIZE_MB},
            )

        storage = get_file_storage()
        storage_path = await storage.save(f"rag/{collection_name}", filename, file_data)
        rag_doc = await self.create_document(
            collection_name=collection_name,
            filename=filename,
            filesize=len(file_data),
            filetype=ext.lstrip("."),
            storage_path=storage_path,
        )
        doc_id = rag_doc.id

        # Ensure the target collection exists before the worker starts
        await vector_store.create_collection(collection_name)

        # Stage the upload in the volume shared with the worker container
        tmp_dir = os.path.join(str(settings.MEDIA_DIR), "_rag_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = os.path.join(tmp_dir, f"{doc_id!s}{ext}")
        with open(tmp_path, "wb") as f:
            f.write(file_data)
        from app.worker.tasks.rag_tasks import ingest_document_task

        ingest_document_task.delay(
            rag_document_id=str(doc_id),
            collection_name=collection_name,
            filepath=tmp_path,
            source_path=filename,
            replace=replace,
        )

        return RAGIngestResponse(
            id=str(doc_id),
            status="processing",
            filename=filename,
            collection=collection_name,
            message="File accepted. Processing in background.",
        )

    async def complete_ingestion(
        self,
        doc_id: str,
        vector_document_id: str,
        chunk_count: int = 0,
    ) -> None:
        """Mark a document as successfully ingested."""
        doc = await self.get_document(doc_id)
        await rag_document_repo.update_status(
            self.db,
            doc.id,
            status="done",
            vector_document_id=vector_document_id,
            chunk_count=chunk_count,
            completed_at=datetime.now(UTC),
        )

    async def fail_ingestion(self, doc_id: str, error_message: str) -> None:
        """Mark a document ingestion as failed."""
        doc = await self.get_document(doc_id)
        await rag_document_repo.update_status(
            self.db,
            doc.id,
            status="error",
            error_message=error_message,
            completed_at=datetime.now(UTC),
        )

    async def retry_ingestion(self, doc_id: str) -> RAGDocument:
        """Reset a failed document for re-ingestion.

        Raises:
            NotFoundError: If document does not exist.
            ValueError: If document status is not 'error'.
        """
        doc = await self.get_document(doc_id)
        if doc.status != "error":
            raise ValueError("Only failed documents can be retried")
        updated = await rag_document_repo.update_status(
            self.db,
            doc.id,
            status="processing",
            error_message="",
            completed_at=None,
        )
        if updated is None:
            raise NotFoundError(message="Document not found", details={"doc_id": doc_id})
        return updated

    async def delete_document(
        self,
        doc_id: str,
        ingestion_service: Any = None,
    ) -> None:
        """Delete a document with cascading cleanup.

        Removes the record from the database and attempts to clean up
        the vector store entry and stored file. Failures in cleanup
        are logged but do not prevent the DB deletion.
        """
        doc = await self.get_document(doc_id)

        # Cascade: vector store
        if doc.vector_document_id and ingestion_service:
            try:
                await ingestion_service.remove_document(doc.collection_name, doc.vector_document_id)
            except Exception as e:
                logger.warning(f"Failed to delete from vector store: {e}")

        # Cascade: file storage
        if doc.storage_path:
            try:
                storage = get_file_storage()
                await storage.delete(doc.storage_path)
            except Exception as e:
                logger.warning(f"Failed to delete file: {e}")

        # Cascade: DB record
        await rag_document_repo.delete(self.db, doc.id)

    async def delete_by_collection(self, collection_name: str) -> int:
        """Delete all RAG document records for a collection.

        Returns:
            Number of deleted records.
        """
        return await rag_document_repo.delete_by_collection(self.db, collection_name)

    async def get_download_info(self, doc_id: str) -> tuple[str, str, str]:
        """Get file download information for a document.

        Returns:
            Tuple of (file_path, filename, mime_type).

        Raises:
            NotFoundError: If document or its file does not exist.
        """
        doc = await self.get_document(doc_id)
        if not doc.storage_path:
            raise NotFoundError(message="No file stored for this document")

        storage = get_file_storage()
        file_path = storage.get_full_path(doc.storage_path)
        if not file_path:
            raise NotFoundError(message="File not found on disk")

        mime_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
            "md": "text/markdown",
        }
        mime_type = mime_map.get(doc.filetype, "application/octet-stream")
        return str(file_path), doc.filename, mime_type
