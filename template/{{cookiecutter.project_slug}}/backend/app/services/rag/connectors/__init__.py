{%- if cookiecutter.enable_rag %}
"""RAG sync connectors — extensible source adapters for document ingestion."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RemoteFile(BaseModel):
    """Metadata for a file from a remote source."""

    id: str
    name: str
    mime_type: str | None = None
    size: int | None = None
    modified_at: datetime | None = None
    source_path: str  # Dedup key: "gdrive://file_id", "s3://bucket/key"


class BaseSyncConnector(ABC):
    """Base class for all sync source connectors.

    To add a new connector:
    1. Create a new class inheriting BaseSyncConnector
    2. Implement list_files() and download_file()
    3. Define CONFIG_SCHEMA with required/optional fields
    4. Register in CONNECTOR_REGISTRY
    """

    CONNECTOR_TYPE: ClassVar[str] = ""
    DISPLAY_NAME: ClassVar[str] = ""
    CONFIG_SCHEMA: ClassVar[dict[str, dict[str, Any]]] = {}

    @abstractmethod
    async def list_files(self, config: dict) -> list[RemoteFile]:
        """List files available for sync from this source."""

    @abstractmethod
    async def download_file(
        self, file: RemoteFile, dest_dir: Path, config: dict | None = None
    ) -> Path:
        """Download a single file to local temp directory. Returns local file path."""

    async def validate_config(self, config: dict) -> tuple[bool, str | None]:
        """Validate connector config. Returns (is_valid, error_message)."""
        for field_name, field_spec in self.CONFIG_SCHEMA.items():
            if field_spec.get("required") and not config.get(field_name):
                return False, f"Missing required field: {field_spec.get('label', field_name)}"
        return True, None


# Registry of available connectors — import conditionally to avoid missing deps
CONNECTOR_REGISTRY: dict[str, type[BaseSyncConnector]] = {}

{%- if cookiecutter.enable_google_drive_ingestion %}
from app.services.rag.connectors.google_drive import GoogleDriveConnector

CONNECTOR_REGISTRY["gdrive"] = GoogleDriveConnector
{%- endif %}

{%- if cookiecutter.enable_s3_ingestion %}
from app.services.rag.connectors.s3 import S3Connector

CONNECTOR_REGISTRY["s3"] = S3Connector
{%- endif %}
{%- endif %}
