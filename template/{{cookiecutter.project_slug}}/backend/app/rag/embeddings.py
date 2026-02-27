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
    @abstractmethod
    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        pass

    @abstractmethod
    def embed_document(self, document: Document) -> list[list[float]]:
        pass

{%- if cookiecutter.use_openai_embeddings %}
class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str) -> None:
        self.model = model
        self.client = OpenAI()
        
    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [data.embedding for data in response.data]
    
    def embed_document(self, document: Document) -> list[list[float]]:
        texts = [doc.content for doc in document.pages]
        return self.embed_queries(texts)
{%- endif %}

{%- if cookiecutter.use_voyage_embeddings %}
class VoyageEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str) -> None:
        self.model = model
        self.client = Client()
        
    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self.client.embed(texts, model=self.model, input_type="query").embeddings
    
    def embed_document(self, document: Document) -> list[list[float]]:
        texts = [doc.content for doc in document.pages]
        return self.client.embed(texts, model=self.model, input_type="document").embeddings
{%- endif %}

{%- if cookiecutter.use_sentence_transformers %}
class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str) -> None:
        #TODO add model preload in fastAPI lifespan?
        self.model = SentenceTransformer(model)
        
    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
            ).tolist()
    
    def embed_document(self, document: Document) -> list[list[float]]:
        texts = [doc.content for doc in document.pages]
        return self.embed_queries(texts)
{%- endif %}

# Embedding orchestrator
class EmbeddingService:
    def __init__(self, settings: RAGSettings):
        config = settings.embeddings_config
        {%- if cookiecutter.use_openai_embeddings %}
        self.provider = OpenAIEmbeddingProvider(model=config.model)
        {%- elif cookiecutter.use_voyage_embeddings %}
        self.provider = VoyageEmbeddingProvider(model=config.model)
        {%- elif cookiecutter.use_sentence_transformers %}
        self.provider = SentenceTransformerEmbeddingProvider(model=config.model)
        {%- endif %}
        
    def embed_query(self, query: str) -> list[float]:
        return self.provider.embed_queries([query])[0]
    
    def embed_document(self, document: Document) -> list[list[float]]:
        return self.provider.embed_document(document)

{%- endif %}