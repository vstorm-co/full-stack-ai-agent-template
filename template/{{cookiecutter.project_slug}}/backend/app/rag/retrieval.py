{%- if cookiecutter.enable_rag %}
import logging
import time
from abc import ABC, abstractmethod

from app.rag.models import SearchResult
from app.rag.vectorstore import BaseVectorStore
from app.rag.config import RAGSettings

{%- if cookiecutter.enable_reranker %}
from app.rag.reranker import RerankService
{%- endif %}

logger = logging.getLogger(__name__)

class BaseRetrievalService(ABC):
    """Abstract base class for retrieval service implementations.
    
    Defines the interface for querying the vector store and retrieving
    relevant document chunks based on a query.
    """
    
    @abstractmethod
    async def retrieve(
        self, 
        query: str, 
        collection_name: str,
        limit: int = 5,
        min_score: float = 0.0,
        filter: str = ""
    ) -> list[SearchResult]:
        """Execute the retrieval pipeline to find relevant chunks.
        
        Args:
            query: The search query text.
            collection_name: Name of the collection to search in.
            limit: Maximum number of results to return.
            min_score: Minimum similarity score threshold (0.0 to 1.0).
            filter: Optional filter expression for the search.
            
        Returns:
            List of SearchResult objects sorted by relevance.
        """
        pass

    @abstractmethod
    async def retrieve_by_document(
        self, 
        query: str, 
        collection_name: str, 
        document_id: str,
        limit: int = 3
    ) -> list[SearchResult]:
        """Specialized retrieval restricted to a single document.
        
        Useful for "Chat with this PDF" functionality where results
        should only come from a specific document.
        
        Args:
            query: The search query text.
            collection_name: Name of the collection to search in.
            document_id: ID of the document to restrict search to.
            limit: Maximum number of results to return.
            
        Returns:
            List of SearchResult objects from the specified document.
        """
        pass

{%- if cookiecutter.use_milvus %}
class MilvusRetrievalService(BaseRetrievalService):
    """High-level service for query processing and multi-stage retrieval using Milvus.
    
    Handles query execution against the Milvus vector store, including
    vector search, score filtering, and post-processing.
    Optionally supports reranking for improved result quality.
    """

    def __init__(
        self,
        vector_store: BaseVectorStore,
        settings: RAGSettings,
        rerank_service: RerankService | None = None,
    ):
        """Initialize the Milvus retrieval service.
        
        Args:
            vector_store: The vector store to query.
            settings: RAG configuration settings.
            rerank_service: Optional reranking service for improved results.
        """
        self.store = vector_store
        self.settings = settings
        self.rerank_service = rerank_service
        self._reranker_enabled = rerank_service is not None and rerank_service.is_enabled

    async def retrieve(
        self, 
        query: str, 
        collection_name: str,
        limit: int = 5,
        min_score: float = 0.0,
        filter: str = "",
        use_reranker: bool = False,
    ) -> list[SearchResult]:
        """Execute the retrieval pipeline: Vector Search + Reranking (optional) + Filtering.
        
        Args:
            query: The search query text.
            collection_name: Name of the collection to search in.
            limit: Maximum number of results to return.
            min_score: Minimum similarity score threshold (0.0 to 1.0).
            filter: Optional filter expression for the search.
            use_reranker: Whether to use reranking (if configured).
            
        Returns:
            List of SearchResult objects sorted by relevance.
        """
        # Determine if we should actually use reranking
        should_rerank = use_reranker and self._reranker_enabled
        
        # Fetch more results if reranking is enabled (reranker will reduce)
        # We fetch 3x results to give reranker room to pick best ones
        fetch_multiplier = 3 if should_rerank else 2
        
        logger.info(
            f"[RETRIEVAL] Query: '{query[:50]}...', collection: {collection_name}, "
            f"limit: {limit}, filter: '{filter}', rerank: {should_rerank}"
        )
        
        start_time = time.time()
        
        # Step 1: Execute Vector Search via the Vector Store
        raw_results = await self.store.search(
            collection_name=collection_name,
            query=query,
            filter=filter,
            limit=limit * fetch_multiplier
        )
        
        search_time = time.time() - start_time
        logger.info(
            f"[RETRIEVAL] Vector search completed in {search_time:.3f}s, "
            f"found {len(raw_results)} results"
        )
        
        # Log initial results
        for i, r in enumerate(raw_results[:3]):
            logger.debug(
                f"[RETRIEVAL] Initial result #{i+1}: score={r.score:.4f}, "
                f"content='{r.content[:50]}...'"
            )
        
        results = raw_results
        
        # Step 2: Apply reranking if enabled and requested
        if should_rerank and self.rerank_service:
            logger.info("[RETRIEVAL] Applying reranking...")
            rerank_start = time.time()
            
            # Rerank the results - fetches more initially so reranker can pick best
            results = await self.rerank_service.rerank(
                query=query,
                results=raw_results,
                top_k=limit * 2,  # Get more from reranker before filtering
            )
            
            rerank_time = time.time() - rerank_start
            logger.info(
                f"[RETRIEVAL] Reranking completed in {rerank_time:.3f}s, "
                f"returned {len(results)} results"
            )
        elif use_reranker and not self._reranker_enabled:
            logger.warning(
                "[RETRIEVAL] Reranking requested but not configured - skipping"
            )
        
        # Step 3: Post-processing: Filter by score
        # Cosine similarity is higher = better.
        filtered_results = [
            res for res in results 
            if res.score >= min_score
        ]
        
        # Log filtered results
        for i, r in enumerate(filtered_results[:3]):
            logger.debug(
                f"[RETRIEVAL] Final result #{i+1}: score={r.score:.4f}, "
                f"content='{r.content[:50]}...'"
            )
        
        # Apply final limit
        final_results = filtered_results[:limit]
        
        total_time = time.time() - start_time
        logger.info(
            f"[RETRIEVAL] Total retrieval time: {total_time:.3f}s, "
            f"returning {len(final_results)} results"
        )
        
        return final_results

    async def retrieve_by_document(
        self, 
        query: str, 
        collection_name: str, 
        document_id: str,
        limit: int = 3,
        use_reranker: bool = False,
    ) -> list[SearchResult]:
        """Specialized retrieval restricted to a single document.
        
        Useful for "Chat with this PDF" functionality where results
        should only come from a specific document.
        
        Args:
            query: The search query text.
            collection_name: Name of the collection to search in.
            document_id: ID of the document to restrict search to.
            limit: Maximum number of results to return.
            use_reranker: Whether to use reranking (if configured).
            
        Returns:
            List of SearchResult objects from the specified document.
        """
        filter_expr = f'parent_doc_id == "{document_id}"'
        logger.info(
            f"[RETRIEVAL] Retrieve by document: doc_id={document_id}, "
            f"query='{query[:30]}...', limit={limit}, rerank={use_reranker}"
        )
        return await self.retrieve(
            query=query, 
            collection_name=collection_name, 
            limit=limit, 
            filter=filter_expr,
            use_reranker=use_reranker,
        )

{%- endif %}
{%- endif %}