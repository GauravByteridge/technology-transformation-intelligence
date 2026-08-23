"""
Document API route handlers.

Provides semantic search, listing, detail, and deletion endpoints
for documents stored in the RAG pipeline.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_document_search_service, get_document_repository
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentSearchRequest, DocumentSearchResponse, DocumentResponse
from app.services.document_search_service import DocumentSearchService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/search",
    response_model=DocumentSearchResponse,
    summary="Semantic search over documents",
)
async def search_documents(
    payload: DocumentSearchRequest,
    service: DocumentSearchService = Depends(get_document_search_service),
) -> dict:
    """Search documents by natural language query using semantic similarity.

    Returns ranked document chunks matching the query within the specified project.
    """
    results = await service.search_documents(
        project_id=payload.project_id,
        query=payload.query,
        limit=payload.limit,
    )

    return {
        "results": results,
        "total_count": len(results),
        "query": payload.query,
        "project_id": str(payload.project_id),
    }


@router.get(
    "",
    response_model=list[DocumentResponse],
    summary="List documents for a project",
)
async def list_documents(
    project_id: UUID = Query(description="Project ID to list documents for"),
    repository: DocumentRepository = Depends(get_document_repository),
) -> list[dict]:
    """List all documents for the given project with chunk counts."""
    documents = await repository.list_by_project(project_id)

    return [
        {
            "id": str(doc.id),
            "project_id": str(doc.project_id),
            "file_name": doc.file_name,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "processing_status": doc.processing_status,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in documents
    ]


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    responses={404: {"description": "Document not found"}},
)
async def get_document(
    document_id: UUID,
    repository: DocumentRepository = Depends(get_document_repository),
) -> dict:
    """Retrieve a single document by ID."""
    document = await repository.get_document(document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    return {
        "id": str(document.id),
        "project_id": str(document.project_id),
        "file_name": document.file_name,
        "file_type": document.file_type,
        "file_size": document.file_size,
        "processing_status": document.processing_status,
        "created_at": document.created_at.isoformat() if document.created_at else None,
    }


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    responses={
        404: {"description": "Document not found"},
        409: {"description": "Document is currently processing"},
    },
)
async def delete_document(
    document_id: UUID,
    repository: DocumentRepository = Depends(get_document_repository),
) -> None:
    """Delete a document and cascade to its chunks and embeddings.

    Rejects deletion if the document is currently processing.
    """
    document = await repository.get_document(document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    if document.processing_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete document {document_id}: currently processing",
        )

    deleted = await repository.delete_document(document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )
