# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**fastapi-fullstack** is an interactive CLI tool that generates FastAPI projects with Logfire observability integration. It uses Cookiecutter templates to scaffold complete project structures with configurable options for databases, authentication, background tasks, and various integrations including AI agents and RAG.

## Commands

```bash
# Install dependencies
uv sync

# Install dev dependencies
uv sync --dev

# Run tests
pytest

# Run single test
pytest tests/test_file.py::test_name -v

# Linting and formatting
ruff check .
ruff check . --fix
ruff format .

# Type checking
mypy fastapi_gen
```

## CLI Usage

```bash
# Interactive wizard
fastapi-fullstack new

# Quick project creation
fastapi-fullstack create my_project --database postgresql --auth jwt

# Minimal project (no extras)
fastapi-fullstack create my_project --minimal

# With RAG enabled
fastapi-fullstack create my_project --ai-agent --rag --background-tasks celery

# List available options
fastapi-fullstack templates
```

## Architecture

### Core Modules (`fastapi_gen/`)

- **cli.py** - Click-based CLI with three commands: `new` (interactive), `create` (direct), `templates` (list options)
- **config.py** - Pydantic models defining all configuration options (`ProjectConfig`, `DatabaseType`, `AuthType`, etc.) and cookiecutter context conversion
- **prompts.py** - Questionary-based interactive prompts that collect user input and build `ProjectConfig`
- **generator.py** - Cookiecutter invocation and post-generation messaging

### Template System (`template/`)

Uses Cookiecutter with Jinja2 conditionals. Structure:

```
template/
├── cookiecutter.json                    # Default context (~85 variables)
├── hooks/post_gen_project.py            # Post-gen cleanup & ruff formatting
└── {{cookiecutter.project_slug}}/
    ├── backend/
    │   ├── app/                         # FastAPI application
    │   │   ├── main.py                  # App entry with lifespan
    │   │   ├── api/                     # Routes, deps, exception handlers
    │   │   ├── core/                    # Config, security, middleware
    │   │   ├── db/                      # Models, session management
    │   │   ├── schemas/                 # Pydantic request/response models
    │   │   ├── repositories/            # Data access layer
    │   │   ├── services/                # Business logic
    │   │   ├── agents/                  # AI agents (PydanticAI, LangChain, LangGraph, CrewAI, DeepAgents)
    │   │   ├── rag/                     # RAG module (Milvus vector store, embeddings, document processing)
    │   │   ├── commands/                # Django-style CLI commands
    │   │   └── worker/                  # Background tasks (Celery/Taskiq/ARQ)
    │   ├── cli/                         # Generated project CLI
    │   ├── tests/                       # Test suite with fixtures
    │   └── alembic/                     # Migrations (if SQL DB)
    └── frontend/                        # Next.js 15 (optional)
```

Template files use `{% if cookiecutter.use_jwt %}` style conditionals to include/exclude code.

### Configuration Flow

1. CLI collects options (interactive prompts or direct args)
2. Options build `ProjectConfig` Pydantic model
3. `config.to_cookiecutter_context()` converts to template context dict
4. Cookiecutter renders template with context
5. Post-generation hook runs ruff check/format on generated code
6. Post-generation messages guide user setup

## Key Design Decisions

- All database options except SQLite are async (asyncpg, motor)
- Logfire instrumentation is opt-in per subsystem (FastAPI, DB, Redis, Celery, HTTPX)
- Project names must match pattern `^[a-z][a-z0-9_]*$`
- Generated projects use UV for package management
- AI Agent uses PydanticAI with `iter()` for full event streaming over WebSocket
- Template uses repository pattern for data access and service layer for business logic
- RAG uses Milvus vector store with configurable embeddings (OpenAI, Voyage, SentenceTransformers)
- RAG supports reranking (Cohere, CrossEncoder) and multiple document parsers (pdfplumber, LlamaParse)

## RAG Configuration

When RAG is enabled, the following additional components are available:

### Environment Variables

```bash
# Milvus
MILVUS_HOST=milvus
MILVUS_PORT=19530

# Embeddings (provider-dependent)
EMBEDDING_MODEL=text-embedding-3-small  # OpenAI
# or: EMBEDDING_MODEL=voyage-3          # Voyage
# or: EMBEDDING_MODEL=all-MiniLM-L6-v2  # SentenceTransformers

# Optional: Reranker
# COHERE_API_KEY=...
# LLAMAPARSE_API_KEY=...
```

### RAG CLI Commands (in generated project)

```bash
# List collections
python -m app.cli rag-collections

# Ingest documents
python -m app.cli rag-ingest /path/to/document.pdf --collection mydocs

# Search knowledge base
python -m app.cli rag-search "query" --collection mydocs --top-k 5

# Drop collection
python -m app.cli rag-drop collection_name
```

### RAG API Endpoints

- `POST /api/v1/rag/collections/{name}/upload` - Upload & ingest document
- `POST /api/v1/rag/collections/{name}/ingest` - Ingest synchronously
- `GET /api/v1/rag/collections` - List collections
- `POST /api/v1/rag/collections/{name}` - Create collection
- `DELETE /api/v1/rag/collections/{name}` - Drop collection
- `GET /api/v1/rag/collections/{name}/info` - Collection stats
- `POST /api/v1/rag/search` - Search documents
- `DELETE /api/v1/rag/collections/{name}/documents/{source}` - Delete document

## Where to Find More Info

Before starting complex tasks, check these resources:
- Template variables: `template/cookiecutter.json`
- Post-generation logic: `template/hooks/post_gen_project.py`
- Sprint tasks: `notes/sprint_0_1_7/` (current sprint)
