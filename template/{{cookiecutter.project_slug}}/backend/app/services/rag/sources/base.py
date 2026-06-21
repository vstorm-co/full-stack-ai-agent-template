{%- if cookiecutter.enable_rag %}
"""Base class for RAG document source connectors."""

from __future__ import annotations

import logging
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.rag.ingestion import IngestionService
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SourceFile:
    """Metadata about a file available in a source."""

    id: str
    name: str
    mime_type: str = ""
    size: int = 0
    path: str = ""


@dataclass
class SyncResult:
    """Result of a sync operation."""

    total_files: int = 0
    ingested: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


class BaseDocumentSource(ABC):
    """Abstract base for document source connectors.

    Implementations fetch files from external sources (Google Drive, S3, etc.)
    and download them locally for ingestion into the RAG pipeline.
    """

    @abstractmethod
    async def list_files(self, path: str = "", extensions: list[str] | None = None) -> list[SourceFile]:
        """List available files in the source.

        Args:
            path: Path/folder to list (source-specific format).
            extensions: Optional list of extensions to filter by (e.g. [".pdf", ".docx"]).

        Returns:
            List of SourceFile metadata objects.
        """

    @abstractmethod
    async def download_file(self, file_id: str, dest_dir: Path) -> Path:
        """Download a file from the source to a local directory.

        Args:
            file_id: Source-specific file identifier.
            dest_dir: Local directory to download to.

        Returns:
            Path to the downloaded file.
        """

    async def sync(
        self,
        collection_name: str,
        ingestion_service: "IngestionService",
        path: str = "",
        extensions: list[str] | None = None,
    ) -> SyncResult:
        """Sync files from source into a RAG collection.

        Lists files, downloads each, and ingests via IngestionService.

        Args:
            collection_name: Target collection name.
            ingestion_service: Service to handle file ingestion.
            path: Source path/folder to sync from.
            extensions: File extensions to include.

        Returns:
            SyncResult with counts of ingested/skipped/failed files.
        """
        result = SyncResult()
        files = await self.list_files(path=path, extensions=extensions)
        result.total_files = len(files)

        with tempfile.TemporaryDirectory(prefix="rag_sync_") as tmp_dir:
            dest = Path(tmp_dir)
            for source_file in files:
                try:
                    local_path = await self.download_file(source_file.id, dest)
                    # Pass source-specific path for deduplication
                    source_uri = f"{source_file.path or source_file.id}"
                    ingest_result = await ingestion_service.ingest_file(
                        filepath=local_path,
                        collection_name=collection_name,
                        source_path=source_uri,
                    )
                    if ingest_result.status.value == "done":
                        result.ingested += 1
                    else:
                        result.failed += 1
                        result.errors.append(f"{source_file.name}: {ingest_result.error_message}")
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"{source_file.name}: {e}")
                    logger.error("Failed to sync %s: %s", source_file.name, e)

        return result
{%- endif %}
