{%- if cookiecutter.enable_rag %}
from abc import ABC, abstractmethod

{%- if cookiecutter.use_openai_embeddings %}
from openai import OpenAI

from app.core.config import settings as app_settings
{%- endif %}

{%- if cookiecutter.use_voyage_embeddings %}
from voyageai import Client
{%- endif %}

{%- if cookiecutter.use_sentence_transformers %}
from sentence_transformers import SentenceTransformer

from app.core.config import settings as app_settings
{%- endif %}

{%- if cookiecutter.use_gemini_embeddings %}
from google import genai
from google.genai import types as genai_types

from app.core.config import settings as app_settings
{%- endif %}

from app.services.rag.config import RAGSettings
from app.services.rag.models import Document


def _chunk_texts(document: Document) -> list[str]:
    return [doc.chunk_content if doc.chunk_content else "" for doc in (document.chunked_pages or [])]


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

{%- if cookiecutter.use_openai_embeddings %}
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
{%- endif %}

{%- if cookiecutter.use_voyage_embeddings %}
class VoyageEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str) -> None:
        self.model = model
        self.client = Client()

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self.client.embed(texts, model=self.model, input_type="query").embeddings

    def embed_document(self, document: Document) -> list[list[float]]:
        return self.client.embed(_chunk_texts(document), model=self.model, input_type="document").embeddings

    def warmup(self) -> None:
        pass
{%- endif %}

{%- if cookiecutter.use_gemini_embeddings %}
class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Multimodal: text, images, and documents share the same embedding space."""

    def __init__(self, model: str, api_key: str = "") -> None:
        self.model = model
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        result = self.client.models.embed_content(
            model=self.model,
            contents=texts,
        )
        return [e.values for e in result.embeddings]

    def embed_document(self, document: Document) -> list[list[float]]:
        contents = [chunk.chunk_content or "" for chunk in (document.chunked_pages or [])]
        result = self.client.models.embed_content(
            model=self.model,
            contents=contents,
        )
        return [e.values for e in result.embeddings]

    def embed_image(self, image_bytes: bytes, mime_type: str = "image/png") -> list[float]:
        """Returns a vector in the same embedding space as text — enables cross-modal search."""
        result = self.client.models.embed_content(
            model=self.model,
            contents=[
                genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )
        return result.embeddings[0].values

    def warmup(self) -> None:
        pass
{%- endif %}

{%- if cookiecutter.use_sentence_transformers %}
class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    _model: SentenceTransformer | None

    def __init__(self, model: str) -> None:
        self.model_name = model
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load — avoids loading at import time."""
        if self._model is None:
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
        return self.embed_queries(_chunk_texts(document))

    def warmup(self) -> None:
        """Trigger model download and load into memory."""
        _ = self.model
{%- endif %}

class EmbeddingService:
    def __init__(self, settings: RAGSettings):
        config = settings.embeddings_config
        self.expected_dim = config.dim
        {%- if cookiecutter.use_openai_embeddings %}
        {%- if cookiecutter.use_openrouter %}
        self.provider = OpenAIEmbeddingProvider(
            model=config.model,
            api_key=app_settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )
        {%- else %}
        self.provider = OpenAIEmbeddingProvider(
            model=config.model,
            api_key=app_settings.OPENAI_API_KEY,
        )
        {%- endif %}
        {%- elif cookiecutter.use_voyage_embeddings %}
        self.provider = VoyageEmbeddingProvider(model=config.model)
        {%- elif cookiecutter.use_gemini_embeddings %}
        self.provider = GeminiEmbeddingProvider(model=config.model, api_key=app_settings.GOOGLE_API_KEY)
        {%- elif cookiecutter.use_sentence_transformers %}
        self.provider = SentenceTransformerEmbeddingProvider(model=config.model)
        {%- endif %}

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

{%- endif %}
