"""
Project API route handlers.

Thin route layer: validates input, delegates to ProjectService, returns response.
No business logic, no direct database access.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import get_project_service
from app.schemas.project import ProjectResponse
from app.services.project_service import ProjectService

router = APIRouter()


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a project by ID",
    responses={
        404: {"description": "Project not found"},
        422: {"description": "Invalid project ID format"},
    },
)
async def get_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Retrieve a single project by its UUID.

    - Validates that project_id is a valid UUID (FastAPI/Pydantic handles this)
    - Delegates to ProjectService for business logic
    - Returns ProjectResponse on success
    - Raises ProjectNotFoundError (mapped to 404) if project does not exist
    """
    return await service.get_project(project_id)
