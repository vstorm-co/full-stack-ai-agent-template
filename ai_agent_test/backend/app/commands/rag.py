"""
RAG CLI commands for document management and retrieval.

Commands:
    rag-collections   - List collections with stats
    rag-ingest        - Ingest file/directory
    rag-search        - Search knowledge base
    rag-drop          - Drop collection
    rag-stats         - Overall RAG system statistics
    rag-sources       - List configured sync sources
    rag-source-add    - Add a new sync source
    rag-source-remove - Remove a sync source
    rag-source-sync   - Trigger sync for a source (or all)
"""

import asyncio
from pathlib import Path

import click

from app.commands import command, error, info, success, warning
from app.services.rag.config import DocumentExtensions, RAGSettings
from app.services.rag.documents import DocumentProcessor
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.ingestion import IngestionService
from app.services.rag.retrieval import RetrievalService
from app.services.rag.vectorstore import BaseVectorStore, MilvusVectorStore


def get_rag_services() -> tuple[
    RAGSettings, BaseVectorStore, DocumentProcessor, RetrievalService, IngestionService
]:
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
    retrieval = RetrievalService(vector_store=vector_store, settings=settings)
    ingestion = IngestionService(processor=processor, vector_store=vector_store)
    return settings, vector_store, processor, retrieval, ingestion


async def list_collections_async(vector_store: BaseVectorStore) -> None:
    """List all collections with their stats.

    Args:
        vector_store: The Milvus vector store to query.
    """
    collection_names = await vector_store.list_collections()

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
def rag_collections() -> None:
    """List all available collections in the vector store with their statistics."""
    _, vector_store, _, _, _ = get_rag_services()
    asyncio.run(list_collections_async(vector_store))


