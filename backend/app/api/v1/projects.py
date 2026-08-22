"""
Project API route handlers.

Thin route layer: validates input, delegates to ProjectService, returns response.
No business logic, no direct database access.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies import get_project_service
from app.schemas.projects import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter()


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
    responses={422: {"description": "Validation error"}},
)
async def create_project(
    payload: ProjectCreate,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Create a new project."""
    return await service.create_project(payload)


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List all projects",
)
async def list_projects(
    service: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    """Retrieve all projects."""
    return await service.list_projects()


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
    """Retrieve a single project by its UUID."""
    return await service.get_project(project_id)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project",
    responses={
        404: {"description": "Project not found"},
        422: {"description": "Validation error"},
    },
)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Apply partial updates to a project."""
    updates = payload.model_dump(exclude_unset=True)
    return await service.update_project(project_id, updates)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
    responses={404: {"description": "Project not found"}},
)
async def delete_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> None:
    """Delete a project by its UUID."""
    await service.delete_project(project_id)
