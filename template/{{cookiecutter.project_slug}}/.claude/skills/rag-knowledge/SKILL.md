---
name: rag-knowledge
description: Work with the RAG knowledge base — ingest documents, run semantic search, manage collections, or add a sync source/connector (Google Drive, S3). Use when populating or debugging the knowledge base, tuning retrieval, or adding a new document source. This project uses {{ cookiecutter.vector_store }} + {{ cookiecutter.embedding_provider }} embeddings.
---

# RAG Knowledge Base ({{ cookiecutter.vector_store }})

The RAG stack lives in `backend/app/services/rag/` (ingestion, vectorstore, embeddings, connectors). Retrieval is exposed to the agent as the `search_knowledge_base` tool, and to operators via the CLI and the dashboard.

## CLI (run from `backend/`)

```bash
uv run {{ cookiecutter.project_slug }} cmd rag-ingest ./docs/ --collection docs --recursive   # ingest files/folder
uv run {{ cookiecutter.project_slug }} cmd rag-search "your question" --collection docs        # semantic search
uv run {{ cookiecutter.project_slug }} cmd rag-collections                                     # list collections
uv run {{ cookiecutter.project_slug }} cmd rag-stats                                           # chunk/vector counts
uv run {{ cookiecutter.project_slug }} cmd rag-drop <collection> --yes                         # delete a collection
```

Ingestion = parse → chunk → embed → upsert into {{ cookiecutter.vector_store }}. Re-ingesting the same source updates it (use `--no-replace` / `--sync-mode` to control dedupe).

## Sync sources (connectors)

Connectors keep a collection in sync with an external source (Google Drive, S3/MinIO) on a schedule, and can be managed per-organization from the dashboard (`/orgs/[id]/integrations`) or via CLI:

```bash
uv run {{ cookiecutter.project_slug }} cmd rag-sources                  # list
uv run {{ cookiecutter.project_slug }} cmd rag-source-add               # add (interactive)
uv run {{ cookiecutter.project_slug }} cmd rag-source-sync --all        # trigger a sync
```

Connector credentials are encrypted at rest with `CHANNEL_ENCRYPTION_KEY` (Fernet).

## Adding a new connector type

Implement a connector in `backend/app/services/rag/connectors/` following the existing Google Drive / S3 connectors, register it in the connector registry, and expose its config fields. See `docs/howto/add-sync-connector.md` and `docs/howto/configure-sync-sources.md`.

## Tuning retrieval

- Chunk size/overlap and parser (PyMuPDF / LlamaParse) are configured via env — see `docs/configuration.md` and `docs/rag.md`.
- Reranking (Cohere or local CrossEncoder) improves result ordering when enabled.
- If search returns poor results: confirm the collection is populated (`rag-stats`), check the active collection in the chat's KB selector, and verify the embedding provider/key.

## Rules

- Embedding provider and dimensions are fixed per project ({{ cookiecutter.embedding_provider }}) — don't mix embeddings across a collection; re-ingest if you change them.
- Heavy ingestion runs as a background job, not inline in a request.
- See `docs/rag.md` for the full pipeline reference.
