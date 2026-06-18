"""RAG configuration."""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class DocumentExtensions(StrEnum):
    """Extensions supported by the RAG ingestion pipeline."""

    PDF = ".pdf"
    DOCX = ".docx"
    MD = ".md"
    TXT = ".txt"


# Supported file formats per parser
PYMUPDF_FORMATS: set[str] = {".pdf", ".docx", ".txt", ".md"}

LITEPARSE_FORMATS: set[str] = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".txt",
    ".md",
    ".jpg",
    ".jpeg",
    ".png",
    ".tiff",
}

LLAMAPARSE_FORMATS: set[str] = {
    # Documents
    ".pdf",
    ".docx",
    ".doc",
    ".pptx",
    ".ppt",
    ".rtf",
    ".txt",
    ".md",
    ".epub",
    # Images
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".webp",
    # Spreadsheets
    ".xlsx",
    ".xls",
    ".csv",
    ".tsv",
    ".ods",
    # Audio
    ".mp3",
    ".mp4",
    ".wav",
    ".m4a",
    ".webm",
    # Web
    ".html",
    ".htm",
    ".xml",
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
    # OpenAI
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    # Voyage AI
    "voyage-3": 1024,
    "voyage-3-lite": 512,
    "voyage-code-3": 1024,
    # Google Gemini
    "gemini-embedding-exp-03-07": 3072,
    # SentenceTransformers (local)
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
    "bge-small-en-v1.5": 384,
    "bge-base-en-v1.5": 768,
    "bge-large-en-v1.5": 1024,
}


class EmbeddingsConfig(BaseModel):
    """Embeddings configuration. Dimension is auto-derived from model name."""

    model: str = "all-MiniLM-L6-v2"
    dim: int = 384

    @model_validator(mode="after")
    def set_dim_from_model(self) -> "EmbeddingsConfig":
        if self.model in EMBEDDING_DIMENSIONS:
            self.dim = EMBEDDING_DIMENSIONS[self.model]
        return self


class DocumentParser(BaseModel):
    """Document parsing settings (non-PDF files)."""

    method: str = "python_native"


class PdfParser(BaseModel):
    """PDF parsing settings."""

    method: str = "pymupdf"  # Runtime: pymupdf, llamaparse, liteparse
    api_key: str = ""
    tier: str = "agentic"
    # LiteParse-specific. ocr_server_url=None falls back to bundled Tesseract.js.
    # Set to e.g. "http://easyocr:8000" to use an external OCR microservice.
    liteparse_ocr_server_url: str | None = None
    liteparse_ocr_language: str = "en"
    liteparse_timeout_seconds: float = 600.0


class RAGSettings(BaseModel):
    """RAG pipeline configuration."""

    collection_name: str = "documents"

    allowed_extensions: list[DocumentExtensions] = Field(
        default_factory=lambda: list(DocumentExtensions)
    )

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50
    chunking_strategy: str = "recursive"
    enable_hybrid_search: bool = False
    enable_ocr: bool = False

    # Embeddings
    embeddings_config: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)

    # Parsers
    document_parser: DocumentParser = Field(default_factory=DocumentParser)
    pdf_parser: PdfParser = Field(default_factory=PdfParser)
    # Image description
    enable_image_description: bool = True
    image_description_model: str = ""

    # Sources
    gdrive_ingestion: bool = True
