# File Processing

This document covers how files are handled in two contexts: chat file uploads
(user-facing) and RAG document ingestion (admin/CLI).

{%- if cookiecutter.use_jwt %}

## Chat File Uploads

When a user uploads a file in the chat interface, the following pipeline runs:

### Flow

```
1. Upload     POST /api/v1/files/upload
               |
2. Validate    Check MIME type against allowed list + enforce size limit
               |
3. Classify    Determine file_type: "image", "pdf", "docx", "text"
               |
4. Parse       Extract text content (images skip this step)
               |
5. Store       Save file to media/{user_id}/ via FileStorageService
               |
6. Record      Create ChatFile row in database
               |
7. Link        When message is sent, ChatFile is attached via message_id FK
               |
8. Display     Frontend shows images as thumbnails, documents as badges
```

### Supported File Types

| Category | MIME Types | Extensions | Processing |
|----------|-----------|------------|------------|
| **Images** | image/jpeg, image/png, image/webp, image/gif | .jpg, .png, .webp, .gif | Stored as-is. Sent to LLM as `BinaryContent` for vision analysis. |
| **PDF** | application/pdf | .pdf | Text extracted via configured PDF parser. Appended to prompt as context. |
| **DOCX** | application/vnd.openxmlformats-officedocument.wordprocessingml.document | .docx | Paragraphs extracted via `python-docx`. Appended to prompt as context. |
| **Text** | text/plain, text/markdown | .txt, .md | UTF-8 decoded directly. Appended to prompt as context. |

### PDF Parser Selection (Chat)

{%- if cookiecutter.use_all_pdf_parsers %}

The `CHAT_PDF_PARSER` environment variable controls which parser processes PDFs
uploaded in chat. This is separate from the RAG ingestion parser (`PDF_PARSER`).

| Parser | `CHAT_PDF_PARSER=` | Requirements | Speed | Quality |
|--------|-------------------|--------------|-------|---------|
| PyMuPDF | `pymupdf` (default) | None (bundled) | Fast | Good for text-heavy PDFs |
| LlamaParse | `llamaparse` | `LLAMAPARSE_API_KEY` | Slow (API call) | Best for complex layouts |
| LiteParse | `liteparse` | None | Medium | Good balance |

If the selected parser fails, it automatically falls back to PyMuPDF.

{%- elif cookiecutter.use_llamaparse %}

PDFs are processed using LlamaParse (AI-powered parsing). Requires the
`LLAMAPARSE_API_KEY` environment variable. Falls back to basic text extraction
if the API is unavailable.

{%- else %}

PDFs are processed using PyMuPDF. This is a local parser that requires no API
key and handles text extraction, table detection, and block-level parsing.

{%- endif %}

### Size Limits

- Maximum file size: `MAX_UPLOAD_SIZE_MB` environment variable (default: **50 MB**)
- The limit is enforced server-side after reading the file content.

### Storage

Files are saved by `FileStorageService` to the `media/` directory:

```
media/
  {user_id}/
    document.pdf
    screenshot.png
    ...
```

{%- if cookiecutter.enable_file_storage %}
If S3/MinIO storage is configured (`S3_ENDPOINT`), files are uploaded to the
configured bucket instead of local disk.
{%- endif %}

### ChatFile Model

The `ChatFile` database model tracks uploaded files:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID/FK | Owner (used for access control) |
| `filename` | String | Original filename |
| `mime_type` | String | MIME type (e.g. `application/pdf`) |
| `size` | Integer | File size in bytes |
| `storage_path` | String | Relative path in storage |
| `file_type` | String | Classified type: `image`, `pdf`, `docx`, `text` |
| `parsed_content` | Text | Extracted text content (NULL for images) |
| `message_id` | UUID/FK | Linked message (set when message is sent) |
| `created_at` | DateTime | Upload timestamp |

### Ownership & Access

- Only the file owner can download their files (`GET /files/{id}`).
- The `FileUploadService.get_user_file()` method compares `chat_file.user_id`
  against the requesting user's ID. Returns `NotFoundError` on mismatch.
- There is no admin override -- admins cannot access other users' chat files
  through the file API.

{%- endif %}

{%- if cookiecutter.enable_rag %}

## RAG Document Ingestion

When documents are ingested into the RAG knowledge base (via CLI or API), a
different pipeline handles parsing, chunking, and embedding.

### Ingestion Flow

```
1. Input       File path (CLI) or uploaded file (API)
                |
2. Parse       DocumentProcessor selects parser by file type
                |
3. Chunk       Text split into segments (configurable size/overlap/strategy)
                |
4. Embed       Chunks embedded via configured provider
                |
5. Store       Vectors written to vector database
                |
6. Track       RAGDocument record created in SQL (status tracking)
```

### Supported Formats

The set of supported formats depends on the configured PDF parser:

{%- if cookiecutter.use_all_pdf_parsers or cookiecutter.use_llamaparse %}

**LlamaParse** supports 130+ formats including PDF, DOCX, XLSX, PPTX, HTML,
CSV, RTF, and many more.

**PyMuPDF** supports a smaller set: PDF, TXT, MD, DOCX, and common text formats.

Use `GET /api/v1/rag/supported-formats` to check what the current configuration
supports at runtime.

{%- else %}

Supported file types with the default PyMuPDF parser:

| Extension | Type | Notes |
|-----------|------|-------|
| `.pdf` | PDF | Text + table extraction via PyMuPDF |
| `.docx` | Word | Paragraph extraction via python-docx |
| `.txt` | Plain text | Direct read |
| `.md` | Markdown | Direct read |

{%- endif %}

### PDF Parser Selection (RAG)

