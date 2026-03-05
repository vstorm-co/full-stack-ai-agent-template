# Cookiecutter Template Variables

This document describes all variables available in `cookiecutter.json` for the fastapi-fullstack template.

## Table of Contents

- [Cookiecutter Template Variables](#cookiecutter-template-variables)
  - [Table of Contents](#table-of-contents)
  - [Metadata](#metadata)
  - [Project Information](#project-information)
  - [Database Settings](#database-settings)
    - [ORM Library](#orm-library)
  - [Authentication](#authentication)
  - [OAuth](#oauth)
  - [Observability (Logfire)](#observability-logfire)
  - [Background Tasks](#background-tasks)
  - [Redis \& Caching](#redis--caching)
  - [Rate Limiting](#rate-limiting)
  - [Features](#features)
  - [AI Agent](#ai-agent)
  - [WebSocket](#websocket)
  - [Development Tools](#development-tools)
  - [Deployment](#deployment)
  - [Frontend](#frontend)
  - [Variable Naming Conventions](#variable-naming-conventions)
  - [Computed Variables](#computed-variables)

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

---

## Database Settings

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `database` | enum | `"postgresql"` | Database type. Values: `postgresql`, `mongodb`, `sqlite`, `none` | - |
| `use_postgresql` | bool | `true` | PostgreSQL is selected | Computed from `database` |
| `use_mongodb` | bool | `false` | MongoDB is selected | Computed from `database` |
| `use_sqlite` | bool | `false` | SQLite is selected | Computed from `database` |
| `use_sqlserver` | bool | `false` | MS SQL Server | Computed from `database` |
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
| `auth` | enum | `"jwt"` | Authentication type. Values: `jwt`, `api_key`, `none` | - |
| `use_jwt` | bool | `true` | JWT authentication is selected | Computed from `auth` |
| `use_api_key` | bool | `false` | API Key authentication is selected | Computed from `auth` |
| `use_auth` | bool | `true` | Any authentication is enabled | Computed from `auth` |

---

## OAuth

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `oauth_provider` | enum | `"none"` | OAuth provider. Values: `google`, `none` | - |
| `enable_oauth` | bool | `false` | OAuth is enabled | Computed from `oauth_provider` |
| `enable_oauth_google` | bool | `false` | Google OAuth is enabled | Computed from `oauth_provider` |
| `enable_session_management` | bool | `false` | Enable session management for OAuth | Requires OAuth |

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
| `enable_orjson` | bool | `true` | Use orjson for faster JSON serialization | - |
| `enable_i18n` | bool | `false` | Enable internationalization | - |
| `include_example_crud` | bool | `true` | Include example CRUD endpoints | Requires database |
| `enable_webhooks` | bool | `false` | Enable webhook support | - |

---

## AI Agent

| Variable | Type | Default | Description | Dependencies |
|----------|------|---------|-------------|--------------|
| `enable_ai_agent` | bool | `false` | Enable AI agent functionality | - |
| `ai_framework` | enum | `"pydantic_ai"` | AI framework. Values: `pydantic_ai`, `langchain`, `langgraph`, `crewai`, `deepagents` | Requires `enable_ai_agent` |
| `use_pydantic_ai` | bool | `true` | PydanticAI is selected | Computed from `ai_framework` |
| `use_langchain` | bool | `false` | LangChain is selected | Computed from `ai_framework` |
| `use_langgraph` | bool | `false` | LangGraph (ReAct agent) is selected | Computed from `ai_framework` |
| `use_crewai` | bool | `false` | CrewAI (multi-agent crews) is selected | Computed from `ai_framework` |
| `use_deepagents` | bool | `false` | DeepAgents (agentic coding) is selected | Computed from `ai_framework` |
| `llm_provider` | enum | `"openai"` | LLM provider. Values: `openai`, `anthropic`, `openrouter` | Requires `enable_ai_agent` |
| `use_openai` | bool | `true` | OpenAI is selected | Computed from `llm_provider` |
| `use_anthropic` | bool | `false` | Anthropic is selected | Computed from `llm_provider` |
| `use_openrouter` | bool | `false` | OpenRouter is selected | Computed from `llm_provider` |
| `enable_conversation_persistence` | bool | `false` | Persist AI conversations to database | Requires `enable_ai_agent` and database |

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
| `websocket_auth` | enum | `"none"` | WebSocket authentication. Values: `jwt`, `api_key`, `none` | Requires `enable_websockets` |
| `websocket_auth_jwt` | bool | `false` | JWT auth for WebSocket | Computed from `websocket_auth` |
| `websocket_auth_api_key` | bool | `false` | API Key auth for WebSocket | Computed from `websocket_auth` |
| `websocket_auth_none` | bool | `true` | No auth for WebSocket | Computed from `websocket_auth` |

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
| `backend_port` | int | `8000` | Port for backend server | - |

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

```
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
