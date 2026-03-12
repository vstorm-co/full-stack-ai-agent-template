{%- if cookiecutter.use_milvus %}
"""RAG Config.

Variables and constants used in the RAG feature to run it."""
from enum import StrEnum

from pydantic import BaseModel, Field

class DocumentExtensions(StrEnum):
    """Extensions supported by the RAG ingestion pipeline."""
    PDF = ".pdf"
    DOCX = ".docx"
    MD = ".md"
    TXT = ".txt"

    
class EmbeddingsConfig(BaseModel):
    """Embeddings configuration for usage in RAG feature."""
    {%- if cookiecutter.use_openai_embeddings %}
    model: str = "text-embedding-3-small"
    dim: int = 1536
    {%- elif cookiecutter.use_voyage_embeddings %}
    model: str = "voyage-3"
    dim: int = 1024
    {%- elif cookiecutter.use_sentence_transformers %}
    model: str = "all-MiniLM-L6-v2"
    dim: int = 384    
    {%- endif %}  
    
    
{%- if cookiecutter.enable_reranker %}    
class RerankerConfig(BaseModel):
    """Reranker configuration for usage in RAG features."""
    {%- if cookiecutter.use_cohere_reranker %}
    model: str = "cohere"
    {%- elif cookiecutter.use_cross_encoder_reranker %}
    model: str = "cross_encoder"
    {%- endif %}
{%- endif %}


class DocumentParser(BaseModel):
    """Document parsing settings for RAG features.
    
    Note: This now only applies to non-PDF files (txt, md, docx).
    PDF parsing is controlled separately via pdf_parser.
    """
    method: str = "python_native"  # Always python_native for non-PDF


class PdfParser(BaseModel):
    """PDF parsing settings for RAG features."""
    {%- if cookiecutter.use_llamaparse %}
    method: str = "llamaparse"
    api_key: str = ""
    {%- else %}
    method: str = "pdfplumber"
    {%- endif %}


class RAGSettings(BaseModel):
    """Constants and variables used to setup the RAG features."""
    
    # Collection
    collection_name: str = "documents"
    
    # Documents
    allowed_extensions: list[DocumentExtensions] = Field(default_factory=lambda: list(DocumentExtensions))
    
    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # Embeddings
    embeddings_config: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    
    # Reranker
    {%- if cookiecutter.enable_reranker %}
    reranker_config: RerankerConfig = Field(default_factory=RerankerConfig)
    {%- endif %}
    
    # Document parsing
    document_parser: DocumentParser = Field(default_factory=DocumentParser)
    
    # PDF parsing
    pdf_parser: PdfParser = Field(default_factory=PdfParser)
    
    {%- if cookiecutter.enable_google_drive_ingestion %}
    # Ingestion
    gdrive_ingestion: bool = True
    {%- else %}
    gdrive_ingestion: bool = False
    {%- endif %}
{%- endif %}
