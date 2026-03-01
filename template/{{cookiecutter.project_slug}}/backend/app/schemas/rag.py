{%- if cookiecutter.enable_rag %}
"""RAG API schemas."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class RAGUploadResponse(BaseModel):
    """Response after a document is accepted for ingestion."""
    message: str
    document_id: Optional[str] = None

class RAGSearchRequest(BaseModel):
    """Parameters for a vector search query."""
    collection_name: str = Field(..., description="Target collection for search")
    query: str = Field(..., description="Natural language search query")
    limit: int = Field(default=4, ge=1, le=20)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    filter: Optional[str] = Field(None, description="Scalar filter expression (e.g. 'filetype == \"pdf\"')")

class RAGSearchResult(BaseModel):
    """A single retrieved chunk with its associated metadata.
    
    This is the API-facing schema for SearchResult found in internal models.
    """
    content: str
    score: float
    metadata: Dict[str, Any]
    parent_doc_id: str

class RAGSearchResponse(BaseModel):
    """List of results found in the vector store."""
    results: List[RAGSearchResult]

class RAGCollectionInfo(BaseModel):
    """Statistical information about a specific collection."""
    name: str
    total_vectors: int
    dim: int
    indexing_status: str = "complete"

class RAGCollectionList(BaseModel):
    """List of all available collection names."""
    items: List[str]
{%- endif %}
