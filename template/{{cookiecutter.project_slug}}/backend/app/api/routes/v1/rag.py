{%- if cookiecutter.enable_rag %}
"""RAG API routes for document management and retrieval.

Coordinates between IngestionService for document processing and 
RetrievalService for querying vector data.
"""

from fastapi import APIRouter, Depends, File, UploadFile, status, BackgroundTasks, HTTPException
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
    RAGCollectionList,
    RAGCollectionInfo
)

router = APIRouter()

@router.post("/collections/{name}/upload", response_model=RAGUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    name: str,
    background_tasks: BackgroundTasks,
    ingestion_service: IngestionSvc,
    file: UploadFile = File(...),
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Upload and ingest a document into a collection."""
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


@router.get("/collections", response_model=RAGCollectionList)
async def list_collections(
    vector_store: VectorStoreSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """List all available collections in the vector store."""
    # Milvus client exposes list_collections
    names = await vector_store.client.list_collections()
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


@router.post("/search", response_model=RAGSearchResponse)
async def search_documents(
    request: RAGSearchRequest,
    retrieval_service: RetrievalSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Search for relevant document chunks."""
    results = await retrieval_service.retrieve(
        query=request.query,
        collection_name=request.collection_name,
        limit=request.limit,
        min_score=request.min_score,
        filter=request.filter or ""
    )
    return RAGSearchResponse(results=results)


@router.delete("/collections/{name}/documents/{source}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    name: str,
    source: str,
    ingestion_service: IngestionSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentUser,
{%- endif %}
):
    """Delete a specific document (by source name/ID) from a collection."""
    success = await ingestion_service.remove_document(name, source)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete document")
    return None # Correct for 204

{%- else %}
"""RAG routes - not configured."""
{%- endif %}