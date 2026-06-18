"""S3/MinIO document source for RAG ingestion.

Fetches files from S3-compatible storage (AWS S3, MinIO, etc.)
for ingestion into the RAG pipeline.
"""

import logging
from pathlib import Path

import boto3
from botocore.config import Config

from app.core.config import settings
from app.services.rag.sources.base import BaseDocumentSource, SourceFile

logger = logging.getLogger(__name__)


class S3Source(BaseDocumentSource):
    """S3-compatible document source.

    Works with AWS S3, MinIO, and any S3-compatible storage.
    Uses credentials from app settings (S3_ENDPOINT, S3_ACCESS_KEY, etc.).
    """

    def __init__(self, bucket: str = ""):
        self.bucket = bucket or settings.S3_RAG_BUCKET
        client_kwargs = {
            "aws_access_key_id": settings.S3_RAG_ACCESS_KEY,
            "aws_secret_access_key": settings.S3_RAG_SECRET_KEY,
            "region_name": settings.S3_RAG_REGION,
        }
        if settings.S3_RAG_ENDPOINT:
            client_kwargs["endpoint_url"] = settings.S3_RAG_ENDPOINT
        self.client = boto3.client("s3", **client_kwargs, config=Config(signature_version="s3v4"))

    async def list_files(
        self, path: str = "", extensions: list[str] | None = None
    ) -> list[SourceFile]:
        """List files in an S3 bucket/prefix.

        Args:
            path: S3 prefix (folder path). Empty = bucket root.
            extensions: Optional list of extensions to filter by.

        Returns:
            List of SourceFile objects.
        """
        paginator = self.client.get_paginator("list_objects_v2")
        params = {"Bucket": self.bucket}
        if path:
            params["Prefix"] = path

        files = []
        for page in paginator.paginate(**params):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/"):
                    continue  # skip directories

                name = Path(key).name
                ext = Path(name).suffix.lower()

                if extensions and ext not in extensions:
                    continue

                files.append(
                    SourceFile(
                        id=key,
                        name=name,
                        mime_type="",
                        size=obj.get("Size", 0),
                        path=f"s3://{self.bucket}/{key}",
                    )
                )

        return files

    async def download_file(self, file_id: str, dest_dir: Path) -> Path:
        """Download a file from S3.

        Args:
            file_id: S3 object key.
            dest_dir: Local directory to save to.

        Returns:
            Path to the downloaded file.
        """
        name = Path(file_id).name
        dest_path = dest_dir / name
        self.client.download_file(self.bucket, file_id, str(dest_path))
        logger.info(f"Downloaded s3://{self.bucket}/{file_id} ({dest_path.stat().st_size} bytes)")
        return dest_path
