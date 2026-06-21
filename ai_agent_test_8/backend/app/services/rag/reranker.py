"""Reranker implementations for RAG retrieval quality improvement."""

import logging
from abc import ABC, abstractmethod

from app.services.rag.config import RAGSettings
from app.services.rag.models import SearchResult

logger = logging.getLogger(__name__)


class BaseReranker(ABC):
    """Abstract base for reranker providers."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]: ...

    @abstractmethod
    def warmup(self) -> None: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class RerankService:
    """Orchestrates reranking with the configured reranker provider."""

    def __init__(self, settings: RAGSettings):
        self.settings = settings
        config = settings.reranker_config  # type: ignore[attr-defined]
        self._reranker: BaseReranker | None = None

        if self._reranker is None:
            logger.warning(
                "[RERANKER] No reranker configured (model: %s). Reranking will be skipped.",
                config.model,
            )

    @property
    def reranker(self) -> BaseReranker | None:
        return self._reranker

    @property
    def is_enabled(self) -> bool:
        return self._reranker is not None

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        if not self._reranker:
            logger.debug("[RERANKER] No reranker configured, returning original results")
            return results[:top_k]

        logger.debug(
            "[RERANKER] Starting reranking with %s, query: '%.50s...', results: %d, top_k: %d",
            self._reranker.name,
            query,
            len(results),
            top_k,
        )

        for i, r in enumerate(results[:5]):
            logger.debug("[RERANKER] Pre-rerank #%d: score=%.4f", i + 1, r.score)

        reranked = await self._reranker.rerank(query, results, top_k)

        for i, r in enumerate(reranked[:5]):
            logger.debug("[RERANKER] Post-rerank #%d: score=%.4f", i + 1, r.score)

        return reranked

    def warmup(self) -> None:
        if self._reranker:
            logger.info("[RERANKER] Warming up %s", self._reranker.name)
            self._reranker.warmup()
            logger.info("[RERANKER] %s warmup complete", self._reranker.name)
