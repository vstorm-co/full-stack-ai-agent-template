
# How to: Add a New Sync Connector

## Architecture

Sync connectors are pluggable adapters that fetch files from external systems
(cloud storage, SaaS APIs, etc.) for ingestion into the RAG pipeline.

### Key classes

| Class | Location | Purpose |
|-------|----------|---------|
| `BaseSyncConnector` | `app/services/rag/connectors/__init__.py` | Abstract base class for all connectors |
| `RemoteFile` | `app/services/rag/connectors/__init__.py` | Pydantic model describing a remote file |
| `CONNECTOR_REGISTRY` | `app/services/rag/connectors/__init__.py` | Dict mapping connector type strings to classes |
| `SyncSource` | `app/db/models/sync_source.py` | Database model storing source configurations |
| `SyncLog` | `app/db/models/sync_log.py` | Database model tracking sync operations |

### Flow

1. User creates a **SyncSource** (connector type + config + collection name)
2. User triggers a **sync** (via API, CLI, or scheduled task)
3. The connector's `list_files()` returns `list[RemoteFile]`
4. For each file, `download_file()` saves it locally
5. The ingestion pipeline parses, chunks, embeds, and stores each file
6. A **SyncLog** entry records the result

## Step-by-Step: Notion Connector

This example implements a Notion connector that fetches pages from a Notion
workspace.

### 1. Create the connector file

```python
# app/services/rag/connectors/notion.py
import asyncio
import logging
from pathlib import Path
from typing import Any, ClassVar

from app.services.rag.connectors import BaseSyncConnector, RemoteFile

logger = logging.getLogger(__name__)


class NotionConnector(BaseSyncConnector):
    """Sync connector for Notion pages."""

    CONNECTOR_TYPE: ClassVar[str] = "notion"
    DISPLAY_NAME: ClassVar[str] = "Notion"

    # CONFIG_SCHEMA is used for:
    #   - API validation when creating/updating sync sources
    #   - Dynamic form generation in the frontend UI
    CONFIG_SCHEMA: ClassVar[dict[str, dict[str, Any]]] = {
        "api_token": {
            "type": "string",
            "required": True,
            "label": "Integration Token",
            "help": "Notion internal integration token (secret_...)",
        },
        "database_id": {
            "type": "string",
            "required": False,
            "default": "",
            "label": "Database ID",
            "help": "Limit sync to a specific Notion database (optional)",
        },
        "include_subpages": {
            "type": "boolean",
            "required": False,
            "default": True,
            "label": "Include sub-pages",
        },
    }

    async def list_files(self, config: dict) -> list[RemoteFile]:
        """List Notion pages available for sync."""
        api_token = config["api_token"]
        database_id = config.get("database_id", "")

        def _list():
            from notion_client import Client

            notion = Client(auth=api_token)
            files: list[RemoteFile] = []

            if database_id:
                # Query a specific database
                response = notion.databases.query(database_id=database_id)
                pages = response.get("results", [])
            else:
                # Search all accessible pages
                response = notion.search(filter={"property": "object", "value": "page"})
                pages = response.get("results", [])

            for page in pages:
                page_id = page["id"]
                title = "Untitled"
                # Extract title from properties
                for prop in page.get("properties", {}).values():
                    if prop.get("type") == "title" and prop.get("title"):
                        title = prop["title"][0].get("plain_text", "Untitled")
                        break

                files.append(
                    RemoteFile(
                        id=page_id,
                        name=f"{title}.md",
                        mime_type="text/markdown",
                        size=None,
                        modified_at=page.get("last_edited_time"),
                        source_path=f"notion://{page_id}",
                    )
                )

            return files

        return await asyncio.to_thread(_list)

    async def download_file(self, file: RemoteFile, dest_dir: Path) -> Path:
        """Export a Notion page as Markdown and save locally."""
        def _download():
            from notion_client import Client

            # Note: in a real implementation you would retrieve the token
            # from the config passed during sync, not hardcode it.
            # This is simplified for illustration.
            dest_path = dest_dir / file.name

            # Fetch page blocks and convert to markdown
            # (simplified — use a library like notion2md in practice)
            content = f"# {file.name.replace('.md', '')}\n\nPage content here..."
            dest_path.write_text(content)

            logger.info(f"Exported Notion page {file.id} -> {dest_path}")
            return dest_path

        return await asyncio.to_thread(_download)

    async def validate_config(self, config: dict) -> tuple[bool, str | None]:
        """Test Notion API access with the provided token."""
        is_valid, err = await super().validate_config(config)
        if not is_valid:
            return is_valid, err

        try:
            def _test():
                from notion_client import Client

                notion = Client(auth=config["api_token"])
                notion.users.me()

            await asyncio.to_thread(_test)
            return True, None
        except Exception as e:
            return False, f"Cannot connect to Notion: {e}"
```

