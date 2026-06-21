{%- if cookiecutter.enable_rag %}
from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.services.rag.models import SearchResult
from app.services.rag.vectorstore import BaseVectorStore
from app.services.rag.config import RAGSettings

{%- if cookiecutter.enable_reranker %}
from app.services.rag.reranker import RerankService
{%- else %}
if TYPE_CHECKING:
    from app.services.rag.reranker import RerankService
{%- endif %}

logger = logging.getLogger(__name__)


def _result_key(r: SearchResult) -> str:
    if r.parent_doc_id:
        return f"{r.parent_doc_id}:{r.metadata.get('chunk_num', '')}"
    return hashlib.md5(r.content.encode()).hexdigest()


class BaseRetrievalService(ABC):

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        collection_name: str,
        limit: int = 5,
        min_score: float = 0.0,
        filter: str = ""
    ) -> list[SearchResult]:
        pass

    @abstractmethod
    async def retrieve_by_document(
        self,
        query: str,
        collection_name: str,
        document_id: str,
        limit: int = 3
    ) -> list[SearchResult]:
        pass

class RetrievalService(BaseRetrievalService):
    def __init__(
        self,
        vector_store: BaseVectorStore,
        settings: RAGSettings,
        rerank_service: RerankService | None = None,
    ):
        self.store = vector_store
        self.settings = settings
        self.rerank_service = rerank_service
        self._reranker_enabled = rerank_service is not None and rerank_service.is_enabled
        self._hybrid_enabled = settings.enable_hybrid_search

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
            key = _result_key(r)
            scores[key] = scores.get(key, 0) + 1.0 / (k + rank + 1)
            result_map[key] = r

        for rank, r in enumerate(bm25_results):
            key = _result_key(r)
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
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.warning("rank-bm25 not installed, skipping BM25 search")
            return []

        docs = await self.store.get_documents(collection_name)
        if not docs:
            return []

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
        should_rerank = use_reranker and self._reranker_enabled

        # Fetch 3x when reranking: gives the reranker room to eliminate weak candidates
        fetch_multiplier = 3 if should_rerank else 2

        logger.info(
            "[RETRIEVAL] Query: '%.50s...', collection: %s, limit: %d, filter: '%s', rerank: %s",
            query, collection_name, limit, filter, should_rerank,
        )

        start_time = time.time()

        pipeline_results = await self.store.search(
            collection_name=collection_name,
            query=query,
            filter_expr=filter,
            limit=limit * fetch_multiplier
        )

        search_time = time.time() - start_time
        logger.info(
            "[RETRIEVAL] Vector search completed in %.3fs, found %d results",
            search_time, len(pipeline_results),
        )

        if self._hybrid_enabled:
            bm25_results = await self._bm25_search(query, collection_name, limit * fetch_multiplier)
            if bm25_results:
                pipeline_results = self._rrf_fuse(pipeline_results, bm25_results)
                logger.info("[RETRIEVAL] Hybrid search: fused %d results", len(pipeline_results))

        for i, r in enumerate(pipeline_results[:3]):
            logger.debug(
                "[RETRIEVAL] Initial result #%d: score=%.4f, content='%.50s...'",
                i + 1, r.score, r.content,
            )

        if should_rerank and self.rerank_service:
            logger.info("[RETRIEVAL] Applying reranking...")
            rerank_start = time.time()
            pipeline_results = await self.rerank_service.rerank(
                query=query,
                results=pipeline_results,
                top_k=limit * 2,  # Get more from reranker before filtering
            )

            rerank_time = time.time() - rerank_start
            logger.info(
                "[RETRIEVAL] Reranking completed in %.3fs, returned %d results",
                rerank_time, len(pipeline_results),
            )
        elif use_reranker and not self._reranker_enabled:
            logger.warning(
                "[RETRIEVAL] Reranking requested but not configured - skipping"
            )

        filtered_results = [
            res for res in pipeline_results
            if res.score >= min_score
        ]

        seen_keys: set[str] = set()
        deduped_results: list[SearchResult] = []
        for r in filtered_results:
            key = _result_key(r)
            if key not in seen_keys:
                seen_keys.add(key)
                deduped_results.append(r)

        if len(deduped_results) < len(filtered_results):
            logger.info(
                "[RETRIEVAL] Deduplicated: %d -> %d results",
                len(filtered_results), len(deduped_results),
            )

        for i, r in enumerate(deduped_results[:3]):
            logger.debug(
                "[RETRIEVAL] Final result #%d: score=%.4f, content='%.50s...'",
                i + 1, r.score, r.content,
            )

        final_results = deduped_results[:limit]

        total_time = time.time() - start_time
        logger.info(
            "[RETRIEVAL] Total retrieval time: %.3fs, returning %d results",
            total_time, len(final_results),
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
            except Exception:
                logger.exception("[RETRIEVAL] Failed to search collection '%s'", name)

        all_results.sort(key=lambda r: r.score, reverse=True)

        seen_keys: set[str] = set()
        deduped: list[SearchResult] = []
        for r in all_results:
            key = _result_key(r)
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
        """Retrieve chunks restricted to a single document."""
        # Sanitize document_id to prevent filter injection
        sanitized_id = document_id.replace('"', "").replace("\\", "")
        filter_expr = f'parent_doc_id == "{sanitized_id}"'
        logger.info(
            "[RETRIEVAL] Retrieve by document: doc_id=%s, query='%.30s...', limit=%d, rerank=%s",
            document_id, query, limit, use_reranker,
        )
        return await self.retrieve(
            query=query,
            collection_name=collection_name,
            limit=limit,
            filter=filter_expr,
            use_reranker=use_reranker,
        )

{%- endif %}
