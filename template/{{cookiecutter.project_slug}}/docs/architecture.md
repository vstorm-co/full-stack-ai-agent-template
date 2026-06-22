# Architecture Guide

This project follows a **Repository + Service** layered architecture.
Every feature — users, conversations, files, RAG documents, sync sources — uses
the same pattern: **Models → Schemas → Repositories → Services → Endpoints**.

## Request Flow

```
HTTP Request → API Route → Service → Repository → Database
                  ↓
              Response ← Service ← Repository ←
```

Routes never contain direct database calls. All data access goes through
services, which in turn delegate to repositories.

## Directory Structure (`backend/app/`)

| Directory / File | Purpose |
|-----------|---------|
| `api/routes/v1/` | HTTP endpoints, request validation, auth |
| `api/deps.py` | Dependency injection (db session, current user) |
| **`services/`** | **Business logic, orchestration** |
| ↳ `user.py` | User CRUD, profile updates |
| ↳ `conversation.py` | Conversation & message management |
| ↳ `message_rating.py` | Message rating CRUD, statistics, export |
| ↳ `file_upload.py` | Chat file upload handling |
| ↳ `file_storage.py` | File storage abstraction (local / S3) |
{%- if cookiecutter.enable_rag %}
| ↳ `rag_document.py` | RAG document lifecycle |
| ↳ `rag_sync.py` | Remote-source sync orchestration |
| ↳ `sync_source.py` | Sync-source CRUD |
{%- endif %}
| **`repositories/`** | **Data access layer, database queries** |
| ↳ `user.py` | User queries |
| ↳ `conversation.py` | Conversation queries |
| ↳ `chat_file.py` | Chat file queries |
| ↳ `message_rating.py` | Message rating queries |
{%- if cookiecutter.enable_rag %}
| ↳ `rag_document.py` | RAG document queries |
| ↳ `sync_log.py` | Sync log queries |
| ↳ `sync_source.py` | Sync source queries |
{%- endif %}
| **`schemas/`** | **Pydantic request/response models** |
| ↳ `user.py` | User schemas |
| ↳ `conversation.py` | Conversation & message schemas |
| ↳ `file.py` | File upload schemas |
| ↳ `message_rating.py` | Message rating schemas |
{%- if cookiecutter.enable_rag %}
| ↳ `rag.py` | RAG query/response schemas |
| ↳ `sync_source.py` | Sync source schemas |
{%- endif %}
| **`db/models/`** | **SQLAlchemy 2.0 models** |
| ↳ `user.py` | User model |
| ↳ `conversation.py` | Conversation & message models |
| ↳ `chat_file.py` | Chat file model |
| ↳ `message_rating.py` | Message rating model |
| ↳ `webhook.py` | Webhook model |
{%- if cookiecutter.enable_rag %}
| ↳ `rag_document.py` | RAG document model |
| ↳ `sync_log.py` | Sync log model |
| ↳ `sync_source.py` | Sync source model |
{%- endif %}
| `core/config.py` | Settings via pydantic-settings |
| `core/security.py` | JWT / API key utilities |
| `agents/` | AI agents and tools |
{%- if cookiecutter.enable_rag %}
| `rag/` | RAG module (embeddings, vector store, retrieval) |
| `rag/connectors/` | Sync connectors (Google Drive, S3) |
{%- endif %}
| `commands/` | Django-style CLI commands |
{%- if cookiecutter.use_celery or cookiecutter.use_taskiq %}
| `worker/` | Background task definitions |
{%- endif %}

## Layer Responsibilities

### API Routes (`api/routes/v1/`)
- HTTP request/response handling
- Input validation via Pydantic schemas
- Authentication and authorization checks
- **Never** contains direct DB calls — always delegates to a service

### Services (`services/`)
- Business logic and validation
- Orchestrates one or more repository calls
- Raises domain exceptions (`NotFoundError`, `AlreadyExistsError`, etc.)
- Manages transaction boundaries

### Repositories (`repositories/`)
- Database operations only
- No business logic
- Uses `db.flush()` not `commit()` (the dependency-injected session manages transactions)
- Returns domain models

