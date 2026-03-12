from abc import ABC, abstractmethod

from app.rag.models import CollectionInfo, Document, SearchResult, DocumentInfo


class BaseVectorStore(ABC):
    """Abstract base class for vector store implementations.

    Defines the interface that all vector store providers must implement.
    """

    @abstractmethod
    async def insert_document(self, collection_name: str, document: Document) -> None:
        """Embeds and stores document chunks.

        Args:
            collection_name: Name of the collection to insert into.
            document: Document object containing chunked pages to embed and store.
        """
        pass

    @abstractmethod
    async def search(
        self, collection_name: str, query: str, limit: int = 4, filter: str = ""
    ) -> list[SearchResult]:
        """Retrieves similar chunks based on a text query.

        Args:
            collection_name: Name of the collection to search in.
            query: The text query to search for.
            limit: Maximum number of results to return.
            filter: Optional filter expression for the search.

        Returns:
            List of search results sorted by relevance.
        """
        pass

    @abstractmethod
    async def delete_collection(self, collection_name: str) -> None:
        """Removes a collection and all its data.

        Args:
            collection_name: Name of the collection to delete.
        """
        pass

    @abstractmethod
    async def delete_document(self, collection_name: str, document_id: str) -> None:
        """Removes all chunks associated with a document ID.

        Args:
            collection_name: Name of the collection containing the document.
            document_id: ID of the document to remove.
        """
        pass

    @abstractmethod
    async def get_collection_info(self, collection_name: str) -> CollectionInfo:
        """Returns metadata and stats about a collection.

        Args:
            collection_name: Name of the collection to get info for.

        Returns:
            CollectionInfo object with collection metadata.
        """
        pass

    @abstractmethod
    async def list_collections(self) -> list[str]:
        """Returns list of all collection names.

        Returns:
            List of collection names as strings.
        """
        pass

    @abstractmethod
    async def get_documents(self, collection_name: str) -> list[DocumentInfo]:
        """Returns list of unique documents in a collection.

        Args:
            collection_name: Name of the collection to get documents from.

        Returns:
            List of DocumentInfo objects with document metadata.
        """
        pass


from pymilvus import AsyncMilvusClient, DataType

from app.core.config import settings as app_settings
from app.rag.config import RAGSettings
from app.rag.embeddings import EmbeddingService


