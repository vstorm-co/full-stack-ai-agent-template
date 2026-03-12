{%- if cookiecutter.enable_rag %}
"""RAG API routes for document management and retrieval.

Coordinates between IngestionService for document processing and 
RetrievalService for querying vector data.
"""

from fastapi import APIRouter, File, UploadFile, status, BackgroundTasks, HTTPException, Query
from pathlib import Path
import shutil
import uuid

from app.api.deps import IngestionSvc, RetrievalSvc, VectorStoreSvc
{%- if cookiecutter.use_jwt %}
from app.api.deps import CurrentUser
{%- endif %}

from app.schemas.rag import (
    RAGUploadResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGSearchResult,
    RAGCollectionList,
    RAGCollectionInfo,
    RAGDocumentList,
    RAGDocumentItem
)

router = APIRouter()

@router.post("/collections/{name}/upload", response_model=RAGUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    name: str,
    background_tasks: BackgroundTasks,
    ingestion_service: IngestionSvc,
    {%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
    {%- endif %}
    file: UploadFile = File(...),

):
    """Upload and ingest a document into a collection (async - for production use)."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[RAG Upload] Received upload request for collection: {name}, filename: {file.filename}")
    
    temp_dir = Path("/tmp/rag_uploads")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4()}_{file.filename}"
    
    with temp_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Helper function to ensure cleanup after background processing
    async def ingest_and_cleanup():
        try:
            await ingestion_service.ingest_file(filepath=temp_path, collection_name=name)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    background_tasks.add_task(ingest_and_cleanup)
    
    return RAGUploadResponse(message=f"Ingestion of {file.filename} started.")


@router.post("/collections/{name}/ingest", response_model=RAGUploadResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    name: str,
    ingestion_service: IngestionSvc,
    {%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
    {%- endif %}
    file: UploadFile = File(...),
):
    """Ingest a document synchronously (for immediate processing/testing).
    
    Unlike the /upload endpoint which processes in background, this endpoint
    waits for ingestion to complete and returns the document_id immediately.
    Use this for testing or when you need immediate confirmation of ingestion.
    """
    temp_dir = Path("/tmp/rag_uploads")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4()}_{file.filename}"
    
    with temp_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        result = await ingestion_service.ingest_file(filepath=temp_path, collection_name=name)
        return RAGUploadResponse(
            message=result.message,
            document_id=result.document_id
        )
    finally:
        if temp_path.exists():
            temp_path.unlink()


@router.get("/collections", response_model=RAGCollectionList)
async def list_collections(
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """List all available collections in the vector store."""
    names = await vector_store.list_collections()
    return RAGCollectionList(items=names)


@router.post("/collections/{name}", status_code=status.HTTP_201_CREATED)
async def create_collection(
    name: str,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Create and initialize a new collection."""
    await vector_store._ensure_collection(name)
    return {"message": f"Collection '{name}' created successfully."}


@router.delete("/collections/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def drop_collection(
    name: str,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Drop an entire collection and all its vectors."""
    await vector_store.delete_collection(name)


@router.get("/collections/{name}/info", response_model=RAGCollectionInfo)
async def get_collection_info(
    name: str,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Retrieve stats for a specific collection."""
    return await vector_store.get_collection_info(name)


@router.get("/collections/{name}/documents", response_model=RAGDocumentList)
async def list_documents(
    name: str,
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """List all documents in a specific collection.
    
    Returns unique documents with their metadata and chunk count.
    """
    documents = await vector_store.get_documents(name)
    return RAGDocumentList(
        items=[
            RAGDocumentItem(
                document_id=doc.document_id,
                filename=doc.filename,
                filesize=doc.filesize,
                filetype=doc.filetype,
                chunk_count=doc.chunk_count,
                additional_info=doc.additional_info,
            )
            for doc in documents
        ],
        total=len(documents)
    )


@router.post("/search", response_model=RAGSearchResponse)
async def search_documents(
    request: RAGSearchRequest,
    retrieval_service: RetrievalSvc,
    {%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
    {%- endif %}
    use_reranker: bool = Query(False, description="Whether to use reranking (if configured)"),
):
    """Search for relevant document chunks.
    
    Optionally uses reranking to improve result quality.
    Set use_reranker=true to enable reranking (if configured in the project).
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[RAG Search] Query: '{request.query}', use_reranker: {use_reranker}")
    
    results = await retrieval_service.retrieve(
        query=request.query,
        collection_name=request.collection_name,
        limit=request.limit,
        min_score=request.min_score,
        filter=request.filter or "",
        use_reranker=use_reranker,
    )
    api_results = [
        RAGSearchResult(**hit.model_dump()) 
        for hit in results
    ]
    return RAGSearchResponse(results=api_results)


@router.delete("/collections/{name}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    name: str,
    document_id: str,
    ingestion_service: IngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Delete a specific document by its ID from a collection."""
    success = await ingestion_service.remove_document(name, document_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete document")

{%- else %}
"""RAG routes - not configured."""
{%- endif %}