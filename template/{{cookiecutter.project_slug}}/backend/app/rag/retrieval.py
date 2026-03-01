{%- if cookiecutter.enable_rag %}
from abc import ABC, abstractmethod
from app.rag.models import SearchResult
from app.rag.vectorstore import BaseVectorStore
from app.rag.config import RAGSettings

class BaseRetrievalService(ABC):
    """Contract for any retrieval service implementation."""
    
    @abstractmethod
    async def retrieve(
        self, 
        query: str, 
        collection_name: str,
        limit: int = 5,
        min_score: float = 0.0,
        filter: str = ""
    ) -> list[SearchResult]:
        """Executes the retrieval pipeline."""
        pass

    @abstractmethod
    async def retrieve_by_document(
        self, 
        query: str, 
        collection_name: str, 
        document_id: str,
        limit: int = 3
    ) -> list[SearchResult]:
        """Specialized retrieval restricted to a single document."""
        pass

{%- if cookiecutter.use_milvus %}
class MilvusRetrievalService(BaseRetrievalService):
    """
    High-level service to handle query processing and multi-stage retrieval.
    """

    def __init__(self, vector_store: BaseVectorStore, settings: RAGSettings):
        self.store = vector_store
        self.settings = settings

    async def retrieve(
        self, 
        query: str, 
        collection_name: str,
        limit: int = 5,
        min_score: float = 0.0,
        filter: str = ""
    ) -> list[SearchResult]:
        """
        Executes the retrieval pipeline: 
        1. (Optional) Query Expansion/Rewriting
        2. Vector Search
        3. Threshold Filtering
        """
        
        # Execute Search via the Vector Store
        raw_results = await self.store.search(
            collection_name=collection_name,
            query=query,
            filter=filter,
            limit=limit * 2 # Retrieve more for post-filtering
        )

        # Post-processing: Filter by score and limit
        # Cosine is higher = better.
        # This example assumes a basic score-based filter.
        filtered_results = [
            res for res in raw_results 
            if res.score >= min_score
        ]

        # Apply final limit
        return filtered_results[:limit]

    async def retrieve_by_document(
        self, 
        query: str, 
        collection_name: str, 
        document_id: str,
        limit: int = 3
    ) -> list[SearchResult]:
        """
        Specialized retrieval restricted to a single document (e.g., 'Chat with this PDF').
        """
        filter = f'parent_doc_id == "{document_id}"'
        return await self.retrieve(
            query=query, 
            collection_name=collection_name, 
            limit=limit, 
            filter=filter
        )

{%- endif %}
{%- endif %}