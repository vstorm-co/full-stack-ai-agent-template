{%- if cookiecutter.enable_rag and cookiecutter.use_postgresql %}
"""RAG document service (PostgreSQL async).

Contains business logic for tracking RAG document ingestion, status updates,
file downloads, and cascading deletions across DB, vector store, and file storage.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.rag_document import RAGDocument
from app.repositories import rag_document_repo
from app.schemas.rag import RAGTrackedDocumentItem, RAGTrackedDocumentList
from app.services.file_storage import get_file_storage


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
                await ingestion_service.remove_document(
                    doc.collection_name, doc.vector_document_id
                )
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


{%- elif cookiecutter.enable_rag and cookiecutter.use_sqlite %}
"""RAG document service (SQLite sync).

Contains business logic for tracking RAG document ingestion, status updates,
file downloads, and cascading deletions across DB, vector store, and file storage.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models.rag_document import RAGDocument
from app.repositories import rag_document_repo
from app.schemas.rag import RAGTrackedDocumentItem, RAGTrackedDocumentList
from app.services.file_storage import get_file_storage


logger = logging.getLogger(__name__)


class RAGDocumentService:
    """Service for RAG document tracking and lifecycle management."""

    def __init__(self, db: Session):
        self.db = db

    def list_documents(
        self,
        collection_name: str | None = None,
    ) -> RAGTrackedDocumentList:
        """List tracked RAG documents, optionally filtered by collection."""
        docs = rag_document_repo.get_all(self.db, collection_name)
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

    def get_document(self, doc_id: str) -> RAGDocument:
        """Get a RAG document by ID.

        Raises:
            NotFoundError: If document does not exist.
        """
        doc = rag_document_repo.get_by_id(self.db, doc_id)
        if not doc:
            raise NotFoundError(
                message="Document not found",
                details={"doc_id": doc_id},
            )
        return doc

    def create_document(
        self,
        *,
        collection_name: str,
        filename: str,
        filesize: int,
        filetype: str,
        storage_path: str | None = None,
    ) -> RAGDocument:
        """Create a new RAG document tracking record."""
        return rag_document_repo.create(
            self.db,
            collection_name=collection_name,
            filename=filename,
            filesize=filesize,
            filetype=filetype,
            storage_path=storage_path or "",
        )

    def complete_ingestion(
        self,
        doc_id: str,
        vector_document_id: str,
        chunk_count: int = 0,
    ) -> None:
        """Mark a document as successfully ingested."""
        doc = self.get_document(doc_id)
        rag_document_repo.update_status(
            self.db,
            doc.id,
            status="done",
            vector_document_id=vector_document_id,
            chunk_count=chunk_count,
            completed_at=datetime.now(UTC),
        )

    def fail_ingestion(self, doc_id: str, error_message: str) -> None:
        """Mark a document ingestion as failed."""
        doc = self.get_document(doc_id)
        rag_document_repo.update_status(
            self.db,
            doc.id,
            status="error",
            error_message=error_message,
            completed_at=datetime.now(UTC),
        )

    def retry_ingestion(self, doc_id: str) -> RAGDocument:
        """Reset a failed document for re-ingestion.

        Raises:
            NotFoundError: If document does not exist.
            ValueError: If document status is not 'error'.
        """
        doc = self.get_document(doc_id)
        if doc.status != "error":
            raise ValueError("Only failed documents can be retried")
        updated = rag_document_repo.update_status(
            self.db,
            doc.id,
            status="processing",
            error_message="",
            completed_at=None,
        )
        if updated is None:
            raise NotFoundError(message="Document not found", details={"doc_id": doc_id})
        return updated

    def delete_document(
        self,
        doc_id: str,
        ingestion_service: Any = None,
    ) -> None:
        """Delete a document with cascading cleanup.

        Removes the record from the database and attempts to clean up
        the vector store entry and stored file. Failures in cleanup
        are logged but do not prevent the DB deletion.
        """
        doc = self.get_document(doc_id)

        # Cascade: vector store
        if doc.vector_document_id and ingestion_service:
            try:
                ingestion_service.remove_document(
                    doc.collection_name, doc.vector_document_id
                )
            except Exception as e:
                logger.warning(f"Failed to delete from vector store: {e}")

        # Cascade: file storage
        if doc.storage_path:
            try:
                storage = get_file_storage()
                storage.delete(doc.storage_path)
            except Exception as e:
                logger.warning(f"Failed to delete file: {e}")

        # Cascade: DB record
        rag_document_repo.delete(self.db, doc.id)

    def delete_by_collection(self, collection_name: str) -> int:
        """Delete all RAG document records for a collection.

        Returns:
            Number of deleted records.
        """
        return rag_document_repo.delete_by_collection(self.db, collection_name)

    def get_download_info(self, doc_id: str) -> tuple[str, str, str]:
        """Get file download information for a document.

        Returns:
            Tuple of (file_path, filename, mime_type).

        Raises:
            NotFoundError: If document or its file does not exist.
        """
        doc = self.get_document(doc_id)
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


{%- else %}
"""RAG document service - not configured."""
{%- endif %}
