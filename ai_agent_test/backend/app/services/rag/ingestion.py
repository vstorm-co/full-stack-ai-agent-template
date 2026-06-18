from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

from app.services.rag.documents import DocumentProcessor
from app.services.rag.models import Document, IngestionResult, IngestionStatus
from app.services.rag.vectorstore import BaseVectorStore

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Orchestrates the data flow:
    File Path -> Parse/Chunk -> Deduplicate -> Embed/Store -> Query-Ready
    """

    def __init__(
        self,
        processor: DocumentProcessor,
        vector_store: BaseVectorStore,
        on_event: Callable[..., Awaitable[None]] | None = None,
    ):
        self.processor = processor
        self.store = vector_store
        self._on_event = on_event

    @classmethod
    def from_settings(
        cls,
        on_event: Callable[..., Awaitable[None]] | None = None,
    ) -> IngestionService:
        """Build an IngestionService using the application's RAG settings."""
        from app.core.config import settings
        from app.services.rag.embeddings import EmbeddingService
        from app.services.rag.vectorstore import MilvusVectorStore as VectorStore

        rag_settings = settings.rag
        embed_service = EmbeddingService(settings=rag_settings)
        vector_store = VectorStore(settings=rag_settings, embedding_service=embed_service)
        processor = DocumentProcessor(settings=rag_settings)
        return cls(processor=processor, vector_store=vector_store, on_event=on_event)

    async def _emit(self, event: str, data: dict[str, object]) -> None:
        """Emit a webhook event if callback is configured."""
        if self._on_event:
            try:
                await self._on_event(event, data)
            except Exception as e:
                logger.warning(f"Webhook event dispatch failed: {e}")

    async def _find_existing_by_source(self, collection_name: str, source_path: str) -> str | None:
        """Find an existing document by source_path.

        Returns the document_id if found, None otherwise.
        """
        try:
            docs = await self.store.get_documents(collection_name)
            for doc in docs:
                meta = doc.additional_info or {}
                if meta.get("source_path") == source_path:
                    return doc.document_id
                # Also check top-level metadata fields
                # (source_path is stored in metadata dict per chunk)
            # Fallback: check filename match
            for doc in docs:
                if doc.filename and doc.filename == Path(source_path).name:
                    return doc.document_id
        except Exception:
            pass
        return None

    async def _find_existing_by_hash(self, collection_name: str, content_hash: str) -> str | None:
        """Find an existing document by content hash (exact duplicate check)."""
        try:
            docs = await self.store.get_documents(collection_name)
            for doc in docs:
                meta = doc.additional_info or {}
                if meta.get("content_hash") == content_hash:
                    return doc.document_id
        except Exception:
            pass
        return None

    async def ingest_file(
        self,
        filepath: Path,
        collection_name: str,
        replace: bool = True,
        source_path: str = "",
    ) -> IngestionResult:
        """Processes a file and pushes it into the vector database.

        Args:
            filepath: Path to the file to process.
            collection_name: Target collection name.
            replace: If True, replace existing document with same source_path.
            source_path: Override source path (e.g., gdrive://id, s3://bucket/key).
        """
        try:
            # Processing (Parsing + Chunking)
            document: Document = await self.processor.process_file(filepath)

            # Set source_path override if provided (e.g., from GDrive/S3)
            if source_path:
                document.metadata.source_path = source_path
                document.metadata.filename = Path(source_path).name

            # Deduplication check
            existing_id = None
            if replace:
                # Check by source_path first
                if document.metadata.source_path:
                    existing_id = await self._find_existing_by_source(
                        collection_name, document.metadata.source_path
                    )
                # If not found by path, check by content hash (exact duplicate)
                if not existing_id and document.metadata.content_hash:
                    existing_id = await self._find_existing_by_hash(
                        collection_name, document.metadata.content_hash
                    )

            if existing_id:
                # Remove old version before inserting new
                await self.store.delete_document(collection_name, existing_id)
                logger.info(f"Replaced existing document {existing_id} for '{filepath.name}'")

            # Storage (Embedding + Insertion)
            await self.store.insert_document(
                collection_name=collection_name,
                document=document,
            )

            action = "replaced" if existing_id else "ingested"

            await self._emit(
                "rag.document.ingested",
                {
                    "document_id": document.id,
                    "filename": filepath.name,
                    "collection": collection_name,
                    "action": action,
                    "chunks": len(document.chunked_pages or []),
                    "source_path": document.metadata.source_path,
                },
            )

            return IngestionResult(
                status=IngestionStatus.DONE,
                document_id=document.id,
                message=f"Successfully {action} '{filepath.name}'",
            )

        except Exception as e:
            logger.error(f"Ingestion error for {filepath.name}: {e!s}")
            return IngestionResult(
                status=IngestionStatus.ERROR,
                error_message=str(e),
                message=f"Failed to process {filepath.name}",
            )

    async def find_existing(self, collection_name: str, source_path: str) -> str | None:
        """Check if a document with this source_path already exists. Returns document_id or None."""
        return await self._find_existing_by_source(collection_name, source_path)

    async def get_existing_hash(self, collection_name: str, source_path: str) -> str | None:
        """Get content_hash of existing document by source_path."""
        doc_id = await self._find_existing_by_source(collection_name, source_path)
        if not doc_id:
            return None
        try:
            docs = await self.store.get_documents(collection_name)
            for doc in docs:
                if doc.document_id == doc_id and doc.additional_info:
                    return doc.additional_info.get("content_hash")
        except Exception:
            pass
        return None

    async def remove_document(self, collection_name: str, document_id: str) -> bool:
        """Wipes all traces of a document from the vector store."""
        try:
            await self.store.delete_document(
                collection_name=collection_name,
                document_id=document_id,
            )
            await self._emit(
                "rag.document.deleted",
                {
                    "document_id": document_id,
                    "collection": collection_name,
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e!s}")
            return False
