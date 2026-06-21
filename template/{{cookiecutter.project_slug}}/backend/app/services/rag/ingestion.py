{%- if cookiecutter.enable_rag %}
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

from app.core.config import settings
from app.services.rag.documents import DocumentProcessor
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.models import IngestionResult, IngestionStatus, Document
from app.services.rag.vectorstore import BaseVectorStore
{%- if cookiecutter.use_milvus %}
from app.services.rag.vectorstore import MilvusVectorStore as VectorStore
{%- elif cookiecutter.use_qdrant %}
from app.services.rag.vectorstore import QdrantVectorStore as VectorStore
{%- elif cookiecutter.use_chromadb %}
from app.services.rag.vectorstore import ChromaVectorStore as VectorStore
{%- elif cookiecutter.use_pgvector %}
from app.services.rag.vectorstore import PgVectorStore as VectorStore
{%- endif %}

logger = logging.getLogger(__name__)


class IngestionService:
    """File → Parse/Chunk → Deduplicate → Embed/Store → Query-Ready."""

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
    ) -> "IngestionService":
        rag_settings = settings.rag
        embed_service = EmbeddingService(settings=rag_settings)
        vector_store = VectorStore(settings=rag_settings, embedding_service=embed_service)
        processor = DocumentProcessor(settings=rag_settings)
        return cls(processor=processor, vector_store=vector_store, on_event=on_event)

    async def _emit(self, event: str, data: dict[str, object]) -> None:
        if self._on_event:
            try:
                await self._on_event(event, data)
            except Exception as e:
                logger.warning("Webhook event dispatch failed: %s", e)

    async def _find_existing_by_source(
        self, collection_name: str, source_path: str
    ) -> str | None:
        try:
            docs = await self.store.get_documents(collection_name)
            for doc in docs:
                meta = doc.additional_info or {}
                if meta.get("source_path") == source_path:
                    return doc.document_id
                # Also check top-level metadata fields
                # (source_path is stored in metadata dict per chunk)
            for doc in docs:
                if doc.filename and doc.filename == Path(source_path).name:
                    return doc.document_id
        except Exception as exc:
            logger.warning("Could not check for existing document: %s", exc, exc_info=True)
        return None

    async def _find_existing_by_hash(
        self, collection_name: str, content_hash: str
    ) -> str | None:
        """Find an existing document by content hash (exact duplicate check)."""
        try:
            docs = await self.store.get_documents(collection_name)
            for doc in docs:
                meta = doc.additional_info or {}
                if meta.get("content_hash") == content_hash:
                    return doc.document_id
        except Exception as exc:
            logger.warning("Could not check for existing document: %s", exc, exc_info=True)
        return None

    async def ingest_file(
        self,
        filepath: Path,
        collection_name: str,
        replace: bool = True,
        source_path: str = "",
    ) -> IngestionResult:
        """`source_path` accepts URI schemes like gdrive://id or s3://bucket/key."""
        try:
            document: Document = await self.processor.process_file(filepath)

            if source_path:
                document.metadata.source_path = source_path
                document.metadata.filename = Path(source_path).name

            existing_id = None
            if replace:
                if document.metadata.source_path:
                    existing_id = await self._find_existing_by_source(
                        collection_name, document.metadata.source_path
                    )
                # Check by content hash when path lookup missed (exact duplicate detection)
                if not existing_id and document.metadata.content_hash:
                    existing_id = await self._find_existing_by_hash(
                        collection_name, document.metadata.content_hash
                    )

            if existing_id:
                await self.store.delete_document(collection_name, existing_id)
                logger.info("Replaced existing document %s for '%s'", existing_id, filepath.name)

            await self.store.insert_document(
                collection_name=collection_name,
                document=document,
            )

            action = "replaced" if existing_id else "ingested"

            await self._emit("rag.document.ingested", {
                "document_id": document.id,
                "filename": filepath.name,
                "collection": collection_name,
                "action": action,
                "chunks": len(document.chunked_pages or []),
                "source_path": document.metadata.source_path,
            })

            return IngestionResult(
                status=IngestionStatus.DONE,
                document_id=document.id,
                message=f"Successfully {action} '{filepath.name}'",
            )

        except Exception as e:
            logger.error("Ingestion error for %s: %s", filepath.name, e)
            return IngestionResult(
                status=IngestionStatus.ERROR,
                error_message=str(e),
                message=f"Failed to process {filepath.name}",
            )

    async def find_existing(self, collection_name: str, source_path: str) -> str | None:
        return await self._find_existing_by_source(collection_name, source_path)

    async def get_existing_hash(self, collection_name: str, source_path: str) -> str | None:
        try:
            docs = await self.store.get_documents(collection_name)
            doc_id: str | None = None
            content_hash: str | None = None
            for doc in docs:
                meta = doc.additional_info or {}
                if doc_id is None:
                    if meta.get("source_path") == source_path:
                        doc_id = doc.document_id
                        content_hash = meta.get("content_hash")
                        break
                    if doc.filename and doc.filename == Path(source_path).name:
                        doc_id = doc.document_id
                        content_hash = meta.get("content_hash")
            return content_hash
        except Exception as exc:
            logger.warning("Could not retrieve existing hash: %s", exc, exc_info=True)
        return None

    async def remove_document(self, collection_name: str, document_id: str) -> bool:
        """Wipes all traces of a document from the vector store."""
        try:
            await self.store.delete_document(
                collection_name=collection_name,
                document_id=document_id,
            )
            await self._emit("rag.document.deleted", {
                "document_id": document_id,
                "collection": collection_name,
            })
            return True
        except Exception as e:
            logger.error("Failed to delete document %s: %s", document_id, e)
            return False
{%- endif %}
