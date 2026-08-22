"""
Source connection API route handlers.

Manages project-to-data-source relationships. Routes are nested under
/projects/{project_id}/data-sources to reflect the resource hierarchy.

Delegates to DataSourceService — source connection methods live there.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies import get_data_source_service
from app.schemas.source_connection import SourceConnectionCreate, SourceConnectionResponse
from app.services.data_source_service import DataSourceService

router = APIRouter()


@router.post(
    "",
    response_model=SourceConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect a data source to a project",
    responses={
        404: {"description": "Project or data source not found"},
        409: {"description": "Source connection already exists"},
        422: {"description": "Validation error"},
    },
)
async def create_source_connection(
    project_id: UUID,
    payload: SourceConnectionCreate,
    service: DataSourceService = Depends(get_data_source_service),
) -> SourceConnectionResponse:
    """Link a data source to a project with a stated purpose."""
    result = await service.create_source_connection(
        project_id=project_id,
        data_source_id=payload.data_source_id,
        purpose=payload.purpose,
    )
    return SourceConnectionResponse(**result)


@router.get(
    "",
    response_model=list[SourceConnectionResponse],
    summary="List source connections for a project",
)
async def list_source_connections(
    project_id: UUID,
    service: DataSourceService = Depends(get_data_source_service),
) -> list[SourceConnectionResponse]:
    """List all data source connections for the given project."""
    results = await service.list_source_connections(project_id)
    return [SourceConnectionResponse(**r) for r in results]


@router.delete(
    "/{data_source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect a data source from a project",
    responses={404: {"description": "Source connection not found"}},
)
async def delete_source_connection(
    project_id: UUID,
    data_source_id: UUID,
    service: DataSourceService = Depends(get_data_source_service),
) -> None:
    """Remove the connection between a project and a data source."""
    await service.delete_source_connection(project_id, data_source_id)
