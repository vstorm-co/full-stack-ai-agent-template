{%- if cookiecutter.enable_rag %}
{% if cookiecutter.use_milvus %}
"""
RAG CLI commands for document management and retrieval.

Commands:
    rag-collections - List collections with stats
    rag-ingest      - Ingest file/directory
    rag-search      - Search knowledge base
    rag-drop        - Drop collection
    rag-stats       - Overall RAG system statistics
"""
import asyncio
import os
from pathlib import Path

import click

from app.commands import command, info, success, error, warning
from app.rag.config import RAGSettings
from app.rag.documents import DocumentProcessor
from app.rag.embeddings import EmbeddingService
from app.rag.ingestion import IngestionService
from app.rag.retrieval import MilvusRetrievalService
from app.rag.vectorstore import MilvusVectorStore


def get_rag_services() -> tuple[RAGSettings, MilvusVectorStore, DocumentProcessor, MilvusRetrievalService, IngestionService]:
    """Initialize RAG services for CLI usage.
    
    Creates and returns all necessary RAG service components:
    - Settings (RAG configuration)
    - Vector store (Milvus)
    - Document processor
    - Retrieval service
    - Ingestion service
    
    Returns:
        Tuple of (settings, vector_store, processor, retrieval, ingestion) services.
    """
    settings = RAGSettings()
    embedder = EmbeddingService(settings=settings)
    vector_store = MilvusVectorStore(settings=settings, embedding_service=embedder)
    processor = DocumentProcessor(settings=settings)
    retrieval = MilvusRetrievalService(vector_store=vector_store, settings=settings)
    ingestion = IngestionService(processor=processor, vector_store=vector_store)
    return settings, vector_store, processor, retrieval, ingestion


async def list_collections_async(vector_store: MilvusVectorStore) -> None:
    """List all collections with their stats.
    
    Args:
        vector_store: The Milvus vector store to query.
    """
    collection_names = await vector_store.client.list_collections()
    
    if not collection_names:
        info("No collections found.")
        return
    
    click.echo(f"\nFound {len(collection_names)} collection(s):\n")
    
    for name in collection_names:
        try:
            info_obj = await vector_store.get_collection_info(name)
            click.echo(f"  {name}")
            click.echo(f"    Vectors: {info_obj.total_vectors:,}")
            click.echo(f"    Dimension: {info_obj.dim}")
            click.echo(f"    Status: {info_obj.indexing_status}")
            click.echo()
        except Exception as e:
            warning(f"Could not get info for '{name}': {e}")


@command("rag-collections", help="List collections with stats")
def rag_collections():
    """List all available collections in the vector store with their statistics."""
    _, vector_store, _, _, _ = get_rag_services()
    asyncio.run(list_collections_async(vector_store))


async def ingest_path_async(
    path: str,
    collection: str,
    recursive: bool,
    vector_store: MilvusVectorStore,
    processor: DocumentProcessor,
    ingestion: IngestionService,
) -> None:
    """Ingest files from a path (file or directory).
    
    Args:
        path: Path to a file or directory to ingest.
        collection: Target collection name.
        recursive: Whether to recursively process directories.
        vector_store: The Milvus vector store.
        processor: Document processor for parsing files.
        ingestion: Ingestion service for storing documents.
    """
    target_path = Path(path).resolve()
    
    if not target_path.exists():
        error(f"Path does not exist: {target_path}")
        return
    
    # Collect files to process
    if target_path.is_file():
        files = [target_path]
    elif target_path.is_dir():
        if recursive:
            files = list(target_path.rglob("*"))
            files = [f for f in files if f.is_file() and not f.name.startswith(".")]
        else:
            files = list(target_path.iterdir())
            files = [f for f in files if f.is_file() and not f.name.startswith(".")]
    else:
        error(f"Invalid path: {target_path}")
        return
    
    if not files:
        warning("No files found to ingest.")
        return
    
    # Filter by allowed extensions
    allowed_extensions = {f".{ext.value}" for ext in processor.parser.allowed}
    files = [f for f in files if f.suffix.lower() in allowed_extensions]
    
    if not files:
        warning(f"No supported files found. Allowed: {', '.join(allowed_extensions)}")
        return
    
    info(f"Ingesting {len(files)} file(s) into collection '{collection}'...")
    
    success_count = 0
    error_count = 0
    
    for filepath in files:
        try:
            result = await ingestion.ingest_file(filepath=filepath, collection_name=collection)
            if result.status.value == "done":
                success_count += 1
                click.echo(f"  ✓ {filepath.name}")
            else:
                error_count += 1
                click.echo(f"  ✗ {filepath.name}: {result.error_message}")
        except Exception as e:
            error_count += 1
            click.echo(f"  ✗ {filepath.name}: {str(e)}")
    
    click.echo()
    success(f"Ingested: {success_count} files")
    if error_count > 0:
        error(f"Failed: {error_count} files")


@command("rag-ingest", help="Ingest file/directory into knowledge base")
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--collection",
    "-c",
    default="documents",
    help="Collection name (default: documents)",
)
@click.option(
    "--recursive/--no-recursive",
    "-r",
    default=False,
    help="Recursively process directories (default: False)",
)
def rag_ingest(path: str, collection: str, recursive: bool):
    """
    Ingest a file or directory into the knowledge base.
    
    PATH: Path to a file or directory to ingest.
    
    Example:
        project cmd rag-ingest ./docs
        project cmd rag-ingest ./docs --collection my_docs --recursive
    """
    _, vector_store, processor, _, ingestion = get_rag_services()
    asyncio.run(
        ingest_path_async(path, collection, recursive, vector_store, processor, ingestion)
    )


