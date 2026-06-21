import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from app.schemas.rag import RAGDocumentItem, RAGDocumentList
from app.services.rag.models import (
    CollectionInfo,
    Document,
    DocumentInfo,
    DocumentPageChunk,
    SearchResult,
)

logger = logging.getLogger(__name__)

_COLLECTION_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")
_RESERVED_COLLECTION_NAMES = frozenset({"all"})


class BaseVectorStore(ABC):
    @abstractmethod
    async def insert_document(self, collection_name: str, document: Document) -> None:
        pass

    @abstractmethod
    async def search(
        self, collection_name: str, query: str, limit: int = 4, filter_expr: str = ""
    ) -> list[SearchResult]:
        pass

    @abstractmethod
    async def delete_collection(self, collection_name: str) -> None:
        pass

    @abstractmethod
    async def delete_document(self, collection_name: str, document_id: str) -> None:
        pass

    @abstractmethod
    async def get_collection_info(self, collection_name: str) -> CollectionInfo:
        pass

    @abstractmethod
    async def list_collections(self) -> list[str]:
        pass

    @abstractmethod
    async def get_documents(self, collection_name: str) -> list[DocumentInfo]:
        pass

    async def get_document_list(self, collection_name: str) -> RAGDocumentList:
        docs = await self.get_documents(collection_name)
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
                for doc in docs
            ],
            total=len(docs),
        )

    async def create_collection(self, name: str) -> None:
        if not _COLLECTION_NAME_RE.match(name):
            raise ValueError(
                "Collection name must start with a letter and contain only "
                "letters, numbers, and underscores (max 64 chars)"
            )
        if name.lower() in _RESERVED_COLLECTION_NAMES:
            raise ValueError(f"'{name}' is a reserved collection name")
        await self._ensure_collection(name)

    def _build_chunk_metadata(
        self, chunk: "DocumentPageChunk", document: Document
    ) -> dict[str, Any]:
        # `document.metadata.model_dump()` is spread last so it can override per-chunk
        # defaults. `getattr` with defaults is used for optional image fields that may
        # not be present on all chunk types.
        meta = {
            "page_num": chunk.page_num,
            "chunk_num": chunk.chunk_num,
            "has_images": bool(getattr(chunk, "images", None)),
            "image_count": len(getattr(chunk, "images", [])),
            **document.metadata.model_dump(),
        }
        return meta

    def _sanitize_id(self, document_id: str) -> str:
        """Sanitize document_id to prevent filter injection."""
        return document_id.replace('"', "").replace("\\", "")

    def _group_documents(self, results: list[dict[str, Any]]) -> list[DocumentInfo]:
        # Iterates results twice: first to record the initial occurrence of each
        # parent_doc_id (capturing filename/filesize/filetype and merging source_path,
        # content_hash, and any extra dict into additional_info), then to increment
        # chunk_count for every row belonging to that document.
        doc_map: dict[str, dict[str, Any]] = {}
        for item in results:
            doc_id = item.get("parent_doc_id")
            metadata = item.get("metadata", {})
            if doc_id and doc_id not in doc_map:
                doc_map[doc_id] = {
                    "document_id": doc_id,
                    "filename": metadata.get("filename"),
                    "filesize": metadata.get("filesize"),
                    "filetype": metadata.get("filetype"),
                    "additional_info": {
                        "source_path": metadata.get("source_path", ""),
                        "content_hash": metadata.get("content_hash", ""),
                        **(metadata.get("additional_info") or {}),
                    },
                    "chunk_count": 0,
                }
            if doc_id:
                doc_map[doc_id]["chunk_count"] += 1
        return [
            DocumentInfo(
                document_id=d["document_id"],
                filename=d.get("filename"),
                filesize=d.get("filesize"),
                filetype=d.get("filetype"),
                chunk_count=d["chunk_count"],
                additional_info=d.get("additional_info"),
            )
            for d in doc_map.values()
        ]


from pymilvus import AsyncMilvusClient, DataType

from app.core.config import settings as app_settings
from app.services.rag.config import RAGSettings
from app.services.rag.embeddings import EmbeddingService


