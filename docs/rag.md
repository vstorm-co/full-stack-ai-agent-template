# RAG (Retrieval-Augmented Generation)

This document describes the RAG (Retrieval-Augmented Generation) features available in the template.

## Overview

The template provides a complete RAG pipeline for document-based knowledge retrieval:

- **Document Processing**: Parse PDF, DOCX, TXT, and MD files
- **Embeddings**: Convert text to vectors using OpenAI, Voyage AI, or Sentence Transformers
- **Vector Storage**: Milvus vector database for similarity search
- **Retrieval**: Semantic search with optional reranking
- **Agent Integration**: RAG tool available for AI agents

## Quick Start

Enable RAG during project creation:

```bash
# Interactive wizard
fastapi-fullstack new

# With RAG enabled
fastapi-fullstack create my_project --enable-rag

# Full RAG with all features
fastapi-fullstack create my_project --enable-rag --pdf-parser llamaparse --reranker cohere
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Document Sources                         │
│          (Upload API, Google Drive, File System)            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Document Parsers                          │
│    (PDF: pdfplumber/LlamaParse, DOCX, TXT, MD)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Chunking (Recursive)                        │
│            (Default: 512 chars, 50 overlap)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Embedding Providers                        │
│     (OpenAI, Voyage AI, Sentence Transformers)              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Vector Store (Milvus)                      │
│              Similarity Search (Cosine)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Retrieval API                             │
│              Search, Filter, Rerank                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables

```bash
# Required for Milvus
MILVUS_URI=localhost:19530
MILVUS_TOKEN=

# Optional - Embedding Provider
OPENAI_API_KEY=sk-...        # For OpenAI embeddings
VOYAGE_API_KEY=...           # For Voyage AI embeddings

# Optional - PDF Parser
LLAMA_CLOUD_API_KEY=...      # For LlamaParse

# Optional - Reranker
COHERE_API_KEY=...           # For Cohere reranker
HF_TOKEN=...                # For HuggingFace Cross-Encoder reranker
CROSS_ENCODER_MODEL=...    # Model name (default: cross-encoder/ms-marco-MiniLM-L6-v2)
```

### Configuration Options

| Option | Values | Description |
|--------|--------|-------------|
| `enable_rag` | bool | Enable RAG functionality |
| `embedding_provider` | auto-derived | Embedding model provider (auto-derived from LLM provider: OpenAI→openai, Anthropic→voyage, OpenRouter→sentence_transformers) |
| `pdf_parser` | `pdfplumber`, `llamaparse` | PDF parsing method (set via `--pdf-parser` CLI flag) |
| `enable_reranker` | bool | Enable reranking (set via `--reranker` CLI flag: none/cohere/cross_encoder) |

---

## Document Processing

### Supported File Types

| Format | Extension | Parser |
|--------|-----------|--------|
| PDF | `.pdf` | pdfplumber (default) or LlamaParse |
| Word | `.docx` | python-docx |
| Markdown | `.md` | Python native |
| Text | `.txt` | Python native |

### Chunking Configuration

Default settings in [`app/rag/config.py`](backend/app/rag/config.py):

```python
class RAGSettings(BaseModel):
    chunk_size: int = 512       # Characters per chunk
    chunk_overlap: int = 50     # Overlap between chunks
```

---

## Embedding Providers

### OpenAI Embeddings

Uses `text-embedding-3-small` (1536 dimensions) by default.

```python
from app.rag.embeddings import EmbeddingService

service = EmbeddingService(settings)
vector = service.embed_query("your search query")
```

### Voyage AI

Uses `voyage-3` (1024 dimensions) - optimized for retrieval tasks.

### Sentence Transformers

Local embedding using `all-MiniLM-L6-v2` (384 dimensions). No API required.

---

## Reranking

Reranking improves search result quality by re-ordering initial vector search results using a dedicated reranker model. Enable via `--reranker` CLI flag.

### Cohere Reranker

Uses Cohere's rerank API. Requires `COHERE_API_KEY`.

```bash
fastapi-fullstack create my_project --enable-rag --reranker cohere
```

### Cross-Encoder Reranker

Uses HuggingFace Cross-Encoder models locally. Requires `HF_TOKEN` for private models (optional for public models).

```bash
fastapi-fullstack create my_project --enable-rag --reranker cross_encoder
```

Default model: `cross-encoder/ms-marco-MiniLM-L6-v2`. Override with `CROSS_ENCODER_MODEL` env var.

### Using Reranking in API

Pass `use_reranker=true` as a query parameter when calling the search endpoint:

## API Endpoints

All RAG endpoints are prefixed with `/api/v1/rag`.

### Upload Document

```http
POST /api/v1/rag/collections/{name}/upload
Content-Type: multipart/form-data

