{%- if cookiecutter.enable_rag and cookiecutter.enable_s3_ingestion %}
"""S3/MinIO sync connector for RAG ingestion.

Credentials are supplied per-source via ``access_key_id`` and
``secret_access_key`` config fields. ``endpoint_url`` and ``region`` are
optional. Falls back to the ``S3_RAG_*`` settings for backwards compatibility.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import boto3
from botocore.config import Config

from app.core.config import settings
from app.services.rag.connectors import BaseSyncConnector, RemoteFile

logger = logging.getLogger(__name__)


class S3Connector(BaseSyncConnector):
    """S3-compatible sync connector.

    Works with AWS S3, MinIO, and any S3-compatible storage.
    Credentials are read from the per-source ``config`` dict; falls back to
    ``S3_RAG_*`` environment settings when a config key is absent.
    """

    CONNECTOR_TYPE: ClassVar[str] = "s3"
    DISPLAY_NAME: ClassVar[str] = "S3 / MinIO"
    CONFIG_SCHEMA: ClassVar[dict[str, dict[str, Any]]] = {
        "bucket": {
            "type": "string",
            "required": True,
            "label": "Bucket Name",
        },
        "prefix": {
            "type": "string",
            "required": False,
            "default": "",
            "label": "Path Prefix",
            "help": "e.g. 'documents/legal/' — leave empty for entire bucket",
        },
        "access_key_id": {
            "type": "string",
            "required": True,
            "label": "Access Key ID",
            "secret": True,
        },
        "secret_access_key": {
            "type": "string",
            "required": True,
            "label": "Secret Access Key",
            "secret": True,
        },
        "endpoint_url": {
            "type": "string",
            "required": False,
            "label": "Custom Endpoint URL",
            "help": "For MinIO or compatible services (e.g., http://minio:9000). Leave empty for AWS S3.",
        },
        "region": {
            "type": "string",
            "required": False,
            "default": "us-east-1",
            "label": "Region",
        },
    }

    def _get_s3_client(self, config: dict):
        """Build a boto3 S3 client from per-source config with settings fallback."""
        client_kwargs: dict[str, Any] = {
            "aws_access_key_id": config.get("access_key_id") or settings.S3_RAG_ACCESS_KEY or None,
            "aws_secret_access_key": config.get("secret_access_key") or settings.S3_RAG_SECRET_KEY or None,
            "region_name": config.get("region") or settings.S3_RAG_REGION,
        }
        endpoint = config.get("endpoint_url") or settings.S3_RAG_ENDPOINT
        if endpoint:
            client_kwargs["endpoint_url"] = endpoint
        return boto3.client("s3", **client_kwargs, config=Config(signature_version="s3v4"))

    async def validate_config(self, config: dict) -> tuple[bool, str | None]:
        """Validate required fields only — connectivity is checked at sync time."""
        return await super().validate_config(config)

    async def list_files(self, config: dict) -> list[RemoteFile]:
        """List files in an S3 bucket/prefix."""
        bucket = config["bucket"]
        prefix = config.get("prefix", "")

        def _list():
            client = self._get_s3_client(config)
            paginator = client.get_paginator("list_objects_v2")
            params: dict[str, Any] = {"Bucket": bucket}
            if prefix:
                params["Prefix"] = prefix

            files: list[RemoteFile] = []
            for page in paginator.paginate(**params):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key.endswith("/"):
                        continue

                    name = Path(key).name
                    modified_at = None
                    if obj.get("LastModified"):
                        modified_at = obj["LastModified"]
                        if isinstance(modified_at, str):
                            modified_at = datetime.fromisoformat(modified_at)

                    files.append(
                        RemoteFile(
                            id=key,
                            name=name,
                            mime_type=None,
                            size=obj.get("Size"),
                            modified_at=modified_at,
                            source_path=f"s3://{bucket}/{key}",
                        )
                    )

            return files

        return await asyncio.to_thread(_list)

    async def download_file(
        self, file: RemoteFile, dest_dir: Path, config: dict | None = None
    ) -> Path:
        """Download a file from S3."""
        cfg = config or {}
        parts = file.source_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]

        def _download():
            client = self._get_s3_client(cfg)
            dest_path = dest_dir / file.name
            client.download_file(bucket, file.id, str(dest_path))
            logger.info(
                "Downloaded s3://%s/%s (%d bytes)", bucket, file.id, dest_path.stat().st_size
            )
            return dest_path

        return await asyncio.to_thread(_download)
{%- endif %}