{%- if cookiecutter.use_all_pdf_parsers %}

The `PDF_PARSER` environment variable controls which parser processes PDFs
during RAG ingestion:

| Parser | `PDF_PARSER=` | Best For |
|--------|--------------|----------|
| PyMuPDF | `pymupdf` (default) | Fast local processing, text-heavy documents |
| LlamaParse | `llamaparse` | Complex layouts, scanned PDFs, 130+ formats |
| LiteParse | `liteparse` | Balance of speed and quality |

Note: `PDF_PARSER` controls RAG ingestion. `CHAT_PDF_PARSER` controls chat
file uploads. They can be set independently.

{%- elif cookiecutter.use_llamaparse %}

RAG ingestion uses LlamaParse for document parsing. Configure via:
- `LLAMAPARSE_API_KEY` -- Your LlamaParse API key
- `LLAMAPARSE_TIER` -- Parsing tier: `fast`, `cost_effective`, `agentic` (default), `agentic_plus`

{%- else %}

RAG ingestion uses PyMuPDF for document parsing (local, no API key required).

{%- endif %}

### Chunking Configuration

Text is split into chunks before embedding. Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_CHUNK_SIZE` | `512` | Maximum characters per chunk |
| `RAG_CHUNK_OVERLAP` | `50` | Characters of overlap between chunks |
| `RAG_CHUNKING_STRATEGY` | `recursive` | Strategy: `recursive`, `markdown`, `fixed` |

**Strategy comparison:**

| Strategy | Best For |
|----------|----------|
| `recursive` | General text; splits by paragraph, then sentence, then word |
| `markdown` | Markdown/structured docs; splits at heading boundaries |
| `fixed` | Uniform chunk sizes; simplest but may split mid-sentence |

### Embedding Providers

{%- if cookiecutter.use_openai_embeddings %}
Embeddings are generated using **OpenAI** (`text-embedding-3-small` by default).
Set `EMBEDDING_MODEL` to change the model.
{%- elif cookiecutter.use_voyage_embeddings %}
Embeddings are generated using **Voyage AI** (`voyage-3` by default).
Set `VOYAGE_API_KEY` and `EMBEDDING_MODEL` to configure.
{%- elif cookiecutter.use_gemini_embeddings %}
Embeddings are generated using **Google Gemini** (`gemini-embedding-exp-03-07`
by default). Supports multimodal embeddings (text + images).
{%- elif cookiecutter.use_sentence_transformers %}
Embeddings are generated locally using **Sentence Transformers**
(`all-MiniLM-L6-v2` by default). No API key needed. Models are cached in
`MODELS_CACHE_DIR`.
{%- endif %}

### Vector Storage

{%- if cookiecutter.use_milvus %}
Vectors are stored in **Milvus**. Configure with `MILVUS_HOST`, `MILVUS_PORT`,
`MILVUS_DATABASE`, and `MILVUS_TOKEN`.
{%- elif cookiecutter.use_qdrant %}
Vectors are stored in **Qdrant**. Configure with `QDRANT_HOST`, `QDRANT_PORT`,
and optionally `QDRANT_API_KEY`.
{%- elif cookiecutter.use_chromadb %}
Vectors are stored in **ChromaDB**. By default uses embedded/persistent mode
(data in `CHROMA_PERSIST_DIR`). Set `CHROMA_HOST` for client-server mode.
{%- elif cookiecutter.use_pgvector %}
Vectors are stored in **pgvector** using the existing PostgreSQL database.
No additional services needed.
{%- endif %}

### RAG is Global

Collections are shared across **all users**:

- Any authenticated user can search any collection via `POST /rag/search` or
  through the AI agent's RAG tool.
- Only admins can manage collections, upload documents, configure sync sources,
  and view ingestion logs.
- There is no per-user document isolation.

### Document Tracking


Ingested documents are tracked in the SQL database via the `RAGDocument` model:

| Field | Description |
|-------|-------------|
| `collection_name` | Target collection |
| `filename` | Original filename |
| `filesize` | File size in bytes |
| `filetype` | File extension (without dot) |
| `status` | `processing`, `done`, or `error` |
| `error_message` | Error details (if status is `error`) |
| `vector_document_id` | ID in the vector store |
| `chunk_count` | Number of chunks created |
| `storage_path` | Path to original file (for re-ingestion/download) |
| `created_at` | Ingestion start time |
| `completed_at` | Ingestion completion time |

Failed ingestions can be retried via `POST /rag/documents/{id}/retry`.


### Sync Operations

Sync operations are tracked via the `SyncLog` model, recording source, mode,
total files, ingested/updated/skipped/failed counts, and timing. View sync
history via `GET /rag/sync/logs`.

{%- if cookiecutter.enable_rag_image_description %}

### Image Description

When processing documents that contain images, the system can optionally
describe images using LLM vision capabilities. Set `RAG_IMAGE_DESCRIPTION_MODEL`
to a vision-capable model (defaults to `AI_MODEL` if empty). The generated
descriptions are included in the document text for better semantic search.

{%- endif %}

{%- if cookiecutter.enable_reranker %}

### Reranking

Search results can optionally be reranked for better relevance. Enable
reranking by passing `use_reranker=True` to the search API.
{%- if cookiecutter.use_cohere_reranker %}
Reranking uses Cohere's reranker model. Set `COHERE_API_KEY` to enable.
{%- elif cookiecutter.use_cross_encoder_reranker %}
Reranking uses a cross-encoder model (`CROSS_ENCODER_MODEL`, default:
`cross-encoder/ms-marco-MiniLM-L6-v2`). Runs locally, no API key needed.
{%- endif %}

{%- endif %}
{%- endif %}
