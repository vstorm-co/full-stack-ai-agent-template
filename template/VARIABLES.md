# Cookiecutter Template Variables

This document describes all variables available in `cookiecutter.json` for the fastapi-fullstack template.

## Table of Contents

- [Metadata](#metadata)
- [Project Information](#project-information)
- [Database Settings](#database-settings)
- [Authentication](#authentication)
- [OAuth](#oauth)
- [Observability (Logfire)](#observability-logfire)
- [Background Tasks](#background-tasks)
- [Redis & Caching](#redis--caching)
- [Rate Limiting](#rate-limiting)
- [Features](#features)
- [RAG (Retrieval-Augmented Generation)](#rag-retrieval-augmented-generation)
- [AI Agent](#ai-agent)
- [WebSocket](#websocket)
- [Development Tools](#development-tools)
- [Deployment](#deployment)
- [Frontend](#frontend)
- [Email](#email)
- [Teams & Billing](#teams--billing)
- [Embed & White-label](#embed--white-label)

---

## Metadata

These variables are set automatically by the generator.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `generator_name` | string | `"fastapi-fullstack"` | Name of the generator tool |
| `generator_version` | string | `"DYNAMIC"` | Version of the generator (set at runtime) |
| `generated_at` | string | `""` | Timestamp when project was generated |

---

## Project Information

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `project_name` | string | `"my_project"` | Name of the project. Must match pattern `^[a-z][a-z0-9_]*$` |
| `project_slug` | computed | - | URL-safe version derived from `project_name` |
| `project_description` | string | `"A FastAPI project"` | Short description of the project |
| `author_name` | string | `"Your Name"` | Author's full name |
| `author_email` | string | `"your@email.com"` | Author's email address (validated format) |
| `timezone` | string | `"UTC"` | Project timezone in IANA format (e.g. `UTC`, `Europe/Warsaw`) |

---

## Database Settings

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `database` | enum | `"postgresql"` | Database type. Values: `postgresql`, `mongodb`, `sqlite`, `none` | - |
| `use_postgresql` | bool | `true` | PostgreSQL is selected | Computed from `database` |
| `use_mongodb` | bool | `false` | MongoDB is selected | Computed from `database` |
| `use_sqlite` | bool | `false` | SQLite is selected | Computed from `database` |
| `use_database` | bool | `true` | Any database is enabled | Computed from `database` |
| `db_pool_size` | int | `5` | Database connection pool size | Requires SQL database |
| `db_max_overflow` | int | `10` | Max overflow connections above pool size | Requires SQL database |
| `db_pool_timeout` | int | `30` | Timeout (seconds) waiting for connection | Requires SQL database |

### ORM Library

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `orm_type` | enum | `"sqlalchemy"` | ORM library. Values: `sqlalchemy`, `sqlmodel` | Requires SQL database |
| `use_sqlalchemy` | bool | `true` | SQLAlchemy is selected | Computed from `orm_type` |
| `use_sqlmodel` | bool | `false` | SQLModel is selected | Computed from `orm_type` |

**Notes:**

- SQLModel provides simplified syntax combining SQLAlchemy and Pydantic
- SQLModel is only available for PostgreSQL and SQLite (not MongoDB)
- SQLModel uses the same database session and migrations as SQLAlchemy

**Notes:**

- PostgreSQL uses `asyncpg` for async operations
- MongoDB uses `motor` for async operations
- SQLite is synchronous and not recommended for production

---

## Authentication

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `auth` | string | `"both"` | Authentication mode (always "both" = JWT + API Key) | Always "both" |
| `use_jwt` | bool | `true` | JWT authentication is enabled | Always true |
| `use_api_key` | bool | `true` | API Key authentication is enabled | Always true |
| `use_auth` | bool | `true` | Authentication is enabled | Always true |
| `auth_mode` | string | `"local"` | Auth architecture: `local` (app manages passwords/JWTs) or `delegated` (external IdP like Auth0, Clerk, Cognito, Keycloak) | - |
| `use_local_auth` | bool | `true` | Local auth is active (app issues its own JWTs) | Computed from `auth_mode` |
| `use_delegated_auth` | bool | `false` | Delegated auth is active (external IdP issues tokens) | Computed from `auth_mode` |
| `use_shared_secret_jwt` | bool | `false` | IdP tokens validated with a shared HS256 secret | Computed from `auth_mode` + IdP config |
| `use_jwks_idp` | bool | `false` | IdP tokens validated via JWKS endpoint (RS256/ES256) | Computed from `auth_mode` + IdP config |
| `use_external_user_id_in_conversations` | bool | `false` | Store external IdP user ID on conversation records | Requires `use_delegated_auth` |
| `use_all_providers` | bool | `false` | Enable all LLM providers in generated config | Computed from LLM provider selection |

---

## OAuth

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `oauth_provider` | enum | `"none"` | OAuth provider. Values: `google`, `none` | - |
| `enable_oauth` | bool | `false` | OAuth is enabled | Computed from `oauth_provider` |
| `enable_oauth_google` | bool | `false` | Google OAuth is enabled | Computed from `oauth_provider` |
| `enable_session_management` | bool | `false` | Enable session management for OAuth | Requires OAuth |
| `allowed_email_domains` | string | `""` | Comma-separated list of allowed email domains for OAuth sign-in (e.g. `"example.com,corp.io"`). Empty = allow all | - |
| `enable_email_domain_allowlist` | bool | `false` | Enable email domain restriction for OAuth sign-in | Computed from `allowed_email_domains` |

---

## Observability (Logfire)

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `enable_logfire` | bool | `true` | Enable Logfire observability | - |
| `logfire_fastapi` | bool | `true` | Instrument FastAPI with Logfire | Requires `enable_logfire` |
| `logfire_database` | bool | `true` | Instrument database with Logfire | Requires `enable_logfire` and database |
| `logfire_redis` | bool | `false` | Instrument Redis with Logfire | Requires `enable_logfire` and Redis |
| `logfire_celery` | bool | `false` | Instrument Celery with Logfire | Requires `enable_logfire` and Celery |
| `logfire_httpx` | bool | `false` | Instrument HTTPX client with Logfire | Requires `enable_logfire` |

---

## Background Tasks

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `background_tasks` | enum | `"none"` | Background task system. Values: `celery`, `taskiq`, `arq`, `none` | - |
| `use_celery` | bool | `false` | Celery is selected | Computed from `background_tasks` |
| `use_taskiq` | bool | `false` | Taskiq is selected | Computed from `background_tasks` |
| `use_arq` | bool | `false` | ARQ is selected | Computed from `background_tasks` |

**Notes:**

- Celery requires Redis as broker
- Taskiq and ARQ also benefit from Redis

---

## Redis & Caching

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `enable_redis` | bool | `false` | Enable Redis integration | - |
| `enable_caching` | bool | `false` | Enable response caching | Requires Redis |

**Notes:**

- Redis is automatically enabled when using Celery, ARQ, or Redis-based rate limiting

---

## Rate Limiting

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `enable_rate_limiting` | bool | `false` | Enable API rate limiting | - |
| `rate_limit_requests` | int | `100` | Number of requests allowed | Requires `enable_rate_limiting` |
| `rate_limit_period` | int | `60` | Period in seconds for rate limit window | Requires `enable_rate_limiting` |
| `rate_limit_storage` | enum | `"memory"` | Rate limit storage backend. Values: `memory`, `redis` | Requires `enable_rate_limiting` |
| `rate_limit_storage_memory` | bool | `true` | Memory storage is selected | Computed from `rate_limit_storage` |
| `rate_limit_storage_redis` | bool | `false` | Redis storage is selected | Computed from `rate_limit_storage` |

**Notes:**

- Memory storage is not suitable for multi-process deployments
- Redis storage requires Redis to be enabled

---

## Features

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `enable_pagination` | bool | `true` | Enable pagination utilities | - |
| `enable_sentry` | bool | `false` | Enable Sentry error tracking | - |
| `enable_prometheus` | bool | `false` | Enable Prometheus metrics | - |
| `enable_admin_panel` | bool | `false` | Enable SQLAdmin panel | Requires SQL database |
| `admin_environments` | enum | `"dev_staging"` | Environments where admin is active. Values: `all`, `dev_only`, `dev_staging`, `disabled` | Requires `enable_admin_panel` |
| `admin_env_all` | bool | `false` | Admin enabled in all environments | Computed from `admin_environments` |
| `admin_env_dev_only` | bool | `false` | Admin enabled only in dev | Computed from `admin_environments` |
| `admin_env_dev_staging` | bool | `true` | Admin enabled in dev and staging | Computed from `admin_environments` |
| `admin_env_disabled` | bool | `false` | Admin is disabled | Computed from `admin_environments` |
| `admin_require_auth` | bool | `true` | Require authentication for admin panel | Requires `enable_admin_panel` |
| `enable_websockets` | bool | `false` | Enable WebSocket support | - |
| `enable_file_storage` | bool | `false` | Enable file upload/storage | - |
| `enable_cors` | bool | `true` | Enable CORS middleware | - |
| `enable_webhooks` | bool | `false` | Enable webhook support | - |
| `enable_conversation_persistence` | bool | `true` | Enable conversation persistence (derived from `use_ai`) | Computed from `use_ai` |
| `include_example_crud` | bool | `false` | Include example CRUD endpoints (always disabled) | Always false |
| `enable_i18n` | bool | `true` | Enable internationalization in frontend (always enabled) | Always true |
| `seed_admin_email` | string | `""` | Email of a user to auto-promote to app-admin on first startup (via `FIRST_ADMIN_EMAIL` env var) | - |
| `enable_seed_admin` | bool | `false` | Enable startup auto-promotion of `seed_admin_email` to app-admin | Computed from `seed_admin_email` |
| `embed_allowed_origins` | string | `""` | Comma-separated origins allowed to embed the app in an iframe (e.g. `"https://parent.com"`). Sets CSP `frame-ancestors` and CORS origins | - |
| `enable_embed_mode` | bool | `false` | Enable iframe embed mode: relaxes `frame-ancestors`, gates `/login` + `/register` pages | Computed from `embed_allowed_origins` |
| `enable_brand_from_config` | bool | `false` | Enable runtime brand color/logo override from `NEXT_PUBLIC_BRAND_COLOR` and `NEXT_PUBLIC_BRAND_LOGO_URL` env vars (white-label) | Requires frontend |

---

## RAG (Retrieval-Augmented Generation)

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `enable_rag` | bool | `false` | Enable RAG functionality with vector database | - |
| `vector_store` | enum | `"milvus"` | Vector store backend. Values: `milvus`, `qdrant`, `chromadb`, `pgvector` | Requires `enable_rag` |
| `use_milvus` | bool | `false` | Milvus vector database is selected | Computed from `vector_store` |
| `use_qdrant` | bool | `false` | Qdrant vector database is selected | Computed from `vector_store` |
| `use_chromadb` | bool | `false` | ChromaDB vector database is selected (embedded mode) | Computed from `vector_store` |
| `use_pgvector` | bool | `false` | pgvector (PostgreSQL extension) is selected | Computed from `vector_store`, requires PostgreSQL |
| `embedding_provider` | enum | auto-derived | Embedding model provider. Auto-derived from LLM provider: OpenAI→openai, Anthropic→voyage, OpenRouter→sentence_transformers | Auto-derived from `llm_provider` |
| `use_openai_embeddings` | bool | `false` | OpenAI embeddings are selected | Computed from `llm_provider` |
| `use_voyage_embeddings` | bool | `false` | Voyage AI embeddings are selected | Computed from `llm_provider` |
| `use_gemini_embeddings` | bool | `false` | Google Gemini multimodal embeddings are selected | Computed from `llm_provider` |
| `use_sentence_transformers` | bool | `true` | Local Sentence Transformers are selected | Computed from `llm_provider` |
| `enable_reranker` | bool | `false` | Enable reranker for search results (set via `--reranker` CLI flag) | Computed from `--reranker` CLI flag |
| `use_cohere_reranker` | bool | `false` | Cohere reranker is selected | Computed from `--reranker` CLI flag |
| `use_cross_encoder_reranker` | bool | `false` | Cross-encoder reranker (sentence-transformers) is selected | Computed from `--reranker` CLI flag |
| `pdf_parser` | enum | `"pymupdf"` | PDF parsing method. Values: `pymupdf`, `liteparse`, `llamaparse`, `all` | Requires RAG |
| `use_pymupdf` | bool | `false` | PyMuPDF (local) is selected for PDF parsing | Computed from `pdf_parser` |
| `use_llamaparse` | bool | `false` | LlamaParse (cloud AI) is selected for PDF parsing | Computed from `pdf_parser` |
| `use_liteparse` | bool | `false` | LiteParse (local AI-native) is selected for PDF parsing | Computed from `pdf_parser` |
| `use_all_pdf_parsers` | bool | `false` | All PDF parsers installed, runtime selection via PDF_PARSER env var | Computed from `pdf_parser` |
| `use_python_parser` | bool | `true` | Python-based parsing is selected (always true for non-PDF) | Always true |
| `enable_google_drive_ingestion` | bool | `false` | Enable Google Drive as document source | Requires RAG |
| `enable_s3_ingestion` | bool | `false` | Enable S3/MinIO as document source | Requires RAG |
| `enable_rag_image_description` | bool | `false` | Extract images from documents and describe via LLM vision API | Requires RAG |

**Notes:**

- RAG requires a vector database (Milvus, Qdrant, ChromaDB, or pgvector)
- Embedding provider is auto-derived from LLM provider (OpenAI→openai, Anthropic→voyage, Google→gemini, OpenRouter→sentence_transformers)
- Reranker is enabled via `--reranker` CLI flag (cohere, cross_encoder)
- Cohere and Cross-Encoder rerankers improve search result relevance
- LlamaParse requires an API key; PyMuPDF is free and local (with tables, OCR fallback)
- Google Drive ingestion enables direct document loading from Google Workspace

---

## Messaging Channels

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `use_telegram` | bool | `false` | Enable Telegram bot integration (multi-bot, polling + webhook, role-based access) | Requires JWT auth |
| `use_slack` | bool | `false` | Enable Slack bot integration (Events API, threads, @mention support) | Requires JWT auth |

**Notes:**

- Telegram bots can run in polling mode (default, no public URL needed) or webhook mode (requires HTTPS)
- Multiple bots are supported — each bot can have its own access policy, model override, and system prompt
- Account linking uses a 6-digit OTP code (users type `/link` in the bot chat)
- Bot tokens are encrypted at rest using Fernet (AES-128-CBC) from `CHANNEL_ENCRYPTION_KEY`
- Rate limiting: 10 requests/min per user per bot (configurable per bot via access policy)

---

## AI Agent

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `ai_framework` | enum | `"pydantic_ai"` | AI framework. Values: `pydantic_ai`, `langchain`, `langgraph`, `crewai`, `deepagents`, `pydantic_deep`, `none` | - |
| `use_ai` | bool | `true` | Any AI framework is selected (false when `ai_framework=none`) | Computed from `ai_framework` |
| `use_pydantic_ai` | bool | `true` | PydanticAI is selected | Computed from `ai_framework` |
| `use_langchain` | bool | `false` | LangChain is selected | Computed from `ai_framework` |
| `use_langgraph` | bool | `false` | LangGraph (ReAct agent) is selected | Computed from `ai_framework` |
| `use_crewai` | bool | `false` | CrewAI (multi-agent crews) is selected | Computed from `ai_framework` |
| `use_deepagents` | bool | `false` | DeepAgents (agentic coding, LangChain) is selected | Computed from `ai_framework` |
| `use_pydantic_deep` | bool | `false` | PydanticDeep (deep agentic coding, Docker sandbox) is selected | Computed from `ai_framework` |
| `sandbox_backend` | enum | `"state"` | Agent sandbox environment for DeepAgents/PydanticDeep. Values: `state`, `daytona` | Only used when `use_deepagents` or `use_pydantic_deep` is true |
| `llm_provider` | enum | `"openai"` | LLM provider. Values: `openai`, `anthropic`, `google`, `openrouter` | - |
| `use_openai` | bool | `true` | OpenAI is selected | Computed from `llm_provider` |
| `use_anthropic` | bool | `false` | Anthropic is selected | Computed from `llm_provider` |
| `use_google` | bool | `false` | Google Gemini is selected | Computed from `llm_provider` |
| `use_openrouter` | bool | `false` | OpenRouter is selected | Computed from `llm_provider` |
| `enable_langsmith` | bool | `false` | Enable LangSmith observability (tracing, prompt management) | Requires LangChain, LangGraph, or DeepAgents |
| `enable_web_search` | bool | `false` | Web search. PydanticAI/PydanticDeep use the model-native WebSearch capability; LangChain/LangGraph/CrewAI/DeepAgents use a Tavily-backed tool (needs `TAVILY_API_KEY`) | Requires an AI framework |
| `enable_web_fetch` | bool | `false` | Web fetch. PydanticAI/PydanticDeep use the model-native WebFetch capability; LangChain/LangGraph/CrewAI/DeepAgents use the portable `fetch_url` tool | Requires an AI framework |
| `web_fetch_tool` | bool | `false` | Computed: portable `fetch_url` tool is generated | `enable_web_fetch` and framework is LangChain/LangGraph/CrewAI/DeepAgents |
| `enable_charts` | bool | `false` | Enable the chart-generation tool (line/bar/pie/area/scatter); interactive in web chat, PNG on Slack/Telegram | Requires an AI framework |
| `charts_channel_png` | bool | `false` | Computed: render charts to PNG for messaging channels | `enable_charts` and (`use_slack` or `use_telegram`) |
| `enable_antv_charts` | bool | `false` | Adds the interactive `create_map` tool (Leaflet/OpenStreetMap, works out of the box) plus AntV advanced-diagram tools (flowchart, mind-map, org-chart, sankey, ...) via an `mcp-server-chart` Docker sidecar. Wired into all 5 frameworks. The AntV diagrams need the sidecar running (`docker compose --profile antv up -d`) and `ENABLE_ANTV_CHARTS=true` at runtime; maps work without it. Present in the production compose but profile-gated — off by default and publishes no host port, so it's opt-in per environment; for prod, self-host GPT-Vis-SSR via `ANTV_VIS_REQUEST_SERVER` rather than AntV's public render backend | Requires an AI framework |
| `enable_code_execution` | bool | `false` | Adds a `run_python` tool backed by the Monty sandboxed Python interpreter (`pydantic-monty`). The model can compute projections, run aggregations, and call `create_chart`/`create_map` from inside the sandbox — charts render as interactive Recharts cards immediately. Sandbox allows `math`, `asyncio`, `json`, `datetime`, `re`; no `statistics`, `random`, `itertools`, numpy/pandas. Activated at runtime with `ENABLE_CODE_EXECUTION=true`. **PydanticAI only.** Temporary shim — swap to the official `CodeExecutionToolset` when it ships in pydantic-ai | Requires `use_pydantic_ai` |
| `enable_skills` | bool | `false` | Adds a `pydantic-ai-skills` `SkillsToolset` that loads `SKILL.md` files from `backend/skills/` as agent tools (the model picks a skill, then follows its instructions). Ships the loader only — drop your own skills into `backend/skills/`; the toolset no-ops when the directory is empty. Pairs well with `enable_code_execution` for skills that compute. **PydanticAI only.** | Requires `use_pydantic_ai` |
| `enable_deep_research` | bool | `false` | Turns the assistant into a deep research agent: a TODO planner (`pydantic-ai-todo`), researcher/analyst/writer subagents (`subagents-pydantic-ai`), and an automatic context manager (`summarization-pydantic-ai`). The planner delegates web work to subagents and streams a live research panel (plan checklist, subagent status, context-usage meter). TODO state persists in PostgreSQL when available, else in memory. Activated at runtime with `ENABLE_DEEP_RESEARCH=true`; the client can opt a single turn out with `deep_research=false`. **PydanticAI only.** | Requires `use_pydantic_ai` |

**Notes:**

- PydanticAI uses `iter()` for full event streaming over WebSocket
- LangGraph implements a ReAct (Reasoning + Acting) agent pattern with graph-based architecture
- CrewAI enables multi-agent teams that collaborate on complex tasks
- DeepAgents provides an agentic coding assistant with built-in filesystem tools (ls, read_file, write_file, edit_file, glob, grep) and task management
- OpenRouter with LangChain, LangGraph, CrewAI, or DeepAgents is not supported

---

## WebSocket

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `websocket_auth` | enum | `"jwt"` | WebSocket authentication | Always `jwt` |
| `websocket_auth_jwt` | bool | `true` | JWT auth for WebSocket | Always true |
| `websocket_auth_api_key` | bool | `false` | API Key auth for WebSocket | Always false |
| `websocket_auth_none` | bool | `false` | No auth for WebSocket | Always false |

---

## Development Tools

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_pytest` | bool | `true` | Include pytest configuration and fixtures |
| `enable_precommit` | bool | `true` | Include pre-commit hooks configuration |
| `enable_makefile` | bool | `true` | Include Makefile with common commands |
| `enable_docker` | bool | `true` | Include Dockerfile and docker-compose |
| `generate_env` | bool | `true` | Generate `.env.example` file |
| `python_version` | string | `"3.12"` | Python version for the project |

---

## Deployment

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `ci_type` | enum | `"github"` | CI/CD system. Values: `github`, `gitlab`, `none` | - |
| `use_github_actions` | bool | `true` | GitHub Actions is selected | Computed from `ci_type` |
| `use_gitlab_ci` | bool | `false` | GitLab CI is selected | Computed from `ci_type` |
| `enable_kubernetes` | bool | `false` | Include Kubernetes manifests | - |
| `reverse_proxy` | enum | `"traefik_included"` | Reverse proxy config. Values: `traefik_included`, `traefik_external`, `nginx_included`, `nginx_external`, `none` | Requires Docker |
| `include_traefik_service` | bool | `true` | Include Traefik container in docker-compose | Computed from `reverse_proxy` |
| `include_traefik_labels` | bool | `true` | Include Traefik labels on services | Computed from `reverse_proxy` |
| `use_traefik` | bool | `true` | Using Traefik (included or external) | Computed from `reverse_proxy` |
| `include_nginx_service` | bool | `false` | Include Nginx container in docker-compose | Computed from `reverse_proxy` |
| `include_nginx_config` | bool | `false` | Generate nginx configuration files | Computed from `reverse_proxy` |
| `use_nginx` | bool | `false` | Using Nginx (included or external) | Computed from `reverse_proxy` |

**Reverse Proxy Options:**

- `traefik_included`: Full Traefik setup included in docker-compose.prod.yml (default)
- `traefik_external`: Services have Traefik labels but no Traefik container (for shared Traefik)
- `nginx_included`: Full Nginx setup included in docker-compose.prod.yml with config template
- `nginx_external`: Nginx config template only, for external Nginx (no container in compose)
- `none`: No reverse proxy, ports exposed directly (use your own proxy)

---

## Frontend

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `frontend` | enum | `"none"` | Frontend framework. Values: `nextjs`, `none` | - |
| `use_frontend` | bool | `false` | Any frontend is enabled | Computed from `frontend` |
| `use_nextjs` | bool | `false` | Next.js is selected | Computed from `frontend` |
| `frontend_port` | int | `3000` | Port for frontend development server | Requires frontend |
| `brand_color` | string | `"blue"` | Brand color preset (blue, green, red, violet, orange) | Requires frontend |
| `brand_color_hue` | string | `"250"` | oklch hue value for the brand color | Computed from `brand_color` |
| `backend_port` | int | `8000` | Port for backend server | - |
| `enable_marketing_site` | bool | `false` | Include public marketing pages (landing, pricing, testimonials, changelog) in the Next.js frontend | Requires frontend |
| `enable_changelog` | bool | `false` | Include a public `/changelog` page listing product updates | Requires `enable_marketing_site` |
| `enable_comparison_pages` | bool | `false` | Include competitor comparison landing pages (`/vs/competitor-name`) | Requires `enable_marketing_site` |
| `enable_testimonials` | bool | `false` | Include testimonial/social-proof sections on marketing pages | Requires `enable_marketing_site` |
| `enable_status_badge` | bool | `false` | Include a live status badge on the frontend that links to a status page | Requires frontend |
| `enable_affiliate_program` | bool | `false` | Include affiliate/referral tracking pages and hooks | Requires frontend |
| `enable_admin_features_users` | bool | `false` | Include admin user management UI (`/admin/users`) | Requires frontend + JWT |
| `enable_admin_features_organizations` | bool | `false` | Include admin organization browser UI (`/admin/organizations`) | Requires frontend + `enable_teams` |
| `enable_admin_features_subscriptions` | bool | `false` | Include admin subscription management UI (`/admin/subscriptions`) | Requires frontend + `enable_billing` |
| `enable_admin_features_stripe_events` | bool | `false` | Include admin Stripe event log UI (`/admin/stripe-events`) | Requires frontend + `enable_billing` |
| `enable_admin_features_usage` | bool | `false` | Include admin usage & credits dashboard UI (`/admin/usage`) | Requires frontend + `enable_credits_system` |
| `enable_admin_features_audit_log` | bool | `false` | Include admin audit log UI (`/admin/audit-log`) | Requires frontend |
| `enable_admin_features_system_health` | bool | `false` | Include admin system health / status dashboard UI (`/admin/health`) | Requires frontend |
| `enable_storybook` | bool | `false` | Include Storybook component playground (`frontend/.storybook/`) | Requires frontend |

---

## Teams & Billing

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `enable_teams` | bool | `false` | Enable multi-tenant teams: Organizations, OrganizationMembers, Invitations, role-based access (OWNER/ADMIN/MEMBER/VIEWER), Personal Org auto-create on signup | Requires JWT auth + SQL DB |
| `tenancy` | enum | `"single"` | Tenancy mode. Values: `single` (one workspace), `multi_org` (per-org isolation), `platform` (platform-level multi-tenancy with cross-org admin) | Requires `enable_teams` for non-single |
| `tenancy_single` | bool | `true` | Single-tenant mode | Computed from `tenancy` |
| `tenancy_multi_org` | bool | `false` | Multi-org tenancy mode | Computed from `tenancy` |
| `tenancy_platform` | bool | `false` | Platform tenancy mode | Computed from `tenancy` |
| `enable_per_org_quotas` | bool | `false` | Enable per-organization resource quotas (API calls, storage, seats) | Requires `enable_teams` |
| `enable_billing` | bool | `false` | Enable Stripe billing: Plans, Prices, Subscriptions, checkout flow, customer portal, webhook handler | Requires `enable_teams` |
| `payment_provider` | enum | `"stripe"` | Payment provider. Values: `stripe`, `paddle`, `lemonsqueezy`, `polar` | Requires `enable_billing` |
| `payment_provider_stripe` | bool | `true` | Stripe is selected (fully implemented) | Computed from `payment_provider` |
| `payment_provider_paddle` | bool | `false` | Paddle is selected (flag only) | Computed from `payment_provider` |
| `payment_provider_lemonsqueezy` | bool | `false` | LemonSqueezy is selected (flag only) | Computed from `payment_provider` |
| `payment_provider_polar` | bool | `false` | Polar is selected (flag only) | Computed from `payment_provider` |
| `billing_model` | enum | `"subscription"` | Billing model. Values: `subscription`, `usage`, `hybrid`, `one_time` | Requires `enable_billing` |
| `billing_model_subscription` | bool | `true` | Subscription billing (fully implemented) | Computed from `billing_model` |
| `billing_model_usage` | bool | `false` | Usage-based billing (flag only) | Computed from `billing_model` |
| `billing_model_hybrid` | bool | `false` | Hybrid billing (flag only) | Computed from `billing_model` |
| `billing_model_one_time` | bool | `false` | One-time payment billing (flag only) | Computed from `billing_model` |
| `enable_credits_system` | bool | `false` | Enable credit-based usage metering: credit balance per org, usage events, subscription grants, top-up purchases | Requires `enable_billing` |
| `enable_usage_anomaly_detection` | bool | `false` | Enable hourly usage spike detection (alerts when current-hour credits exceed 3× rolling 24h average) | Requires `enable_credits_system` |
| `enable_usage_dashboard` | bool | `false` | Enable admin usage dashboard routes (`/admin/usage/*`) | Requires `enable_credits_system` |
| `enable_slack_alerts` | bool | `false` | Send anomaly-detection alerts to a Slack webhook URL (`SLACK_ANOMALY_WEBHOOK_URL`) | Requires `enable_usage_anomaly_detection` |
| `billing_default_currency` | string | `"usd"` | Default Stripe currency (ISO 4217 lowercase, e.g. `usd`, `eur`) | Requires `enable_billing` |
| `billing_trial_days_default` | int | `14` | Default number of trial days for new subscriptions | Requires `enable_billing` |
| `billing_trial_requires_card` | bool | `false` | Whether a payment method is required to start a trial | Requires `enable_billing` |
| `billing_credits_per_usd` | int | `100` | Credit units per 1 USD for top-up purchases | Requires `enable_credits_system` |
| `billing_credits_free_tier_grant` | int | `500` | One-time credit grant on signup (free tier) | Requires `enable_credits_system` |
| `billing_credits_low_threshold` | int | `50` | Credit balance threshold below which a low-credits email is sent | Requires `enable_credits_system` |

**Notes:**

- When `enable_teams=true`, every new user gets a Personal Organization (is_personal=True) automatically on registration
- All resources (Conversations, RAGDocuments, etc.) are scoped to an Organization via `organization_id`
- Active organization context is passed via `X-Organization-Id` header (falls back to Personal Org if omitted)
- Roles hierarchy: OWNER > ADMIN > MEMBER > VIEWER. VIEWERs are non-billable read-only collaborators
- Personal Org is hard-capped at 1 member (the owner) and cannot be deleted

---

## Email

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `enable_email` | bool | `false` | Enable transactional email sending (welcome, invitation, password reset, billing notifications) | - |
| `email_provider` | enum | `"log"` | Email provider. Values: `resend`, `smtp`, `log` (`log` prints emails to console — useful for development) | Requires `enable_email` |
| `enable_newsletter_signup` | bool | `false` | Enable public `POST /newsletter/signup` endpoint that sends a welcome email to new subscribers | Requires `enable_email` |
| `newsletter_provider` | enum | `"resend"` | Newsletter / mailing list provider. Values: `resend`, `mailchimp`, `convertkit` | Requires `enable_newsletter_signup` |
| `newsletter_provider_resend` | bool | `true` | Resend is selected for newsletters | Computed from `newsletter_provider` |
| `newsletter_provider_mailchimp` | bool | `false` | Mailchimp is selected (flag only) | Computed from `newsletter_provider` |
| `newsletter_provider_convertkit` | bool | `false` | ConvertKit/Kit is selected (flag only) | Computed from `newsletter_provider` |

---

## Variable Naming Conventions

The template uses consistent naming patterns:

| Pattern | Meaning | Example |
|---------|---------|---------|
| `use_X` | Boolean flag, X is selected | `use_jwt`, `use_postgresql` |
| `enable_X` | Boolean flag, feature is enabled | `enable_redis`, `enable_cors` |
| `X_Y` | Grouped settings | `db_pool_size`, `rate_limit_requests` |
| `logfire_X` | Logfire instrumentation for X | `logfire_fastapi`, `logfire_database` |

## Computed Variables

Many `use_*` and `enable_*` variables are computed from their parent enum variable:

```bash
database = "postgresql"
  → use_postgresql = true
  → use_mongodb = false
  → use_sqlite = false
  → use_database = true

orm_type = "sqlmodel"
  → use_sqlalchemy = false
  → use_sqlmodel = true
```

These computed variables are used in Jinja2 conditionals within templates:

```jinja2
{% if cookiecutter.use_postgresql %}
# PostgreSQL-specific code
{% endif %}
```
