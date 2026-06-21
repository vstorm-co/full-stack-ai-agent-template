import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from app.services.rag.models import CollectionInfo, Document, DocumentPageChunk, SearchResult, DocumentInfo
from app.schemas.rag import RAGDocumentItem, RAGDocumentList

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

    def _build_chunk_metadata(self, chunk: "DocumentPageChunk", document: Document) -> dict[str, Any]:
        # `document.metadata.model_dump()` is spread last so it can override per-chunk
        # defaults. `getattr` with defaults is used for optional image fields that may
        # not be present on all chunk types.
        meta = {
            "page_num": chunk.page_num,
            "chunk_num": chunk.chunk_num,
{%- if cookiecutter.enable_rag_image_description %}
            "has_images": bool(getattr(chunk, "images", None)),
            "image_count": len(getattr(chunk, "images", [])),
{%- endif %}
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


{%- if cookiecutter.use_milvus %}
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
            index_params.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE")
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

    async def search(self, collection_name: str, query: str, limit: int = 4, filter_expr: str = "") -> list[SearchResult]:
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
        return CollectionInfo(name=collection_name, total_vectors=count.get("row_count", 0), dim=self.settings.embeddings_config.dim)

    async def delete_collection(self, collection_name: str) -> None:
        await self.client.drop_collection(collection_name)

    async def delete_document(self, collection_name: str, document_id: str) -> None:
        sanitized = self._sanitize_id(document_id)
        await self.client.delete(collection_name=collection_name, filter=f'parent_doc_id == "{sanitized}"')

    async def get_documents(self, collection_name: str) -> list[DocumentInfo]:
        # Return empty list for non-existent collections instead of silently
        # creating them, which would be inconsistent with get_collection_info.
        if not await self.client.has_collection(collection_name):
            return []
        results = await self.client.query(collection_name=collection_name, filter="", output_fields=["parent_doc_id", "metadata"], limit=10000)
        return self._group_documents(results)

    async def list_collections(self) -> list[str]:
        result: list[str] = await self.client.list_collections()
        return result
{%- endif %}


{%- if cookiecutter.use_qdrant %}
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, FilterSelector, PointStruct, VectorParams, Filter, FieldCondition, MatchValue

from app.core.config import settings as app_settings
from app.services.rag.config import RAGSettings
from app.services.rag.embeddings import EmbeddingService


class QdrantVectorStore(BaseVectorStore):
    """Qdrant vector store implementation."""

    def __init__(self, settings: RAGSettings, embedding_service: EmbeddingService):
        self.settings = settings
        self.embedder = embedding_service
        self.client = AsyncQdrantClient(
            host=app_settings.QDRANT_HOST,
            port=app_settings.QDRANT_PORT,
            # QDRANT_API_KEY is str | None; pass directly without `or None`
            # to avoid silently coercing empty strings to None.
            api_key=app_settings.QDRANT_API_KEY,
        )

    async def _ensure_collection(self, name: str) -> None:
        collections = await self.client.get_collections()
        if name not in [c.name for c in collections.collections]:
            await self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=self.settings.embeddings_config.dim,
                    distance=Distance.COSINE,
                ),
            )

    async def insert_document(self, collection_name: str, document: Document) -> None:
        await self._ensure_collection(collection_name)
        if not document.chunked_pages:
            raise ValueError("Document has no chunked pages.")
        vectors = self.embedder.embed_document(document)
        points = [
            PointStruct(
                id=chunk.chunk_id,
                vector=vectors[i],
                payload={
                    "content": chunk.chunk_content,
                    "parent_doc_id": chunk.parent_doc_id,
                    "metadata": self._build_chunk_metadata(chunk, document),
                },
            )
            for i, chunk in enumerate(document.chunked_pages)
        ]
        await self.client.upsert(collection_name=collection_name, points=points)

    async def search(self, collection_name: str, query: str, limit: int = 4, filter_expr: str = "") -> list[SearchResult]:
        query_vector = self.embedder.embed_query(query)
        qdrant_filter = None
        if filter_expr and "parent_doc_id" in filter_expr:
            m = re.search(r'parent_doc_id\s*==\s*"([^"]+)"', filter_expr)
            if m:
                qdrant_filter = Filter(must=[FieldCondition(key="parent_doc_id", match=MatchValue(value=m.group(1)))])
        results = await self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=qdrant_filter,
        )
        return [
            SearchResult(
                content=hit.payload.get("content", ""),
                score=hit.score,
                metadata=hit.payload.get("metadata", {}),
                parent_doc_id=hit.payload.get("parent_doc_id"),
            )
            for hit in results
        ]

    async def get_collection_info(self, collection_name: str) -> CollectionInfo:
        info = await self.client.get_collection(collection_name)
        return CollectionInfo(
            name=collection_name,
            total_vectors=info.points_count or 0,
            dim=self.settings.embeddings_config.dim,
        )

    async def delete_collection(self, collection_name: str) -> None:
        await self.client.delete_collection(collection_name)

    async def delete_document(self, collection_name: str, document_id: str) -> None:
        sanitized = self._sanitize_id(document_id)
        await self.client.delete(
            collection_name=collection_name,
            points_selector=FilterSelector(filter=Filter(
                must=[FieldCondition(key="parent_doc_id", match=MatchValue(value=sanitized))]
            )),
        )

    async def get_documents(self, collection_name: str) -> list[DocumentInfo]:
        await self._ensure_collection(collection_name)
        records, _ = await self.client.scroll(collection_name=collection_name, limit=10000, with_payload=True)
        results = [
            {"parent_doc_id": r.payload.get("parent_doc_id"), "metadata": r.payload.get("metadata", {})}
            for r in records
        ]
        return self._group_documents(results)

    async def list_collections(self) -> list[str]:
        collections = await self.client.get_collections()
        return [c.name for c in collections.collections]
{%- endif %}