class MilvusVectorStore(BaseVectorStore):
    """Milvus vector store implementation.

    Provides vector storage and retrieval capabilities using Milvus.
    Handles document embedding, storage, and similarity search.
    """

    def __init__(self, settings: RAGSettings, embedding_service: EmbeddingService):
        """Initialize the Milvus vector store.

        Args:
            settings: RAG configuration settings.
            embedding_service: Service for generating text embeddings.
        """
        self.settings = settings
        self.embedder = embedding_service
        self.client = AsyncMilvusClient(
            uri=app_settings.MILVUS_URI, token=app_settings.MILVUS_TOKEN
        )

    async def _ensure_collection(self, name: str):
        """Ensure a collection exists, creating it if necessary.

        Args:
            name: Name of the collection to ensure exists.
        """
        # Create collection if it doesn't exist
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
            
        # Check and create index if missing
        # load_collection will fail without an index
        indexes = await self.client.list_indexes(name)
        if not indexes:
            index_params = self.client.prepare_index_params()
            index_params.add_index(
                field_name="vector",
                index_type="AUTOINDEX",  # Standard for most use cases
                metric_type="COSINE"     # Matches your original metric
            )
            await self.client.create_index(collection_name=name, index_params=index_params)
        
        await self.client.load_collection(name)

    async def insert_document(self, collection_name: str, document: Document) -> None:
        """Embed and store document chunks in Milvus.

        Args:
            collection_name: Name of the collection to insert into.
            document: Document object with chunked pages to embed and store.

        Raises:
            ValueError: If document has no chunked pages.
        """
        await self._ensure_collection(collection_name)

        if not document.chunked_pages:
            raise ValueError("Document has no chunked pages. Did you run the processor?")

        vectors = self.embedder.embed_document(document)

        data = [
            {
                "id": chunk.chunk_id,
                "parent_doc_id": chunk.parent_doc_id,
                "content": chunk.chunk_content,
                "vector": vectors[i],
                "metadata": {"page_num": chunk.page_num, **document.metadata.model_dump()},
            }
            for i, chunk in enumerate(document.chunked_pages)
        ]
        await self.client.insert(collection_name, data=data)

    async def search(
        self, collection_name: str, query: str, limit: int = 4, filter: str = ""
    ) -> list[SearchResult]:
        """Search for similar chunks using vector similarity.

        Args:
            collection_name: Name of the collection to search in.
            query: The text query to search for.
            limit: Maximum number of results to return.
            filter: Optional filter expression for the search.

        Returns:
            List of search results sorted by relevance.
        """
        query_vector = self.embedder.embed_query(query)

        results = await self.client.search(
            collection_name=collection_name,
            data=[query_vector],
            limit=limit,
            filter=filter,
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
        """Get metadata and statistics about a collection.

        Args:
            collection_name: Name of the collection to get info for.

        Returns:
            CollectionInfo object with collection metadata.
        """
        count = await self.client.get_collection_stats(collection_name)
        
        return CollectionInfo(
            name=collection_name,
            total_vectors=count.get("row_count", 0),
            dim=self.settings.embeddings_config.dim,
        )

    async def delete_collection(self, collection_name: str) -> None:
        """Delete an entire collection and all its data.

        Args:
            collection_name: Name of the collection to delete.
        """
        await self.client.drop_collection(collection_name)

    async def delete_document(self, collection_name: str, document_id: str) -> None:
        """Delete all chunks associated with a document ID.

        Args:
            collection_name: Name of the collection containing the document.
            document_id: ID of the document to remove.
        """
        filter_expr = f'parent_doc_id == "{document_id}"'
        await self.client.delete(collection_name=collection_name, filter=filter_expr)

    async def get_documents(self, collection_name: str) -> list[DocumentInfo]:
        """Get all unique documents in a collection.

        Queries the collection to find all unique parent_doc_id values
        and their associated metadata.

        Args:
            collection_name: Name of the collection to get documents from.

        Returns:
            List of DocumentInfo objects with document metadata.
        """
        await self._ensure_collection(collection_name)
        
        # Query to get unique documents with their metadata
        # We use a group by on parent_doc_id to get unique documents
        results = await self.client.query(
            collection_name=collection_name,
            filter="",
            output_fields=["parent_doc_id", "metadata"],
            limit=10000,  # Adjust as needed for large collections
        )
        
        if not results:
            return []
        
        # Group by parent_doc_id and count chunks
        doc_map: dict[str, dict] = {}
        for item in results:
            doc_id = item.get("parent_doc_id")
            metadata = item.get("metadata", {})
            
            if doc_id and doc_id not in doc_map:
                doc_map[doc_id] = {
                    "document_id": doc_id,
                    "filename": metadata.get("filename"),
                    "filesize": metadata.get("filesize"),
                    "filetype": metadata.get("filetype"),
                    "additional_info": metadata.get("additional_info"),
                    "chunk_count": 0,
                }
            
            if doc_id:
                doc_map[doc_id]["chunk_count"] += 1
        
        return [
            DocumentInfo(
                document_id=data["document_id"],
                filename=data.get("filename"),
                filesize=data.get("filesize"),
                filetype=data.get("filetype"),
                chunk_count=data["chunk_count"],
                additional_info=data.get("additional_info"),
            )
            for data in doc_map.values()
        ]

    async def list_collections(self) -> list[str]:
        """List all available collection names.

        Returns:
            List of collection names as strings.
        """
        return await self.client.list_collections()
