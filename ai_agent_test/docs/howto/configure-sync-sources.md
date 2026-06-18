
# How to: Configure Sync Sources

## Overview

Sync sources let you automatically pull documents from external services
(Google Drive, S3/MinIO) into your RAG collections. Each source is a
persistent configuration that stores a connector type, target collection,
connector-specific settings, a sync mode, and an optional schedule.

When a sync runs, the connector lists remote files, downloads them to a
temporary directory, and feeds them through the standard ingestion pipeline
(parse, chunk, embed, store). A `SyncLog` entry records the outcome of
every sync operation.

### Architecture at a glance

| Component | Location | Role |
|-----------|----------|------|
| `BaseSyncConnector` | `app/rag/connectors/__init__.py` | Abstract base for all connectors |
| `RemoteFile` | `app/rag/connectors/__init__.py` | Pydantic model describing a remote file |
| `CONNECTOR_REGISTRY` | `app/rag/connectors/__init__.py` | Maps connector type strings to classes |
| `SyncSource` (DB model) | `app/db/models/sync_source.py` | Persists source configurations |
| `SyncLog` (DB model) | `app/db/models/sync_log.py` | Tracks individual sync operations |
| `SyncSourceService` | `app/services/sync_source.py` | Business logic for CRUD + trigger |
| RAG CLI commands | `app/commands/rag.py` | CLI interface for managing sources |
| RAG API routes | `app/api/routes/v1/rag.py` | REST API for managing sources |

---

## Quick Start -- CLI

### List available connector types

```bash
# Shows all registered connectors (e.g. gdrive, s3)
uv run ai_agent_test cmd rag-sources
```

### Add a Google Drive source -- sync every 2 hours

```bash
uv run ai_agent_test cmd rag-source-add \
  --name "Legal docs" \
  --type gdrive \
  --collection legal \
  --config '{"folder_id": "1abc123def", "include_subfolders": true}' \
  --sync-mode new_only \
  --schedule 120
```

### Add an S3 source -- manual sync only

```bash
uv run ai_agent_test cmd rag-source-add \
  --name "Marketing" \
  --type s3 \
  --collection marketing \
  --config '{"bucket": "my-docs", "prefix": "marketing/"}' \
  --sync-mode full \
  --schedule 0
```

### Trigger sync manually

```bash
# Sync a single source by ID
uv run ai_agent_test cmd rag-source-sync <source-id>

# Sync all active sources
uv run ai_agent_test cmd rag-source-sync --all
```

### Remove a source

```bash
uv run ai_agent_test cmd rag-source-remove <source-id>
```

The `<source-id>` is a UUID printed when you create the source and shown
in the `rag-sources` listing.

---

## Quick Start -- UI

1. Navigate to **Knowledge Base** and open the **Sync** tab.
2. Click **"+ Add Source"**.
3. Select a connector type (Google Drive, S3). The form fields are
   generated dynamically from the connector's `CONFIG_SCHEMA`.
4. Fill in the connector-specific config fields (e.g. folder ID, bucket
   name).
5. Choose a target collection, sync mode, and schedule interval.
6. Click **"Create Source"**.
7. Use the **"Sync Now"** button to trigger an immediate sync, or wait
   for the schedule to fire automatically.

The UI calls the same REST API documented below, so anything you can do
in the UI you can also do with `curl` or any HTTP client.

---

## Sync Modes

| Mode | Behavior |
|------|----------|
| `full` | Re-sync everything. All files are (re-)ingested, existing documents replaced. |
| `new_only` | Add new files + update changed files. Uses SHA-256 hash to detect changes — unchanged files are skipped. |
| `update_only` | Only update files already in the collection. New files are skipped. Uses SHA-256 hash to skip unchanged files. |

Choose `new_only` for most workflows — it adds new files and updates
modified ones while skipping unchanged files (fastest incremental sync).
Choose `update_only` when you only want to refresh existing documents
without adding new ones. Choose `full` for a clean re-import every time.

---

## Schedule

The `schedule_minutes` field controls how often the source syncs
automatically:

| Value | Meaning |
|-------|---------|
| `0` (or `null`) | Manual only -- trigger via CLI or UI |
| `30` | Every 30 minutes |
| `120` | Every 2 hours |
| `1440` | Once per day |

Scheduled syncs require a running background task system:
- **Celery Beat** -- the periodic scheduler that ships with your Celery
  worker. Make sure the worker is running with `--beat`.

Without a background task system, only manual triggers (CLI or API) work.

---

## Google Drive Setup

### 1. Create a service account

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Enable the **Google Drive API**.
4. Go to **IAM & Admin > Service Accounts** and create a new service
   account.
5. Create a JSON key for the service account and download it.

### 2. Share your Drive folder

1. Open Google Drive and navigate to the folder you want to sync.
2. Click **Share** and add the service account email address (it looks
   like `name@project.iam.gserviceaccount.com`).
3. Grant at least **Viewer** access.

### 3. Configure the environment

Add the path to the credentials file in your `.env`:

```bash
GOOGLE_DRIVE_CREDENTIALS_FILE=/path/to/service-account-credentials.json
```

### 4. Get the folder ID

The folder ID is the last segment of the Google Drive folder URL:

```
https://drive.google.com/drive/folders/1abc123def456ghi
                                        ^^^^^^^^^^^^^^^
                                        This is the folder ID
```

### 5. Google Drive connector config fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `folder_id` | string | Yes | -- | Google Drive folder ID from the URL |
| `include_subfolders` | boolean | No | `true` | Recursively include files from subfolders |

Google Docs, Sheets, and Slides are automatically exported to portable
formats (PDF, XLSX, PPTX) during download.

---

## S3 / MinIO Setup

### 1. Configure the environment

