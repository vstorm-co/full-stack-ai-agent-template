from abc import ABC, abstractmethod

from openai import OpenAI

from app.core.config import settings as app_settings
from app.services.rag.config import RAGSettings
from app.services.rag.models import Document


def _chunk_texts(document: Document) -> list[str]:
    return [
        doc.chunk_content if doc.chunk_content else "" for doc in (document.chunked_pages or [])
    ]


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        pass

    @abstractmethod
    def embed_document(self, document: Document) -> list[list[float]]:
        pass

    @abstractmethod
    def warmup(self) -> None:
        """Ensures the model is loaded and ready for inference."""
        pass


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider using the OpenAI API.

    Uses OpenAI's embedding models to generate text embeddings.
    """

    def __init__(self, model: str, api_key: str = "", base_url: str | None = None) -> None:
        """Initialize the OpenAI embedding provider.

        Args:
            model: The OpenAI embedding model name (e.g., 'text-embedding-3-small').
            api_key: API key; falls back to OPENAI_API_KEY env var when empty.
            base_url: Override base URL (e.g. OpenRouter-compatible endpoint).
        """
        self.model = model
        self.client = OpenAI(api_key=api_key or None, base_url=base_url)

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [data.embedding for data in response.data]

    def embed_document(self, document: Document) -> list[list[float]]:
        return self.embed_queries(_chunk_texts(document))

    def warmup(self) -> None:
        pass


class EmbeddingService:
    def __init__(self, settings: RAGSettings):
        config = settings.embeddings_config
        self.expected_dim = config.dim
        self.provider = OpenAIEmbeddingProvider(
            model=config.model,
            api_key=app_settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )

    def embed_query(self, query: str) -> list[float]:
        result = self.provider.embed_queries([query])[0]
        if len(result) != self.expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.expected_dim}, "
                f"got {len(result)}. Check your embedding model configuration."
            )
        return result

    def embed_document(self, document: Document) -> list[list[float]]:
        results = self.provider.embed_document(document)
        if results and len(results[0]) != self.expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.expected_dim}, "
                f"got {len(results[0])}. Check your embedding model configuration."
            )
        return results

    def warmup(self) -> None:
        self.provider.warmup()
