# AGENTS.md

Guidance for AI coding agents (Codex, Copilot, Cursor, Zed, OpenCode) working with this repository.

## Project Overview

**Full-Stack AI Agent Template** — CLI tool that generates production-ready FastAPI + Next.js projects with AI agents (5 frameworks), RAG (4 vector stores), and 20+ enterprise integrations.

## Commands

```bash
uv sync                    # Install dependencies
uv run pytest              # Run tests
uv run ruff check . --fix  # Lint
uv run ruff format .       # Format
uv run mypy fastapi_gen    # Type check
```

## CLI

```bash
fastapi-fullstack                                  # Interactive wizard (default)
fastapi-fullstack create my_app --database postgresql
fastapi-fullstack create my_app --rag --task-queue celery
fastapi-fullstack templates                        # List all options
```

Generated project CLI includes sync source commands:
```bash
uv run <project_slug> cmd rag-sources              # List configured sources
uv run <project_slug> cmd rag-source-add           # Add a new source
uv run <project_slug> cmd rag-source-sync          # Trigger sync for a source
```

## Architecture

| Module | Purpose |
|--------|---------|
| `fastapi_gen/cli.py` | Click CLI: `new`, `create`, `templates` |
| `fastapi_gen/config.py` | Pydantic models, enums, validation, cookiecutter context |
| `fastapi_gen/prompts.py` | Interactive prompts (Questionary) |
| `fastapi_gen/generator.py` | Cookiecutter invocation |

### Template (`template/`)

```
template/
├── cookiecutter.json            # ~120 variables
├── hooks/post_gen_project.py    # Cleanup & formatting
└── {{cookiecutter.project_slug}}/
    ├── backend/app/             # FastAPI (agents, rag, services, repos)
    └── frontend/                # Next.js 15 (optional)
```

Jinja2 conditionals: `{%- if cookiecutter.enable_rag %}...{%- endif %}`

## Key Features

- **5 AI Frameworks**: PydanticAI, PydanticDeep, LangChain, LangGraph, DeepAgents
- **4 LLM Providers**: OpenAI, Anthropic, Google Gemini, OpenRouter
- **RAG**: 4 vector stores (Milvus, Qdrant, ChromaDB, pgvector), 4 embedding providers, reranking, image description
- **Document Sources**: Local files (CLI), API upload, Google Drive (service account), S3/MinIO
- **Sync Sources**: Configurable connectors (Google Drive, S3) with scheduled sync
- **PDF Parsers**: PyMuPDF, LiteParse, LlamaParse (runtime selection via env var)
- **Observability**: Logfire (PydanticAI), LangSmith (LangChain/LangGraph/DeepAgents)

## Common Tasks

**Adding a new CLI option:**
1. Add to `config.py` (enum/field on `ProjectConfig` or sub-model)
2. Add prompt to `prompts.py`
3. Add to `cookiecutter.json`
4. Add conditionals to template files
5. Update `hooks/post_gen_project.py` for cleanup
6. Document in `template/VARIABLES.md`

**Adding a new vector store:**
1. Add to `VectorStoreType` enum in `config.py`
2. Add `use_<name>` to `to_cookiecutter_context()`
3. Implement `<Name>VectorStore(BaseVectorStore)` in `rag/vectorstore.py`
4. Add conditional in `api/deps.py`, `commands/rag.py`, `agents/tools/rag_tool.py`
5. Add Docker service (if needed) and dependencies

**Adding a new sync connector:**
1. Create connector class in `rag/connectors/` following the `BaseConnector` pattern
2. Register connector type in `rag/connectors/__init__.py`
3. Add CLI command in `commands/rag.py` (e.g. `rag-source-add`, `rag-source-sync`)
4. Add sync source schema in `schemas/sync_source.py`
5. Wire up background task in `worker/tasks/rag_tasks.py`

## Reference

| Resource | Location |
|----------|----------|
| Template variables | `template/cookiecutter.json` |
| Variable docs | `template/VARIABLES.md` |
| Post-gen hooks | `template/hooks/post_gen_project.py` |
| CLI help | `fastapi-fullstack templates` |