file: <document>
```

### Search Documents

```http
POST /api/v1/rag/search
Content-Type: application/json

{
  "query": "search term",
  "collection_name": "documents",
  "limit": 5,
  "min_score": 0.0,
  "filter": ""
}
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_reranker` | bool | false | Whether to use reranking (if configured) |

**Note:** Set `use_reranker=true` to enable reranking during search. Reranking must be enabled in the project configuration (via `--reranker cohere` or `--reranker cross_encoder` CLI flags).

### List Collections

```http
GET /api/v1/rag/collections
```

### Get Collection Info

```http
GET /api/v1/rag/collections/{name}/info
```

### Create Collection

```http
POST /api/v1/rag/collections/{name}
```

### Delete Collection

```http
DELETE /api/v1/rag/collections/{name}
```

### Delete Document

```http
DELETE /api/v1/rag/collections/{name}/documents/{document_id}
```

---

## AI Agent Integration

RAG is integrated with AI agents through the `search_knowledge_base` tool.

### PydanticAI Agent

```python
# app/agents/tools/rag_tool.py
from app.agents.tools.rag_tool import search_knowledge_base

# Use in your agent tools
result = await search_knowledge_base(
    query="What is the project about?",
    collection="documents",
    top_k=5
)
```

### Available Tools

| Function | Description |
|----------|-------------|
| `search_knowledge_base` | Async search function |
| `search_knowledge_base_sync` | Sync wrapper for CrewAI |

### Tool Definition

```python
{
    "name": "search_knowledge_base",
    "description": "Search the knowledge base and return formatted results",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query string"},
            "collection": {"type": "string", "description": "Name of the collection to search"},
            "top_k": {"type": "integer", "description": "Number of top results to retrieve"}
        },
        "required": ["query"]
    }
}
```

---

## Scheduled Tasks

RAG ingestion can be scheduled using background task workers:

### Task Configuration

In [`app/worker/tasks/schedules.py`](backend/app/worker/tasks/schedules.py):

```python
@scheduler.scheduled("interval", hours=24)
async def rag_ingestion_task():
    """Daily RAG ingestion from configured sources."""
    # Implements periodic document sync
```

---

## CLI Commands

### Upload Documents

```bash
# Upload a document to a collection
python -m app.commands.rag upload --collection my_docs --path ./document.pdf

# Batch upload
python -m app.commands.rag upload --collection my_docs --path ./docs/
```

### List Collections

```bash
python -m app.commands.rag list-collections
```

---

## Frontend Integration

The frontend includes RAG API client at [`frontend/src/lib/rag-api.ts`](frontend/src/lib/rag-api.ts):

```typescript
import { ragApi } from '@/lib/rag-api';

// Upload document
await ragApi.uploadDocument(collection, file);

// Search
const results = await ragApi.searchDocuments({
  query: 'search query',
  collection_name: 'documents',
  limit: 5
});
```

---

## Reranking

Improve search results with reranking:

### Cohere Reranker

```bash
fastapi-fullstack create my_project --enable-rag --enable-reranker cohere
```

### Cross-Encoder Reranker

Uses Sentence Transformers locally:

```bash
fastapi-fullstack create my_project --enable-rag --enable-reranker cross_encoder
```

---

## Google Drive Integration

Enable Google Drive as a document source:

```bash
fastapi-fullstack create my_project --enable-rag --enable-google-drive-ingestion
```

Requires OAuth2 configuration in Google Cloud Console.

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `MILVUS_URI` | Yes | Milvus connection URI |
| `MILVUS_TOKEN` | No | Milvus authentication token |
| `OPENAI_API_KEY` | For OpenAI embeddings | OpenAI API key |
| `VOYAGE_API_KEY` | For Voyage embeddings | Voyage AI API key |
| `LLAMA_CLOUD_API_KEY` | For LlamaParse | LlamaCloud API key |
| `COHERE_API_KEY` | For Cohere reranker | Cohere API key |

---

## Troubleshooting

### Milvus Connection Issues

Ensure Milvus is running:

```bash
docker run -d -p 19530:19530 milvusdb/milvus
```

### Embedding Model Not Loading

For Sentence Transformers, check model cache directory permissions:

```python
from app.core.config import settings
print(settings.MODELS_CACHE_DIR)
```

### Document Parsing Errors

- **PDF has no text**: Use LlamaParse for scanned documents
- **Large files**: Increase chunk size in RAGSettings
