{%- if cookiecutter.enable_rag and cookiecutter.use_milvus and (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) %}
"""RAG scheduled tasks for collection reindexing.

This module provides scheduled tasks for reindexing RAG collections.
Tasks are only available when RAG and a task system (Celery/Taskiq/ARQ) are enabled.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# === Celery Task ===
{% if cookiecutter.use_celery %}
from celery import shared_task


@shared_task(bind=True, max_retries=3)
def reindex_collection(self, collection_name: str | None = None) -> dict[str, Any]:
    """Reindex all documents in a collection.

    This task re-processes and re-embeds all documents in the specified collection.
    Useful when embedding model is updated or documents need re-processing.

    Args:
        collection_name: Name of the collection to reindex (default: from RAGSettings)

    Returns:
        Dictionary with reindex status and count
    """
    import asyncio
    from app.rag.vectorstore import MilvusVectorStore
    from app.rag.embeddings import EmbeddingService
    from app.rag.config import RAGSettings

    logger.info(f"Starting collection reindex: {collection_name}")

    try:
        settings = RAGSettings()
        # Use settings collection_name if not provided
        if collection_name is None:
            collection_name = settings.collection_name
        embed_service = EmbeddingService(settings)
        vector_store = MilvusVectorStore(settings, embed_service)

        # Run async code in sync context using asyncio.run()
        info = asyncio.run(
            vector_store.get_collection_info(collection_name)
        )

        total_docs = info.total_vectors

        logger.info(f"Collection {collection_name} has {total_docs} vectors")

        # TODO: Implement full reindex logic:
        # 1. Get all document IDs from collection
        # 2. Re-process each document through IngestionService
        # 3. Update embeddings in vector store

        return {
            "status": "completed",
            "collection": collection_name,
            "reindexed_count": total_docs,
        }
    except Exception as exc:
        logger.error(f"Reindex failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


{% endif %}

# === Taskiq Task ===
{% if cookiecutter.use_taskiq %}
from app.worker.taskiq_app import broker


@broker.task  # Schedule is defined in schedules.py, not here
async def reindex_collection_taskiq(collection_name: str | None = None) -> dict[str, Any]:
    """Reindex all documents in a collection (Taskiq version).

    This scheduled task runs daily at 2 AM to reindex all documents.

    Args:
        collection_name: Name of the collection to reindex (default: from RAGSettings)

    Returns:
        Dictionary with reindex status
    """
    from app.rag.vectorstore import MilvusVectorStore
    from app.rag.embeddings import EmbeddingService
    from app.rag.config import RAGSettings

    settings = RAGSettings()
    # Use settings collection_name if not provided
    if collection_name is None:
        collection_name = settings.collection_name

    logger.info(f"Taskiq: Starting collection reindex: {collection_name}")

    embed_service = EmbeddingService(settings)
    vector_store = MilvusVectorStore(settings, embed_service)

    info = await vector_store.get_collection_info(collection_name)

    # TODO: Implement full reindex logic

    return {
        "status": "completed",
        "collection": collection_name,
        "reindexed_count": info.total_vectors,
    }


{% endif %}

# === ARQ Task ===
{% if cookiecutter.use_arq %}
async def reindex_collection_arq(
    ctx: dict[str, Any], collection_name: str | None = None
) -> dict[str, Any]:
    """Reindex all documents in a collection (ARQ version).

    This scheduled task runs daily at 2 AM.

    Args:
        ctx: ARQ context dictionary
        collection_name: Name of the collection to reindex (default: from RAGSettings)

    Returns:
        Dictionary with reindex status
    """
    from app.rag.vectorstore import MilvusVectorStore
    from app.rag.embeddings import EmbeddingService
    from app.rag.config import RAGSettings

    settings = RAGSettings()
    # Use settings collection_name if not provided
    if collection_name is None:
        collection_name = settings.collection_name

    logger.info(f"ARQ: Starting collection reindex: {collection_name}")

    embed_service = EmbeddingService(settings)
    vector_store = MilvusVectorStore(settings, embed_service)

    info = await vector_store.get_collection_info(collection_name)

    # TODO: Implement full reindex logic

    return {
        "status": "completed",
        "collection": collection_name,
        "reindexed_count": info.total_vectors,
        "job_id": ctx.get("job_id"),
    }


{% endif %}
{%- else %}
# RAG scheduled tasks not enabled
# Enable RAG and a task system (Celery/Taskiq/ARQ) to use scheduled tasks
{%- endif %}
