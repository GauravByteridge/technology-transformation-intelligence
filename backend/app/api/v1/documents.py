"""
Document API route handlers.

Thin route layer: validates input, delegates to document pipeline, returns response.
No business logic, no direct database access.
"""

import logging

from fastapi import APIRouter, Depends, Request, UploadFile

from app.schemas.document import DocumentUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload a document for ingestion",
    responses={
        422: {"description": "Invalid file or missing required fields"},
    },
)
async def upload_document(
    request: Request,
    file: UploadFile | None = None,
) -> DocumentUploadResponse:
    """
    Accept a document for ingestion into the RAG pipeline.

    This endpoint proves the pipeline integration point. The full
    implementation (file validation, extraction, chunking, embedding)
    is delivered in Phase 1+.

    Returns a stub response confirming the route is wired correctly
    and the pipeline entry point is reachable.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    file_name = file.filename if file else "no file provided"

    logger.info(
        "document_upload_received",
        extra={
            "file_name": file_name,
            "request_id": request_id,
        },
    )

    return DocumentUploadResponse(
        message=f"Document upload accepted: {file_name}",
        status="accepted",
        request_id=request_id,
    )
