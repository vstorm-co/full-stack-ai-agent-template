"""Reranker implementations for improving RAG retrieval quality.

This module provides reranking functionality to improve the relevance of
search results. It supports both API-based rerankers (Cohere) and local
models (Cross Encoder).
"""

import logging
from abc import ABC, abstractmethod

from app.services.rag.config import RAGSettings
from app.services.rag.models import SearchResult

logger = logging.getLogger(__name__)


class BaseReranker(ABC):
    """Abstract base class for reranking implementations.

    Defines the interface that all reranker providers must implement.
    Rerankers take an initial set of search results and reorder them
    based on semantic relevance to the query.
    """

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        """Rerank search results based on query relevance.

        Args:
            query: The original search query.
            results: Initial search results from vector search.
            top_k: Number of top results to return after reranking.

        Returns:
            Reranked list of SearchResult objects, sorted by relevance.
        """
        pass

    @abstractmethod
    def warmup(self) -> None:
        """Ensure the reranker model is loaded and ready for inference.

        For API-based rerankers, this may validate credentials.
        For local models, this triggers model download and loading.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the reranker for logging purposes."""
        pass


class RerankService:
    """Service for managing reranking operations.

    Orchestrates reranking using a configured reranker provider.
    Supports both Cohere API and local Cross Encoder models.
    """

    def __init__(self, settings: RAGSettings):
        """Initialize the rerank service.

        Args:
            settings: RAG configuration settings containing reranker config.
        """
        self.settings = settings
        config = settings.reranker_config  # type: ignore[attr-defined]
        self._reranker: BaseReranker | None = None

        if self._reranker is None:
            logger.warning(
                f"[RERANKER] No reranker configured (model: {config.model}). "
                "Reranking will be skipped."
            )

    @property
    def reranker(self) -> BaseReranker | None:
        """Return the configured reranker, if any."""
        return self._reranker

    @property
    def is_enabled(self) -> bool:
        """Check if reranking is enabled."""
        return self._reranker is not None

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        """Rerank search results if a reranker is configured.

        Args:
            query: The search query.
            results: Initial search results to rerank.
            top_k: Number of results to return.

        Returns:
            Reranked results if reranker is configured, otherwise original results.
        """
        if not self._reranker:
            logger.debug("[RERANKER] No reranker configured, returning original results")
            return results[:top_k]

        print(
            f"[RERANKER] Starting reranking with {self._reranker.name}, "
            f"query: '{query[:50]}...', results: {len(results)}, top_k: {top_k}"
        )

        # Log pre-reranking scores
        for i, r in enumerate(results[:5]):
            logger.debug(
                f"[RERANKER] Pre-rerank #{i + 1}: score={r.score:.4f}, "
                f"content='{r.content[:50]}...'"
            )

        reranked = await self._reranker.rerank(query, results, top_k)

        # Log post-reranking scores
        for i, r in enumerate(reranked[:5]):
            logger.debug(
                f"[RERANKER] Post-rerank #{i + 1}: score={r.score:.4f}, "
                f"content='{r.content[:50]}...'"
            )

        return reranked

    def warmup(self) -> None:
        """Initialize the reranker model if configured."""
        if self._reranker:
            logger.info(f"[RERANKER] Warming up {self._reranker.name}")
            self._reranker.warmup()
            logger.info(f"[RERANKER] {self._reranker.name} warmup complete")
