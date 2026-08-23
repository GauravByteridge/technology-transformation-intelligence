"""
File upload and inspection API route handlers.

Provides the unified file upload entry point for content-aware ingestion,
plus endpoints for inspecting file structure, regions, and datasets.
"""

import logging
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status

from app.constants import SYSTEM_USER_ID
from app.dependencies import get_dataset_service, get_ingestion_orchestrator
from app.documents.orchestrator import IngestionOrchestrator
from app.models.uploaded_file import UploadedFile
from app.repositories.file_repository import FileRepository
from app.schemas.dataset import (
    DataRegionResponse,
    DatasetResponse,
    FileUploadResponse,
)
from app.services.dataset_service import DatasetService

logger = logging.getLogger(__name__)

router = APIRouter()

# Upload constraints
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
SUPPORTED_EXTENSIONS = {"xlsx", "xls", "csv", "json", "pdf", "docx", "txt"}


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file for content-aware ingestion",
    responses={
        422: {"description": "Invalid file, empty file, or unsupported type"},
    },
)
async def upload_file(
    file: UploadFile,
    project_id: UUID | None = Form(None),
    service: IngestionOrchestrator = Depends(get_ingestion_orchestrator),
) -> FileUploadResponse:
    """Upload a file for content-aware ingestion processing.

    Validates the file, creates an UploadedFile record, saves to a temp
    location, and triggers content-aware processing via the orchestrator.
    """
    # Validation: file must be present with a filename
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is required",
        )

    # Validation: check file is not empty
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is empty",
        )

    # Validation: check file size
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File size exceeds maximum of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
        )

    # Validation: check supported file type
    file_extension = _extract_extension(file.filename)
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type: {file_extension}. "
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Save to temp file for processing
    suffix = f".{file_extension}" if file_extension else ""
    temp_dir = tempfile.mkdtemp(prefix="ingestion_")
    temp_path = Path(temp_dir) / f"upload{suffix}"
    temp_path.write_bytes(content)

    try:
        # Trigger content-aware processing
        result = await service.process_file(
            file_id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder — real ID from DB
            file_path=str(temp_path),
            file_name=file.filename,
            file_type=file_extension,
            file_size=len(content),
            project_id=project_id,
            uploaded_by=SYSTEM_USER_ID,
        )

        logger.info(
            "file_upload_processed",
            extra={
                "file_name": file.filename,
                "file_type": file_extension,
                "file_size": len(content),
                "status": result.get("status", "unknown"),
            },
        )

        return FileUploadResponse(
            file_id=UUID(result.get("file_id", "00000000-0000-0000-0000-000000000000")),
            file_name=file.filename,
            file_type=file_extension,
            processing_status=result.get("status", "UPLOADED"),
            datasets_created=result.get("datasets_created", []),
            documents_indexed=result.get("documents_indexed", 0),
        )
    finally:
        # Cleanup temp file
        try:
            temp_path.unlink(missing_ok=True)
            Path(temp_dir).rmdir()
        except OSError:
            pass


@router.get(
    "/{file_id}/structure",
    summary="Get file inspection structure",
    responses={
        404: {"description": "File not found"},
    },
)
async def get_file_structure(
    file_id: UUID,
    service: DatasetService = Depends(get_dataset_service),
) -> dict:
    """Return the file's inspection structure result including datasets and regions."""
    try:
        return await service.get_file_structure(file_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{file_id}/regions",
    response_model=list[DataRegionResponse],
    summary="Get detected regions for a file",
    responses={
        404: {"description": "File not found"},
    },
)
async def get_file_regions(
    file_id: UUID,
    service: DatasetService = Depends(get_dataset_service),
) -> list[dict]:
    """Return all detected regions with classifications for a file."""
    return await service.get_file_regions(file_id)


@router.get(
    "/{file_id}/datasets",
    response_model=list[DatasetResponse],
    summary="Get datasets extracted from a file",
)
async def get_file_datasets(
    file_id: UUID,
    service: DatasetService = Depends(get_dataset_service),
) -> list[dict]:
    """Return all detected datasets for a file."""
    return await service.list_datasets(file_id=file_id)


def _extract_extension(filename: str) -> str:
    """Extract and normalize the file extension from a filename."""
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()
