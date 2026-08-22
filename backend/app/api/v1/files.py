"""
File metadata API route handlers.

Thin route layer: validates input, delegates to FileService, returns response.
No business logic, no direct database access.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import get_file_service
from app.schemas.file import FileCreate, FileResponse, FileUpdate
from app.services.file_service import FileService

router = APIRouter()


@router.post(
    "",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a file record",
    responses={
        404: {"description": "Project or data source not found"},
        422: {"description": "Validation error"},
    },
)
async def create_file(
    payload: FileCreate,
    service: FileService = Depends(get_file_service),
) -> FileResponse:
    """Create a new file metadata record."""
    result = await service.create_file(
        project_id=payload.project_id,
        file_name=payload.file_name,
        file_type=payload.file_type,
        file_size=payload.file_size,
        data_source_id=payload.data_source_id,
    )
    return FileResponse(**result)


@router.get(
    "",
    response_model=list[FileResponse],
    summary="List files for a project",
)
async def list_files(
    project_id: UUID = Query(description="Filter files by project ID"),
    service: FileService = Depends(get_file_service),
) -> list[FileResponse]:
    """List all file records for the given project."""
    results = await service.list_by_project(project_id)
    return [FileResponse(**r) for r in results]


@router.get(
    "/{file_id}",
    response_model=FileResponse,
    summary="Get a file record",
    responses={
        404: {"description": "File not found"},
        422: {"description": "Invalid file ID format"},
    },
)
async def get_file(
    file_id: UUID,
    service: FileService = Depends(get_file_service),
) -> FileResponse:
    """Retrieve a single file record by ID."""
    result = await service.get_file(file_id)
    return FileResponse(**result)


@router.patch(
    "/{file_id}",
    response_model=FileResponse,
    summary="Update a file record",
    responses={
        404: {"description": "File not found"},
        422: {"description": "Validation error"},
    },
)
async def update_file(
    file_id: UUID,
    payload: FileUpdate,
    service: FileService = Depends(get_file_service),
) -> FileResponse:
    """Update file processing status."""
    updates = payload.model_dump(exclude_unset=True)
    result = await service.update_file(file_id, updates)
    return FileResponse(**result)


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file record",
    responses={404: {"description": "File not found"}},
)
async def delete_file(
    file_id: UUID,
    service: FileService = Depends(get_file_service),
) -> None:
    """Delete a file record by its UUID."""
    await service.delete_file(file_id)
