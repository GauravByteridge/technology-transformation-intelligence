"""
Catalog API route handlers.

Thin route layer: validates input, delegates to CatalogService, returns response.
No business logic, no direct database access.

Credentials are never exposed in any catalog response — only technical
and semantic metadata from the Enterprise Data Catalog.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_catalog_service
from app.errors.catalog_errors import CatalogEntryNotFoundError
from app.schemas.catalog import CatalogEntryResponse
from app.services.catalog_service import CatalogService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/project/{project_id}",
    response_model=list[CatalogEntryResponse],
    summary="Get catalog entries for a project",
    responses={422: {"description": "Invalid project ID format"}},
)
async def get_catalog_for_project(
    project_id: UUID,
    service: CatalogService = Depends(get_catalog_service),
) -> list[CatalogEntryResponse]:
    """Retrieve all catalog entries mapped to a specific project.

    Returns technical and semantic metadata for discovered data objects.
    Never exposes connection credentials or sensitive configuration.
    """
    entries = await service.get_catalog_for_project(project_id)
    return [_map_entry_to_response(entry) for entry in entries]


@router.get(
    "/entries/{entry_id}",
    response_model=CatalogEntryResponse,
    summary="Get a specific catalog entry",
    responses={
        404: {"description": "Catalog entry not found"},
        422: {"description": "Invalid entry ID format"},
    },
)
async def get_catalog_entry(
    entry_id: UUID,
    service: CatalogService = Depends(get_catalog_service),
) -> CatalogEntryResponse:
    """Retrieve a single catalog entry by its ID.

    Returns technical and semantic metadata for the discovered data object.
    Never exposes connection credentials or sensitive configuration.
    """
    entry = await service.get_catalog_entry(entry_id)

    if entry is None:
        raise CatalogEntryNotFoundError(entry_id=str(entry_id))

    return _map_entry_to_response(entry)


@router.get(
    "/search",
    response_model=list[CatalogEntryResponse],
    summary="Search catalog by natural language",
    responses={422: {"description": "Validation error"}},
)
async def search_catalog(
    q: str = Query(
        ...,
        min_length=1,
        description="Natural-language search query",
    ),
    project_id: UUID | None = Query(
        default=None,
        description="Optional project ID to scope search results",
    ),
    service: CatalogService = Depends(get_catalog_service),
) -> list[CatalogEntryResponse]:
    """Search catalog entries by natural-language query.

    Matches against object names, semantic names, and descriptions.
    Optionally scoped to entries mapped to a specific project.
    Never exposes connection credentials or sensitive configuration.
    """
    entries = await service.search_catalog(query=q, project_id=project_id)
    return [_map_entry_to_response(entry) for entry in entries]


def _map_entry_to_response(entry) -> CatalogEntryResponse:
    """Map a CatalogEntry ORM model to its API response schema.

    Extracts source_type and source_name from the related data_source,
    ensuring no credentials leak into the response.
    """
    # Access related data_source for source_type and source_name
    source_type = entry.data_source.source_type if entry.data_source else "unknown"
    source_name = entry.data_source.name if entry.data_source else "unknown"

    return CatalogEntryResponse(
        entry_id=str(entry.id),
        source_id=str(entry.source_id),
        source_type=source_type,
        source_name=source_name,
        database_name=entry.database_name,
        schema_name=entry.schema_name,
        object_name=entry.object_name,
        object_type=entry.object_type,
        fields=entry.fields or [],
        primary_keys=entry.primary_keys or [],
        foreign_keys=entry.foreign_keys or [],
        indexes=entry.indexes or [],
        semantic_name=entry.semantic_name,
        semantic_description=entry.semantic_description,
        domain_tags=entry.domain_tags or [],
        query_capabilities=entry.query_capabilities or [],
        suggested_queries=entry.suggested_queries or [],
        confidence=entry.confidence,
        project_fields=entry.project_fields or [],
        version=entry.version,
        discovered_at=entry.discovered_at,
    )
