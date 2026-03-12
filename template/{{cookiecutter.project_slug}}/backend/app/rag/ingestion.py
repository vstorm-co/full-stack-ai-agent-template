{%- if cookiecutter.enable_rag %}
import logging
from pathlib import Path

from app.rag.models import IngestionResult, IngestionStatus, Document
from app.rag.documents import DocumentProcessor
from app.rag.vectorstore import BaseVectorStore

logger = logging.getLogger(__name__)

class IngestionService:
    """
    Orchestrates the data flow: 
    File Path -> Parse/Chunk -> Embed/Store -> Query-Ready
    """

    def __init__(
        self, 
        processor: DocumentProcessor, 
        vector_store: BaseVectorStore
    ):
        self.processor = processor
        self.store = vector_store

    async def ingest_file(
        self, 
        filepath: Path, 
        collection_name: str
    ) -> IngestionResult:
        """
        Processes a file and pushes it into the vector database.
        """
        try:
            # Processing (Parsing + Chunking)
            # Returns a Document model with chunked_pages populated
            document: Document = await self.processor.process_file(filepath)
            
            # Storage (Embedding + Insertion)
            # MilvusVectorStore handles the embedding internally via EmbeddingService
            await self.store.insert_document(
                collection_name=collection_name, 
                document=document
            )

            return IngestionResult(
                status=IngestionStatus.DONE,
                document_id=document.id,
                message=f"Successfully ingested '{filepath.name}'"
            )

        except Exception as e:
            logger.error(f"Ingestion error for {filepath.name}: {str(e)}")
            return IngestionResult(
                status=IngestionStatus.ERROR,
                error_message=str(e),
                message=f"Failed to process {filepath.name}"
            )

    async def remove_document(self, collection_name: str, document_id: str) -> bool:
        """
        Wipes all traces of a document from the vector store.
        """
        try:
            await self.store.delete_document(
                collection_name=collection_name,
                document_id=document_id
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {str(e)}")
            return False
{%- endif %}