{%- if cookiecutter.use_chromadb %}
import asyncio
import chromadb

from app.core.config import settings as app_settings
from app.services.rag.config import RAGSettings
from app.services.rag.embeddings import EmbeddingService


class ChromaVectorStore(BaseVectorStore):
    """ChromaDB vector store implementation (embedded or HTTP client).

    All ChromaDB calls are synchronous, so we use asyncio.to_thread()
    to avoid blocking the FastAPI event loop.
    """

    def __init__(self, settings: RAGSettings, embedding_service: EmbeddingService):
        self.settings = settings
        self.embedder = embedding_service
        if app_settings.CHROMA_HOST:
            self.client = chromadb.HttpClient(
                host=app_settings.CHROMA_HOST,
                port=app_settings.CHROMA_PORT,
            )
        else:
            self.client = chromadb.PersistentClient(path=app_settings.CHROMA_PERSIST_DIR)

    def _get_collection(self, name: str) -> Any:
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    async def _ensure_collection(self, name: str) -> None:
        """Ensure collection exists (ChromaDB creates on access)."""
        await asyncio.to_thread(self._get_collection, name)

    async def insert_document(self, collection_name: str, document: Document) -> None:
        if not document.chunked_pages:
            raise ValueError("Document has no chunked pages.")

        vectors = self.embedder.embed_document(document)
        ids = [chunk.chunk_id for chunk in document.chunked_pages]
        documents = [chunk.chunk_content for chunk in document.chunked_pages]
        metadatas = [self._build_chunk_metadata(chunk, document) for chunk in document.chunked_pages]

        def _upsert():
            collection = self._get_collection(collection_name)
            collection.upsert(ids=ids, embeddings=vectors, documents=documents, metadatas=metadatas)

        await asyncio.to_thread(_upsert)

    async def search(self, collection_name: str, query: str, limit: int = 4, filter_expr: str = "") -> list[SearchResult]:
        query_vector = self.embedder.embed_query(query)

        def _query():
            collection = self._get_collection(collection_name)
            kwargs: dict[str, Any] = {
                "query_embeddings": [query_vector],
                "n_results": limit,
                "include": ["documents", "metadatas", "distances"],
            }
            # Convert Milvus-style filter to ChromaDB where clause
            if filter_expr and "parent_doc_id" in filter_expr:
                m = re.search(r'parent_doc_id\s*==\s*"([^"]+)"', filter_expr)
                if m:
                    kwargs["where"] = {"parent_doc_id": m.group(1)}
            return collection.query(**kwargs)

        results = await asyncio.to_thread(_query)
        search_results = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                search_results.append(SearchResult(
                    content=results["documents"][0][i] if results["documents"] else "",
                    score=1.0 - (results["distances"][0][i] if results["distances"] else 0.0),
                    metadata=metadata,
                    parent_doc_id=metadata.get("parent_doc_id"),
                ))
        return search_results

    async def get_collection_info(self, collection_name: str) -> CollectionInfo:
        def _info():
            collection = self._get_collection(collection_name)
            return collection.count()

        count = await asyncio.to_thread(_info)
        return CollectionInfo(name=collection_name, total_vectors=count, dim=self.settings.embeddings_config.dim)

    async def delete_collection(self, collection_name: str) -> None:
        await asyncio.to_thread(self.client.delete_collection, collection_name)

    async def delete_document(self, collection_name: str, document_id: str) -> None:
        sanitized = self._sanitize_id(document_id)

        def _delete():
            collection = self._get_collection(collection_name)
            collection.delete(where={"parent_doc_id": sanitized})

        await asyncio.to_thread(_delete)

    async def get_documents(self, collection_name: str) -> list[DocumentInfo]:
        def _get():
            collection = self._get_collection(collection_name)
            return collection.get(include=["metadatas"])

        all_data = await asyncio.to_thread(_get)
        results = [
            {"parent_doc_id": m.get("parent_doc_id"), "metadata": m}
            for m in (all_data["metadatas"] or [])
        ]
        return self._group_documents(results)

    async def list_collections(self) -> list[str]:
        def _list():
            return [c.name for c in self.client.list_collections()]

        return await asyncio.to_thread(_list)
{%- endif %}


