{%- if cookiecutter.use_milvus %}
"""RAG Data Models.

Structures used to interface with the RAG feature."""

import uuid
from pydantic import BaseModel, Field, model_validator, computed_field
from typing import Optional, Any

from enum import Enum


class DocumentPage(BaseModel):
    """Content of document's page."""
    
    page_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    page_num: int
    content: str
    parent_doc_id: Optional[str] = None
    
    
class DocumentPageChunk(DocumentPage):
    """Content of chunked document's page."""
    chunk_content: str
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class DocumentMetadata(BaseModel):
    """Metadata of a document."""
    
    filename: str
    filesize: int
    filetype: str
    additional_info: Optional[dict[str, Any]] = None


class Document(BaseModel):
    """A Document object that describes an ingested file."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pages: list[DocumentPage]
    chunked_pages: Optional[list[DocumentPageChunk]] = None
    metadata: DocumentMetadata
    
    @computed_field
    @property
    def num_pages(self) -> int:
        return len(self.pages) 
    
    @model_validator(mode="after")
    def connect_pages(self) -> "Document":
        for page in self.pages:
            page.parent_doc_id = self.id
        return self     
         
    
class SearchResult(BaseModel):
    """A schema of vector store query output."""
    
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    parent_doc_id: Optional[str] = None


class IngestionStatus(str, Enum):
    """A collection of available ingestion statuses."""
    
    NEW = "new"
    PROCESSING = "processing"
    ADDING = "adding"
    DONE = "done"
    ERROR = "error"
    

class IngestionResult(BaseModel):
    """A schema to handle document ingestion results."""
    
    status: IngestionStatus = IngestionStatus.NEW
    message: Optional[str] = None
    error_message: Optional[str] = None
    document_id: Optional[str] = None
    
    
class CollectionInfo(BaseModel):
    """Collection of information about given collection."""
    
    name: str
    total_vectors: int
    dim: int
    indexing_status: str = "complete"
{%- endif %}
