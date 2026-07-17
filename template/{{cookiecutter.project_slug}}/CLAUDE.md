# CLAUDE.md

## Project Overview

**{{ cookiecutter.project_name }}** - FastAPI application generated with [Full-Stack AI Agent Template](https://github.com/vstorm-co/full-stack-ai-agent-template).

**Stack:** FastAPI + Pydantic v2
{%- if True %}, PostgreSQL (async via asyncpg){%- endif %}
{%- if False %}, MongoDB (async via Motor){%- endif %}
{%- if False %}, SQLite (sync){%- endif %}
, JWT + API Key auth
{%- if cookiecutter.enable_redis %}, Redis{%- endif %}
{%- if cookiecutter.use_pydantic_ai %}, PydanticAI{%- endif %}
{%- if cookiecutter.use_langchain %}, LangChain{%- endif %}
{%- if cookiecutter.use_langgraph %}, LangGraph{%- endif %}{%- if cookiecutter.use_deepagents %}, DeepAgents{%- endif %}
{%- if cookiecutter.enable_rag %}, RAG ({{ cookiecutter.vector_store }}){%- endif %}
{%- if cookiecutter.use_celery %}, Celery{%- endif %}
{%- if cookiecutter.use_taskiq %}, Taskiq{%- endif %}
{%- if cookiecutter.use_frontend %}, Next.js 15 (i18n){%- endif %}

## Commands

```bash
# Backend
cd backend
uv run uvicorn app.main:app --reload --port {{ cookiecutter.backend_port }}
uv run pytest
uv run pytest tests/test_file.py::test_name -v
uv run ruff check . --fix && uv run ruff format .
uv run ty check

# Database migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "Description"
{%- if cookiecutter.use_frontend %}

# Frontend
cd frontend
bun dev
bun test
bun run lint
{%- endif %}
{%- if cookiecutter.enable_docker %}

# Docker
docker compose up -d
{%- endif %}
{%- if cookiecutter.enable_rag %}

# RAG
uv run {{ cookiecutter.project_slug }} rag-collections
uv run {{ cookiecutter.project_slug }} rag-ingest /path/to/file.pdf --collection docs
uv run {{ cookiecutter.project_slug }} rag-search "query" --collection docs
{%- if cookiecutter.enable_google_drive_ingestion %}
uv run {{ cookiecutter.project_slug }} rag-sync-gdrive --collection docs
{%- endif %}
{%- if cookiecutter.enable_s3_ingestion %}
uv run {{ cookiecutter.project_slug }} rag-sync-s3 --collection docs
{%- endif %}

# Sync Sources
uv run {{ cookiecutter.project_slug }} cmd rag-sources
uv run {{ cookiecutter.project_slug }} cmd rag-source-add
uv run {{ cookiecutter.project_slug }} cmd rag-source-sync
{%- endif %}
```

## Hard Boundaries

Non-obvious rules that are easy to violate and cross-cutting enough to state up front:

- Repositories use `db.flush()` + `db.refresh()`, **never** `db.commit()` — the session auto-commits via `get_db_session`.
- Routes call services only — **never** import or call repositories directly.
- Route handlers return `-> Any`; serialization is handled by `response_model` (avoids double Pydantic validation).
- `datetime.now(UTC)`, never `datetime.utcnow()`.
- `secrets.compare_digest()` for API key comparison, never `==`.

## Detailed Conventions

Path-scoped guidance lives in `.claude/rules/*` and loads automatically when you edit matching files — it is intentionally NOT repeated here:

- `architecture.md` — Routes → Services → Repositories, dependency injection, thin vs. thick domains
- `schemas-models.md` — Pydantic v2 schemas (`*Create`/`*Update`/`*Read`/`*List`), SQLAlchemy models
- `api-conventions.md` — REST structure, status codes, response format, pagination, auth
- `exceptions-security.md` — domain exceptions (`NotFoundError`, etc.), JWT, RBAC
- `code-style.md` — formatting, naming, imports, type hints
- `testing.md` — test structure, fixtures, async patterns
{%- if cookiecutter.use_frontend %}
- `frontend.md` — Next.js 15 conventions
{%- endif %}

Longer-form docs: `docs/architecture.md`, `docs/adding_features.md`, `docs/testing.md`, `docs/patterns.md`.