{%- if cookiecutter.use_pgvector %}
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings as app_settings
from app.services.rag.config import RAGSettings
from app.services.rag.embeddings import EmbeddingService


def _validate_collection_name(name: str) -> str:
    """Validate collection name to prevent SQL injection."""
    if not re.match(r"^[a-zA-Z0-9_]+$", name):
        raise ValueError(f"Invalid collection name: {name}. Only alphanumeric and underscores allowed.")
    return name


class PgVectorStore(BaseVectorStore):
    """PostgreSQL + pgvector implementation.

    Uses the existing PostgreSQL database with pgvector extension.
    No additional Docker services needed.

    NOTE: This class creates its own SQLAlchemy engine per instance. In
    production, prefer injecting a shared engine from app.db.session to
    avoid multiple connection pools. Call `await self.aclose()` on shutdown
    to release pool connections.
    """

    def __init__(self, settings: RAGSettings, embedding_service: EmbeddingService):
        self.settings = settings
        self.embedder = embedding_service
        self.dim = settings.embeddings_config.dim
        self.engine = create_async_engine(app_settings.DATABASE_URL, echo=False)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def aclose(self) -> None:
        """Dispose the connection pool. Call during application shutdown."""
        await self.engine.dispose()

    def _table(self, name: str) -> str:
        """Get validated table name for a collection."""
        return f"rag_{_validate_collection_name(name)}"

    async def _ensure_collection(self, name: str) -> None:
        """Create table for collection if not exists."""
        table = self._table(name)
        async with self.async_session() as session:
            await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await session.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id VARCHAR(100) PRIMARY KEY,
                    parent_doc_id VARCHAR(100),
                    content TEXT,
                    embedding vector({self.dim}),
                    metadata JSONB DEFAULT '{% raw %}{{}}{% endraw %}'::jsonb
                )
            """))
            await session.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {table}_embedding_idx
                ON {table} USING hnsw (embedding vector_cosine_ops)
            """))
            await session.commit()

    async def _collection_exists(self, name: str) -> bool:
        """Return True if the backing table for a collection exists."""
        table = self._table(name)
        async with self.async_session() as session:
            result = await session.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = :table AND table_schema = 'public'"
                ),
                {"table": table},
            )
            return result.scalar() is not None

    async def insert_document(self, collection_name: str, document: Document) -> None:
        table = self._table(collection_name)
        await self._ensure_collection(collection_name)
        if not document.chunked_pages:
            raise ValueError("Document has no chunked pages.")
        vectors = self.embedder.embed_document(document)
        async with self.async_session() as session:
            for i, chunk in enumerate(document.chunked_pages):
                meta = self._build_chunk_metadata(chunk, document)
                await session.execute(
                    text(f"""
                        INSERT INTO {table} (id, parent_doc_id, content, embedding, metadata)
                        VALUES (:id, :parent_doc_id, :content, :embedding, :metadata)
                        ON CONFLICT (id) DO UPDATE SET content = :content, embedding = :embedding, metadata = :metadata
                    """),
                    {
                        "id": chunk.chunk_id,
                        "parent_doc_id": chunk.parent_doc_id,
                        "content": chunk.chunk_content,
                        "embedding": str(vectors[i]),
                        "metadata": json.dumps(meta),
                    },
                )
            await session.commit()

    async def search(self, collection_name: str, query: str, limit: int = 4, filter_expr: str = "") -> list[SearchResult]:
        table = self._table(collection_name)
        query_vector = self.embedder.embed_query(query)

        # Parse the shared `parent_doc_id == "<value>"` filter format and apply
        # it as a parameterised WHERE clause to avoid returning results from
        # unrelated documents (same behaviour as Qdrant/Chroma implementations).
        doc_id_filter: str | None = None
        if filter_expr and "parent_doc_id" in filter_expr:
            m = re.search(r'parent_doc_id\s*==\s*"([^"]+)"', filter_expr)
            if m:
                doc_id_filter = m.group(1)

        where_clause = "WHERE parent_doc_id = :doc_id" if doc_id_filter else ""
        params: dict[str, Any] = {"query_vec": str(query_vector), "limit": limit}
        if doc_id_filter:
            params["doc_id"] = doc_id_filter

        async with self.async_session() as session:
            result = await session.execute(
                text(f"""
                    SELECT content, parent_doc_id, metadata,
                           1 - (embedding <=> :query_vec) AS score
                    FROM {table}
                    {where_clause}
                    ORDER BY embedding <=> :query_vec
                    LIMIT :limit
                """),
                params,
            )
            rows = result.fetchall()
        return [
            SearchResult(
                content=row[0],
                score=float(row[3]),
                metadata=row[2] if isinstance(row[2], dict) else json.loads(row[2]),
                parent_doc_id=row[1],
            )
            for row in rows
        ]

    async def get_collection_info(self, collection_name: str) -> CollectionInfo:
        table = self._table(collection_name)
        async with self.async_session() as session:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar() or 0
        return CollectionInfo(name=collection_name, total_vectors=count, dim=self.dim)

    async def delete_collection(self, collection_name: str) -> None:
        table = self._table(collection_name)
        async with self.async_session() as session:
            await session.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await session.commit()

    async def delete_document(self, collection_name: str, document_id: str) -> None:
        table = self._table(collection_name)
        sanitized = self._sanitize_id(document_id)
        async with self.async_session() as session:
            await session.execute(
                text(f"DELETE FROM {table} WHERE parent_doc_id = :doc_id"),
                {"doc_id": sanitized},
            )
            await session.commit()

    async def get_documents(self, collection_name: str) -> list[DocumentInfo]:
        # Return an empty list for non-existent collections instead of silently
        # creating them via _ensure_collection, which is inconsistent with
        # get_collection_info (which already handles the missing case gracefully).
        if not await self._collection_exists(collection_name):
            return []
        table = self._table(collection_name)
        async with self.async_session() as session:
            result = await session.execute(
                text(f"SELECT parent_doc_id, metadata FROM {table}")
            )
            rows = result.fetchall()
        results = [
            {"parent_doc_id": row[0], "metadata": row[1] if isinstance(row[1], dict) else json.loads(row[1])}
            for row in rows
        ]
        return self._group_documents(results)

    async def list_collections(self) -> list[str]:
        async with self.async_session() as session:
            result = await session.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'rag_%' AND table_schema = 'public'")
            )
            # removeprefix (Python 3.9+) strips only the leading "rag_" occurrence,
            # unlike str.replace which would also hit inner occurrences.
            return [row[0].removeprefix("rag_") for row in result.fetchall()]
{%- endif %}
