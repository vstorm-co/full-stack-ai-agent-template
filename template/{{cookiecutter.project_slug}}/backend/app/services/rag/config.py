{%- if cookiecutter.enable_rag %}
"""RAG configuration."""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class DocumentExtensions(StrEnum):
    """Extensions supported by the RAG ingestion pipeline."""

    PDF = ".pdf"
    DOCX = ".docx"
    MD = ".md"
    TXT = ".txt"


PYMUPDF_FORMATS: set[str] = {".pdf", ".docx", ".txt", ".md"}

LITEPARSE_FORMATS: set[str] = {
    ".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md",
    ".jpg", ".jpeg", ".png", ".tiff",
}

LLAMAPARSE_FORMATS: set[str] = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".rtf", ".txt", ".md", ".epub",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
    ".xlsx", ".xls", ".csv", ".tsv", ".ods",
    ".mp3", ".mp4", ".wav", ".m4a", ".webm",
    ".html", ".htm", ".xml",
}

PARSER_FORMATS: dict[str, set[str]] = {
    "pymupdf": PYMUPDF_FORMATS,
    "liteparse": LITEPARSE_FORMATS,
    "llamaparse": LLAMAPARSE_FORMATS,
}


def get_supported_formats(parser_name: str = "pymupdf") -> set[str]:
    """Get supported file formats for a given parser."""
    return PARSER_FORMATS.get(parser_name, PYMUPDF_FORMATS)


# Known embedding models and their output dimensions.
# Used to auto-set vector store dimension from model name.
EMBEDDING_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "voyage-3": 1024,
    "voyage-3-lite": 512,
    "voyage-code-3": 1024,
    "gemini-embedding-exp-03-07": 3072,
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
    "bge-small-en-v1.5": 384,
    "bge-base-en-v1.5": 768,
    "bge-large-en-v1.5": 1024,
}


class EmbeddingsConfig(BaseModel):
    """Embeddings configuration. Dimension is auto-derived from model name."""

{%- if cookiecutter.use_openai_embeddings %}
    model: str = "text-embedding-3-large"
    dim: int = 3072
{%- elif cookiecutter.use_voyage_embeddings %}
    model: str = "voyage-3"
    dim: int = 1024
{%- elif cookiecutter.use_gemini_embeddings %}
    model: str = "gemini-embedding-exp-03-07"
    dim: int = 3072
{%- elif cookiecutter.use_sentence_transformers %}
    model: str = "all-MiniLM-L6-v2"
    dim: int = 384
{%- endif %}

    @model_validator(mode="after")
    def set_dim_from_model(self) -> "EmbeddingsConfig":
        if self.model in EMBEDDING_DIMENSIONS:
            self.dim = EMBEDDING_DIMENSIONS[self.model]
        return self


{%- if cookiecutter.enable_reranker %}

class RerankerConfig(BaseModel):
    """Reranker configuration."""

{%- if cookiecutter.use_cohere_reranker %}
    model: str = "cohere"
{%- elif cookiecutter.use_cross_encoder_reranker %}
    model: str = "cross_encoder"
{%- endif %}
{%- endif %}


class DocumentParser(BaseModel):
    """Document parsing settings (non-PDF files)."""

    method: str = "python_native"


class PdfParser(BaseModel):
    """PDF parsing settings."""

{%- if cookiecutter.use_all_pdf_parsers %}
    method: str = "pymupdf"  # Runtime: pymupdf, llamaparse, liteparse
    api_key: str = ""
    tier: str = "agentic"
{%- elif cookiecutter.use_llamaparse %}
    method: str = "llamaparse"
    api_key: str = ""
    tier: str = "agentic"
{%- elif cookiecutter.use_liteparse %}
    method: str = "liteparse"
{%- else %}
    method: str = "pymupdf"
{%- endif %}
{%- if cookiecutter.use_liteparse or cookiecutter.use_all_pdf_parsers %}
    # LiteParse-specific. ocr_server_url=None falls back to bundled Tesseract.js.
    # Set to e.g. "http://easyocr:8000" to use an external OCR microservice.
    liteparse_ocr_server_url: str | None = None
    liteparse_ocr_language: str = "en"
    liteparse_timeout_seconds: float = 600.0
{%- endif %}


class RAGSettings(BaseModel):
    """RAG pipeline configuration."""

    collection_name: str = "documents"

    allowed_extensions: list[DocumentExtensions] = Field(
        default_factory=lambda: list(DocumentExtensions)
    )

    chunk_size: int = 512
    chunk_overlap: int = 50
    chunking_strategy: str = "recursive"
    enable_hybrid_search: bool = False
    enable_ocr: bool = False

    embeddings_config: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)

{%- if cookiecutter.enable_reranker %}
    reranker_config: RerankerConfig = Field(default_factory=RerankerConfig)
{%- endif %}

    document_parser: DocumentParser = Field(default_factory=DocumentParser)
    pdf_parser: PdfParser = Field(default_factory=PdfParser)

{%- if cookiecutter.enable_rag_image_description %}
    enable_image_description: bool = True
    image_description_model: str = ""
{%- endif %}

{%- if cookiecutter.enable_google_drive_ingestion %}
    gdrive_ingestion: bool = True
{%- else %}
    gdrive_ingestion: bool = False
{%- endif %}
{%- endif %}
