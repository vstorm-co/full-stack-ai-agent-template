# Configuration Reference

All configuration is managed via environment variables, loaded from
`backend/.env` using [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

Settings are defined in `app/core/config.py` and accessed via the global
`settings` object:

```python
from app.core.config import settings

print(settings.AI_MODEL)
print(settings.DEBUG)
```

## Getting Started

```bash
cd backend

# Copy the example file (may already exist if generated with --generate-env)
cp .env.example .env

# Generate a secure secret key
openssl rand -hex 32
# Paste the output as SECRET_KEY in .env
```

## Project Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_NAME` | `{{ cookiecutter.project_name }}` | Display name for the project |
| `API_V1_STR` | `/api/v1` | API version prefix |
| `DEBUG` | `false` | Enable debug mode (verbose errors, auto-reload) |
| `ENVIRONMENT` | `local` | One of: `development`, `local`, `staging`, `production` |
| `TIMEZONE` | `{{ cookiecutter.timezone }}` | IANA timezone (e.g. `UTC`, `Europe/Warsaw`, `America/New_York`) |
| `MODELS_CACHE_DIR` | `./models_cache` | Directory for cached ML models |
| `MEDIA_DIR` | `./media` | Directory for uploaded files |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum file upload size in megabytes |

{%- if cookiecutter.use_jwt %}

## Authentication

### JWT

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (insecure default) | JWT signing key. **Must** be changed in production. Generate with: `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | `10080` | Refresh token lifetime (7 days) |
| `ALGORITHM` | `HS256` | JWT signing algorithm |

Production validation: `SECRET_KEY` must be at least 32 characters and cannot
use the default value in `ENVIRONMENT=production`.
{%- endif %}

{%- if cookiecutter.use_api_key %}

### API Key

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `change-me-in-production` | Shared API key for programmatic access |
| `API_KEY_HEADER` | `X-API-Key` | HTTP header name for API key |

Production validation: `API_KEY` cannot use the default value in
`ENVIRONMENT=production`.
{%- endif %}

{%- if cookiecutter.enable_oauth_google %}

### OAuth2 (Google)

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLIENT_ID` | (empty) | Google OAuth2 client ID |
| `GOOGLE_CLIENT_SECRET` | (empty) | Google OAuth2 client secret |
| `GOOGLE_REDIRECT_URI` | `http://localhost:{{ cookiecutter.backend_port }}/api/v1/oauth/google/callback` | OAuth2 callback URL |
| `FRONTEND_URL` | `http://localhost:{{ cookiecutter.frontend_port }}` | Frontend URL for OAuth2 redirects |
{%- endif %}


## Database (PostgreSQL)

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | `postgres` | PostgreSQL user |
| `POSTGRES_PASSWORD` | (empty) | PostgreSQL password |
| `POSTGRES_DB` | `{{ cookiecutter.project_slug }}` | Database name |
| `DB_POOL_SIZE` | `{{ cookiecutter.db_pool_size }}` | Connection pool size |
| `DB_MAX_OVERFLOW` | `{{ cookiecutter.db_max_overflow }}` | Max overflow connections |
| `DB_POOL_TIMEOUT` | `{{ cookiecutter.db_pool_timeout }}` | Pool timeout in seconds |

Computed properties:
- `DATABASE_URL` -- async connection string (`postgresql+asyncpg://...`)
- `DATABASE_URL_SYNC` -- sync connection string for Alembic



{%- if cookiecutter.enable_redis %}

## Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | (none) | Redis password (optional) |
| `REDIS_DB` | `0` | Redis database number |
{%- endif %}

## AI Agent

| Variable | Default | Description |
|----------|---------|-------------|
{%- if cookiecutter.use_openai %}
| `OPENAI_API_KEY` | (empty) | OpenAI API key |
| `AI_MODEL` | `gpt-5.5` | Default LLM model for chat |
{%- endif %}
{%- if cookiecutter.use_anthropic %}
| `ANTHROPIC_API_KEY` | (empty) | Anthropic API key |
| `AI_MODEL` | `claude-opus-4-7` | Default LLM model for chat |
{%- endif %}
{%- if cookiecutter.use_google %}
| `GOOGLE_API_KEY` | (empty) | Google AI API key |
| `AI_MODEL` | `gemini-2.5-flash` | Default LLM model for chat |
{%- endif %}
{%- if cookiecutter.use_openrouter %}
| `OPENROUTER_API_KEY` | (empty) | OpenRouter API key |
| `AI_MODEL` | `anthropic/claude-opus-4-7` | Default LLM model for chat |
{%- endif %}
| `AI_TEMPERATURE` | `0.7` | LLM temperature (0.0 = deterministic, 1.0 = creative) |
| `AI_AVAILABLE_MODELS` | (auto-configured) | JSON list of models shown in the UI model selector |
| `AI_FRAMEWORK` | `{{ cookiecutter.ai_framework }}` | AI framework (informational) |
| `LLM_PROVIDER` | `{{ cookiecutter.llm_provider }}` | LLM provider (informational) |

### Customizing Available Models

Override `AI_AVAILABLE_MODELS` in `.env` to customize the model selector:

```bash
AI_AVAILABLE_MODELS=["gpt-5.5","gpt-5.4","claude-opus-4-7"]
```

{%- if cookiecutter.enable_logfire %}

## Observability (Logfire)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOGFIRE_TOKEN` | (none) | Pydantic Logfire token. Get one at https://logfire.pydantic.dev |
| `LOGFIRE_SERVICE_NAME` | `{{ cookiecutter.project_slug }}` | Service name in Logfire dashboard |
| `LOGFIRE_ENVIRONMENT` | `development` | Environment tag |
{%- endif %}

{%- if cookiecutter.enable_langsmith %}

## Observability (LangSmith)

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGCHAIN_TRACING_V2` | `true` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | (none) | LangSmith API key. Get one at https://smith.langchain.com |
| `LANGCHAIN_PROJECT` | `{{ cookiecutter.project_slug }}` | Project name in LangSmith |
| `LANGCHAIN_ENDPOINT` | `https://api.smith.langchain.com` | LangSmith API endpoint |
{%- endif %}

{%- if cookiecutter.enable_web_search %}

## Web Search

| Variable | Default | Description |
|----------|---------|-------------|
| `TAVILY_API_KEY` | (empty) | Tavily API key for web search tool. Get one at https://tavily.com |
{%- endif %}

{%- if cookiecutter.use_deepagents %}

## DeepAgents

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPAGENTS_BACKEND_TYPE` | `state` | Backend: `state` (in-memory, ephemeral) |
| `DEEPAGENTS_MEMORY_PATHS` | (none) | Comma-separated AGENTS.md memory file paths loaded at agent startup |
| `DEEPAGENTS_SKILLS_PATHS` | (none) | Comma-separated paths to skill directories |
| `DEEPAGENTS_ENABLE_FILESYSTEM` | `true` | Enable filesystem tools (ls, read, write, edit, glob, grep) |
| `DEEPAGENTS_ENABLE_EXECUTE` | `false` | Enable shell execution (disabled by default for security) |
| `DEEPAGENTS_ENABLE_TODOS` | `true` | Enable write_todos tool |
| `DEEPAGENTS_ENABLE_SUBAGENTS` | `true` | Enable task tool for spawning subagents |
| `DEEPAGENTS_INTERRUPT_TOOLS` | (none) | Tools requiring human approval (comma-separated, or `"all"`) |
| `DEEPAGENTS_ALLOWED_DECISIONS` | `approve,edit,reject` | Allowed decisions for interrupted tools |
{%- endif %}

{%- if cookiecutter.enable_rag %}

## RAG (Retrieval Augmented Generation)

### Vector Database

{%- if cookiecutter.use_milvus %}

| Variable | Default | Description |
|----------|---------|-------------|
| `MILVUS_HOST` | `localhost` | Milvus host |
| `MILVUS_PORT` | `19530` | Milvus port |
| `MILVUS_DATABASE` | `default` | Milvus database name |
| `MILVUS_TOKEN` | `root:Milvus` | Milvus authentication token |
{%- endif %}

{%- if cookiecutter.use_qdrant %}

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `QDRANT_API_KEY` | (empty) | Qdrant API key (optional) |
{%- endif %}

{%- if cookiecutter.use_chromadb %}

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROMA_HOST` | (empty) | ChromaDB host. Leave empty for embedded/persistent mode. |
| `CHROMA_PORT` | `8100` | ChromaDB port (when using client-server mode) |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | Data directory for embedded mode |
{%- endif %}

{%- if cookiecutter.use_pgvector %}

pgvector uses the existing PostgreSQL connection. No additional configuration
is needed.
{%- endif %}

### Embeddings

| Variable | Default | Description |
|----------|---------|-------------|
{%- if cookiecutter.use_openai_embeddings %}
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
{%- elif cookiecutter.use_voyage_embeddings %}
| `EMBEDDING_MODEL` | `voyage-3` | Voyage AI embedding model |
| `VOYAGE_API_KEY` | (empty) | Voyage AI API key |
{%- elif cookiecutter.use_gemini_embeddings %}
| `EMBEDDING_MODEL` | `gemini-embedding-exp-03-07` | Google Gemini embedding model |
{%- elif cookiecutter.use_sentence_transformers %}
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence Transformers model (runs locally) |
{%- else %}
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
{%- endif %}

### Chunking & Retrieval

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_CHUNK_SIZE` | `512` | Maximum characters per chunk |
| `RAG_CHUNK_OVERLAP` | `50` | Characters of overlap between chunks |
| `RAG_CHUNKING_STRATEGY` | `recursive` | Chunking strategy: `recursive`, `markdown`, `fixed` |
| `RAG_DEFAULT_COLLECTION` | `documents` | Default collection for search (used by agent tool) |
| `RAG_TOP_K` | `10` | Default number of results to return |
| `RAG_HYBRID_SEARCH` | `false` | Enable BM25 + vector hybrid search |
| `RAG_ENABLE_OCR` | `false` | OCR fallback for scanned PDFs (requires `tesseract-ocr`) |

### Document Parsing

{%- if cookiecutter.use_all_pdf_parsers %}

| Variable | Default | Description |
|----------|---------|-------------|
| `PDF_PARSER` | `pymupdf` | PDF parser for RAG ingestion: `pymupdf`, `llamaparse`, `liteparse` |
| `CHAT_PDF_PARSER` | `pymupdf` | PDF parser for chat file uploads: `pymupdf`, `llamaparse`, `liteparse` |
| `LLAMAPARSE_API_KEY` | (empty) | LlamaParse API key (required for `llamaparse` parser) |
| `LLAMAPARSE_TIER` | `agentic` | LlamaParse tier: `fast`, `cost_effective`, `agentic`, `agentic_plus` |
{%- elif cookiecutter.use_llamaparse %}

| Variable | Default | Description |
|----------|---------|-------------|
| `LLAMAPARSE_API_KEY` | (empty) | LlamaParse API key |
| `LLAMAPARSE_TIER` | `agentic` | LlamaParse tier: `fast`, `cost_effective`, `agentic`, `agentic_plus` |
{%- endif %}

{%- if cookiecutter.enable_reranker %}

### Reranking

{%- if cookiecutter.use_cohere_reranker %}

| Variable | Default | Description |
|----------|---------|-------------|
| `COHERE_API_KEY` | (empty) | Cohere API key for reranking |
{%- endif %}

{%- if cookiecutter.use_cross_encoder_reranker %}

| Variable | Default | Description |
|----------|---------|-------------|
| `HF_TOKEN` | (empty) | HuggingFace token (for gated models) |
| `CROSS_ENCODER_MODEL` | `cross-encoder/ms-marco-MiniLM-L6-v2` | Cross-encoder model for reranking |
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_rag_image_description %}

### Image Description

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_IMAGE_DESCRIPTION_MODEL` | (empty, uses `AI_MODEL`) | LLM model for describing images found in documents |
{%- endif %}

{%- if cookiecutter.enable_google_drive_ingestion %}

### Google Drive Sync

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_DRIVE_CREDENTIALS_FILE` | `credentials/google-drive-sa.json` | Path to Google service account credentials |
{%- endif %}

{%- if cookiecutter.enable_s3_ingestion %}

### S3/MinIO Sync

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_RAG_ENDPOINT` | (none) | S3/MinIO endpoint URL |
| `S3_RAG_ACCESS_KEY` | (empty) | Access key |
| `S3_RAG_SECRET_KEY` | (empty) | Secret key |
| `S3_RAG_BUCKET` | `{{ cookiecutter.project_slug }}-rag` | Bucket name |
| `S3_RAG_REGION` | `us-east-1` | AWS region |
{%- endif %}
{%- endif %}

{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}

## Messaging Channels

| Variable | Default | Description |
|----------|---------|-------------|
| `CHANNEL_ENCRYPTION_KEY` | (empty) | Fernet key for encrypting bot tokens and sync-source connector credentials at rest. Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
{%- if cookiecutter.use_telegram %}
| `TELEGRAM_WEBHOOK_BASE_URL` | (empty) | Base URL for Telegram webhook (e.g. `https://yourdomain.com`). Required only in webhook mode |
{%- endif %}
{%- if cookiecutter.use_slack %}
| `SLACK_SIGNING_SECRET` | (empty) | Slack app signing secret for Events API signature verification |
| `SLACK_BOT_TOKEN` | (empty) | Slack bot OAuth token (`xoxb-...`) for sending messages via Web API |
| `SLACK_APP_TOKEN` | (empty) | Slack app-level token (`xapp-...`) for Socket Mode (development only) |
{%- endif %}

{%- endif %}

{%- if cookiecutter.use_celery %}

## Celery

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Celery result backend URL |
{%- endif %}

{%- if cookiecutter.use_taskiq %}

## Taskiq

| Variable | Default | Description |
|----------|---------|-------------|
| `TASKIQ_BROKER_URL` | `redis://localhost:6379/1` | Taskiq broker URL |
| `TASKIQ_RESULT_BACKEND` | `redis://localhost:6379/1` | Taskiq result backend URL |
{%- endif %}

{%- if cookiecutter.use_arq %}

## ARQ (Async Redis Queue)

| Variable | Default | Description |
|----------|---------|-------------|
| `ARQ_REDIS_HOST` | `localhost` | Redis host for ARQ |
| `ARQ_REDIS_PORT` | `6379` | Redis port for ARQ |
| `ARQ_REDIS_PASSWORD` | (none) | Redis password for ARQ |
| `ARQ_REDIS_DB` | `2` | Redis database number for ARQ |
{%- endif %}

{%- if cookiecutter.enable_cors %}

## CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:8080"]` | Allowed origins (JSON array) |
| `CORS_ALLOW_CREDENTIALS` | `true` | Allow credentials (cookies) |
| `CORS_ALLOW_METHODS` | `["*"]` | Allowed HTTP methods |
| `CORS_ALLOW_HEADERS` | `["*"]` | Allowed HTTP headers |

Production validation: `CORS_ORIGINS` cannot contain `"*"` in
`ENVIRONMENT=production`.
{%- endif %}

{%- if cookiecutter.enable_rate_limiting %}

## Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_REQUESTS` | `{{ cookiecutter.rate_limit_requests }}` | Maximum requests per period |
| `RATE_LIMIT_PERIOD` | `{{ cookiecutter.rate_limit_period }}` | Period in seconds |
{%- endif %}

{%- if cookiecutter.enable_sentry %}

## Sentry

| Variable | Default | Description |
|----------|---------|-------------|
| `SENTRY_DSN` | (none) | Sentry DSN for error tracking |
{%- endif %}

{%- if cookiecutter.enable_prometheus %}

## Prometheus

| Variable | Default | Description |
|----------|---------|-------------|
| `PROMETHEUS_METRICS_PATH` | `/metrics` | Metrics endpoint path |
| `PROMETHEUS_INCLUDE_IN_SCHEMA` | `false` | Include metrics endpoint in OpenAPI schema |
{%- endif %}

{%- if cookiecutter.enable_file_storage %}

## File Storage (S3/MinIO)

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_ENDPOINT` | (none) | S3/MinIO endpoint URL |
| `S3_ACCESS_KEY` | (empty) | Access key |
| `S3_SECRET_KEY` | (empty) | Secret key |
| `S3_BUCKET` | `{{ cookiecutter.project_slug }}` | Bucket name |
| `S3_REGION` | `us-east-1` | AWS region |
{%- endif %}

{%- if cookiecutter.enable_docker %}

## Docker / Production

| Variable | Default | Description |
|----------|---------|-------------|
| `DOMAIN` | `example.com` | Production domain (for Traefik) |
| `ACME_EMAIL` | `admin@example.com` | Let's Encrypt email for SSL certs |
{%- if cookiecutter.enable_redis %}
| `REDIS_PASSWORD` | `change-me-in-production` | Redis password for production |
{%- endif %}
{%- if cookiecutter.use_celery %}
| `FLOWER_USER` | `admin` | Flower monitoring UI username |
| `FLOWER_PASSWORD` | `change-me-in-production` | Flower monitoring UI password |
{%- endif %}
{%- endif %}

## Production Checklist

Before deploying to production, ensure these variables are properly set:

{%- if cookiecutter.use_jwt %}
1. `SECRET_KEY` -- Generate a unique 64-character hex key: `openssl rand -hex 32`
{%- endif %}
{%- if cookiecutter.use_api_key %}
2. `API_KEY` -- Generate a unique key: `openssl rand -hex 32`
{%- endif %}
3. `ENVIRONMENT` -- Set to `production`
4. `DEBUG` -- Set to `false`
5. `POSTGRES_PASSWORD` -- Use a strong, unique password
{%- if cookiecutter.enable_cors %}
6. `CORS_ORIGINS` -- List only your actual frontend domain(s)
{%- endif %}
{%- if cookiecutter.enable_redis %}
7. `REDIS_PASSWORD` -- Set a strong password
{%- endif %}
{%- if cookiecutter.use_openai %}
8. `OPENAI_API_KEY` -- Your production API key
{%- endif %}
{%- if cookiecutter.use_anthropic %}
8. `ANTHROPIC_API_KEY` -- Your production API key
{%- endif %}
{%- if cookiecutter.use_google %}
8. `GOOGLE_API_KEY` -- Your production API key
{%- endif %}
{%- if cookiecutter.use_openrouter %}
8. `OPENROUTER_API_KEY` -- Your production API key
{%- endif %}
