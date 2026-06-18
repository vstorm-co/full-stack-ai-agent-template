"""RAG API schemas."""

from typing import Any

from pydantic import BaseModel, Field


class RAGSearchRequest(BaseModel):
    """Parameters for a vector search query."""

    collection_name: str = Field("documents", description="Target collection for search")
    collection_names: list[str] | None = Field(
        None, description="Search across multiple collections (overrides collection_name)"
    )
    query: str = Field(..., description="Natural language search query")
    limit: int = Field(default=4, ge=1, le=20)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    filter: str | None = Field(
        None, description="Scalar filter expression (e.g. 'filetype == \"pdf\"')"
    )


class RAGSearchResult(BaseModel):
    """A single retrieved chunk with its associated metadata."""

    content: str
    score: float
    metadata: dict[str, Any]
    parent_doc_id: str


class RAGSearchResponse(BaseModel):
    """List of results found in the vector store."""

    results: list[RAGSearchResult]


class RAGCollectionInfo(BaseModel):
    """Statistical information about a specific collection."""

    name: str
    total_vectors: int
    dim: int
    indexing_status: str = "complete"


class RAGCollectionList(BaseModel):
    """List of all available collection names."""

    items: list[str]


class RAGDocumentItem(BaseModel):
    """Information about a single document in a collection."""

    document_id: str = Field(..., description="Unique identifier of the document")
    filename: str | None = Field(None, description="Original filename of the document")
    filesize: int | None = Field(None, description="Size of the file in bytes")
    filetype: str | None = Field(None, description="MIME type of the file")
    chunk_count: int = Field(default=0, description="Number of chunks/vectors in the collection")
    additional_info: dict[str, Any] | None = Field(None, description="Additional metadata")


class RAGDocumentList(BaseModel):
    """List of all documents in a collection."""

    items: list[RAGDocumentItem]
    total: int = Field(..., description="Total number of unique documents")


class RAGMessageResponse(BaseModel):
    """Simple message response."""

    message: str


class RAGTrackedDocumentItem(BaseModel):
    """A document tracked in the SQL database."""

    id: str
    collection_name: str
    filename: str
    filesize: int
    filetype: str
    status: str
    error_message: str | None = None
    vector_document_id: str | None = None
    chunk_count: int = 0
    has_file: bool = False
    created_at: str | None = None
    completed_at: str | None = None


class RAGTrackedDocumentList(BaseModel):
    """List of tracked RAG documents."""

    items: list[RAGTrackedDocumentItem]
    total: int


class RAGIngestResponse(BaseModel):
    """Response for document ingestion (async or sync)."""

    id: str
    status: str
    filename: str
    collection: str
    message: str
    document_id: str | None = None


class RAGRetryResponse(BaseModel):
    """Response for document retry."""

    id: str
    status: str
    message: str


class RAGSyncRequest(BaseModel):
    """Request to trigger a sync operation."""

    collection_name: str = Field("documents", description="Target collection")
    mode: str = Field("full", description="Sync mode: full, new_only, update_only")
    path: str = Field("", description="Source path")


class RAGSyncLogItem(BaseModel):
    """A sync operation log entry."""

    id: str
    source: str
    collection_name: str
    status: str
    mode: str
    total_files: int = 0
    ingested: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class RAGSyncLogList(BaseModel):
    """List of sync log entries."""

    items: list[RAGSyncLogItem]
    total: int


class RAGSyncResponse(BaseModel):
    """Response for sync trigger."""

    id: str
    status: str
    message: str
