"""Google Drive document source for RAG ingestion.

Fetches files from Google Drive using a service account credentials JSON file.
Supports listing folders, downloading files, and syncing to RAG collections.

Setup:
1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Share the target Drive folder with the service account email
4. Set GOOGLE_DRIVE_CREDENTIALS_FILE to the path of the JSON key file
"""

import logging
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.core.config import settings
from app.services.rag.sources.base import BaseDocumentSource, SourceFile

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Google Drive MIME types for exportable Google Docs formats
GOOGLE_DOCS_EXPORT = {
    "application/vnd.google-apps.document": ("application/pdf", ".pdf"),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    ),
}


class GoogleDriveSource(BaseDocumentSource):
    """Google Drive document source using service account credentials.

    Authenticates via a service account JSON key file.
    The target folder must be shared with the service account email.
    """

    def __init__(self):
        creds_file = settings.GOOGLE_DRIVE_CREDENTIALS_FILE
        if not creds_file or not Path(creds_file).exists():
            raise ValueError(
                f"Google Drive credentials file not found: {creds_file}. "
                "Set GOOGLE_DRIVE_CREDENTIALS_FILE to the path of your service account JSON key."
            )
        creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
        self.service = build("drive", "v3", credentials=creds)

    async def list_files(
        self, path: str = "", extensions: list[str] | None = None
    ) -> list[SourceFile]:
        """List files in a Google Drive folder.

        Args:
            path: Google Drive folder ID. Empty string = root.
            extensions: Optional list of extensions to filter by.

        Returns:
            List of SourceFile objects.
        """
        query_parts = ["trashed = false"]
        if path:
            query_parts.append(f"'{path}' in parents")

        query_parts.append("mimeType != 'application/vnd.google-apps.folder'")
        query = " and ".join(query_parts)

        results = (
            self.service.files()
            .list(
                q=query,
                fields="files(id, name, mimeType, size)",
                pageSize=1000,
            )
            .execute()
        )

        files = []
        for f in results.get("files", []):
            mime = f.get("mimeType", "")
            name = f.get("name", "")

            if mime in GOOGLE_DOCS_EXPORT:
                _, ext = GOOGLE_DOCS_EXPORT[mime]
                name = f"{name}{ext}" if not name.endswith(ext) else name
            else:
                ext = Path(name).suffix.lower()

            if extensions and ext not in extensions:
                continue

            files.append(
                SourceFile(
                    id=f["id"],
                    name=name,
                    mime_type=mime,
                    size=int(f.get("size", 0)),
                    path=f"gdrive://{f['id']}",
                )
            )

        return files

    async def download_file(self, file_id: str, dest_dir: Path) -> Path:
        """Download a file from Google Drive.

        For Google Docs formats, exports as PDF/XLSX/PPTX.
        For regular files, downloads directly.

        Args:
            file_id: Google Drive file ID.
            dest_dir: Local directory to save to.

        Returns:
            Path to the downloaded file.
        """
        meta = self.service.files().get(fileId=file_id, fields="name, mimeType").execute()
        mime = meta.get("mimeType", "")
        name = meta.get("name", "download")

        if mime in GOOGLE_DOCS_EXPORT:
            export_mime, ext = GOOGLE_DOCS_EXPORT[mime]
            if not name.endswith(ext):
                name = f"{name}{ext}"
            request = self.service.files().export_media(fileId=file_id, mimeType=export_mime)
        else:
            request = self.service.files().get_media(fileId=file_id)

        dest_path = dest_dir / name
        with open(dest_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        logger.info(f"Downloaded {name} from Google Drive ({dest_path.stat().st_size} bytes)")
        return dest_path
