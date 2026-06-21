{%- if cookiecutter.enable_rag %}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""RAG tool for agent knowledge base search."""

import contextvars
import logging
from typing import TYPE_CHECKING, Any

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.retrieval import RetrievalService
{%- if cookiecutter.use_milvus %}
from app.services.rag.vectorstore import MilvusVectorStore
{%- elif cookiecutter.use_qdrant %}
from app.services.rag.vectorstore import QdrantVectorStore
{%- elif cookiecutter.use_chromadb %}
from app.services.rag.vectorstore import ChromaVectorStore
{%- elif cookiecutter.use_pgvector %}
from app.services.rag.vectorstore import PgVectorStore
{%- endif %}

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.services.rag.retrieval import BaseRetrievalService

_retrieval_service: "BaseRetrievalService | None" = None


def get_retrieval_service() -> "BaseRetrievalService":
    """Get or create retrieval service singleton."""
    global _retrieval_service
    if _retrieval_service is not None:
        return _retrieval_service

    rag_settings = settings.rag
    embedding_service = EmbeddingService(rag_settings)
{%- if cookiecutter.use_milvus %}
    vector_store = MilvusVectorStore(rag_settings, embedding_service)
{%- elif cookiecutter.use_qdrant %}
    vector_store = QdrantVectorStore(rag_settings, embedding_service)
{%- elif cookiecutter.use_chromadb %}
    vector_store = ChromaVectorStore(rag_settings, embedding_service)
{%- elif cookiecutter.use_pgvector %}
    vector_store = PgVectorStore(rag_settings, embedding_service)
{%- endif %}
    _retrieval_service = RetrievalService(vector_store, rag_settings)
    return _retrieval_service


def _format_results(results: list[Any]) -> str:
    if not results:
        return "No relevant documents found in the knowledge base."
    formatted = []
    for i, result in enumerate(results, start=1):
        source = result.metadata.get("filename", "unknown")
        page = result.metadata.get("page_num", "")
        chunk = result.metadata.get("chunk_num", "")
        col = result.metadata.get("collection", "")
        page_info = f", page {page}" if page else ""
        chunk_info = f", chunk {chunk}" if chunk else ""
        col_info = f" [{col}]" if col else ""
        formatted.append(
            f"[{i}] Source: {source}{page_info}{chunk_info}{col_info} (score: {result.score:.3f})\n"
            f"{result.content}"
        )
    return "Search results (cite inline using [1], [2], etc. — do NOT list sources at the end):\n\n" + "\n\n".join(formatted)


{%- if cookiecutter.enable_teams %}
# ContextVar set by non-PydanticAI frameworks before each agent invocation so that
# the tool can read the active KB collections without needing explicit Deps injection.
# Default is None (not []) — mutable defaults on ContextVar are a foot-gun
# because every reader gets the same shared list. Callers should treat None
# as "no collections active".
_active_kb_collections: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "_active_kb_collections", default=None
)


async def search_knowledge_base(
    query: str,
    kb_collection_names: list[str] | None = None,
    top_k: int = 5,
) -> str:
    """Search the knowledge base and return formatted results.

    Args:
        query: The search query string.
        kb_collection_names: Vector-store collection names resolved server-side from the
            conversation's active_knowledge_base_ids. Never supplied by the LLM directly —
            injected via PydanticAI Deps or the _active_kb_collections ContextVar.
        top_k: Number of top results to retrieve (default: 5).
    """
    resolved = kb_collection_names if kb_collection_names else (_active_kb_collections.get() or [])
    if not resolved:
        return "No active knowledge bases selected for this conversation."

    service: Any = get_retrieval_service()
    try:
        if len(resolved) == 1:
            results = await service.retrieve(
                query=query, collection_name=resolved[0], limit=top_k
            )
        else:
            results = await service.retrieve_multi(
                query=query, collection_names=resolved, limit=top_k
            )
    except Exception as e:
        logger.error("Knowledge base search failed: %s", e, exc_info=True)
        raise ExternalServiceError(
            message="Knowledge base search failed",
            details={"query": query, "error": str(e)},
        ) from e

    return _format_results(results)

{%- else %}
async def search_knowledge_base(
    query: str,
    collection: str | None = None,
    collections: list[str] | None = None,
    top_k: int = 5,
) -> str:
    """Search the knowledge base and return formatted results.

    Args:
        query: The search query string.
        collection: Name of a single collection. If None, uses settings.rag.collection_name.
        collections: List of collection names for cross-collection search (overrides collection).
        top_k: Number of top results to retrieve (default: 5).
    """
    service: Any = get_retrieval_service()

    default_collection = settings.rag.collection_name
    target_collection = collection or default_collection

    if collections and len(collections) > 1:
        results = await service.retrieve_multi(
            query=query,
            collection_names=collections,
            limit=top_k,
        )
    elif target_collection == "all":
        try:
            all_collections = await service.store.list_collections()
            if not all_collections:
                return "No collections found in the knowledge base."
            if len(all_collections) == 1:
                results = await service.retrieve(
                    query=query, collection_name=all_collections[0], limit=top_k
                )
            else:
                results = await service.retrieve_multi(
                    query=query, collection_names=all_collections, limit=top_k
                )
        except Exception as e:
            logger.error("Failed to list collections: %s", e, exc_info=True)
            raise ExternalServiceError(
                message="Failed to list knowledge base collections",
                details={"error": str(e)},
            ) from e
    else:
        results = await service.retrieve(
            query=query,
            collection_name=target_collection,
            limit=top_k,
        )

    return _format_results(results)

{%- endif %}

__all__ = ["search_knowledge_base"]

{%- else %}
"""RAG tool - not configured."""
{%- endif %}
