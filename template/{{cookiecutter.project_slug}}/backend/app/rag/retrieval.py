{%- if cookiecutter.enable_rag %}
from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod

from app.rag.models import SearchResult
from app.rag.vectorstore import BaseVectorStore
from app.rag.config import RAGSettings

{%- if cookiecutter.enable_reranker %}
from app.rag.reranker import RerankService
{%- else %}
from typing import Any

RerankService = Any
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

class RetrievalService(BaseRetrievalService):
    """High-level retrieval service with multi-stage pipeline.

    Handles query execution against any vector store backend, including
    vector search, hybrid BM25 fusion, score filtering, and reranking.
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
        self._hybrid_enabled = settings.enable_hybrid_search
        self._bm25_index: dict[str, object] = {}  # collection_name -> BM25 index

    @staticmethod
    def _rrf_fuse(
        vector_results: list[SearchResult],
        bm25_results: list[SearchResult],
        k: int = 60,
    ) -> list[SearchResult]:
        """Reciprocal Rank Fusion of vector and BM25 results."""
        scores: dict[str, float] = {}
        result_map: dict[str, SearchResult] = {}

        for rank, r in enumerate(vector_results):
            key = f"{r.parent_doc_id}:{r.metadata.get('chunk_num', '')}" if r.parent_doc_id else hashlib.md5(r.content.encode()).hexdigest()
            scores[key] = scores.get(key, 0) + 1.0 / (k + rank + 1)
            result_map[key] = r

        for rank, r in enumerate(bm25_results):
            key = f"{r.parent_doc_id}:{r.metadata.get('chunk_num', '')}" if r.parent_doc_id else hashlib.md5(r.content.encode()).hexdigest()
            scores[key] = scores.get(key, 0) + 1.0 / (k + rank + 1)
            if key not in result_map:
                result_map[key] = r

        sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
        return [
            SearchResult(
                content=result_map[key].content,
                score=scores[key],
                metadata=result_map[key].metadata,
                parent_doc_id=result_map[key].parent_doc_id,
            )
            for key in sorted_keys
        ]

    async def _bm25_search(
        self, query: str, collection_name: str, limit: int
    ) -> list[SearchResult]:
        """BM25 keyword search over stored documents."""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.warning("rank-bm25 not installed, skipping BM25 search")
            return []

        # Get all documents for BM25 (cached per collection)
        docs = await self.store.get_documents(collection_name)
        if not docs:
            return []

        # Build corpus from stored content via vector store search with high limit
        all_results = await self.store.search(
            collection_name=collection_name, query=query, limit=min(limit * 10, 100)
        )
        if not all_results:
            return []

        corpus = [r.content.lower().split() for r in all_results]
        bm25 = BM25Okapi(corpus)
        query_tokens = query.lower().split()
        bm25_scores = bm25.get_scores(query_tokens)

        scored = sorted(
            zip(all_results, bm25_scores), key=lambda x: x[1], reverse=True
        )
        return [
            SearchResult(
                content=r.content,
                score=float(s),
                metadata=r.metadata,
                parent_doc_id=r.parent_doc_id,
            )
            for r, s in scored[:limit]
            if s > 0
        ]

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

        # Step 1b: Hybrid search (BM25 + vector fusion) if enabled
        if self._hybrid_enabled:
            bm25_results = await self._bm25_search(query, collection_name, limit * fetch_multiplier)
            if bm25_results:
                raw_results = self._rrf_fuse(raw_results, bm25_results)
                logger.info(f"[RETRIEVAL] Hybrid search: fused {len(raw_results)} results")

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

        # Step 4: Deduplicate — keep highest-scored result per unique chunk
        seen_keys: set[str] = set()
        deduped_results: list[SearchResult] = []
        for r in filtered_results:
            key = (
                f"{r.parent_doc_id}:{r.metadata.get('chunk_num', '')}"
                if r.parent_doc_id
                else hashlib.md5(r.content.encode()).hexdigest()
            )
            if key not in seen_keys:
                seen_keys.add(key)
                deduped_results.append(r)

        if len(deduped_results) < len(filtered_results):
            logger.info(
                f"[RETRIEVAL] Deduplicated: {len(filtered_results)} -> {len(deduped_results)} results"
            )

        # Log final results
        for i, r in enumerate(deduped_results[:3]):
            logger.debug(
                f"[RETRIEVAL] Final result #{i+1}: score={r.score:.4f}, "
                f"content='{r.content[:50]}...'"
            )

        # Apply final limit
        final_results = deduped_results[:limit]

        total_time = time.time() - start_time
        logger.info(
            f"[RETRIEVAL] Total retrieval time: {total_time:.3f}s, "
            f"returning {len(final_results)} results"
        )

        return final_results

    async def retrieve_multi(
        self,
        query: str,
        collection_names: list[str],
        limit: int = 5,
        min_score: float = 0.0,
        use_reranker: bool = False,
    ) -> list[SearchResult]:
        """Search across multiple collections and merge results.

        Searches each collection, merges results, sorts by score.
        """
        all_results: list[SearchResult] = []
        for name in collection_names:
            try:
                results = await self.retrieve(
                    query=query,
                    collection_name=name,
                    limit=limit,
                    min_score=min_score,
                    use_reranker=use_reranker,
                )
                # Tag results with collection name in metadata
                for r in results:
                    r.metadata["collection"] = name
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"[RETRIEVAL] Failed to search collection '{name}': {e}")

        all_results.sort(key=lambda r: r.score, reverse=True)

        # Deduplicate across collections
        seen_keys: set[str] = set()
        deduped: list[SearchResult] = []
        for r in all_results:
            key = (
                f"{r.parent_doc_id}:{r.metadata.get('chunk_num', '')}"
                if r.parent_doc_id
                else hashlib.md5(r.content.encode()).hexdigest()
            )
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(r)

        return deduped[:limit]

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
        # Sanitize document_id to prevent filter injection
        sanitized_id = document_id.replace('"', "").replace("\\", "")
        filter_expr = f'parent_doc_id == "{sanitized_id}"'
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
