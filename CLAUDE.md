# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Full-Stack AI Agent Template** is an interactive CLI tool that generates production-ready FastAPI + Next.js projects with AI agents, RAG, and 20+ enterprise integrations. Uses Cookiecutter templates with Jinja2 conditionals.

## Commands

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run single test
uv run pytest tests/test_file.py::test_name -v

# Linting and formatting
uv run ruff check . --fix
uv run ruff format .

# Type checking
uv run ty check
```

## CLI Usage

```bash
# Interactive wizard (default)
fastapi-fullstack

# Quick project creation
fastapi-fullstack create my_project --database postgresql

# With RAG
fastapi-fullstack create my_project --ai-framework pydantic_ai --rag --database postgresql --task-queue celery

# List available options
fastapi-fullstack templates
```

## Architecture

### Core Modules (`fastapi_gen/`)

- **cli.py** - Click-based CLI: `new` (interactive, default), `create` (direct), `templates` (list options)
- **config.py** - Pydantic models: `ProjectConfig`, enums (`AIFrameworkType`, `LLMProviderType`, `VectorStoreType`, etc.), validation, cookiecutter context
- **prompts.py** - Questionary-based interactive prompts → `ProjectConfig`
- **generator.py** - Cookiecutter invocation and post-generation messaging

### Template System (`template/`)

```
template/
├── cookiecutter.json                    # Default context (~120 variables)
├── hooks/post_gen_project.py            # Post-gen cleanup & formatting
└── {{cookiecutter.project_slug}}/
    ├── backend/
    │   ├── app/
    │   │   ├── main.py                  # FastAPI app with lifespan
    │   │   ├── api/                     # Routes, deps, exception handlers
    │   │   ├── core/                    # Config, security, middleware
    │   │   ├── db/                      # Models, session management
    │   │   ├── schemas/                 # Pydantic request/response models
    │   │   ├── repositories/            # Data access layer
    │   │   ├── services/               # Business logic
    │   │   ├── agents/                  # AI agents (5 frameworks)
    │   │   ├── rag/                     # RAG module (4 vector stores, embeddings, sources)
    │   │   │   └── connectors/          # Sync source connectors (Google Drive, S3)
    │   │   ├── commands/                # Django-style CLI commands
    │   │   └── worker/                  # Background tasks (Celery/Taskiq/ARQ)
    │   ├── cli/                         # Generated project CLI
    │   └── alembic/                     # Migrations (if SQL DB)
    └── frontend/                        # Next.js 15 (optional)
        └── src/
            ├── app/[locale]/            # i18n-routed pages (PL/EN)
            │   ├── (marketing)/         # Public pages (home, pricing, blog, legal)
            │   ├── (auth)/              # Login, register, reset-password
            │   ├── chat/, kb/, settings/, admin/
            │   └── auth/magic-link/     # Magic-link verify
            ├── components/
            │   ├── marketing/           # Hero, features, pricing, FAQ, CTAs
            │   ├── legal/               # privacy/terms/cookies content (per-locale)
            │   ├── auth/, chat/, kb/, settings/, dashboard/, admin/
            │   └── ui/                  # shadcn-style primitives
            └── app/{icon,opengraph-image,manifest,robots,sitemap}.tsx
```

## Key Design Decisions

- 5 AI frameworks: PydanticAI, PydanticDeep, LangChain, LangGraph, DeepAgents
- 4 LLM providers: OpenAI, Anthropic, Google Gemini, OpenRouter
- 4 vector store backends: Milvus, Qdrant, ChromaDB, pgvector
- 4 embedding providers: OpenAI, Voyage, Gemini (multimodal), SentenceTransformers
- RAG document sources: local files (CLI), Google Drive, S3/MinIO
- Document ingestion via CLI and API upload
- Sync sources: configurable connectors (Google Drive, S3) with scheduled sync
- 3 PDF parsers: PyMuPDF, LiteParse, LlamaParse (runtime selection via env var)
- Image description via LLM vision API (optional, opt-in)
- LlamaParse support for 130+ document formats
- Logfire for PydanticAI observability, LangSmith for LangChain/LangGraph/DeepAgents
- Repository + Service pattern — routes never contain direct DB calls
- Database always required (PostgreSQL async, MongoDB async, SQLite sync)
- Frontend i18n: PL + EN via `next-intl`, locale-prefixed routes, per-locale TSX for long-form prose
- Marketing site (gated by `enable_marketing_site`): home, pricing, FAQ, blog, contact, legal
- Auth flows: password + JWT, password reset, magic link sign-in, OAuth-ready
- User-scoped API keys (`sk_<43>` format, prefix lookup + bcrypt verify)
- Admin panel (gated by `enable_admin_panel`): workspace stats, Stripe events browser
- SEO defaults: `opengraph-image.tsx`, `icon.tsx`, `manifest.ts`, `robots.ts`, `sitemap.ts`

## Where to Find More Info

- Template variables: `template/cookiecutter.json`
- Post-generation logic: `template/hooks/post_gen_project.py`
- Variable documentation: `template/VARIABLES.md`
