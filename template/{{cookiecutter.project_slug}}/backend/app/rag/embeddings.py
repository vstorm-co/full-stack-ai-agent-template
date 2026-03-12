{%- if cookiecutter.enable_rag %}
from abc import ABC, abstractmethod

{%- if cookiecutter.use_openai_embeddings %}
from openai import OpenAI
{%- endif %}

{%- if cookiecutter.use_voyage_embeddings %}
from voyageai import Client
{%- endif %}

{%- if cookiecutter.use_sentence_transformers %}
from sentence_transformers import SentenceTransformer
{%- endif %}

from app.rag.config import RAGSettings
from app.rag.models import Document


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers.
    
    Defines the interface that all embedding providers must implement.
    """
    @abstractmethod
    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of query texts.
        
        Args:
            texts: List of text strings to embed.
            
        Returns:
            List of embedding vectors, one for each input text.
        """
        pass

    @abstractmethod
    def embed_document(self, document: Document) -> list[list[float]]:
        """Embed all chunks of a document.
        
        Args:
            document: Document object containing chunked pages to embed.
            
        Returns:
            List of embedding vectors, one for each chunk in the document.
        """
        pass

    @abstractmethod
    def warmup(self) -> None:
        """Ensures the model is loaded and ready for inference."""
        pass

{%- if cookiecutter.use_openai_embeddings %}
class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider using the OpenAI API.
    
    Uses OpenAI's embedding models to generate text embeddings.
    """
    
    def __init__(self, model: str) -> None:
        """Initialize the OpenAI embedding provider.
        
        Args:
            model: The OpenAI embedding model name (e.g., 'text-embedding-3-small').
        """
        self.model = model
        self.client = OpenAI()
        
    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of query texts using OpenAI.
        
        Args:
            texts: List of text strings to embed.
            
        Returns:
            List of embedding vectors.
        """
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [data.embedding for data in response.data]
    
    def embed_document(self, document: Document) -> list[list[float]]:
        """Embed all chunks of a document using OpenAI.
        
        Args:
            document: Document object containing chunked pages.
            
        Returns:
            List of embedding vectors for each chunk.
        """
        texts = [doc.chunk_content if doc.chunk_content else "" for doc in (document.chunked_pages or [])]
        return self.embed_queries(texts)

    def warmup(self) -> None:
        """Warmup method for OpenAI client.
        
        OpenAI API is a remote service, so this is a no-op.
        """
        pass
{%- endif %}

{%- if cookiecutter.use_voyage_embeddings %}
class VoyageEmbeddingProvider(BaseEmbeddingProvider):
    """Voyage AI embedding provider using the Voyage API.
    
    Uses Voyage's embedding models to generate text embeddings.
    """
    
    def __init__(self, model: str) -> None:
        """Initialize the Voyage AI embedding provider.
        
        Args:
            model: The Voyage AI model name (e.g., 'voyage-3').
        """
        self.model = model
        self.client = Client()
        
    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of query texts using Voyage AI.
        
        Args:
            texts: List of text strings to embed.
            
        Returns:
            List of embedding vectors.
        """
        return self.client.embed(texts, model=self.model, input_type="query").embeddings
    
    def embed_document(self, document: Document) -> list[list[float]]:
        """Embed all chunks of a document using Voyage AI.
        
        Args:
            document: Document object containing chunked pages.
            
        Returns:
            List of embedding vectors for each chunk.
        """
        texts = [doc.chunk_content if doc.chunk_content else "" for doc in (document.chunked_pages or [])]
        return self.client.embed(texts, model=self.model, input_type="document").embeddings

    def warmup(self) -> None:
        """Warmup method for Voyage AI client.
        
        Voyage AI is a remote service, so this is a no-op.
        """
        pass
{%- endif %}

{%- if cookiecutter.use_sentence_transformers %}
from app.core.config import settings as app_settings

class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str) -> None:
        self.model_name = model
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load model to avoid loading at import time."""
        if self._model is None:
            # Ensure the cache directory exists
            app_settings.MODELS_CACHE_DIR.mkdir(exist_ok=True, parents=True)
            self._model = SentenceTransformer(
                self.model_name,
                cache_folder=str(app_settings.MODELS_CACHE_DIR)
            )
        return self._model
        
    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
            ).tolist()
    
    def embed_document(self, document: Document) -> list[list[float]]:
        texts = [doc.chunk_content if doc.chunk_content else "" for doc in (document.chunked_pages or [])]
        return self.embed_queries(texts)

    def warmup(self) -> None:
        """Trigger model download and load into memory."""
        _ = self.model
{%- endif %}

# Embedding orchestrator
class EmbeddingService:
    """Service for managing text embeddings.
    
    Orchestrates embedding operations using a configured embedding provider.
    Supports multiple backends: OpenAI, Voyage AI, and Sentence Transformers.
    """
    
    def __init__(self, settings: RAGSettings):
        """Initialize the embedding service.
        
        Args:
            settings: RAG configuration settings.
        """
        config = settings.embeddings_config
        {%- if cookiecutter.use_openai_embeddings %}
        self.provider = OpenAIEmbeddingProvider(model=config.model)
        {%- elif cookiecutter.use_voyage_embeddings %}
        self.provider = VoyageEmbeddingProvider(model=config.model)
        {%- elif cookiecutter.use_sentence_transformers %}
        self.provider = SentenceTransformerEmbeddingProvider(model=config.model)
        {%- endif %}
        
    def embed_query(self, query: str) -> list[float]:
        """Embed a single query text.
        
        Args:
            query: The text query to embed.
            
        Returns:
            Embedding vector for the query.
        """
        return self.provider.embed_queries([query])[0]
    
    def embed_document(self, document: Document) -> list[list[float]]:
        """Embed all chunks of a document.
        
        Args:
            document: Document object containing chunked pages.
            
        Returns:
            List of embedding vectors for each chunk.
        """
        return self.provider.embed_document(document)

    def warmup(self) -> None:
        """Ensures the provider is ready for usage."""
        self.provider.warmup()

{%- endif %}