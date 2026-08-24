"""
Discovery API route handlers.

Thin route layer: validates input, delegates to DiscoveryEngine, returns response.
No business logic, no direct database access.

Credentials are never exposed in responses — the DiscoveryEngine resolves
connector credentials server-side through the existing security layer.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_app_db_session, get_discovery_engine
from app.errors.datasource_errors import DataSourceNotFoundError
from app.repositories.data_source_repository import DataSourceRepository
from app.schemas.catalog import DiscoveryResultResponse
from app.services.discovery_engine import DiscoveryEngine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/{source_id}/discover",
    response_model=DiscoveryResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger schema discovery and semantic profiling",
    responses={
        404: {"description": "Data source not found"},
        422: {"description": "Invalid source ID format"},
    },
)
async def discover_source(
    source_id: UUID,
    request: Request,
    engine: DiscoveryEngine = Depends(get_discovery_engine),
    session: AsyncSession = Depends(get_app_db_session),
) -> DiscoveryResultResponse:
    """Trigger full schema discovery and semantic profiling for a data source.

    Introspects the connected source to discover tables/collections,
    fields, types, and relationships. Generates semantic metadata
    (business names, domain tags, query capabilities) and stores
    the results in the Enterprise Data Catalog.

    Never exposes connection credentials in the response.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Resolve data source — raises 404 if not found
    repository = DataSourceRepository(session)
    data_source = await repository.get_data_source(source_id)

    if data_source is None:
        raise DataSourceNotFoundError(data_source_id=str(source_id))

    logger.info(
        "discovery_triggered",
        extra={
            "source_id": str(source_id),
            "source_type": data_source.source_type,
            "request_id": request_id,
        },
    )

    result = await engine.discover_source(source_id, data_source)

    logger.info(
        "discovery_completed",
        extra={
            "source_id": str(source_id),
            "success": result.success,
            "objects_discovered": result.objects_discovered,
            "fields_discovered": result.fields_discovered,
            "duration_ms": result.duration_ms,
            "request_id": request_id,
        },
    )

    return DiscoveryResultResponse(
        source_id=str(result.source_id),
        success=result.success,
        objects_discovered=result.objects_discovered,
        fields_discovered=result.fields_discovered,
        relationships_discovered=result.relationships_discovered,
        project_fields_found=result.project_fields_found,
        duration_ms=result.duration_ms,
        # NOTE: result.error is already sanitized by DiscoveryEngine (credentials redacted)
        error=result.error,
        discovered_at=result.discovered_at,
    )