async def ingest_path_async(
    path: str,
    collection: str,
    recursive: bool,
    vector_store: BaseVectorStore,
    processor: DocumentProcessor,
    ingestion: IngestionService,
    replace: bool = True,
    sync_mode: str = "full",
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
    allowed_extensions = {ext.value for ext in DocumentExtensions}
    files = [f for f in files if f.suffix.lower() in allowed_extensions]

    if not files:
        warning(f"No supported files found. Allowed: {', '.join(allowed_extensions)}")
        return

    import hashlib

    from tqdm import tqdm

    from app.db.session import get_db_context
    from app.services.rag_document import RAGDocumentService
    from app.services.rag_sync import RAGSyncService

    info(f"Syncing {len(files)} file(s) into '{collection}' (mode={sync_mode})...")

    success_count = 0
    error_count = 0
    replaced_count = 0
    skipped_count = 0
    # Create SyncLog
    async with get_db_context() as db:
        sync_log = await RAGSyncService(db).create_sync_log(
            source="local", collection_name=collection, mode=sync_mode
        )
        sync_log_id = str(sync_log.id)

    with tqdm(files, unit="file", desc="Syncing", ncols=80) as pbar:
        for filepath in pbar:
            pbar.set_postfix_str(filepath.name[:30], refresh=True)

            # Sync mode checks
            source_path = str(filepath.resolve())
            if sync_mode in ("new_only", "update_only"):
                existing_id: str | None = await ingestion.find_existing(collection, source_path)

                if sync_mode == "new_only":
                    if existing_id:
                        # File exists — check if content changed via hash
                        file_hash: str = hashlib.sha256(filepath.read_bytes()).hexdigest()
                        existing_hash: str | None = await ingestion.get_existing_hash(
                            collection, source_path
                        )
                        if existing_hash and file_hash == existing_hash:
                            skipped_count += 1
                            continue
                        # Hash changed — will re-ingest below

                elif sync_mode == "update_only":
                    if not existing_id:
                        # Not in collection — skip (update_only ignores new files)
                        skipped_count += 1
                        continue
                    file_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()
                    existing_hash = await ingestion.get_existing_hash(collection, source_path)
                    if existing_hash and file_hash == existing_hash:
                        skipped_count += 1
                        continue

            # Create RAGDocument record in SQL
            async with get_db_context() as db:
                rag_doc = await RAGDocumentService(db).create_document(
                    collection_name=collection,
                    filename=filepath.name,
                    filesize=filepath.stat().st_size,
                    filetype=filepath.suffix.lstrip(".").lower(),
                )
                doc_id = str(rag_doc.id)

            try:
                result = await ingestion.ingest_file(
                    filepath=filepath, collection_name=collection, replace=replace
                )
                if result.status.value == "done":
                    success_count += 1
                    if result.message and "replaced" in result.message:
                        replaced_count += 1
                    async with get_db_context() as db:
                        await RAGDocumentService(db).complete_ingestion(
                            doc_id, vector_document_id=result.document_id
                        )
                else:
                    error_count += 1
                    tqdm.write(f"  ✗ {filepath.name}: {result.error_message}")
                    async with get_db_context() as db:
                        await RAGDocumentService(db).fail_ingestion(
                            doc_id, error_message=result.error_message or "Unknown error"
                        )
            except Exception as e:
                error_count += 1
                tqdm.write(f"  ✗ {filepath.name}: {e!s}")
                async with get_db_context() as db:
                    await RAGDocumentService(db).fail_ingestion(doc_id, error_message=str(e))
    # Update SyncLog
    async with get_db_context() as db:
        await RAGSyncService(db).complete_sync(
            sync_log_id,
            status="done" if error_count == 0 else "error",
            total_files=len(files),
            ingested=success_count - replaced_count,
            updated=replaced_count,
            skipped=skipped_count,
            failed=error_count,
        )

    click.echo()
    msg = f"Done: {success_count} ingested"
    if replaced_count > 0:
        msg += f" ({replaced_count} updated)"
    if skipped_count > 0:
        msg += f", {skipped_count} skipped"
    success(msg)
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
@click.option(
    "--replace/--no-replace",
    default=True,
    help="Replace existing documents with same source path (default: True)",
)
@click.option(
    "--sync-mode",
    type=click.Choice(["full", "new_only", "update_only"]),
    default="full",
    help="Sync mode: full (replace all), new_only (add new + update changed), update_only (only update changed, skip new)",
)
def rag_ingest(path: str, collection: str, recursive: bool, replace: bool, sync_mode: str) -> None:
    """
    Ingest a file or directory into the knowledge base.

    PATH: Path to a file or directory to ingest.

    Example:
        project cmd rag-ingest ./docs
        project cmd rag-ingest ./docs --sync-mode new_only
        project cmd rag-ingest ./docs --sync-mode update_only
    """
    _, vector_store, processor, _, ingestion = get_rag_services()
    asyncio.run(
        ingest_path_async(
            path, collection, recursive, vector_store, processor, ingestion, replace, sync_mode
        )
    )


async def search_async(
    query: str,
    collection: str,
    top_k: int,
    retrieval: RetrievalService,
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
def rag_search(query: str, collection: str, top_k: int) -> None:
    """
    Search the knowledge base for relevant content.

    QUERY: The search query.

    Example:
        project cmd rag-search "what is fastapi"
        project cmd rag-search "deployment guide" --collection docs --top-k 10
    """
    _, _, _, retrieval, _ = get_rag_services()
    asyncio.run(search_async(query, collection, top_k, retrieval))


async def drop_collection_async(collection: str, yes: bool, vector_store: BaseVectorStore) -> None:
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
def rag_drop(collection: str, yes: bool) -> None:
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
def rag_stats() -> None:
    """Display overall RAG system statistics."""
    settings, vector_store, _, _, _ = get_rag_services()

    asyncio.run(stats_async(settings, vector_store))


async def stats_async(settings: RAGSettings, vector_store: BaseVectorStore) -> None:
    """Show RAG system statistics.

    Args:
        settings: RAG configuration settings.
        vector_store: The Milvus vector store.
    """
    click.echo("RAG System Statistics")
    click.echo("=" * 40)

    # Collection info
    try:
        collection_names = await vector_store.list_collections()
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


@command("rag-sync-gdrive")
@click.option("--collection", "-c", default="documents", help="Target collection name")
@click.option("--folder-id", "-f", default="", help="Google Drive folder ID (empty = root)")
def rag_sync_gdrive(collection: str, folder_id: str) -> None:
    """Sync documents from Google Drive into a RAG collection."""
    from app.services.rag.sources.google_drive import GoogleDriveSource

    _, vector_store, processor, _, ingestion = get_rag_services()
    source = GoogleDriveSource()

    async def _sync() -> None:
        result = await source.sync(
            collection_name=collection,
            ingestion_service=ingestion,
            path=folder_id,
        )
        success(f"Synced {result.ingested}/{result.total_files} files from Google Drive")
        if result.failed:
            for err in result.errors:
                warning(f"  {err}")

    asyncio.run(_sync())


@command("rag-sync-s3")
@click.option("--collection", "-c", default="documents", help="Target collection name")
@click.option("--prefix", "-p", default="", help="S3 prefix (folder path)")
@click.option("--bucket", "-b", default="", help="S3 bucket (empty = default from settings)")
def rag_sync_s3(collection: str, prefix: str, bucket: str) -> None:
    """Sync documents from S3/MinIO into a RAG collection."""
    from app.services.rag.sources.s3 import S3Source

    _, vector_store, processor, _, ingestion = get_rag_services()
    source = S3Source(bucket=bucket)

    async def _sync() -> None:
        result = await source.sync(
            collection_name=collection,
            ingestion_service=ingestion,
            path=prefix,
        )
        success(f"Synced {result.ingested}/{result.total_files} files from S3")
        if result.failed:
            for err in result.errors:
                warning(f"  {err}")

    asyncio.run(_sync())


@command("rag-sources", help="List configured sync sources")
def rag_sources() -> None:
    """List all configured sync sources with their status."""
    from app.db.session import get_db_context

    async def _list() -> None:
        async with get_db_context() as db:
            from app.services.sync_source import SyncSourceService

            svc = SyncSourceService(db)
            sources = await svc.list_sources()

            if not sources:
                info("No sync sources configured.")
                return

            click.echo(f"\nFound {len(sources)} sync source(s):\n")
            for s in sources:
                status_str = s.last_sync_status or "never"
                active_str = "active" if s.is_active else "inactive"
                click.echo(f"  [{active_str}] {s.name} (id={s.id})")
                click.echo(f"    Type: {s.connector_type}")
                click.echo(f"    Collection: {s.collection_name}")
                click.echo(f"    Sync mode: {s.sync_mode}")
                if s.schedule_minutes:
                    click.echo(f"    Schedule: every {s.schedule_minutes} min")
                else:
                    click.echo("    Schedule: manual")
                click.echo(f"    Last sync: {status_str}")
                if s.last_error:
                    click.echo(f"    Last error: {s.last_error}")
                click.echo()

    asyncio.run(_list())


@command("rag-source-add", help="Add a new sync source")
@click.option("--name", required=True, help="Source name")
@click.option("--type", "connector_type", required=True, help="Connector type (e.g. gdrive, s3)")
@click.option("--collection", required=True, help="Target collection name")
@click.option("--config", "config_json", required=True, help="Config JSON string")
@click.option(
    "--sync-mode",
    default="new_only",
    type=click.Choice(["full", "new_only", "update_only"]),
    help="Sync mode",
)
@click.option(
    "--schedule",
    "schedule_minutes",
    type=int,
    default=0,
    help="Schedule interval in minutes (0=manual)",
)
def rag_source_add(
    name: str,
    connector_type: str,
    collection: str,
    config_json: str,
    sync_mode: str,
    schedule_minutes: int,
) -> None:
    """
    Add a new sync source configuration.

    Example:
        project cmd rag-source-add --name "My Drive" --type gdrive --collection docs \\
            --config '{"folder_id": "abc123"}' --sync-mode new_only
    """
    import json as _json

    try:
        config_dict = _json.loads(config_json)
    except _json.JSONDecodeError as e:
        error(f"Invalid JSON config: {e}")
        return

    from app.schemas.sync_source import SyncSourceCreate

    data = SyncSourceCreate(
        name=name,
        connector_type=connector_type,
        collection_name=collection,
        config=config_dict,
        sync_mode=sync_mode,
        schedule_minutes=schedule_minutes if schedule_minutes > 0 else None,
    )
    from app.db.session import get_db_context

    async def _create() -> None:
        async with get_db_context() as db:
            from app.services.sync_source import SyncSourceService

            svc = SyncSourceService(db)
            try:
                source = await svc.create_source(data)
                success(f"Sync source created: {source.name} (id={source.id})")
            except ValueError as e:
                error(f"Failed to create source: {e}")

    asyncio.run(_create())


@command("rag-source-remove", help="Remove a sync source")
@click.argument("source_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def rag_source_remove(source_id: str, yes: bool) -> None:
    """
    Remove a sync source configuration.

    SOURCE_ID: The ID of the sync source to remove.

    Example:
        project cmd rag-source-remove abc-123-def
    """
    if not yes:
        click.confirm(f"Are you sure you want to remove sync source '{source_id}'?", abort=True)
    from app.db.session import get_db_context

    async def _remove() -> None:
        async with get_db_context() as db:
            from app.services.sync_source import SyncSourceService

            svc = SyncSourceService(db)
            try:
                await svc.delete_source(source_id)
                success(f"Sync source '{source_id}' removed.")
            except Exception as e:
                error(f"Failed to remove source: {e}")

    asyncio.run(_remove())


@command("rag-source-sync", help="Trigger sync for a source")
@click.argument("source_id", required=False)
@click.option("--all", "sync_all", is_flag=True, help="Sync all active sources")
def rag_source_sync(source_id: str | None, sync_all: bool) -> None:
    """
    Trigger sync for a configured source (or all active sources).

    SOURCE_ID: The ID of the sync source to sync (optional if --all).

    Example:
        project cmd rag-source-sync abc-123-def
        project cmd rag-source-sync --all
    """
    if not source_id and not sync_all:
        error("Provide a SOURCE_ID or use --all to sync all active sources.")
        return
    from app.db.session import get_db_context

    async def _sync() -> None:
        async with get_db_context() as db:
            from app.services.sync_source import SyncSourceService

            svc = SyncSourceService(db)

            if sync_all:
                sources = await svc.list_sources(is_active=True)
                if not sources:
                    warning("No active sync sources found.")
                    return
                info(f"Triggering sync for {len(sources)} active source(s)...")
                for s in sources:
                    try:
                        log = await svc.trigger_sync(str(s.id))
                        success(f"  {s.name}: sync started (log_id={log.id})")
                    except Exception as e:
                        error(f"  {s.name}: failed - {e}")
            else:
                try:
                    assert source_id is not None
                    log = await svc.trigger_sync(source_id)
                    success(f"Sync triggered (log_id={log.id})")
                except Exception as e:
                    error(f"Failed to trigger sync: {e}")

    asyncio.run(_sync())