class MilvusVectorStore(BaseVectorStore):
    """Milvus vector store implementation."""

    def __init__(self, settings: RAGSettings, embedding_service: EmbeddingService):
        self.settings = settings
        self.embedder = embedding_service
        self.client = AsyncMilvusClient(
            uri=app_settings.MILVUS_URI, token=app_settings.MILVUS_TOKEN
        )

    async def _ensure_collection(self, name: str) -> None:
        if not await self.client.has_collection(name):
            schema = self.client.create_schema(auto_id=False)
            schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=100)
            schema.add_field("parent_doc_id", DataType.VARCHAR, max_length=100)
            schema.add_field("content", DataType.VARCHAR, max_length=65535)
            schema.add_field(
                "vector", DataType.FLOAT_VECTOR, dim=self.settings.embeddings_config.dim
            )
            schema.add_field("metadata", DataType.JSON)
            await self.client.create_collection(name, schema=schema, metric_type="COSINE")
        indexes = await self.client.list_indexes(name)
        if not indexes:
            index_params = self.client.prepare_index_params()
            index_params.add_index(
                field_name="vector", index_type="AUTOINDEX", metric_type="COSINE"
            )
            await self.client.create_index(collection_name=name, index_params=index_params)
        await self.client.load_collection(name)

    async def insert_document(self, collection_name: str, document: Document) -> None:
        await self._ensure_collection(collection_name)
        if not document.chunked_pages:
            raise ValueError("Document has no chunked pages.")
        vectors = self.embedder.embed_document(document)
        data = [
            {
                "id": chunk.chunk_id,
                "parent_doc_id": chunk.parent_doc_id,
                "content": chunk.chunk_content,
                "vector": vectors[i],
                "metadata": self._build_chunk_metadata(chunk, document),
            }
            for i, chunk in enumerate(document.chunked_pages)
        ]
        await self.client.insert(collection_name, data=data)

    async def search(
        self, collection_name: str, query: str, limit: int = 4, filter_expr: str = ""
    ) -> list[SearchResult]:
        query_vector = self.embedder.embed_query(query)
        results = await self.client.search(
            collection_name=collection_name,
            data=[query_vector],
            limit=limit,
            filter=filter_expr,
            output_fields=["content", "parent_doc_id", "metadata"],
        )
        return [
            SearchResult(
                content=hit["entity"]["content"],
                score=hit["distance"],
                metadata=hit["entity"]["metadata"],
                parent_doc_id=hit["entity"]["parent_doc_id"],
            )
            for hit in results[0]
        ]

    async def get_collection_info(self, collection_name: str) -> CollectionInfo:
        # A KB created on /kb or /rag has no Milvus collection until its first
        # document is ingested — report zero vectors instead of erroring so the
        # collection still renders consistently across /kb and /rag.
        if not await self.client.has_collection(collection_name):
            return CollectionInfo(
                name=collection_name,
                total_vectors=0,
                dim=self.settings.embeddings_config.dim,
            )
        count = await self.client.get_collection_stats(collection_name)
        return CollectionInfo(
            name=collection_name,
            total_vectors=count.get("row_count", 0),
            dim=self.settings.embeddings_config.dim,
        )

    async def delete_collection(self, collection_name: str) -> None:
        await self.client.drop_collection(collection_name)

    async def delete_document(self, collection_name: str, document_id: str) -> None:
        sanitized = self._sanitize_id(document_id)
        await self.client.delete(
            collection_name=collection_name, filter=f'parent_doc_id == "{sanitized}"'
        )

    async def get_documents(self, collection_name: str) -> list[DocumentInfo]:
        # Return empty list for non-existent collections instead of silently
        # creating them, which would be inconsistent with get_collection_info.
        if not await self.client.has_collection(collection_name):
            return []
        results = await self.client.query(
            collection_name=collection_name,
            filter="",
            output_fields=["parent_doc_id", "metadata"],
            limit=10000,
        )
        return self._group_documents(results)

    async def list_collections(self) -> list[str]:
        result: list[str] = await self.client.list_collections()
        return result