### 2. Register in CONNECTOR_REGISTRY

Edit `app/services/rag/connectors/__init__.py` and add:

```python
from app.services.rag.connectors.notion import NotionConnector

CONNECTOR_REGISTRY["notion"] = NotionConnector
```

### 3. Add dependency (if needed)

If the connector requires a third-party package, add it to `pyproject.toml`:

```bash
uv add notion-client
```

### 4. Test via CLI

```bash
# Create a sync source and trigger sync
uv run ai_agent_test cmd rag-sync \
    --connector notion \
    --config '{"api_token": "secret_...", "database_id": "abc123"}' \
    --collection knowledge-base
```

### 5. Test via API

```bash
# Create sync source
curl -X POST http://localhost:8000/api/v1/rag/sync/sources \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Engineering Wiki",
        "connector_type": "notion",
        "collection_name": "knowledge-base",
        "config": {
            "api_token": "secret_...",
            "database_id": "abc123",
            "include_subpages": true
        }
    }'

# Trigger sync
curl -X POST http://localhost:8000/api/v1/rag/sync/sources/{source_id}/sync \
    -H "Authorization: Bearer $TOKEN"

# Check sync status
curl http://localhost:8000/api/v1/rag/sync/logs \
    -H "Authorization: Bearer $TOKEN"
```

## CONFIG_SCHEMA Reference

The `CONFIG_SCHEMA` class variable defines the connector's configuration
fields. The frontend reads this schema from the
`GET /api/v1/rag/sync/connectors` endpoint to dynamically render form fields.

### Supported field types

| Type | UI Widget | Python type |
|------|-----------|-------------|
| `"string"` | Text input | `str` |
| `"boolean"` | Checkbox/toggle | `bool` |
| `"integer"` | Number input | `int` |

### Field properties

| Property | Required | Description |
|----------|----------|-------------|
| `type` | Yes | Data type (`"string"`, `"boolean"`, `"integer"`) |
| `required` | Yes | Whether the field must be provided |
| `label` | Yes | Human-readable label shown in the UI |
| `help` | No | Tooltip/description text |
| `default` | No | Default value for optional fields |

### Example

```python
CONFIG_SCHEMA: ClassVar[dict[str, dict[str, Any]]] = {
    "api_key": {
        "type": "string",
        "required": True,
        "label": "API Key",
        "help": "Your service API key",
    },
    "max_files": {
        "type": "integer",
        "required": False,
        "default": 100,
        "label": "Max files to sync",
    },
    "recursive": {
        "type": "boolean",
        "required": False,
        "default": True,
        "label": "Include nested items",
    },
}
```

## Tips

- Set `RemoteFile.source_path` to a unique URI (e.g., `notion://page_id`) — this is used for deduplication across syncs
- Use `asyncio.to_thread()` to wrap blocking SDK calls so they don't block the event loop
- Implement `validate_config()` to test connectivity when users create sync sources — it prevents misconfigured sources
- Server-level credentials (shared across all sources) go in `app/core/config.py` and `.env`
- Per-source credentials go in `CONFIG_SCHEMA` and are stored in the database per sync source
- The `download_file()` method should save the file to `dest_dir` and return the local `Path` — the ingestion pipeline handles everything from there