Add the following variables to your `.env`:

```bash
S3_RAG_ENDPOINT=https://s3.amazonaws.com   # or your MinIO URL, e.g. http://localhost:9000
S3_RAG_ACCESS_KEY=your-access-key
S3_RAG_SECRET_KEY=your-secret-key
S3_RAG_REGION=us-east-1                    # required for AWS, optional for MinIO
```

For MinIO, the endpoint is typically `http://minio:9000` (Docker) or
`http://localhost:9000` (local).

### 2. S3 connector config fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `bucket` | string | Yes | -- | S3 bucket name |
| `prefix` | string | No | `""` | Key prefix to limit sync scope (e.g. `documents/legal/`). Leave empty for the entire bucket. |

---

## API Reference

All sync source endpoints live under `/api/v1/rag/sync/`. They require
admin-level authentication when JWT auth is enabled.

### Sync Sources CRUD

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/rag/sync/sources` | List all configured sync sources |
| `POST` | `/api/v1/rag/sync/sources` | Create a new sync source |
| `PATCH` | `/api/v1/rag/sync/sources/{id}` | Update an existing sync source |
| `DELETE` | `/api/v1/rag/sync/sources/{id}` | Delete a sync source |
| `POST` | `/api/v1/rag/sync/sources/{id}/trigger` | Manually trigger a sync |

### Connectors & Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/rag/sync/connectors` | List available connector types with config schemas |
| `GET` | `/api/v1/rag/sync/logs` | List sync history (filterable by `collection_name`) |

### Example: Create a source via API

```bash
curl -X POST http://localhost:8000/api/v1/rag/sync/sources \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Legal Drive",
    "connector_type": "gdrive",
    "collection_name": "legal",
    "config": {
      "folder_id": "1abc123def",
      "include_subfolders": true
    },
    "sync_mode": "new_only",
    "schedule_minutes": 120
  }'
```

### Example: Trigger a sync via API

```bash
curl -X POST http://localhost:8000/api/v1/rag/sync/sources/{source_id}/trigger \
  -H "Authorization: Bearer $TOKEN"
```

### Example: Check sync history

```bash
curl http://localhost:8000/api/v1/rag/sync/logs?limit=10 \
  -H "Authorization: Bearer $TOKEN"
```

### Example: Discover available connectors

```bash
curl http://localhost:8000/api/v1/rag/sync/connectors \
  -H "Authorization: Bearer $TOKEN"
```

The response includes each connector's `config_schema`, which the
frontend uses to render dynamic forms. It is also useful for building
integrations programmatically.

---

## Updating a Source

You can update any subset of fields on an existing source with `PATCH`:

```bash
curl -X PATCH http://localhost:8000/api/v1/rag/sync/sources/{source_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sync_mode": "full",
    "schedule_minutes": 60,
    "is_active": false
  }'
```

Updatable fields: `name`, `config`, `sync_mode`, `schedule_minutes`,
`is_active`, `collection_name`.

Set `is_active` to `false` to pause a source without deleting it.

---

## Monitoring Sync Operations

Every sync creates a `SyncLog` entry with the following fields:

| Field | Description |
|-------|-------------|
| `source` | Connector type or `"local"` for CLI ingestion |
| `collection_name` | Target collection |
| `status` | `running`, `done`, or `error` |
| `mode` | `full`, `new_only`, or `update_only` |
| `total_files` | Number of files discovered |
| `ingested` | Successfully ingested (new) |
| `updated` | Successfully re-ingested (replaced) |
| `skipped` | Skipped (already present or unchanged) |
| `failed` | Failed to ingest |
| `error_message` | Error details (if `status` is `error`) |
| `started_at` | When the sync started |
| `completed_at` | When the sync finished |

View logs via CLI output or the API:

```bash
curl http://localhost:8000/api/v1/rag/sync/logs?collection_name=legal&limit=5 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Adding Custom Connectors

To add a new connector type (e.g. Notion, Confluence, Dropbox), see
[How to: Add a New Sync Connector](./add-sync-connector.md).

The short version:

1. Create a class inheriting `BaseSyncConnector` in
   `app/rag/connectors/`.
2. Implement `list_files()`, `download_file()`, and optionally
   `validate_config()`.
3. Define a `CONFIG_SCHEMA` for the connector's settings.
4. Register it in `CONNECTOR_REGISTRY` in
   `app/rag/connectors/__init__.py`.

Once registered, the connector appears automatically in the CLI, API,
and UI.

---

## Troubleshooting

### "No sync sources configured"

You have not created any sources yet. Use `rag-source-add` (CLI) or
`POST /api/v1/rag/sync/sources` (API) to create one.

### "Unknown connector type"

The connector type you specified is not in `CONNECTOR_REGISTRY`. Check
available types with `rag-sources` or `GET /api/v1/rag/sync/connectors`.
Google Drive (`gdrive`) is available.
S3 (`s3`) is available.

### Google Drive: "credentials file not found"

Set `GOOGLE_DRIVE_CREDENTIALS_FILE` in `.env` to the absolute path of
your service account JSON key file.

### Google Drive: "Cannot access folder"

Make sure you shared the folder with the service account email. The
service account needs at least Viewer access.

### S3: "Cannot access bucket"

Verify that `S3_RAG_ACCESS_KEY`, `S3_RAG_SECRET_KEY`, and
`S3_RAG_ENDPOINT` are set correctly in `.env`. For MinIO, ensure the
endpoint includes the port (e.g. `http://localhost:9000`).

### Scheduled syncs are not running

A background task system must be running. Check that your worker process
is active:
```bash
# Celery worker with Beat scheduler
celery -A app.worker.celery_app worker --beat -l info
```

Without a worker, only manual triggers via CLI or API will work.
