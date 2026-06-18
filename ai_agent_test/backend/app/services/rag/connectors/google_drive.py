"""Google Drive sync connector for RAG ingestion.

Fetches files from Google Drive using a service account credentials JSON file.
Supports listing folders (with optional subfolder recursion), downloading files,
and exporting Google Docs/Sheets/Slides to portable formats.

Setup:
1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Share the target Drive folder with the service account email
4. Set GOOGLE_DRIVE_CREDENTIALS_FILE to the path of the JSON key file
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.core.config import settings
from app.services.rag.connectors import BaseSyncConnector, RemoteFile

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Google Drive MIME types for exportable Google Docs formats
GOOGLE_DOCS_EXPORT: dict[str, tuple[str, str]] = {
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


class GoogleDriveConnector(BaseSyncConnector):
    """Google Drive connector using service account credentials.

    Authenticates via a service account JSON key file.
    The target folder must be shared with the service account email.
    """

    CONNECTOR_TYPE: ClassVar[str] = "gdrive"
    DISPLAY_NAME: ClassVar[str] = "Google Drive"
    CONFIG_SCHEMA: ClassVar[dict[str, dict[str, Any]]] = {
        "folder_id": {
            "type": "string",
            "required": True,
            "label": "Google Drive Folder ID",
            "help": "The ID from the folder URL: drive.google.com/drive/folders/{THIS_ID}",
        },
        "include_subfolders": {
            "type": "boolean",
            "required": False,
            "default": True,
            "label": "Include subfolders",
        },
    }

    def _get_drive_service(self):
        """Get authenticated Google Drive API service."""
        creds_file = settings.GOOGLE_DRIVE_CREDENTIALS_FILE
        if not creds_file or not Path(creds_file).exists():
            raise ValueError(
                f"Google Drive credentials file not found: {creds_file}. "
                "Set GOOGLE_DRIVE_CREDENTIALS_FILE to the path of your service account JSON key."
            )
        creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
        return build("drive", "v3", credentials=creds)

    async def validate_config(self, config: dict) -> tuple[bool, str | None]:
        """Test Google Drive folder access."""
        # First run base validation for required fields
        is_valid, err = await super().validate_config(config)
        if not is_valid:
            return is_valid, err

        try:

            def _test():
                service = self._get_drive_service()
                service.files().list(
                    q=f"'{config['folder_id']}' in parents",
                    pageSize=1,
                    fields="files(id)",
                ).execute()

            await asyncio.to_thread(_test)
            return True, None
        except Exception as e:
            return False, f"Cannot access Google Drive folder: {e}"

    def _list_folder(self, service, folder_id: str, include_subfolders: bool) -> list[RemoteFile]:
        """Recursively list files in a Google Drive folder (sync, runs in thread)."""
        files: list[RemoteFile] = []
        query = f"'{folder_id}' in parents and trashed = false"
        page_token = None

        while True:
            response = (
                service.files()
                .list(
                    q=query,
                    pageSize=100,
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                    pageToken=page_token,
                )
                .execute()
            )

            for f in response.get("files", []):
                mime = f.get("mimeType", "")

                # Handle folders — recurse if enabled, otherwise skip
                if mime == "application/vnd.google-apps.folder":
                    if include_subfolders:
                        files.extend(self._list_folder(service, f["id"], include_subfolders))
                    continue

                name = f.get("name", "")

                # Map Google Apps MIME types to exportable formats
                if mime in GOOGLE_DOCS_EXPORT:
                    export_mime, ext = GOOGLE_DOCS_EXPORT[mime]
                    if not name.endswith(ext):
                        name = f"{name}{ext}"
                    mime = export_mime

                modified_at = None
                if f.get("modifiedTime"):
                    modified_at = datetime.fromisoformat(f["modifiedTime"].replace("Z", "+00:00"))

                files.append(
                    RemoteFile(
                        id=f["id"],
                        name=name,
                        mime_type=mime,
                        size=int(f.get("size", 0)),
                        modified_at=modified_at,
                        source_path=f"gdrive://{f['id']}",
                    )
                )

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return files

    async def list_files(self, config: dict) -> list[RemoteFile]:
        """List all files in the configured Google Drive folder."""
        folder_id = config["folder_id"]
        include_subfolders = config.get("include_subfolders", True)

        def _list():
            service = self._get_drive_service()
            return self._list_folder(service, folder_id, include_subfolders)

        return await asyncio.to_thread(_list)

    async def download_file(self, file: RemoteFile, dest_dir: Path) -> Path:
        """Download a file from Google Drive.

        For Google Docs formats, exports as PDF/XLSX/PPTX.
        For regular files, downloads directly.
        """

        def _download():
            service = self._get_drive_service()
            dest_path = dest_dir / file.name

            # Check original MIME type to decide export vs direct download
            meta = service.files().get(fileId=file.id, fields="mimeType").execute()
            original_mime = meta.get("mimeType", "")

            if original_mime in GOOGLE_DOCS_EXPORT:
                export_mime, ext = GOOGLE_DOCS_EXPORT[original_mime]
                request = service.files().export_media(fileId=file.id, mimeType=export_mime)
            else:
                request = service.files().get_media(fileId=file.id)

            with open(dest_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()

            logger.info(
                f"Downloaded {file.name} from Google Drive ({dest_path.stat().st_size} bytes)"
            )
            return dest_path

        return await asyncio.to_thread(_download)
