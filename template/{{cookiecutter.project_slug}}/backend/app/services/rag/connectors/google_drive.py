{%- if cookiecutter.enable_rag and cookiecutter.enable_google_drive_ingestion %}
"""Google Drive sync connector for RAG ingestion.

Fetches files from Google Drive using a Google service account.
Credentials are supplied per-source via the ``service_account_json`` config
field (a copy of the JSON key file contents). A file-path fallback via
``GOOGLE_DRIVE_CREDENTIALS_FILE`` is kept for backwards compatibility.

Setup:
1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Share the target Drive folder with the service account email
4. Paste the JSON contents into the "Service Account JSON" field when
   creating a sync source (or set GOOGLE_DRIVE_CREDENTIALS_FILE as a fallback)
"""

import asyncio
import json as _json
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
    """Google Drive connector using a service account.

    Credentials are read from ``config["service_account_json"]`` (a JSON string).
    Falls back to the file at ``settings.GOOGLE_DRIVE_CREDENTIALS_FILE`` when
    the config field is absent.
    """

    CONNECTOR_TYPE: ClassVar[str] = "gdrive"
    DISPLAY_NAME: ClassVar[str] = "Google Drive"
    CONFIG_SCHEMA: ClassVar[dict[str, dict[str, Any]]] = {
        "service_account_json": {
            "type": "textarea",
            "required": True,
            "label": "Service Account JSON",
            "help": "Paste the full contents of your Google service account JSON key file.",
            "secret": True,
        },
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

    def _get_drive_service(self, config: dict):
        """Build an authenticated Google Drive API service from config or file fallback."""
        sa_json = config.get("service_account_json")
        if sa_json:
            info = _json.loads(sa_json) if isinstance(sa_json, str) else sa_json
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds_file = settings.GOOGLE_DRIVE_CREDENTIALS_FILE
            if not creds_file or not Path(creds_file).exists():
                raise ValueError(
                    "No service account credentials found. "
                    "Add your Google service account JSON in the connector configuration."
                )
            creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
        return build("drive", "v3", credentials=creds)

    async def validate_config(self, config: dict) -> tuple[bool, str | None]:
        """Validate required fields only — connectivity is checked at sync time."""
        return await super().validate_config(config)

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
                    modified_at = datetime.fromisoformat(
                        f["modifiedTime"].replace("Z", "+00:00")
                    )

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
            service = self._get_drive_service(config)
            return self._list_folder(service, folder_id, include_subfolders)

        return await asyncio.to_thread(_list)

    async def download_file(
        self, file: RemoteFile, dest_dir: Path, config: dict | None = None
    ) -> Path:
        """Download a file from Google Drive.

        For Google Docs formats, exports as PDF/XLSX/PPTX.
        For regular files, downloads directly.
        """
        cfg = config or {}

        def _download():
            service = self._get_drive_service(cfg)
            dest_path = dest_dir / file.name

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
                "Downloaded %s from Google Drive (%d bytes)", file.name, dest_path.stat().st_size
            )
            return dest_path

        return await asyncio.to_thread(_download)
{%- endif %}