### Schemas (`schemas/`)
- Separate `Create`, `Update`, and `Response` models per entity
- `Response` schemas use `model_config = ConfigDict(from_attributes=True)` for ORM conversion

### Models (`db/models/`)
- SQLAlchemy 2.0 model definitions
- Relationships, indexes, and column defaults live here
{%- if cookiecutter.enable_rag %}

### RAG Connectors (`rag/connectors/`)
- Pluggable sync adapters that implement `BaseSyncConnector`
- Each connector provides `list_files()` and `download_file()`
- Registered in `CONNECTOR_REGISTRY` for discovery at runtime
{%- endif %}

## Key Files

- Entry point: `app/main.py`
- Configuration: `app/core/config.py`
- Dependencies: `app/api/deps.py`
- Auth utilities: `app/core/security.py`
- Exception handlers: `app/api/exception_handlers.py`

{%- if cookiecutter.use_jwt %}

## Authentication & Authorization

### Authentication Methods

The project supports two authentication methods, both always available:

1. **JWT (JSON Web Tokens)** -- Used by the frontend and API clients.
   - Login via `POST /api/v1/auth/login` returns `access_token` + `refresh_token`.
   - Access tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 min).
   - Refresh tokens expire after `REFRESH_TOKEN_EXPIRE_MINUTES` (default 7 days).
   - The frontend stores tokens as HTTP-only cookies.
   - WebSocket auth passes the JWT as a query parameter (`?token=<jwt>`) or cookie.
{%- if cookiecutter.use_api_key %}

2. **API Key** -- Used for server-to-server and programmatic access.
   - Passed via the `X-API-Key` header (configurable via `API_KEY_HEADER`).
   - A single shared key set via the `API_KEY` environment variable.
   - Uses constant-time comparison (`secrets.compare_digest`) to prevent timing attacks.
{%- endif %}

### Roles

Two roles are defined in `UserRole` (see `app/db/models/user.py`):

| Role | Value | Description |
|------|-------|-------------|
| **ADMIN** | `"admin"` | Full system access, can manage users, RAG, webhooks, exports |
| **USER** | `"user"` | Standard access: chat, profile, search |

Role hierarchy: `ADMIN` has access to everything. The `has_role()` method on the
User model returns `True` for any role if the user is an admin.

### How RoleChecker Works

`RoleChecker` is a callable FastAPI dependency class in `app/api/deps.py`:

```python
class RoleChecker:
    def __init__(self, required_role: UserRole) -> None:
        self.required_role = required_role

    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        if not user.has_role(self.required_role):
            raise AuthorizationError(...)
        return user
```

Use it in routes:

```python
# Any authenticated user
@router.get("/profile")
async def profile(current_user: CurrentUser): ...

# Admin only
@router.get("/all-users")
async def list_users(current_user: CurrentAdmin): ...
```

The type aliases are:
- `CurrentUser` = `Annotated[User, Depends(get_current_user)]` -- any authenticated user
- `CurrentAdmin` = `Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]` -- admin role required
- `CurrentSuperuser` = `Annotated[User, Depends(get_current_active_superuser)]` -- legacy alias for admin

### IDOR Protection

Conversation and file endpoints enforce ownership at the service layer:
- Conversations pass `user_id=current_user.id` to the service, which filters queries by owner.
- File downloads verify `chat_file.user_id == current_user.id` before returning the file.
- This prevents users from accessing resources belonging to other users.

For full endpoint-level permissions, see `docs/permissions.md`.
{%- endif %}

## File Processing in Chat

{%- if cookiecutter.use_jwt %}

When a user uploads a file in the chat interface, the following pipeline executes:

```
Upload (POST /files/upload)
  -> Validate (MIME type + size)
  -> Classify (image / pdf / docx / text)
  -> Parse (extract text content)
  -> Store (save to media/{user_id}/)
  -> Record (create ChatFile in DB)
  -> Link (attach to message when sent)
```

### Supported File Types

