{%- if cookiecutter.enable_rag %}
"""Reranker implementations for improving RAG retrieval quality.

This module provides reranking functionality to improve the relevance of
search results. It supports both API-based rerankers (Cohere) and local
models (Cross Encoder).
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from app.core.config import settings
from app.rag.config import RAGSettings
from app.rag.models import SearchResult

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


{%- if cookiecutter.use_cohere_reranker %}
class CohereReranker(BaseReranker):
    """Cohere reranker implementation using the Cohere Rerank API.
    
    Uses Cohere's rerank-v3.5 model to improve search result relevance.
    Requires COHERE_API_KEY to be set in environment variables.
    """
    
    def __init__(self, api_key: str, model: str = "rerank-v3.5"):
        """Initialize the Cohere reranker.
        
        Args:
            api_key: Cohere API key for authentication.
            model: The Cohere reranker model to use (default: rerank-v3.5).
        """
        self.api_key = api_key
        self.model = model
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of Cohere client."""
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
        """Rerank results using Cohere API.
        
        Args:
            query: The search query.
            results: Initial search results.
            top_k: Number of results to return.
            
        Returns:
            Reranked results sorted by relevance.
        """
        if not results:
            return []
        
        if not self.api_key:
            logger.warning("[RERANKER] Cohere API key not set, skipping reranking")
            return results[:top_k]
        
        # Prepare documents for Cohere rerank API
        documents = [result.content for result in results]
        
        try:
            print(
                f"[RERANKER] Calling Cohere API for {len(documents)} documents, "
                f"query: '{query[:50]}...', top_k: {top_k}"
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
            print(f"[RERANKER] Cohere rerank completed in {elapsed:.3f}s")
            
            # Map reranked results back to SearchResult objects
            reranked = []
            for item in response.results:
                original_idx = item.index
                original_result = results[original_idx]
                # Create new SearchResult with updated score (Cohere provides relevance 0-1)
                reranked.append(
                    SearchResult(
                        content=original_result.content,
                        score=item.relevance_score,
                        metadata=original_result.metadata,
                        parent_doc_id=original_result.parent_doc_id,
                    )
                )
            
            logger.debug(f"[RERANKER] Cohere reranked results: {len(reranked)} items")
            return reranked
            
        except Exception as e:
            logger.error(f"[RERANKER] Cohere reranking failed: {str(e)}")
            return results[:top_k]
    
    def warmup(self) -> None:
        """Validate Cohere API credentials."""
        if not self.api_key:
            logger.warning("[RERANKER] Cohere API key not set, reranker will be disabled")
            return
        
        # Just verify we can import the client
        try:
            from cohere import AsyncClient
            print(f"[RERANKER] Cohere reranker configured with model: {self.model}")
        except ImportError:
            logger.warning("[RERANKER] cohere package not installed")

{%- endif %}


{%- if cookiecutter.use_cross_encoder_reranker %}
from sentence_transformers import CrossEncoder


class CrossEncoderReranker(BaseReranker):
    """Cross Encoder reranker using local Sentence Transformers model.
    
    Uses a cross-encoder model to score query-document pairs for relevance.
    Runs entirely locally - no API calls required.
    
    Default model: cross-encoder/ms-marco-MiniLM-L6-v2 (lightweight, fast)
    """
    
    # Default cross-encoder model for reranking
    DEFAULT_MODEL = settings.CROSS_ENCODER_MODEL
    
    def __init__(self, model: str | None = None, cache_dir: str | None = None):
        """Initialize the Cross Encoder reranker.
        
        Args:
            model: Cross-encoder model name from Sentence Transformers.
                   Defaults to cross-encoder/ms-marco-MiniLM-L6-v2 if not specified.
            cache_dir: Directory to cache the model. Defaults to app models cache.
        """
        self.model_name = model or self.DEFAULT_MODEL
        self.cache_dir = cache_dir
        self._model = None
    
    @property
    def model(self) -> CrossEncoder:
        """Lazy load the cross-encoder model."""
        if self._model is None:
            from app.core.config import settings as app_settings
            
            cache_path = self.cache_dir or str(app_settings.MODELS_CACHE_DIR)
            # Ensure cache directory exists
            app_settings.MODELS_CACHE_DIR.mkdir(exist_ok=True, parents=True)
            
            print(f"[RERANKER] Loading Cross Encoder model: {self.model_name}")
            self._model = CrossEncoder(
                self.model_name,
                cache_folder=cache_path,
                token=settings.HF_TOKEN,
            )
            print(f"[RERANKER] Cross Encoder model loaded successfully")
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
        """Rerank results using local Cross Encoder model.
        
        Args:
            query: The search query.
            results: Initial search results.
            top_k: Number of results to return.
            
        Returns:
            Reranked results sorted by relevance score.
        """
        if not results:
            return []
        
        print(
            f"[RERANKER] Cross Encoder reranking {len(results)} documents, "
            f"query: '{query[:50]}...', top_k: {top_k}"
        )
        
        start_time = time.time()
        
        try:
            # Prepare query-document pairs for scoring
            # CrossEncoder expects list of [query, document] pairs
            pairs = [[query, result.content] for result in results]
            
            # Get relevance scores (higher = more relevant)
            scores = self.model.predict(pairs)
            
            elapsed = time.time() - start_time
            print(f"[RERANKER] Cross Encoder reranking completed in {elapsed:.3f}s")
            
            # Create new results with cross-encoder scores
            scored_results = []
            for i, (result, score) in enumerate(zip(results, scores)):
                logger.debug(
                    f"[RERANKER] CrossEncoder score for doc {i}: {score:.4f} "
                    f"(original: {result.score:.4f}) - '{result.content[:30]}...'"
                )
                scored_results.append(
                    SearchResult(
                        content=result.content,
                        score=float(score),  # Use cross-encoder score
                        metadata=result.metadata,
                        parent_doc_id=result.parent_doc_id,
                    )
                )
            
            # Sort by cross-encoder score (descending)
            scored_results.sort(key=lambda x: x.score, reverse=True)
            
            # Log top results
            for i, r in enumerate(scored_results[:3]):
                logger.debug(
                    f"[RERANKER] Rank #{i+1}: score={r.score:.4f}, "
                    f"content='{r.content[:50]}...'"
                )
            
            return scored_results[:top_k]
            
        except Exception as e:
            logger.error(f"[RERANKER] Cross Encoder reranking failed: {str(e)}")
            return results[:top_k]
    
    def warmup(self) -> None:
        """Trigger model download and loading."""
        print(f"[RERANKER] Cross Encoder warmup: loading model {self.model_name}")
        _ = self.model
        print(f"[RERANKER] Cross Encoder ready: {self.model_name}")

{%- endif %}


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
        config = settings.reranker_config
        self._reranker: Optional[BaseReranker] = None
        
        {%- if cookiecutter.use_cohere_reranker %}
        if config.model == "cohere":
            from app.core.config import settings as app_settings
            self._reranker = CohereReranker(api_key=app_settings.COHERE_API_KEY)
            print("[RERANKER] Using Cohere reranker")
        {%- endif %}
        
        {%- if cookiecutter.use_cross_encoder_reranker %}
        if config.model == "cross_encoder":
            self._reranker = CrossEncoderReranker()
            print("[RERANKER] Using Cross Encoder reranker")
        {%- endif %}
        
        if self._reranker is None:
            logger.warning(
                f"[RERANKER] No reranker configured (model: {config.model}). "
                "Reranking will be skipped."
            )
    
    @property
    def reranker(self) -> Optional[BaseReranker]:
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
                f"[RERANKER] Pre-rerank #{i+1}: score={r.score:.4f}, "
                f"content='{r.content[:50]}...'"
            )
        
        reranked = await self._reranker.rerank(query, results, top_k)
        
        # Log post-reranking scores
        for i, r in enumerate(reranked[:5]):
            logger.debug(
                f"[RERANKER] Post-rerank #{i+1}: score={r.score:.4f}, "
                f"content='{r.content[:50]}...'"
            )
        
        return reranked
    
    def warmup(self) -> None:
        """Initialize the reranker model if configured."""
        if self._reranker:
            print(f"[RERANKER] Warming up {self._reranker.name}")
            self._reranker.warmup()
            print(f"[RERANKER] {self._reranker.name} warmup complete")

{%- endif %}