async def search_async(
    query: str,
    collection: str,
    top_k: int,
    retrieval: MilvusRetrievalService,
) -> None:
    """Search the knowledge base.
    
    Args:
        query: The search query.
        collection: Target collection name.
        top_k: Number of results to return.
        retrieval: Retrieval service for searching.
    """
    info(f"Searching collection '{collection}' for: \"{query}\"")
    click.echo()
    
    results = await retrieval.retrieve(
        query=query,
        collection_name=collection,
        limit=top_k,
    )
    
    if not results:
        warning("No results found.")
        return
    
    for i, result in enumerate(results, 1):
        click.echo(f"--- Result {i} (score: {result.score:.4f}) ---")
        
        # Show source info if available
        if result.metadata:
            filename = result.metadata.get("filename", "Unknown")
            page_num = result.metadata.get("page_num", "?")
            click.echo(f"Source: {filename} (page {page_num})")
        
        # Show content (truncated)
        content = result.content[:500]
        if len(result.content) > 500:
            content += "..."
        click.echo(content)
        click.echo()


@command("rag-search", help="Search knowledge base")
@click.argument("query")
@click.option(
    "--collection",
    "-c",
    default="documents",
    help="Collection name (default: documents)",
)
@click.option(
    "--top-k",
    "-k",
    default=4,
    type=int,
    help="Number of results to return (default: 4)",
)
def rag_search(query: str, collection: str, top_k: int):
    """
    Search the knowledge base for relevant content.
    
    QUERY: The search query.
    
    Example:
        project cmd rag-search "what is fastapi"
        project cmd rag-search "deployment guide" --collection docs --top-k 10
    """
    _, _, _, retrieval, _ = get_rag_services()
    asyncio.run(search_async(query, collection, top_k, retrieval))


async def drop_collection_async(
    collection: str,
    yes: bool,
    vector_store: MilvusVectorStore
) -> None:
    """Drop a collection.
    
    Args:
        collection: Name of the collection to drop.
        yes: Whether to skip confirmation prompt.
        vector_store: The Milvus vector store.
    """
    if not yes:
        click.confirm(
            f"Are you sure you want to drop collection '{collection}'? This cannot be undone.",
            abort=True,
        )
    
    try:
        await vector_store.delete_collection(collection)
        success(f"Collection '{collection}' dropped successfully.")
    except Exception as e:
        error(f"Failed to drop collection: {e}")


@command("rag-drop", help="Drop a collection")
@click.argument("collection")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def rag_drop(collection: str, yes: bool):
    """
    Drop a collection and all its data.
    
    COLLECTION: Name of the collection to drop.
    
    Example:
        project cmd rag-drop my_collection
        project cmd rag-drop my_collection --yes
    """
    _, vector_store, _, _, _ = get_rag_services()
    asyncio.run(drop_collection_async(collection, yes, vector_store))


@command("rag-stats", help="Show overall RAG system statistics")
def rag_stats():
    """Display overall RAG system statistics."""
    settings, vector_store, _, _, _ = get_rag_services()
    
    asyncio.run(stats_async(settings, vector_store))


async def stats_async(
    settings: RAGSettings,
    vector_store: MilvusVectorStore
) -> None:
    """Show RAG system statistics.
    
    Args:
        settings: RAG configuration settings.
        vector_store: The Milvus vector store.
    """
    click.echo("RAG System Statistics")
    click.echo("=" * 40)
    
    # Collection info
    try:
        collection_names = await vector_store.client.list_collections()
        click.echo(f"\nCollections: {len(collection_names)}")
    except Exception as e:
        warning(f"Could not list collections: {e}")
        collection_names = []
    
    # Configuration
    click.echo("\nConfiguration:")
    click.echo(f"  Embedding model: {settings.embeddings_config.model}")
    click.echo(f"  Embedding dimension: {settings.embeddings_config.dim}")
    click.echo(f"  Chunk size: {settings.chunk_size}")
    click.echo(f"  Chunk overlap: {settings.chunk_overlap}")
    click.echo(f"  Parser method: {settings.pdf_parser.method}")
    
    # Per-collection stats
    if collection_names:
        click.echo("\nCollection Details:")
        total_vectors = 0
        for name in collection_names:
            try:
                info_obj = await vector_store.get_collection_info(name)
                click.echo(f"  {name}:")
                click.echo(f"    Vectors: {info_obj.total_vectors:,}")
                total_vectors += info_obj.total_vectors
            except Exception:
                click.echo(f"  {name}: Error getting info")
        
        click.echo(f"\nTotal vectors: {total_vectors:,}")
    
    click.echo()


{% else %}
# Dummy commands when Milvus is not enabled
import click
from app.commands import command, warning


@command("rag-collections", help="List collections (requires Milvus)")
def rag_collections():
    warning("RAG collections require Milvus to be enabled.")


@command("rag-ingest", help="Ingest files (requires Milvus)")
def rag_ingest():
    warning("RAG ingestion requires Milvus to be enabled.")


@command("rag-search", help="Search knowledge base (requires Milvus)")
def rag_search():
    warning("RAG search requires Milvus to be enabled.")


@command("rag-drop", help="Drop collection (requires Milvus)")
def rag_drop():
    warning("RAG drop requires Milvus to be enabled.")


@command("rag-stats", help="Show RAG stats (requires Milvus)")
def rag_stats():
    warning("RAG stats require Milvus to be enabled.")
{%- endif %}
{%- endif %}