| Category | Extensions | Processing |
|----------|-----------|------------|
| Images | JPEG, PNG, WebP, GIF | Stored as-is, sent to LLM as binary for vision |
| PDF | .pdf | Text extracted via configured parser |
| Documents | .docx | Text extracted via python-docx |
| Text | .txt, .md | UTF-8 decoded directly |

### Parser Selection

{%- if cookiecutter.use_all_pdf_parsers %}
The `CHAT_PDF_PARSER` environment variable controls which parser handles PDFs in
chat file uploads. Options: `pymupdf` (default, fastest, local), `llamaparse`
(AI-powered, requires API key), `liteparse`. Falls back to `pymupdf` on failure.
{%- else %}
PDFs are parsed using PyMuPDF (fast, local, no API key needed).
{%- endif %}

### Storage

Files are saved to `media/{user_id}/` via `FileStorageService`. The `ChatFile`
model stores the `storage_path`, `filename`, `mime_type`, `size`, `file_type`,
and `parsed_content` (extracted text). Only the file owner can access their files.

### Size Limits

Maximum upload size is controlled by `MAX_UPLOAD_SIZE_MB` (default 50MB).
{%- endif %}

{%- if cookiecutter.enable_rag %}

## RAG System

### Architecture Overview

The RAG (Retrieval Augmented Generation) system provides a knowledge base that
the AI agent can search during conversations. It is composed of:

```
Documents -> Parse -> Chunk -> Embed -> Vector Store
                                            |
User Query -> Embed -> Search -> Rerank? -> Results -> Agent Prompt
```

### Key Principle: RAG is Global

**Collections are shared across ALL users.** There is no per-user document
isolation. This means:

- Any authenticated user can **search** any collection.
- Only **admins** can create/delete collections, upload documents, configure sync
  sources, and view sync logs.
- The knowledge base serves as an organization-wide shared resource.

### Components

| Component | File | Purpose |
|-----------|------|---------|
| `DocumentProcessor` | `rag/documents.py` | Parses files into text (PDF, DOCX, TXT, images) |
| `IngestionService` | `rag/ingestion.py` | Orchestrates parse -> chunk -> embed -> store |
| `RetrievalService` | `rag/retrieval.py` | Handles search queries with filtering and scoring |
| `EmbeddingService` | `rag/embeddings.py` | Generates embeddings via configured provider |
| `BaseVectorStore` | `rag/vectorstore.py` | Abstract interface for vector database operations |
{%- if cookiecutter.use_milvus %}
| `MilvusVectorStore` | `rag/vectorstore.py` | Milvus implementation |
{%- elif cookiecutter.use_qdrant %}
| `QdrantVectorStore` | `rag/vectorstore.py` | Qdrant implementation |
{%- elif cookiecutter.use_chromadb %}
| `ChromaVectorStore` | `rag/vectorstore.py` | ChromaDB implementation |
{%- elif cookiecutter.use_pgvector %}
| `PgVectorStore` | `rag/vectorstore.py` | pgvector (PostgreSQL) implementation |
{%- endif %}

### Ingestion Pipeline

Documents can be ingested via:

1. **CLI** -- `uv run {{ cookiecutter.project_slug }} cmd rag-ingest <path>`
2. **API** -- `POST /api/v1/rag/collections/{name}/ingest` (admin only, file upload)
3. **Sync Sources** -- Configured connectors (Google Drive, S3) that pull documents
   on a schedule or on-demand.

Each ingested document gets:
- Parsed into text (with parser selected by `PDF_PARSER` env var)
- Split into chunks (configurable `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP`)
- Embedded via the configured embedding provider
- Stored in the vector database
- Tracked in SQL via `RAGDocument` model with status (`processing`, `done`, `error`)

### Sync Modes

| Mode | Behavior |
|------|----------|
| `full` | Replace all documents (re-ingest everything) |
| `new_only` | Add new files, re-ingest files whose content hash changed, skip unchanged |
| `update_only` | Only re-ingest changed files, skip new files entirely |

### Sync Connectors

Remote document sources use pluggable connectors in `rag/connectors/`. Each
connector implements `BaseSyncConnector` with `list_files()` and `download_file()`
methods. See `docs/patterns.md` for how to add a new connector.
{%- endif %}
