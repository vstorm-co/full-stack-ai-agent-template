{%- if cookiecutter.enable_rag %}
"""RAG tool for agent knowledge base search."""

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.rag.retrieval import BaseRetrievalService


# Module-level lazy singleton for RetrievalService
_retrieval_service: "BaseRetrievalService | None" = None


def get_retrieval_service() -> "BaseRetrievalService":
    """Get or create the module-level lazy singleton RetrievalService.

    This function initializes the service on first call and caches it for
    subsequent calls. The service is created with dependencies from the
    application state.

    Returns:
        Configured BaseRetrievalService instance.
    """
    global _retrieval_service

    if _retrieval_service is None:
        # Import here to avoid circular imports at module load time
{%- if cookiecutter.use_milvus %}
        from app.rag.retrieval import MilvusRetrievalService
        from app.rag.vectorstore import MilvusVectorStore
{%- else %}
        raise RuntimeError("RAG requires Milvus vector store. Please enable use_milvus.")
{%- endif %}
        from app.rag.embeddings import EmbeddingService
        from app.rag.config import RAGSettings

        settings = RAGSettings()
        embedding_service = EmbeddingService(settings)
        vector_store = MilvusVectorStore(settings, embedding_service)
        _retrieval_service = MilvusRetrievalService(vector_store, settings)

    return _retrieval_service


async def search_knowledge_base(
    query: str,
    collection: str = "default",
    top_k: int = 5,
) -> str:
    """Search the knowledge base and return formatted results.

    Args:
        query: The search query string.
        collection: Name of the collection to search (default: "default").
        top_k: Number of top results to retrieve (default: 5).

    Returns:
        Formatted string with search results, including content and scores.
        Each result is formatted as:
        "Document [doc_id]: [content] (score: [score])"
    """
    service = get_retrieval_service()

    results = await service.retrieve(
        query=query,
        collection_name=collection,
        limit=top_k,
    )

    if not results:
        return "No relevant documents found in the knowledge base."

    # Format results as a readable string
    formatted_results = []
    for i, result in enumerate(results, start=1):
        doc_info = ""
        if result.metadata.get("filename"):
            doc_info = f" (source: {result.metadata['filename']})"

        formatted_results.append(
            f"[{i}] Score: {result.score:.3f}{doc_info}\n"
            f"Content: {result.content}"
        )

    return "\n\n".join(formatted_results)


def search_knowledge_base_sync(
    query: str,
    collection: str = "default",
    top_k: int = 5,
) -> str:
    """Synchronous wrapper for search_knowledge_base.

    Use this function in CrewAI agents where async tools need to run
    in a synchronous context.

    Args:
        query: The search query string.
        collection: Name of the collection to search (default: "default").
        top_k: Number of top results to retrieve (default: 5).

    Returns:
        Formatted string with search results.
    """
    return asyncio.run(search_knowledge_base(query, collection, top_k))


__all__ = ["search_knowledge_base", "search_knowledge_base_sync"]

{%- else %}
"""RAG tool - not configured."""
{%- endif %}
