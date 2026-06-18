"""S3/MinIO sync connector for RAG ingestion.

Fetches files from S3-compatible storage (AWS S3, MinIO, etc.)
for ingestion into the RAG pipeline.
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
    Uses credentials from app settings (S3_RAG_ENDPOINT, S3_RAG_ACCESS_KEY, etc.).
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
    }

    def _get_s3_client(self, bucket: str = ""):
        """Get configured boto3 S3 client."""
        client_kwargs: dict[str, Any] = {
            "aws_access_key_id": settings.S3_RAG_ACCESS_KEY,
            "aws_secret_access_key": settings.S3_RAG_SECRET_KEY,
            "region_name": settings.S3_RAG_REGION,
        }
        if settings.S3_RAG_ENDPOINT:
            client_kwargs["endpoint_url"] = settings.S3_RAG_ENDPOINT
        return boto3.client("s3", **client_kwargs, config=Config(signature_version="s3v4"))

    async def validate_config(self, config: dict) -> tuple[bool, str | None]:
        """Test S3 bucket access."""
        # First run base validation for required fields
        is_valid, err = await super().validate_config(config)
        if not is_valid:
            return is_valid, err

        try:

            def _test():
                client = self._get_s3_client()
                client.head_bucket(Bucket=config["bucket"])

            await asyncio.to_thread(_test)
            return True, None
        except Exception as e:
            return False, f"Cannot access S3 bucket '{config['bucket']}': {e}"

    async def list_files(self, config: dict) -> list[RemoteFile]:
        """List files in an S3 bucket/prefix."""
        bucket = config["bucket"]
        prefix = config.get("prefix", "")

        def _list():
            client = self._get_s3_client()
            paginator = client.get_paginator("list_objects_v2")
            params: dict[str, Any] = {"Bucket": bucket}
            if prefix:
                params["Prefix"] = prefix

            files: list[RemoteFile] = []
            for page in paginator.paginate(**params):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key.endswith("/"):
                        continue  # skip directory markers

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

    async def download_file(self, file: RemoteFile, dest_dir: Path) -> Path:
        """Download a file from S3."""
        # Extract bucket from source_path: "s3://bucket/key"
        parts = file.source_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]

        def _download():
            client = self._get_s3_client()
            dest_path = dest_dir / file.name
            client.download_file(bucket, file.id, str(dest_path))
            logger.info(f"Downloaded s3://{bucket}/{file.id} ({dest_path.stat().st_size} bytes)")
            return dest_path

        return await asyncio.to_thread(_download)
