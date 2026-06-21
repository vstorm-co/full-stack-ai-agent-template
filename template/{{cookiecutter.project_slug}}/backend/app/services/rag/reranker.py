{%- if cookiecutter.enable_rag %}
"""Reranker implementations for RAG retrieval quality improvement."""

import importlib.util
import logging
import time
from abc import ABC, abstractmethod
from app.core.config import settings
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


{%- if cookiecutter.use_cohere_reranker %}
class CohereReranker(BaseReranker):
    """Cohere Rerank API implementation. Requires COHERE_API_KEY."""

    def __init__(self, api_key: str, model: str = "rerank-v3.5"):
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy Cohere client initialization."""
        if self._client is None:
            try:
                from cohere import AsyncClient
                self._client = AsyncClient(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "cohere package not installed. Install with: pip install cohere"
                )
        return self._client

    @property
    def name(self) -> str:
        return f"CohereReranker({self.model})"

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        if not results:
            return []

        if not self.api_key:
            logger.warning("[RERANKER] Cohere API key not set, skipping reranking")
            return results[:top_k]

        documents = [result.content for result in results]

        try:
            logger.debug(
                "[RERANKER] Calling Cohere API for %d documents, query: '%.50s...', top_k: %d",
                len(documents), query, top_k,
            )

            start_time = time.time()
            response = await self.client.rerank(
                query=query,
                documents=documents,
                model=self.model,
                top_n=top_k,
                return_documents=False,
            )
            elapsed = time.time() - start_time
            logger.info("[RERANKER] Cohere rerank completed in %.3fs", elapsed)

            reranked = [
                SearchResult(
                    content=results[item.index].content,
                    score=item.relevance_score,
                    metadata=results[item.index].metadata,
                    parent_doc_id=results[item.index].parent_doc_id,
                )
                for item in response.results
            ]
            logger.debug("[RERANKER] Cohere reranked %d results", len(reranked))
            return reranked

        except Exception as e:
            logger.error("[RERANKER] Cohere reranking failed: %s", e)
            return results[:top_k]

    def warmup(self) -> None:
        if not self.api_key:
            logger.warning("[RERANKER] Cohere API key not set, reranker will be disabled")
            return

        if importlib.util.find_spec("cohere") is not None:
            logger.info("[RERANKER] Cohere reranker configured with model: %s", self.model)
        else:
            logger.warning("[RERANKER] cohere package not installed")

{%- endif %}


{%- if cookiecutter.use_cross_encoder_reranker %}
from sentence_transformers import CrossEncoder


class CrossEncoderReranker(BaseReranker):
    """Local Cross Encoder reranker (no API calls required)."""

    DEFAULT_MODEL = settings.CROSS_ENCODER_MODEL

    def __init__(self, model: str | None = None, cache_dir: str | None = None):
        self.model_name = model or self.DEFAULT_MODEL
        self.cache_dir = cache_dir
        self._model = None

    @property
    def model(self) -> CrossEncoder:
        """Lazy-load the cross-encoder model."""
        if self._model is None:
            cache_path = self.cache_dir or str(settings.MODELS_CACHE_DIR)
            settings.MODELS_CACHE_DIR.mkdir(exist_ok=True, parents=True)

            logger.info("[RERANKER] Loading Cross Encoder model: %s", self.model_name)
            self._model = CrossEncoder(
                self.model_name,
                cache_folder=cache_path,
                token=settings.HF_TOKEN,
            )
        return self._model

    @property
    def name(self) -> str:
        return f"CrossEncoderReranker({self.model_name})"

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        if not results:
            return []

        logger.debug(
            "[RERANKER] Cross Encoder reranking %d documents, query: '%.50s...', top_k: %d",
            len(results), query, top_k,
        )

        start_time = time.time()

        try:
            pairs = [[query, result.content] for result in results]
            scores = self.model.predict(pairs)

            elapsed = time.time() - start_time
            logger.info("[RERANKER] Cross Encoder reranking completed in %.3fs", elapsed)

            scored_results = []
            for i, (result, score) in enumerate(zip(results, scores)):
                logger.debug(
                    "[RERANKER] CrossEncoder doc %d: score=%.4f (was %.4f)",
                    i, score, result.score,
                )
                scored_results.append(
                    SearchResult(
                        content=result.content,
                        score=float(score),
                        metadata=result.metadata,
                        parent_doc_id=result.parent_doc_id,
                    )
                )

            scored_results.sort(key=lambda x: x.score, reverse=True)

            for i, r in enumerate(scored_results[:3]):
                logger.debug("[RERANKER] Rank #%d: score=%.4f", i + 1, r.score)

            return scored_results[:top_k]

        except Exception as e:
            logger.error("[RERANKER] Cross Encoder reranking failed: %s", e)
            return results[:top_k]

    def warmup(self) -> None:
        logger.info("[RERANKER] Cross Encoder warmup: loading model %s", self.model_name)
        _ = self.model
        logger.info("[RERANKER] Cross Encoder ready: %s", self.model_name)

{%- endif %}


class RerankService:
    """Orchestrates reranking with the configured reranker provider."""

    def __init__(self, settings: RAGSettings):
        self.settings = settings
        config = settings.reranker_config  # type: ignore[attr-defined]
        self._reranker: BaseReranker | None = None

        {%- if cookiecutter.use_cohere_reranker %}
        if config.model == "cohere":
            self._reranker = CohereReranker(api_key=settings.COHERE_API_KEY)
            logger.info("[RERANKER] Using Cohere reranker")
        {%- endif %}

        {%- if cookiecutter.use_cross_encoder_reranker %}
        if config.model == "cross_encoder":
            self._reranker = CrossEncoderReranker()
            logger.info("[RERANKER] Using Cross Encoder reranker")
        {%- endif %}

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
            self._reranker.name, query, len(results), top_k,
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

{%- endif %}
