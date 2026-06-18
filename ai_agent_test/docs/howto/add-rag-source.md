
# How to: Add a New RAG Document Source

## Overview

Document sources are implemented as **sync connectors** — pluggable adapters
that fetch files from external systems for ingestion into the RAG pipeline.
The connector architecture is based on `BaseSyncConnector`, `RemoteFile`, and
the `CONNECTOR_REGISTRY`.

Built-in connectors:
- **Google Drive** (`gdrive`) — fetches from shared Drive folders
- **S3/MinIO** (`s3`) — fetches from S3-compatible buckets

Adding a new source only requires implementing a connector class. It
automatically works with the CLI, API, and frontend UI.

## Step-by-Step

### 1. Create the connector class

```python
# app/services/rag/connectors/my_source.py
import asyncio
import logging
from pathlib import Path
from typing import Any, ClassVar

from app.services.rag.connectors import BaseSyncConnector, RemoteFile

logger = logging.getLogger(__name__)


class MySourceConnector(BaseSyncConnector):
    """Connector for MySource document storage."""

    CONNECTOR_TYPE: ClassVar[str] = "my_source"
    DISPLAY_NAME: ClassVar[str] = "My Source"

    # CONFIG_SCHEMA drives dynamic form generation in the UI
    CONFIG_SCHEMA: ClassVar[dict[str, dict[str, Any]]] = {
        "api_key": {
            "type": "string",
            "required": True,
            "label": "API Key",
            "help": "Your MySource API key",
        },
        "workspace_id": {
            "type": "string",
            "required": True,
            "label": "Workspace ID",
        },
        "include_archived": {
            "type": "boolean",
            "required": False,
            "default": False,
            "label": "Include archived files",
        },
    }

    async def list_files(self, config: dict) -> list[RemoteFile]:
        """List available files from MySource."""
        api_key = config["api_key"]
        workspace_id = config["workspace_id"]

        def _list():
            # Your API call to list files
            # Return a list of RemoteFile objects
            return []

        return await asyncio.to_thread(_list)

    async def download_file(self, file: RemoteFile, dest_dir: Path) -> Path:
        """Download a single file to a local directory."""
        def _download():
            dest_path = dest_dir / file.name
            # Your download logic here
            # ...
            logger.info(f"Downloaded {file.name} ({dest_path.stat().st_size} bytes)")
            return dest_path

        return await asyncio.to_thread(_download)

    async def validate_config(self, config: dict) -> tuple[bool, str | None]:
        """Test connectivity to MySource (optional but recommended)."""
        is_valid, err = await super().validate_config(config)
        if not is_valid:
            return is_valid, err

        try:
            # Test API access with provided credentials
            return True, None
        except Exception as e:
            return False, f"Cannot connect to MySource: {e}"
```

### 2. Define CONFIG_SCHEMA

The `CONFIG_SCHEMA` dictionary is used to:
- Validate connector configuration via the API
- Dynamically generate form fields in the frontend UI
- Document required/optional settings

Supported field types: `"string"`, `"boolean"`, `"integer"`.

Each field can have:
- `type` — field data type
- `required` — whether the field is mandatory
- `label` — human-readable label for UI
- `help` — tooltip/help text
- `default` — default value for optional fields

### 3. Register in CONNECTOR_REGISTRY

In `app/services/rag/connectors/__init__.py`, add the import and registration:

```python
from app.services.rag.connectors.my_source import MySourceConnector

CONNECTOR_REGISTRY["my_source"] = MySourceConnector
```

Once registered, the connector is automatically available to:
- **CLI** — `uv run ai_agent_test rag-sync` commands
- **API** — `POST /api/v1/rag/sync/sources` endpoint
- **UI** — appears in the sync source management interface

### 4. Add to post_gen_project.py cleanup

In `template/hooks/post_gen_project.py`, add a conditional removal so the
connector file is deleted when the feature is not selected during project
generation:

```python
if not use_my_source_ingestion:
    remove_path("backend/app/services/rag/connectors/my_source.py")
```

### 5. Use it

**Via CLI:**

```bash
# Create a sync source
uv run ai_agent_test cmd rag-sync --connector my_source \
    --config '{"api_key": "...", "workspace_id": "ws-123"}' \
    --collection documents
```

**Via API:**

```bash
# Create a sync source configuration
curl -X POST http://localhost:8000/api/v1/rag/sync/sources \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "My Documents",
        "connector_type": "my_source",
        "collection_name": "documents",
        "config": {"api_key": "...", "workspace_id": "ws-123"}
    }'

# Trigger a sync
curl -X POST http://localhost:8000/api/v1/rag/sync/sources/{source_id}/sync \
    -H "Authorization: Bearer $TOKEN"
```

## Tips

- Set `RemoteFile.source_path` to a unique URI (e.g., `mysource://file_id`) for deduplication
- The `validate_config()` method is called when creating/updating sync sources via the API
- Use `asyncio.to_thread()` to wrap blocking SDK calls
- Add settings to `app/core/config.py` for server-level credentials (API keys, endpoints)
- Per-source settings go in `CONFIG_SCHEMA` and are stored per sync source in the database
