# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.4] - 2026-04-09

### Security

- **SSRF protection for webhook URLs (CWE-918)** — Added `validate_webhook_url()` in `app/core/sanitize.py` that blocks private/reserved/loopback/link-local/multicast/CGNAT IPs, validates DNS resolution against internal networks, rejects non-http(s) schemes and URLs with credentials. Validation enforced at webhook create, update, and delivery time across all three database variants (PostgreSQL, SQLite, MongoDB). Includes `SSRFBlockedError` exception with proper 422 responses and 39 unit tests. (PR #62)

## [0.2.3] - 2026-04-05

### Added

- **`.claude/` directory in generated projects** — Full Claude Code project structure so generated projects work as AI-native codebases out of the box
  - **`settings.json`** — Auto-allow permissions for safe operations (Read, Glob, Grep, git, pytest, ruff, ty, alembic)
  - **`rules/architecture.md`** — Layered architecture patterns (Routes → Services → Repositories), DI with `Annotated` aliases, `db.flush()` convention, domain exceptions
  - **`rules/code-style.md`** — Type hints (`str | None`), naming conventions table, import ordering (stdlib → third-party → local), ruff config
  - **`rules/schemas-models.md`** — Pydantic v2 `*Create/*Update/*Read/*List` pattern, `BaseSchema` with `ConfigDict`, SQLAlchemy `Mapped[]` columns, `TimestampMixin`
  - **`rules/exceptions-security.md`** — Domain exception hierarchy (`AppException` → `NotFoundError`, etc.), JWT/bcrypt patterns, `RoleChecker`, API key verification
  - **`rules/api-conventions.md`** — REST design, pagination (`Query(ge=0, le=100)`), auth deps (`CurrentUser`/`CurrentAdmin`/`ValidAPIKey`), response format, file upload
  - **`rules/testing.md`** — Async test patterns, `httpx.AsyncClient`, fixtures, exception testing with `pytest.raises`
  - **`rules/frontend.md`** — Next.js 15 App Router, Server Components, Tailwind conventions (auto-removed when frontend disabled)
  - **`commands/review.md`** — `/project:review` slash command: checks changes against architecture, types, security, and runs linting
  - **`commands/add-endpoint.md`** — `/project:add-endpoint` slash command: scaffolds full CRUD (schema → model → repo → service → deps → route → migration → test)
  - **`commands/fix-issue.md`** — `/project:fix-issue` slash command: traces through layers, fixes, tests, lints
- **Enhanced `CLAUDE.md`** — Rewritten with precise patterns from the actual codebase: architecture layers, DI pattern, schema conventions, exception table, response format examples, key conventions

### Changed

- **Replaced mypy with [ty](https://github.com/astral-sh/ty)** — Astral's Rust-based type checker (from the makers of ruff/uv). Updated across: `pyproject.toml`, Makefile, CI (GitHub Actions + GitLab CI), pre-commit config, `.gitignore`
- **Dependency version bumps** — All generated project dependencies updated to latest stable versions:
  - **Core:** FastAPI 0.135.3, uvicorn 0.43.0, Pydantic 2.12.0, pydantic-settings 2.13.0
  - **Database:** SQLAlchemy 2.0.40, asyncpg 0.31.0, alembic 1.18.0, sqlmodel 0.0.38, motor 3.7.0, beanie 1.29.0
  - **AI Frameworks:** pydantic-ai 1.77.0, langchain 1.2.0, langchain-openai 1.1.0, langgraph 0.4.0, langgraph-checkpoint 4.0.0, crewai 1.13.0
  - **Vector Stores:** pymilvus 2.6.0, qdrant-client 1.14.0, chromadb 1.5.0
  - **Infra:** redis 7.3.0, celery 5.6.0, sentry-sdk 2.53.0, logfire 4.30.0, sqladmin 0.24.0, boto3 1.42.0
  - **Dev:** pytest 9.0.0, ruff 0.15.0, ty 0.0.29

## [0.2.2] - 2026-03-20

### Changed — CLI Simplification (Breaking)

The interactive wizard and CLI have been significantly simplified. Many options that were previously user-configurable are now always enabled or have sensible defaults. This reduces decision fatigue and eliminates invalid configuration combinations.

- **AI Agent always enabled** — Removed `enable_ai_agent` option. AI agent with WebSocket streaming is always included. Stripped `{%- if cookiecutter.enable_ai_agent %}` conditionals from 53 template files.
- **Auth always JWT + API Key** — Removed `AuthType` enum and `--auth` CLI option. JWT (user management, login, roles) + API Key (utility for programmatic access) are always included. Stripped `WebSocketAuthType` — WebSocket always uses JWT.
- **Database always required** — Removed `DatabaseType.NONE` and `--database none`. JWT needs user storage. Minimal preset now uses SQLite.
- **Conversation persistence always on** — Removed `enable_conversation_persistence` option. Chat history always saved to database. Stripped 139 template conditionals.
- **i18n always enabled** — Removed `enable_i18n` option. `next-intl` always included with `[locale]` routing. Stripped 50 template conditionals.
- **Example CRUD removed** — Removed `include_example_crud` option. Item model/routes/tests no longer generated. Post-gen hook always cleans up CRUD files.
- **Session management defaults to enabled** — Changed default from `False` to `True`.
- **Admin panel simplified** — Removed `AdminEnvironmentType` enum and auth config prompts. Admin panel always uses `dev_staging` environment restriction and always requires auth. Checkbox label clarified: "SQL Admin Panel (SQLAdmin) — web UI for browsing/editing database tables".
- **Background tasks default Celery** — Changed default from `None` to `Celery`. Celery is first option in wizard (was last). `None` option kept for projects without Redis.

### Added

#### CLI

- **`--s3-rag` flag** — Enable S3/MinIO document ingestion from CLI (previously only available in interactive mode)
- **S3 ingestion prompt** — Interactive wizard now asks "Enable S3/MinIO document ingestion?"
- **Image description prompt** — Interactive wizard now asks "Enable image description in documents?" for RAG
- **Reranker type selection** — Replaced boolean `--reranker` with proper `RerankerType` enum. User's choice (Cohere vs Cross-Encoder) is now preserved instead of being auto-determined by LLM provider
- **PDF Parser "All" option** — New option installs all 3 parsers (PyMuPDF, LiteParse, LlamaParse). Runtime selection via `PDF_PARSER` and `CHAT_PDF_PARSER` env vars. `PdfParserFactory` creates parser on demand
- **RAG without Celery** — RAG now works with `BackgroundTasks` (no Celery/Taskiq/ARQ required). Ingestion and sync run in-process via FastAPI `BackgroundTasks`. Removed validation that blocked RAG without a task queue
- **Retry, sync logs, cancel endpoints always available** — Previously gated behind Celery/Taskiq/ARQ, now work with any background task backend

#### Backend

- **`CHAT_PDF_PARSER` env var** — Separate parser config for chat file attachments (independent from RAG ingestion). Defaults to `pymupdf` for speed
- **`PdfParserFactory`** — Factory class for runtime PDF parser selection when "All" parsers installed
- **Conversation IDOR protection** — `get_conversation()` now validates `user_id` ownership. Users can only access their own conversations
- **OAuth null password guard** — `authenticate()` checks `user.hashed_password is not None` before `verify_password()`. Prevents crash for OAuth-only users
- **ChatFile cascade delete** — Added `ondelete="CASCADE"` to `user_id` and `message_id` foreign keys in all 4 DB variants
- **SQLite ToolCall args deserialization** — Added `field_validator` on `ToolCallBase.args` that deserializes JSON strings for SQLite compatibility
- **Embedding dimension validation** — Runtime check in `EmbeddingService` that embedding output matches configured `dim`. Raises `ValueError` on mismatch
- **Collection name validation** — Regex check `^[a-zA-Z][a-zA-Z0-9_]{0,63}$` on collection creation. Prevents SQL injection in pgvector and invalid names
- **Vector store connection cleanup** — Qdrant `client.close()` and PgVector `engine.dispose()` in lifespan shutdown

#### RAG

- **ChromaDB async compliance** — All ChromaDB operations wrapped in `asyncio.to_thread()` to avoid blocking the event loop
- **ChromaDB `_ensure_collection()`** — Added missing method. `POST /collections/{name}` now works with ChromaDB
- **ChromaDB filter support** — `search()` now parses `parent_doc_id` filter and passes as ChromaDB `where` clause
- **ChromaDB consistent metadata** — Now uses `_build_chunk_metadata()` (same as Milvus/Qdrant/pgvector)
- **Qdrant filter support** — `search()` now parses filter string and passes as `query_filter` with `FieldCondition`
- **RRF fusion key fix** — Changed merge key from `content[:100]` (collision-prone) to `parent_doc_id:chunk_num`

#### Frontend

- **Refresh token rotation** — `/api/auth/refresh` now updates `refresh_token` cookie when backend returns a new one
- **WebSocket connection guard** — Prevents orphaned WebSocket instances by checking `CONNECTING` state
- **Scroll pagination guard** — Conversation sidebar scroll handler checks `isLoading` + fetch mutex prevents concurrent requests
- **Message deduplication** — Chat messages cleared before loading conversation history, preventing duplicates on switch

### Fixed

- **Port validator** — Returns descriptive error messages ("Port must be between 1024 and 65535") instead of generic `False`
- **Reverse proxy default** — `ReverseProxyType.NONE` when Docker disabled (was `TRAEFIK_INCLUDED`)
- **OpenRouter validation** — Consolidated 4 separate checks into single message: "OpenRouter is only supported with PydanticAI, not {framework}"
- **RAG prompt cancellation** — All questionary calls in `prompt_rag_config()` now wrapped with `_check_cancelled()`. Ctrl+C during RAG config shows "Cancelled." instead of crashing
- **Stale docstring** — Removed bogus `Args: llm_provider` from `prompt_rag_config()` (function has no parameters)
- **Hardcoded `lang="en"`** — Root layout now uses locale from i18n config
- **Milvus version pinned** — Dev compose files use `v2.5.10` (was `latest`), matching production
- **Frontend CI** — Added `bun run lint` and `bun run type-check` steps to CI pipeline
- **Tailwind CSS** — Updated from `^4.0.0-beta.8` to `^4.0.0` (stable)
- **SQLite WebSocket auth** — `contextmanager(get_db_session)()` pattern verified working with mypy
- **`TYPE_CHECKING` import for ChatFile** — Added to SQLAlchemy PG and SQLite conversation model variants
- **Duplicate import** — Removed duplicate `import Image from "next/image"` in `message-item.tsx`
- **RAG search result off-by-one** — Fixed array indexing in expanded view, uses `.find()` by index value
- **Login loading state** — `setLoading(false)` now in `finally` block (was only in `catch`)
- **Refresh cookie clearing** — Cookie options (`httpOnly`, `secure`, `sameSite`) now consistent with logout route
- **Tool call status fallback** — `statusConfig[status]` falls back to `pending` for unknown statuses

### Added

#### Frontend — Landing Page
- **Floating navbar with animated beam border** — Pill-shaped navbar with rotating conic-gradient border in brand color, glass morphism background, adaptive dark/light mode
- **Tech stack marquee** — Infinite scrolling carousel with all project technologies (30+ items), edge fade mask, 60s animation loop
- **Grid background** — 64px grid pattern on hero section with radial gradient mask fade
- **Glass cards** — Frosted glass feature cards with backdrop-blur, hover lift animation, dark/light mode variants
- **Brand color system** — Global `--color-brand` CSS variable (oklch), configurable hue presets (blue, green, red, violet, orange). Changes one value to retheme entire app
- **Footer** — Two-column footer with product links, resources, API docs link, copyright

#### Frontend — Auth
- **Split layout login/register** — Left panel: dark bg with grid, gradient glow, heading, feature pills (AI Chat, KB, Auth, Real-time), quote. Right panel: form with contrasting background. Mobile: form only
- **Auth guard** — Client-side `AuthGuard` component wraps dashboard layout, redirects unauthenticated users to `/login` with loading spinner

#### Frontend — Dashboard
- **Personalized greeting** — "Good morning/afternoon/evening, {name}" based on time of day
- **Stats row** — Compact 4-column cards (API status, Conversations, Knowledge Base, AI Agent)
- **Recent conversations** — Last 5 chats with relative timestamps, skeleton loading
- **Collections overview** — Clickable RAG collection list with vector counts and status badges
- **Quick actions grid** — 2x2 icon grid (New Chat, Upload Docs, API Docs, Profile)
- **Account card** — Avatar with initials, email, role, registration date
- **Environment card** — Status, version, framework, LLM, vector store info

#### Frontend — Chat
- **"Thinking..." indicator** — Animated bounce dots before first content arrives from LLM
- **Copy buttons** — Appear on hover under both user and assistant messages (moved from inside bubble)
- **Message timestamps** — HH:MM format under each message, hidden during streaming
- **File upload system** — Upload images, text, PDF, DOCX via backend API. Thumbnail preview for images, badge for files. Files parsed on backend (PyMuPDF for PDF, python-docx for DOCX)
- **Image support (LLM Vision)** — Images sent as `BinaryContent` to PydanticAI agent for vision analysis. Stored in `media/` directory, linked to messages via `ChatFile` model
- **Microphone (Speech-to-Text)** — Web Speech API voice input button, always visible, toast fallback for unsupported browsers
- **Message queue** — Input not disabled during processing. Messages queued on frontend, auto-sent when bot finishes responding
- **Model selector** — Dropdown in chat status bar (Claude Sonnet 4, Claude 3.5 Sonnet, GPT-4o, GPT-4o Mini, Gemini 2.5 Flash). Backend `get_agent(model_name=...)` accepts override
- **Tool call persistence** — Tool calls (name, args, result, status) saved to database during WebSocket streaming. Visible when loading conversation history

#### Frontend — Knowledge Base (RAG Dashboard)
- **Sidebar layout** — Collections in left sidebar (collapsible), documents/search in main area
- **Create collection** — Inline input in sidebar with "+" button
- **Upload & ingest** — File upload → backend ingestion (parse, chunk, embed, store). Supports PDF, DOCX, TXT, MD. Max 50MB
- **Document tracking** — `RAGDocument` model in database: status (processing/done/error), error message, timestamps, storage path
- **Document list** — Per-collection with filename, type badge, size, date, status icon (spinner/check/error)
- **View original** — Eye icon opens original uploaded file (stored in local storage / S3)
- **Delete document** — AlertDialog confirmation, removes from vector store + file storage + SQL
- **Search** — Full-text vector search with score badges, source document linking ("View source")

#### Frontend — UI Components (shadcn/ui + Radix)
- **Dialog** — `@radix-ui/react-dialog` based modal with overlay, close button, fade+zoom animations
- **AlertDialog** — `@radix-ui/react-alert-dialog` for destructive action confirmations (delete collection, delete document)
- **Avatar** — `@radix-ui/react-avatar` with image support and initial fallback
- **Skeleton** — Pulse animation placeholder for loading states
- **Separator** — `@radix-ui/react-separator` for visual dividers
- **Tooltip** — `@radix-ui/react-tooltip` with TooltipProvider
- **Button `asChild` fix** — `@radix-ui/react-slot` enables proper `asChild` prop on Button component

#### Frontend — Navigation & Layout
- **Nav links in header** — Dashboard, Chat, Knowledge Base, Profile tabs with icons and active state (moved from sidebar)
- **Sidebar → mobile only** — Desktop sidebar removed, kept as Sheet drawer for mobile
- **Language switcher** — Segmented control buttons (EN | PL) with `router.push` locale switching
- **Softer dark theme** — Zinc-inspired tones (14.5% lightness, subtle blue-purple hue 285) replacing pure black (12%)
- **`BACKEND_URL` constant** — API docs links point to backend (`http://localhost:8000/docs`), not frontend
- **Page transition animations** — Fade-in + 6px slide-up animation (250ms ease-out) on dashboard page navigation via `PageTransition` component with `key={pathname}` re-mount
- **Breadcrumbs** — Auto-generated breadcrumb navigation on Profile and Settings pages with `aria-label="Breadcrumb"`, chevron separators, clickable parent links

#### Frontend — Error Handling
- **404 page** — `not-found.tsx` with "Page not found" message, "Go home" and "Dashboard" buttons, brand-colored styling
- **500 error boundary** — `global-error.tsx` with inline styles (no CSS dependency), "Try again" reset button, error digest ID display
- **Page error boundary** — `[locale]/error.tsx` catches errors within layout, preserves header/sidebar, "Try again" + "Go home" buttons

#### Frontend — Accessibility
- **`aria-current="page"`** — Active nav items in header marked for screen readers
- **`aria-live="polite"`** — Loading/status changes announced: auth guard, chat "Thinking..." indicator, RAG upload progress, RAG document status icons
- **`aria-hidden="true"`** — Decorative bounce dots and spinner icons hidden from screen readers
- **`role="status"`** — RAG `StatusIcon` component with descriptive `aria-label` (Completed/Failed/Processing)

#### Backend — File System
- **`ChatFile` model** — Tracks files uploaded in chat (user_id, message_id, filename, mime_type, storage_path, file_type, parsed_content)
- **`LocalFileStorage` service** — Save/load/delete files in `media/{user_id}/` directory. Extensible `BaseFileStorage` ABC for S3/MinIO
- **`POST /files/upload`** — Multipart upload with MIME validation, 10MB limit, auto-parsing (text/PDF/DOCX)
- **`GET /files/{id}`** — Download with owner-only access check
- **File linking** — Files linked to messages via `message_id` FK, loaded with conversation history

#### Backend — RAG Improvements
- **Async Celery ingestion** — `POST /rag/collections/{name}/ingest` returns `202 Accepted` and dispatches `ingest_document_task` to Celery worker. Falls back to synchronous ingestion when Celery is not enabled
- **WebSocket status updates** — `WS /rag/ws/status` endpoint subscribes to Redis pub/sub channel `rag_status`, forwards real-time ingestion status (processing → done/error) to frontend
- **RAG is global** — Removed `user_id` from `RAGDocument` model. All documents, collections, and vectors are shared across users (no per-user isolation)
- **CLI DB tracking** — `rag-ingest` CLI command now creates `RAGDocument` records in SQL for each file. Documents ingested via CLI appear in the Knowledge Base dashboard with status tracking
- **Retry endpoint** — `POST /rag/documents/{id}/retry` resets failed document status to `processing` for re-ingestion
- **`RAGDocument` model** — Tracks ingestion status (processing/done/error), error_message, vector_document_id, storage_path, timestamps
- **`GET /rag/documents`** — List tracked documents with collection filter
- **`GET /rag/documents/{id}/download`** — Download original ingested file
- **`DELETE /rag/documents/{id}`** — Removes from vector store + file storage + SQL (3-way cleanup)
- **Configurable upload size** — `MAX_UPLOAD_SIZE_MB` setting (default 50MB) used in file upload, RAG ingest, and health endpoint. Frontend reads from `NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB` env var
- **Batch upload** — Frontend RAG page supports multi-file upload with progress bar (X/Y files, filename indicator)
- **Filename fix in ingestion** — `document.metadata.filename` set from `source_path` instead of temp file name
- **`EmbeddingsConfig` model validator** — Auto-derives vector dimensions from model name via `EMBEDDING_DIMENSIONS` lookup table
- **`EMBEDDING_MODEL` env var wired** — Settings → RAGSettings → EmbeddingsConfig flow complete

#### Backend — Agent Improvements
- **Tool call persistence** — WebSocket handler collects tool calls during streaming, saves to DB after assistant message
- **Conversation title auto-set** — Backend updates conversation title from first user message when title is empty
- **Model selection** — WebSocket handler accepts `model` field, passes to `get_agent(model_name=...)`
- **File handling in WS** — Parses `file_ids` from WebSocket message, loads files, images → `BinaryContent` for LLM vision, text/PDF/DOCX → parsed content appended to prompt

#### Backend — Security & Compliance
- **PII redaction in logs** — `PiiRedactionFilter` logging filter scrubs emails, JWT tokens, API keys (OpenAI/Anthropic), Bearer tokens, and password-like values from all log output. Prevents PII leaks to log aggregators (Datadog, CloudWatch, Logfire). Activated via `setup_logging()` at app startup
- **Dependency vulnerability scanning** — CI pipeline includes `security` job with `pip-audit` for supply chain risk detection
- **Docker image scanning** — Trivy vulnerability scanner (`aquasecurity/trivy-action@0.28.0`) runs after Docker build in CI, reports CRITICAL and HIGH severity issues

#### Backend — Database & Infrastructure
- **Missing indexes added** — `users.oauth_provider`, `users.oauth_id`, `sessions.user_id`, `webhooks.user_id`, `webhook_deliveries.webhook_id`, `webhook_deliveries.created_at` (all SQL variants)
- **`MEDIA_DIR` config** — New setting for file storage directory
- **`import sqlmodel` in migrations** — Added to `script.py.mako` template for SQLModel projects
- **Graceful RAG startup** — Embedding, reranker, vector store warmup wrapped in try/except, app doesn't crash on failure

### Changed

- **Auth layout theme-aware** — Left hero panel now adapts to light/dark mode (`bg-zinc-100 dark:bg-zinc-950`) instead of hardcoded `bg-zinc-950`
- **`next/image` migration** — Chat file thumbnails and attached images use `next/image` with `unoptimized` for lazy loading and layout stability
- **Consistent loading states** — All `"..."` placeholder text and `"Loading..."` messages replaced with `Skeleton` components (dashboard stats, conversation sidebar, OAuth callback)
- **RAG sidebar responsive** — Sidebar width `w-52 lg:w-64` (narrower on tablets, full width on desktop)
- **Empty search state** — RAG search shows in-UI "No results found" with icon instead of toast-only
- **Profile inline update** — `window.location.reload()` replaced with Zustand `setUser()` for instant state update without page reload
- **Real-time form validation** — Register: email format on blur, password strength bar (Weak/Fair/Good/Strong), confirm password match indicator. Login: email format on blur
- **`TimestampMixin` uses `sa_column_kwargs`** — Fixed SQLModel shared Column object bug (`Column 'created_at' already assigned to Table`)
- **`MessageList` schema** — Changed from `MessageReadSimple` (no tool_calls) to `MessageRead` (with tool_calls + files)
- **`list_messages` endpoint** — Now passes `include_tool_calls=True` to eagerly load tool call relationships
- **RAG proxy routes** — Removed `NEXT_PUBLIC_AUTH_ENABLED` gate, always forward auth cookie if present
- **Removed unused code** — `pipelines/` directory, `repositories/base.py`, `worker/tasks/rag_ingestion.py` (reindex task), `test_pipelines.py`, `docs/howto/add-data-pipeline.md`
- **Removed section dividers** — `# =========` comments removed from `services/conversation.py`, `repositories/conversation.py`, `schemas/conversation.py`
- **`itsdangerous` dependency** — Added when OAuth enabled (required by Starlette `SessionMiddleware`)
- **`logger` added to `main.py`** — `import logging` + `logger = logging.getLogger(__name__)` for RAG startup error logging
- **Document ingestion is CLI-only** - Removed upload API endpoints. Ingestion exclusively via CLI commands (later re-added as `POST /rag/collections/{name}/ingest`)
- **`RetrievalService` renamed** - `MilvusRetrievalService` → `RetrievalService` (now backend-agnostic)
- **Docker validation relaxed** - Docker only required for Milvus and Qdrant vector stores
- **`.env.example` restructured** - RAG section moved from `use_milvus` to `enable_rag` guard
- **README.md rewritten** - Updated for 5 frameworks, 4 providers, RAG section with vector store/embedding tables
- **CLAUDE.md / AGENTS.md updated** - Both project-level and template versions updated with RAG, Gemini, vector stores

### Fixed

- **Language switching** — `usePathname()` with next-intl returns path with locale prefix, original `segments[1] = newLocale` + `router.push` logic restored
- **Conversation "20531d ago"** — `updated_at` null fallback to `created_at` in dashboard
- **RAG stats "..."** — Set `{collections: [], totalVectors: 0}` on error instead of null
- **`callable | None` TypeError** — Changed to `Callable | None` with proper import in `ingestion.py`
- **Tool call card TS error** — `Type 'unknown' not assignable to ReactNode` fixed with ternary
- **Empty args crash** — `json.loads("")` in tool call persistence fixed with `.strip()` check
- **`user_prompt` serialization** — `BinaryContent` not JSON serializable, now sends text-only prompt in WS event
- **File linking FK violation** — ChatFile `message_id` update moved to same DB session as message insert

#### RAG (Retrieval-Augmented Generation) — Pipeline

- **RAG integration** - Full RAG pipeline: document parsing → chunking → embedding → vector store → retrieval. Integrated with all 5 AI frameworks as `search_knowledge_base` tool
- **4 vector store backends** - Milvus (Docker), Qdrant (Docker), ChromaDB (embedded), pgvector (PostgreSQL extension). Selected via `vector_store` config option
- **4 embedding providers** - OpenAI (`text-embedding-3-small`), Voyage (`voyage-3`), Google Gemini (`gemini-embedding-exp-03-07`, multimodal), SentenceTransformers (`all-MiniLM-L6-v2`)
- **Document parsers** - PyMuPDF (PDF text + tables + headers/footers + images + OCR), LlamaParse (130+ formats via cloud API, configurable tier), python-docx (DOCX), native (TXT/MD)
- **Image description** - Optional extraction of images from documents via PyMuPDF + LLM vision API description (OpenAI GPT-4o / Anthropic Claude / Gemini / OpenRouter). Opt-in via `enable_rag_image_description`
- **Chunking strategies** - 3 strategies: `recursive` (default), `markdown` (split by headers), `fixed` (simple fixed-size). Configurable via `RAG_CHUNKING_STRATEGY` env var
- **Hybrid search** - BM25 keyword search + vector similarity search with Reciprocal Rank Fusion (RRF). Enable via `RAG_HYBRID_SEARCH=true`
- **Reranking** - Cohere API or local CrossEncoder for improved search quality
- **Citation/source tracking** - Agent tool returns `[1] Source: filename, page X, chunk Y` format. Agent prompt instructs citation with `[1]`, `[2]` references and source list
- **Document versioning** - `source_path` (local path / `gdrive://id` / `s3://bucket/key`) and `content_hash` (SHA256) in metadata. Automatic deduplication: re-ingest replaces old chunks. CLI: `--replace` / `--no-replace`
- **Multi-collection search** - `RetrievalService.retrieve_multi()` searches across multiple collections. API: `collection_names: list[str]`. Frontend: "All collections" option
- **Document sources** - Local files (CLI `rag-ingest`), Google Drive (service account, CLI `rag-sync-gdrive`), S3/MinIO (CLI `rag-sync-s3`). Extensible `BaseDocumentSource` ABC
- **Ingestion progress** - `tqdm` progress bar in CLI `rag-ingest` with per-file status and replaced count
- **RAG management page** - Frontend `/rag` page: collection list with stats, search preview with results, metadata filters (filetype, min score), multi-collection support, delete collection
- **RAG API endpoints** - `GET/POST/DELETE /rag/collections`, `GET /rag/collections/{name}/info`, `GET /rag/collections/{name}/documents`, `POST /rag/search`, `DELETE /rag/collections/{name}/documents/{id}`
- **RAG CLI commands** - `rag-collections`, `rag-ingest`, `rag-search`, `rag-drop`, `rag-stats`, `rag-sync-gdrive`, `rag-sync-s3`

#### AI / LLM

- **Google Gemini LLM provider** - New `--llm-provider google` option. PydanticAI: `GoogleModel` + `GoogleProvider`. LangChain/LangGraph/CrewAI/DeepAgents: `ChatGoogleGenerativeAI`. Dependencies: `pydantic-ai-slim[google]`, `langchain-google-genai`
- **Gemini multimodal embeddings** - `GeminiEmbeddingProvider` with `embed_image()` for native multimodal (text + images in same vector space). Model: `gemini-embedding-exp-03-07` (3072 dim)

#### Frontend

- **Toast notification system** - `sonner` library with `<Toaster />` in providers. Toast feedback on: login, register, logout, profile save, RAG operations
- **Profile save wired** - "Save Changes" button now calls `PATCH /users/me`. Editable email field, loading state, toast feedback
- **Dashboard redesigned** - Stats cards (API status, account, AI framework, RAG vector count), quick action links (Chat, Knowledge Base, Profile)
- **Settings page** - New `/settings` page with sections: Appearance (theme toggle), Application (project info, AI framework, vector store), Stack (technology badges), Security (auth type, rate limiting)
- **Metadata filtering UI** - RAG search page: filetype dropdown, min score dropdown, "Clear filters" link
- **Specialized tool call cards** - DateTime tool: Calendar/Clock icons with formatted date/time. RAG search: horizontal card carousel with filename, page, score badges, expandable content. Toggle between formatted and raw JSON view
- **Sidebar "Knowledge Base" link** - Navigation item with Database icon, conditional on `enable_rag`

#### DevOps

- **`make quickstart`** - One command to install deps, start Docker services, run migrations, create admin user
- **Vercel deployment** - `frontend/vercel.json` config + `make vercel-deploy` target with env var instructions
- **Qdrant Docker service** - Added to `docker-compose.dev.yml` with health check, volume, and backend env vars

#### PR #50 RAG Bug Fixes (28 issues found and fixed)

- **`schedules.py` regression** - Outer conditional broke Taskiq scheduling for all non-RAG projects. Fixed: restored `use_taskiq` guard, RAG schedule inside nested conditional
- **Duplicate Milvus settings** - `core/config.py` had Milvus settings twice. Fixed: removed duplicate, nested under `use_milvus` inside `enable_rag`
- **Env vars not wired to RAGSettings** - `RAG_CHUNK_SIZE`, `RAG_DEFAULT_COLLECTION` ignored at runtime. Fixed: wired through `Settings.rag` computed property
- **Copy-paste etcd command in prod MinIO** - `docker-compose.prod.yml` minio had etcd command. Fixed: removed
- **Frontend type mismatch** - `RAGSearchResult.text` vs backend `content`. Fixed: renamed to `content`, added `parent_doc_id`
- **Milvus filter injection** - `document_id` interpolated unsanitized. Fixed: strip `"` and `\` before interpolation
- **File upload security** - No filename sanitization, no size limit. Fixed: `_safe_filename()`, `MAX_UPLOAD_SIZE=50MB`, HTTP 413
- **Hardcoded MinIO credentials in prod** - Fixed: env var substitution `${MINIO_ROOT_USER}` / `${MINIO_ROOT_PASSWORD}`
- **`milvusdb/milvus:latest` in prod** - Fixed: pinned to `v2.5.10`
- **`processor.parser.allowed` AttributeError** - Fixed: use `DocumentExtensions` enum directly
- **Inconsistent default collection** - sync wrapper `"default"` vs async `"documents"`. Fixed: both `"documents"`
- **`RerankService` NameError when disabled** - Fixed: `from __future__ import annotations`
- **`print()` in reranker.py** - Fixed: all 13 `print()` → `logger.info()`
- **`console.log` in rag-api.ts** - Fixed: removed debug statements
- **Legacy typing imports in schemas** - Fixed: `List`→`list`, `Dict`→`dict`, `Optional`→`| None`
- **Hardcoded `/tmp/rag_uploads`** - Fixed: `tempfile.gettempdir()`
- **Inconsistent frontend auth** - Fixed: all RAG routes use `NEXT_PUBLIC_AUTH_ENABLED` pattern
- **Inline `import logging` in routes** - Fixed: moved to module level
- **Unconditional PDF parser import** - Fixed: conditional on `not use_llamaparse`
- **Chat page not removed when i18n disabled** - Fixed: remove both `[locale]/` and direct paths
- **`stores/index.ts` unconditional chat exports** - Fixed: previously gated behind `enable_ai_agent` (now always enabled)
- **`types/index.ts` unconditional chat export** - Fixed: previously gated behind `enable_ai_agent` (now always enabled)
- **`chat-sidebar-store.ts` not cleaned up** - Fixed: added to post-gen hook
- **`rag/config.py` gated by `use_milvus`** - Fixed: changed to `enable_rag`
- **Worker tasks gated by `use_milvus`** - Fixed: `rag_ingestion.py`, `celery_app.py`, `arq_app.py` changed to `enable_rag`
- **pgvector SQL injection** - Fixed: `_validate_collection_name()` regex + `_table()` helper in all methods
- **pgvector IVFFlat on empty table** - Fixed: changed to HNSW index
- **Duplicate `logger` in reranker.py** - Fixed: removed duplicate, reordered imports

## [0.2.1] - 2026-03-05

### Added

- **LangSmith observability integration** - New `enable_langsmith` option for LangChain, LangGraph, and DeepAgents frameworks. Adds `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`, `LANGCHAIN_ENDPOINT` settings and `langsmith` dependency when enabled. Includes interactive prompt, `--langsmith` CLI flag, and auto-enable in `ai-agent` preset. Previously LangSmith env vars were hardcoded to appear with LangChain — now requires explicit opt-in and works with all 3 LangChain-ecosystem frameworks.
- **CLI: `--conversation-persistence` flag** - Enable conversation persistence from the command line (previously only available interactively)
- **CLI: `--websocket-auth` option** - Set WebSocket authentication method (`none`, `jwt`, `api_key`) from the command line

### Changed

- **CLI runs interactive wizard by default** - `fastapi-fullstack` now launches the configurator directly without requiring `new` subcommand
- **CLI branding updated** - Banner, descriptions, and prog name updated from "fastapi-gen / FastAPI Project Generator with Logfire" to "Full-Stack AI Agent Template Generator"
- **`templates` command expanded** - Now lists all 5 AI frameworks, LangSmith, ORM options, WebSocket auth, conversation persistence, and port options

### Fixed

#### CLI Fixes

- **`--ai-framework` missing 3 frameworks** - Added `langgraph`, `crewai`, `deepagents` to choices (previously only `pydantic_ai` and `langchain`)

#### Backend Template Fixes

- **Unconditional `import logfire` in `versioning.py`** - Replaced with `logging` module to prevent `ImportError` when Logfire is disabled
- **Unconditional `import logfire` in `webhook.py`** - Replaced `logfire.error()`/`logfire.info()` with `logger.error()`/`logger.info()` in all 3 database sections (PostgreSQL, SQLite, MongoDB) to prevent `ImportError` when Logfire is disabled but webhooks are enabled
- **`backend/.env` LangSmith conditional wrong** - Was gated by `use_langchain` instead of `enable_langsmith` (only `.env.example` was updated, `.env` was missed)
- **`backend/.env` missing sections** - Added OAuth Google, ARQ, and Prometheus sections that were present in `.env.example` but absent from generated `.env`

#### Frontend Template Fixes

- **Sidebar "Chat" link visible without AI agent** - Chat navigation item now always visible (AI agent is always enabled)
- **Frontend chat files not cleaned up** - No longer applicable (AI agent is always enabled, chat files are always present)
- **Chat component exports unconditional** - Chat exports are now always included (AI agent is always enabled)
- **Chat hook exports unconditional** - Hook exports for `useWebSocket`, `useChat`, `useLocalChat` are now always included (AI agent is always enabled)
- **`WS_URL` and `ROUTES.CHAT` always defined** - `constants.ts` now conditionally defines WebSocket URL and chat route only when AI agent is enabled

## [0.2.0] - 2026-02-27

### Changed

- **Repository renamed** from `full-stack-fastapi-nextjs-llm-template` to `full-stack-ai-agent-template` — all internal links, badges, raw.githubusercontent URLs, mkdocs config, and template files updated. Old GitHub URLs redirect automatically.
- **Repository marked as GitHub Template** — users can now click "Use this template" to create a new repo directly from GitHub
- **README CTA section** — replaced "Made with" footer with Vstorm consultancy call-to-action

## [0.1.18] - 2026-02-01

### Fixed

- **Removed macOS `.DS_Store` artifacts** and added `.DS_Store` to `.gitignore` (contributed by [@vladdoster](https://github.com/vladdoster) in [#42](https://github.com/vstorm-co/full-stack-ai-agent-template/pull/42))

## [0.1.17] - 2026-01-24

### Added

- **MkDocs Material documentation site** with pink theme, Inter/JetBrains Mono fonts
- New documentation pages:
  - `docs/index.md` - Landing page with quick start and features overview
  - `docs/installation.md` - Installation guide with uv/pip/pipx options
  - `docs/getting-help.md` - FAQ and support resources
  - `docs/concepts/index.md` - Architecture overview with Mermaid diagrams
  - `docs/guides/quick-start.md` - Step-by-step first project guide
  - `docs/guides/configuration.md` - All configuration options
- GitHub Actions workflow for automatic docs deployment (`docs.yml`)
- Custom styling (`docs/stylesheets/extra.css`) matching pydantic-deep theme
- GitHub announcement bar in docs header

### Changed

- **README.md redesign**:
  - New centered header with "Full-Stack AI Agent Template" title
  - Reorganized badges: AI frameworks (PydanticAI, LangChain, LangGraph, CrewAI, OpenAI, Anthropic, OpenRouter) moved to Features section
  - Added infrastructure badges: FastAPI, Next.js 15, React 19, TypeScript, Tailwind v4, SQLAlchemy, PostgreSQL, MongoDB, Redis, Celery, Logfire, Sentry, Prometheus, Docker, Kubernetes, GitHub Actions, S3
  - New highlights: "🤖 PydanticAI • 🦜 LangChain, LangGraph & DeepAgents • 👥 CrewAI • 🎯 Fully Type-Safe"
- Moved `CHANGELOG.md` from `docs/` to project root (symlinked in docs)
- Added `docs` optional dependency group with mkdocs packages

## [0.1.16] - 2026-01-20

### Fixed

- **Logfire Celery instrumentation prompt** - Celery instrumentation option now only appears when Celery is selected as background task system (previously caused validation error when selecting the option with Taskiq/ARQ)

### Changed

- **Prompt order** - Background tasks prompt now appears before Logfire prompt to enable dynamic feature filtering

### Tests Added

- Test for Celery instrumentation option visibility based on background task selection

## [0.1.15] - 2026-01-18

### Added

#### DeepAgents Framework Support

- **DeepAgents as fifth AI framework option** alongside PydanticAI, LangChain, LangGraph, and CrewAI
- New `--ai-framework deepagents` CLI option for project creation
- Interactive prompt includes "DeepAgents" choice
- **Built-in tools** for file operations, code execution, and task management:
  - `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`
  - `execute` (disabled by default for safety)
  - `write_todos`, `task` (sub-agents)
- **StateBackend** for in-memory file state management
- **Skills support** via `DEEPAGENTS_SKILLS_PATHS` environment variable
- New template files:
  - `app/agents/deepagents_assistant.py` - DeepAgentsAssistant class with run() and stream()
  - WebSocket route implementation with interrupt handling
- New cookiecutter variable: `use_deepagents`
- Dependencies: `deepagents>=0.1.0`

#### Human-in-the-Loop (HITL) Support

- **Tool approval workflow** for DeepAgents allowing users to approve, edit, or reject tool calls
- Configurable via `DEEPAGENTS_INTERRUPT_TOOLS` environment variable:
  - Comma-separated tool names (e.g., `write_file,edit_file,execute`)
  - Or `all` to require approval for all tools
- **Frontend tool approval dialog** (`tool-approval-dialog.tsx`):
  - Shows pending tool calls with JSON args in editable textarea
  - Cancel/Save buttons for editing args
  - Submit button to send decisions
  - Auto-detects changes and sends appropriate decision (approve/edit/reject)
- **WebSocket protocol** for interrupt handling:
  - Backend sends `tool_approval_required` event with action requests
  - Frontend sends `resume` message with user decisions
  - Thread ID management for state persistence across interrupts
- New types in `chat.ts`: `ActionRequest`, `ReviewConfig`, `PendingApproval`, `Decision`
- Updated hooks (`use-chat.ts`, `use-local-chat.ts`) with:
  - `pendingApproval` state
  - `sendResumeDecisions()` function
- Environment variables:
  - `DEEPAGENTS_INTERRUPT_TOOLS` - tools requiring approval
  - `DEEPAGENTS_ALLOWED_DECISIONS` - allowed decision types (approve, edit, reject)

### Fixed

- **OAuth requires JWT authentication** - Added validation that OAuth providers (Google) require JWT auth to be enabled, preventing invalid configuration combinations

### Changed

- **`AIFrameworkType` enum** extended with `DEEPAGENTS` value
- **AI framework prompt** now shows five options: PydanticAI, LangChain, LangGraph, CrewAI, DeepAgents
- **LLM provider validation** - OpenRouter not supported with DeepAgents (uses LangChain providers directly)
- **`VARIABLES.md`** updated with `use_deepagents` documentation
- **Template `CLAUDE.md`** includes DeepAgents in stack section
- **`CONTRIBUTING.md`** updated with correct repository URL

### Tests Added

- Tests for `DEEPAGENTS` enum value
- Tests for DeepAgents + OpenRouter validation (combination is rejected)
- Tests for `use_deepagents` computed field
- Tests for cookiecutter context generation with DeepAgents

## [0.1.14] - 2026-01-16

### Fixed

- **Dynamic version reading** - `fastapi-fullstack --version` now correctly displays the version from `pyproject.toml` using `importlib.metadata` instead of hardcoded value

### Security

- **CVE-2026-22701** - Updated `filelock` to 3.20.3
- **CVE-2026-21441** - Updated `urllib3` to 2.6.3
- **CVE-2026-22702** - Updated `virtualenv` to 20.36.1

## [0.1.13] - 2026-01-06

### Added

#### Comprehensive Configuration Validation

- **New validation rules** to prevent invalid option combinations at config time:
  - WebSocket JWT auth requires main JWT auth to be enabled
  - WebSocket API key auth requires main API key auth to be enabled
  - Admin panel authentication requires JWT auth (for User model)
  - Conversation persistence requires AI agent to be enabled
  - Admin panel requires SQLAlchemy ORM (SQLModel not fully supported by SQLAdmin)
  - Session management requires JWT auth
  - Webhooks require a database to store subscriptions and delivery history
  - Background task queues (Celery/Taskiq/ARQ) require Redis as broker
  - Logfire database instrumentation requires a database
  - Logfire Redis instrumentation requires Redis
  - Logfire Celery instrumentation requires Celery as background task system

#### Improved Post-Generation Instructions

- **Clearer database setup instructions** with warning message:
  ```
  ⚠️  Run all commands in order: db-migrate creates the migration, db-upgrade applies it
  ```
- **README.md** updated with prominent warning about required migration steps
- Commands displayed with aligned descriptions for better readability

#### Dynamic Integration Prompts

- **Context-aware integration options** in interactive wizard:
  - Admin Panel option only shown when SQLAlchemy is selected (not SQLModel)
  - Webhooks option only shown when a database is enabled
  - WebSocket auth options filtered based on main auth type selected
  - Clearer ORM selection labels: "SQLAlchemy — full control, supports admin panel" vs "SQLModel — less boilerplate, no admin panel support"
- **Auto-enable Redis** when caching is selected (with info message)
- **Better descriptions** for all integration options explaining dependencies

#### Template Improvements

- **ARQ worker service** added to `docker-compose.prod.yml`
- **Prometheus labels** added to backend service in `docker-compose.dev.yml`
- **OAuth environment variable** `NEXT_PUBLIC_API_URL` added to frontend `.env.example`
- **Frontend WS_URL** now uses `backend_port` cookiecutter variable instead of hardcoded 8000

### Changed

#### Post-Generation Hook Improvements

- **Stub file cleanup** - removes files containing only docstrings with no actual code
- **Auth file cleanup** - removes auth/user files when JWT is disabled:
  - `auth.py`, `users.py` routes
  - `user.py` model, repository, service, schema
  - `token.py` schema
- **Logfire cleanup** - removes `logfire_setup.py` when Logfire is disabled
- **Security cleanup** - removes `security.py` when no auth is configured at all
- **LangGraph/CrewAI cleanup** - properly removes unused AI framework files

### Fixed

#### Template Fixes

- **LangChain assistant `stream()` method** - changed from sync generator to async generator using `astream()` for proper async streaming
- **OAuth callback** - made fully async, removed sync `asyncio.new_event_loop()` hack
- **Deprecated `datetime.utcnow()`** - replaced with `datetime.now(UTC)` across all services:
  - `cleanup.py` command
  - `session.py` repository and service
  - `conversation.py` service
  - `webhook.py` service
- **Session model** - added missing `default_factory=datetime.utcnow` for `created_at` and `last_used_at` fields
- **Webhook model** - moved `import json` to module level instead of inside properties
- **Admin panel template condition** - now correctly checks for SQLAlchemy ORM requirement
- **Caching setup** - only runs when both caching AND Redis are enabled
- **Config imports** - fixed conditional imports for Redis-only projects (no database)

### Tests Added

- **290+ new test lines** covering all new validation rules
- Tests for WebSocket auth requiring main auth
- Tests for admin panel requiring SQLAlchemy
- Tests for admin authentication requiring JWT
- Tests for conversation persistence requiring AI agent
- Tests for webhooks requiring database
- Tests for Logfire feature dependencies (database, Redis, Celery)
- Tests for background task queues requiring Redis
- Updated CLI tests to include `--redis` flag with task queue options

## [0.1.12] - 2026-01-02

### Added

#### CrewAI Multi-Agent Framework Improvements

- **Full type annotations** for all CrewAI event handlers in `crewai_assistant.py`
- **Comprehensive event queue listener** with handlers for:
  - `crew_started`, `crew_completed`, `crew_failed`
  - `agent_started`, `agent_completed`
  - `task_started`, `task_completed`
  - `tool_started`, `tool_finished`
  - `llm_started`, `llm_completed`
- **Improved stream method** with proper thread and queue handling:
  - Natural completion path when receiving None sentinel
  - Race condition handling for thread death scenarios
  - Defensive code with `# pragma: no cover` for edge cases
- **100% test coverage** for CrewAI assistant module

### Fixed

#### Backend Fixes

- **Type annotations** - All mypy errors fixed across the codebase:
  - Added `Any` types where needed in `logfire_setup.py`
  - Fixed `Callable` types in `commands/__init__.py`
  - Added proper types to versioning middleware
  - Full type coverage for CrewAI event handlers
- **WebSocket disconnect handling** - Proper logging and cleanup when client disconnects during agent processing (lines 241-242 in `agent.py`)
- **Health endpoint edge cases** - Added `# pragma: no cover` for unreachable 503 response path (checks dict is always empty)
- **Abstract method coverage** - Added `# pragma: no cover` for abstract `run()` method in `BasePipeline`

#### Frontend Fixes

- **Timeline connector lines** for grouped messages now display correctly
- **Message grouping** visual indicators properly connect related messages

### Tests Added

- **100% code coverage achieved** (720 statements, 0 missing)
- Tests for all 11 CrewAI event handlers:
  - `test_crew_started_handler`, `test_crew_completed_handler`, `test_crew_failed_handler`
  - `test_agent_started_handler`, `test_agent_completed_handler`
  - `test_task_started_handler`, `test_task_completed_handler`
  - `test_tool_started_handler`, `test_tool_finished_handler`
  - `test_llm_started_handler`, `test_llm_completed_handler`
- Tests for CrewAI stream method edge cases:
  - `test_stream_complete_flow` - natural completion path
  - `test_stream_empty_queue_break` - queue empty handling
  - `test_stream_with_error` - error event handling
- Tests for WebSocket disconnect during processing:
  - `test_websocket_disconnect_during_stream`
  - `test_websocket_disconnect_during_processing`
- Tests for health endpoint edge cases:
  - `test_readiness_probe_503_unit` - 503 response logic

## [0.1.11] - 2026-01-02

### Added

#### LangGraph ReAct Agent Support

- **LangGraph as third AI framework option** alongside PydanticAI and LangChain
- New `--ai-framework langgraph` CLI option for project creation
- Interactive prompt includes "LangGraph (ReAct agent)" choice
- **ReAct (Reasoning + Acting) agent pattern** with graph-based architecture:
  - Agent node for LLM reasoning and tool decision
  - Tools node for executing tool calls
  - Conditional edges for tool execution loop
  - Memory-based checkpointing for conversation continuity
- **Full WebSocket streaming support** using `astream()` with dual modes:
  - `messages` mode for token-level LLM streaming
  - `updates` mode for node state changes (tool calls/results)
- **Tool result correlation** - proper `tool_call_id` matching between calls and results
- New template files:
  - `app/agents/langgraph_assistant.py` - LangGraphAssistant class with run() and stream()
  - WebSocket route implementation in `app/api/routes/v1/agent.py`
- New cookiecutter variable: `use_langgraph`
- Dependencies for LangGraph projects:
  - `langchain-core>=0.3.0`
  - `langchain-openai>=0.3.0` or `langchain-anthropic>=0.3.0`
  - `langgraph>=0.2.0`
  - `langgraph-checkpoint>=2.0.0`

### Changed

- **`AIFrameworkType` enum** extended with `LANGGRAPH` value
- **AI framework prompt** now shows three options: PydanticAI, LangChain, LangGraph
- **LLM provider validation** - OpenRouter not supported with LangGraph (same as LangChain)
- **`VARIABLES.md`** updated with `use_langgraph` documentation
- **Template `CLAUDE.md`** includes LangGraph in stack section

## [0.1.10] - 2025-12-27

### Added

#### Nginx Reverse Proxy Support

- **Nginx as alternative to Traefik** with two configuration modes:
  - `nginx_included`: Full Nginx setup in docker-compose.prod.yml
  - `nginx_external`: Nginx config template only, for external Nginx
- **Nginx configuration template** (`nginx/nginx.conf`) with:
  - Reverse proxy for backend API (api.DOMAIN)
  - Reverse proxy for frontend (DOMAIN) - conditional
  - Reverse proxy for Flower dashboard (flower.DOMAIN) - conditional
  - WebSocket support for `/ws` endpoint
  - Security headers (X-Frame-Options, X-Content-Type-Options, HSTS, etc.)
  - HTTP to HTTPS redirect
  - SSL/TLS configuration with modern cipher suites
  - Let's Encrypt ACME challenge support
- **SSL certificate directory** (`nginx/ssl/`) with setup instructions
- New cookiecutter variables:
  - `include_nginx_service`: Include Nginx container in docker-compose
  - `include_nginx_config`: Generate nginx configuration files
  - `use_nginx`: Using Nginx (included or external)
  - `use_traefik`: Using Traefik (included or external)

### Changed

- **Reverse proxy prompt** now offers 5 options:
  - Traefik (included in docker-compose) - default
  - Traefik (external, shared between projects)
  - Nginx (included in docker-compose)
  - Nginx (external, config template only)
  - None (expose ports directly)
- **`ReverseProxyType` enum** extended with `NGINX_INCLUDED` and `NGINX_EXTERNAL`
- **docker-compose.prod.yml** updated:
  - Added nginx service definition
  - Services use backend-internal network when nginx is selected
  - No ports exposed on backend/frontend when nginx handles traffic
- **`.env.prod.example`** includes DOMAIN variable for nginx configuration
- **`post_gen_project.py`** removes nginx/ folder when nginx is not selected

### Tests Added

- Tests for `NGINX_INCLUDED` and `NGINX_EXTERNAL` enum values
- Tests for cookiecutter context generation with all reverse proxy options
- Tests for `prompt_reverse_proxy()` with nginx choices

## [0.1.9] - 2025-12-26

### Added

#### SQLModel Support

- **Optional SQLModel ORM** as alternative to SQLAlchemy for PostgreSQL and SQLite
- New `--orm` CLI option: `--orm sqlalchemy` (default) or `--orm sqlmodel`
- Interactive prompt for ORM library selection when using `fastapi-fullstack new`
- SQLModel provides simplified syntax combining SQLAlchemy and Pydantic:
  ```python
  from sqlmodel import SQLModel, Field

  class User(SQLModel, table=True):
      id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
      email: str = Field(max_length=255, unique=True)
      is_active: bool = Field(default=True)
  ```
- Full Alembic compatibility maintained with SQLModel
- SQLAdmin works seamlessly with SQLModel models
- All database models updated with SQLModel variants:
  - `User`, `Item`, `Conversation`, `Message`, `Session`, `Webhook`, `WebhookDelivery`
- `VARIABLES.md` updated with new ORM variables: `orm_type`, `use_sqlalchemy`, `use_sqlmodel`

### Changed

- Database model templates now support conditional SQLModel/SQLAlchemy syntax
- `alembic/env.py` uses `SQLModel.metadata` when SQLModel is selected
- Repositories remain unchanged (SQLModel uses same AsyncSession and methods)

### Tests Added

- Tests for `OrmType` enum values
- Tests for `use_sqlalchemy` and `use_sqlmodel` computed fields
- Tests for SQLModel validation (requires PostgreSQL or SQLite)
- Tests for `prompt_orm_type()` function
- Updated `run_interactive_prompts()` tests with `prompt_orm_type` mocks

## [0.1.7] - 2025-12-23

### Added

#### Docker & Production

- **Optional Traefik reverse proxy** with three configuration modes:
  - `traefik_included`: Full Traefik setup in docker-compose.prod.yml (default)
  - `traefik_external`: Traefik labels only, for shared Traefik instances
  - `none`: No reverse proxy, ports exposed directly
- **`.env.prod.example` template** for production secrets management:
  - Conditional sections for PostgreSQL, Redis, JWT, Traefik, Flower
  - Required variable validation using `${VAR:?error}` syntax
  - Setup instructions in docker-compose.prod.yml header
- **Unique Traefik router names** using `project_slug` prefix for multi-tenant support:
  - `{project_slug}-api`, `{project_slug}-frontend`, `{project_slug}-flower`
  - Prevents conflicts when running multiple projects on same server

#### AI Agent Support

- **`AGENTS.md`** file for non-Claude AI agents (Codex, Copilot, Cursor, Zed, OpenCode)
- **Progressive disclosure documentation** in generated projects:
  - `docs/architecture.md` - layered architecture details
  - `docs/adding_features.md` - how to add endpoints, commands, tools
  - `docs/testing.md` - testing guide and examples
  - `docs/patterns.md` - DI, service, repository patterns
- **README.md** updated with "AI-Agent Friendly" section

### Changed

- **Template `CLAUDE.md` refactored** from 384 to ~80 lines following [progressive disclosure best practices](https://humanlayer.dev/blog/writing-a-good-claude-md)
- **Main project `CLAUDE.md`** updated with "Where to Find More Info" section
- **docker-compose.prod.yml** now uses `env_file: .env.prod` instead of inline defaults
- **Removed hardcoded credentials** (`changeme`) from docker-compose.prod.yml

### Security

- Production credentials no longer have insecure defaults
- `.env.prod` added to `.gitignore` to prevent committing secrets
- Required environment variables fail fast with descriptive error messages

## [0.1.6] - 2025-12-22

### Added

#### Multi-LLM Provider Support
- **Multiple LLM providers** for AI agents: OpenAI, Anthropic, and OpenRouter
- PydanticAI supports all three providers (OpenAI, Anthropic, OpenRouter)
- LangChain supports OpenAI and Anthropic
- New `--llm-provider` CLI option and interactive prompt
- Provider-specific API key configuration in `.env` and `config.py`

#### CLI Enhancements
- **`make create-admin` command** for quick admin user creation
- **Comprehensive CLI options** for `fastapi-fullstack create` command:
  - `--redis`, `--caching`, `--rate-limiting`
  - `--admin-panel`, `--websockets`
  - `--task-queue` (none/celery/taskiq/arq)
  - `--oauth-google`, `--session-management`
  - `--kubernetes`, `--ci` (github/gitlab/none)
  - `--sentry`, `--prometheus`
  - `--file-storage`, `--webhooks`
  - `--python-version` (3.11/3.12/3.13)
  - `--i18n`
- **Configuration presets** for common use cases:
  - `--preset production`: Full production setup with Redis, Sentry, K8s, Prometheus
  - `--preset ai-agent`: AI agent with WebSocket streaming and conversation persistence
- **Interactive rate limit configuration** when rate limiting is enabled:
  - Requests per period (default: 100)
  - Period in seconds (default: 60)
  - Storage backend (memory or Redis)

#### Documentation
- **Improved CLI documentation** in README explaining project CLI naming convention (`uv run <project_slug>`)
- **Makefile shortcuts** documented with `make help` command

#### Template Improvements
- **Generator version metadata** in generated projects (`pyproject.toml`):
  ```toml
  [tool.fastapi-fullstack]
  generator_version = "0.1.6"
  generated_at = "2025-12-22T10:30:00+00:00"
  ```
- **Centralized agent prompts** module (`app/agents/prompts.py`) for easier maintenance
- **Template variables documentation** (`template/VARIABLES.md`) with 88+ variables documented

#### Validation
- **Email validation** for `author_email` field using Pydantic's `EmailStr`
- **Tests for OpenRouter + LangChain** validation (combination is rejected)
- **Tests for agents folder** conditional creation

### Changed

#### Configuration Validation
- **Improved option combination validation** in `ProjectConfig`:
  - Admin panel requires PostgreSQL or SQLite (not MongoDB)
  - Caching requires Redis to be enabled
  - Session management requires a database
  - Conversation persistence requires a database
  - Rate limiting with Redis storage requires Redis enabled
  - OpenRouter is only available with PydanticAI (not LangChain)

#### Database Support
- **Admin panel prompt** now appears for both PostgreSQL and SQLite (previously only PostgreSQL)
- **Database-specific post-generation messages**:
  - PostgreSQL: `make docker-db` + migration commands
  - SQLite: Auto-creation note + migration commands (no Docker)
  - MongoDB: `make docker-mongo` (no migrations)
- **Added `close_db()` function** for SQLite database consistency

#### Project Name Handling
- **Unified project name validation** between `prompts.py` and `config.py`
- Extracted validation into `_validate_project_name()` function with clear error messages
- Shows converted project name to user when it differs from input

### Fixed

#### Backend Fixes
- **Conversation list API response format**: Changed `/conversations` and `/conversations/{id}/messages` endpoints to return paginated response `{ items: [...], total: N }` instead of raw array, fixing frontend conversation list not loading after page refresh
- **Database session handling**: Split `get_db_session` into async generator for FastAPI `Depends()` and `@asynccontextmanager` for manual use (WebSocket handlers)
- **WebSocket authentication**:
  - Update `deps.py` to use `get_db_context` for WebSocket auth
  - Add cookie-based authentication support for WebSocket (`access_token` cookie)
  - Now accepts token via query parameter OR cookie for flexibility
- **WebSocket exception handling**: Fix `AttributeError` when exception occurs on WebSocket connection (`request.method` doesn't exist for WebSocket)
- **WebSocket conversation persistence**:
  - Fix `get_db_session` vs `get_db_context` usage (async generator vs async context manager)
  - Fix event name mismatch: backend now sends `conversation_created` to match frontend expectation
- **Docker Compose**: Fix `env_file` path from `.env` to `./backend/.env`
- **ValidationInfo typing**: Add proper type hints to all field validators in `config.py`

#### Frontend Fixes
- **ThemeToggle hydration mismatch**: Add mounted state to prevent SSR/client mismatch
- **Button component**: Extract `asChild` prop to prevent DOM warning
- **ConversationList**: Add default value for conversations to prevent undefined error
- **New Chat button**:
  - Create conversation in database immediately (eager creation)
  - Clear messages properly when switching conversations
  - Fix message appending issue when switching between conversations
- **Conversation store**: Add defensive checks for undefined state

#### CLI Fixes
- **Consistent package name**: Changed from `fastapi-gen` to `fastapi-fullstack` in version option
- **Makefile**: Always generated now (removed from optional dev tools)

#### Template/Generator Fixes
- **Ruff dependency in hooks**: Graceful handling when ruff is not installed:
  - Check PATH for ruff binary
  - Fall back to `uvx ruff` if uv is available
  - Fall back to `python -m ruff` if available as module
  - Show friendly warning if ruff is not available
- **Dynamic generator version**: Replaced hardcoded version with `DYNAMIC` placeholder
- **Unused files cleanup**: Improved post-generation hook to remove:
  - AI agent files based on framework selection
  - Example CRUD files when disabled
  - Conversation, webhook, session files when features disabled
  - Worker directory when no background tasks selected
  - Empty directories automatically
- **`.env` file location**: Move `.env.example` from root to `backend/`

### Tests Added

- Tests for all configuration validation combinations
- Tests for project name validation edge cases
- Tests for `new` command `--output` option
- Tests for OpenRouter + LangChain validation
- Tests for admin panel prompt with SQLite
- Tests for agents folder conditional creation
- Tests for email validation (config and prompts)
- Tests for rate limit configuration prompts
