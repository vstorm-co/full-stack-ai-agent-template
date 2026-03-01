{%- if cookiecutter.enable_rag %}

from abc import ABC, abstractmethod
from app.rag.models import Document, SearchResult, CollectionInfo

class BaseVectorStore(ABC):
    """Contract for any vector database implementation."""
    
    @abstractmethod
    async def insert_document(self, collection_name: str, document: Document) -> None:
        """Embeds and stores document chunks."""
        pass

    @abstractmethod
    async def search(self, collection_name: str, query: str, limit: int = 4, filter: str = "") -> list[SearchResult]:
        """Retrieves similar chunks based on a text query."""
        pass

    @abstractmethod
    async def delete_collection(self, collection_name: str) -> None:
        """Removes a collection and all its data."""
        pass

    @abstractmethod
    async def delete_document(self, collection_name: str, document_id: str) -> None:
        """Removes all chunks associated with a document ID."""
        pass

    @abstractmethod
    async def get_collection_info(self, collection_name: str) -> CollectionInfo:
        """Returns metadata and stats about a collection."""
        pass

{%- if cookiecutter.use_milvus %}
from pymilvus import AsyncMilvusClient, DataType
from app.core.config import settings as app_settings
from app.rag.config import RAGSettings
from app.rag.embeddings import EmbeddingService

class MilvusVectorStore(BaseVectorStore):
    def __init__(self, settings: RAGSettings, embedding_service: EmbeddingService):
        self.settings = settings
        self.embedder = embedding_service
        self.client = AsyncMilvusClient(
            uri=app_settings.MILVUS_URI,
            token=app_settings.MILVUS_TOKEN
        )

    async def _ensure_collection(self, name: str):
        """Standardizes collection creation with Schema API."""
        if not await self.client.has_collection(name):
            schema = self.client.create_schema(auto_id=False)
            schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=100)
            schema.add_field("parent_doc_id", DataType.VARCHAR, max_length=100)
            schema.add_field("content", DataType.VARCHAR, max_length=65535)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=self.settings.embeddings_config.dim)
            schema.add_field("metadata", DataType.JSON)
            
            await self.client.create_collection(name, schema=schema, metric_type="COSINE")
            await self.client.load_collection(name)

    async def insert_document(self, collection_name: str, document: Document):
        await self._ensure_collection(collection_name)
        
        if not document.chunked_pages:
            raise ValueError("Document has no chunked pages. Did you run the processor?")

        # Use the chunks, not the full pages
        # Assuming embed_document is updated to handle list[DocumentPageChunk]
        vectors = self.embedder.embed_document(document)
        
        data = [
            {
                "id": chunk.chunk_id, 
                "parent_doc_id": chunk.parent_doc_id,
                "content": chunk.chunk_content,
                "vector": vectors[i],
                "metadata": {
                    "page_num": chunk.page_num,
                    **document.metadata.model_dump()
                }
            }
            for i, chunk in enumerate(document.chunked_pages)
        ]
        await self.client.insert(collection_name, data=data)

    async def search(self, collection_name: str, query: str, limit: int = 4, filter: str = "") -> list[SearchResult]:
        query_vector = self.embedder.embed_query(query)
        
        results = await self.client.search(
            collection_name=collection_name,
            data=[query_vector],
            limit=limit,
            filter=filter,
            output_fields=["content", "parent_doc_id", "metadata"]
        )
        
        return [
            SearchResult(
                content=hit["entity"]["content"],
                score=hit["distance"],
                metadata=hit["entity"]["metadata"],
                parent_doc_id=hit["entity"]["parent_doc_id"]
            )
            for hit in results[0]
        ]

    async def get_collection_info(self, collection_name: str) -> CollectionInfo:
        # stats = await self.client.describe_collection(collection_name)
        count = await self.client.get_collection_stats(collection_name)
        return CollectionInfo(
            name=collection_name,
            total_vectors=count.get("row_count", 0),
            dim=self.settings.embeddings_config.dim
        )
        
    async def delete_collection(self, collection_name: str):
        await self.client.drop_collection(collection_name)

    async def delete_document(self, collection_name: str, document_id: str):
        filter_expr = f'parent_doc_id == "{document_id}"'
        await self.client.delete(
            collection_name=collection_name,
            filter=filter_expr
        )

{%- endif %}
{%- endif %}
