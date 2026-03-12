{%- if cookiecutter.enable_rag %}
"""RAG tool for agent knowledge base search."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.rag.retrieval import BaseRetrievalService


@lru_cache(maxsize=1)
def _get_retrieval_service_cached() -> "BaseRetrievalService":
    """Get cached retrieval service singleton.

    This function uses lru_cache to create a cached singleton of the
    RetrievalService. The cache is initialized on first call and reused
    for subsequent calls.

    Returns:
        Configured BaseRetrievalService instance.
    """
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
    return MilvusRetrievalService(vector_store, settings)


def get_retrieval_service() -> "BaseRetrievalService":
    """Get the cached RetrievalService instance.

    This function provides access to a cached RetrievalService singleton.
    It uses lru_cache for proper caching behavior.

    Returns:
        Configured BaseRetrievalService instance.
    """
    return _get_retrieval_service_cached()


async def search_knowledge_base(
    query: str,
    collection: str = "documents",
    top_k: int = 5,
) -> str:
    """Search the knowledge base and return formatted results.

    Args:
        query: The search query string.
        collection: Name of the collection to search (default: "documents").
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


def _run_async_search(query: str, collection: str, top_k: int) -> str:
    """Run async search in a dedicated event loop within a thread.
    
    This creates a fresh event loop for each call, avoiding event loop
    conflicts with the main thread or other async contexts.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            search_knowledge_base(query, collection, top_k)
        )
    finally:
        loop.close()


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
    logger.debug(
        "search_knowledge_base_sync called: query=%s, collection=%s, top_k=%s",
        query,
        collection,
        top_k,
    )
    try:
        # Use ThreadPoolExecutor with a dedicated event loop
        # This avoids "Event loop is closed" errors when asyncio.run()
        # is called multiple times or from within an async context
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_async_search, query, collection, top_k
            )
            result = future.result()
        logger.debug("search_knowledge_base_sync completed successfully")
        return result
    except Exception as e:
        logger.error(
            "search_knowledge_base_sync failed: %s",
            str(e),
            exc_info=True,
        )
        raise

{%- if cookiecutter.use_crewai %}
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class SearchDocumentsInput(BaseModel):
    query: str = Field(..., description="Query string for searching the knowledge base")
    collection: str = Field(default="documents", description="Collection to search")
    top_k: int = Field(default=5, description="Number of top results to return")

class SearchKnowledgeBase(BaseTool):
    """Search the knowledge base and return formatted results.    
    """
    name: str = "search_documents"
    description: str = (
        "Search the knowledge base for relevant documents. "
        "Return formatted excerpts with scores and sources."
    )
    args_schema: type[BaseTool] = SearchDocumentsInput

    def _run(self, query: str, collection: str = "documents", top_k: int = 5) -> str:
        # Use sync wrapper for CrewAI
        return search_knowledge_base_sync(query, collection, top_k)

    async def _arun(self, query: str, collection: str = "documents", top_k: int = 5) -> str:
        # Async version
        return await search_knowledge_base(query, collection, top_k)
    
{%- else %}
__all__ = ["search_knowledge_base", "search_knowledge_base_sync"]
{%- endif %}

{%- else %}
"""RAG tool - not configured."""
{%- endif %}
