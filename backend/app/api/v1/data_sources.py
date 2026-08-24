"""
Data source API route handlers.

Thin route layer: validates input, delegates to DataSourceService, returns response.
No business logic, no direct database access.

All responses use masked credentials — plaintext secrets are never exposed.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.connectors.sanitizer import sanitize_message
from app.dependencies import get_app_db_session, get_connector_service, get_data_source_service
from app.errors.datasource_errors import DataSourceNotFoundError
from app.repositories.data_source_repository import DataSourceRepository
from app.schemas.connector import (
    MetadataResponse,
    QueryExecutionRequest,
    QueryExecutionResponse,
    SchemaDiscoveryResponse,
    TableSchemaResponse,
    SchemaFieldResponse,
)
from app.schemas.data_source import (
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    TestConnectionResponse,
)
from app.services.connector_service import ConnectorService
from app.services.data_source_service import DataSourceService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=DataSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a data source",
    responses={422: {"description": "Validation error"}},
)
async def create_data_source(
    payload: DataSourceCreate,
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceResponse:
    """Create a new data source with encrypted credentials.

    Response contains masked credential indicators — never plaintext secrets.
    """
    result = await service.create_data_source(
        name=payload.name,
        source_type=payload.source_type,
        display_label=payload.display_label,
        connection_config=payload.connection_config,
    )
    return DataSourceResponse(**result)


@router.get(
    "",
    response_model=list[DataSourceResponse],
    summary="List all data sources",
)
async def list_data_sources(
    service: DataSourceService = Depends(get_data_source_service),
) -> list[DataSourceResponse]:
    """Retrieve all data sources with masked credentials."""
    results = await service.list_data_sources()
    return [DataSourceResponse(**r) for r in results]


@router.get(
    "/{data_source_id}",
    response_model=DataSourceResponse,
    summary="Get a data source by ID",
    responses={
        404: {"description": "Data source not found"},
        422: {"description": "Invalid data source ID format"},
    },
)
async def get_data_source(
    data_source_id: UUID,
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceResponse:
    """Retrieve a data source with masked credentials."""
    result = await service.get_data_source(data_source_id)
    return DataSourceResponse(**result)


@router.patch(
    "/{data_source_id}",
    response_model=DataSourceResponse,
    summary="Update a data source",
    responses={
        404: {"description": "Data source not found"},
        422: {"description": "Validation error"},
    },
)
async def update_data_source(
    data_source_id: UUID,
    payload: DataSourceUpdate,
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceResponse:
    """Update a data source. connection_config is a complete replacement when provided."""
    updates = payload.model_dump(exclude_unset=True)
    result = await service.update_data_source(data_source_id, updates)
    return DataSourceResponse(**result)


@router.delete(
    "/{data_source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a data source",
    responses={404: {"description": "Data source not found"}},
)
async def delete_data_source(
    data_source_id: UUID,
    service: DataSourceService = Depends(get_data_source_service),
) -> None:
    """Delete a data source by its UUID."""
    await service.delete_data_source(data_source_id)


@router.post(
    "/{data_source_id}/test-connection",
    response_model=TestConnectionResponse,
    summary="Test connection to a data source",
    responses={
        404: {"description": "Data source not found"},
        422: {"description": "Invalid data source ID format"},
    },
)
async def test_data_source_connection(
    data_source_id: UUID,
    request: Request,
    connector_service: ConnectorService = Depends(get_connector_service),
    session=Depends(get_app_db_session),
) -> TestConnectionResponse:
    """Test connectivity to a configured data source.

    Uses ConnectorService to resolve credentials from data_source_credentials
    table before testing. Never exposes raw credentials in the response.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Resolve connector through ConnectorService (handles credential retrieval)
    repository = DataSourceRepository(session)
    data_source = await repository.get_data_source(data_source_id)

    if data_source is None:
        raise DataSourceNotFoundError(data_source_id=str(data_source_id))

    try:
        connector, _ = await connector_service._resolve_connector(data_source_id)
        success = await connector.test_connection(timeout=10)
    except DataSourceNotFoundError:
        raise
    except Exception as exc:
        logger.warning(
            "connection_test_failed",
            extra={
                "source_id": str(data_source_id),
                "source_type": data_source.source_type,
                "error": sanitize_message(str(exc)),
                "request_id": request_id,
            },
        )
        success = False

    message = "Connection successful" if success else "Connection failed"

    logger.info(
        "connection_test_completed",
        extra={
            "source_id": str(data_source_id),
            "source_type": data_source.source_type,
            "success": success,
            "request_id": request_id,
        },
    )

    return TestConnectionResponse(
        success=success,
        source_type=data_source.source_type,
        source_name=data_source.name,
        message=message,
        request_id=request_id,
    )


@router.get(
    "/{data_source_id}/metadata",
    response_model=MetadataResponse,
    summary="Discover metadata for a data source",
    responses={
        404: {"description": "Data source not found"},
        502: {"description": "External source error"},
        504: {"description": "Operation timeout"},
    },
)
async def discover_metadata(
    data_source_id: UUID,
    request: Request,
    connector_service: ConnectorService = Depends(get_connector_service),
) -> MetadataResponse:
    """Discover metadata (version, properties) from an external data source."""
    request_id = getattr(request.state, "request_id", "unknown")
    result = await connector_service.discover_metadata(data_source_id)
    return MetadataResponse(
        source_type=result.source_type,
        name=result.name,
        version=result.version,
        properties=result.properties,
        request_id=request_id,
    )


@router.get(
    "/{data_source_id}/schema",
    response_model=SchemaDiscoveryResponse,
    summary="Discover schema for a data source",
    responses={
        404: {"description": "Data source not found"},
        502: {"description": "External source error"},
        504: {"description": "Operation timeout"},
    },
)
async def discover_schema(
    data_source_id: UUID,
    request: Request,
    connector_service: ConnectorService = Depends(get_connector_service),
) -> SchemaDiscoveryResponse:
    """Discover tables/collections and their fields from an external data source."""
    request_id = getattr(request.state, "request_id", "unknown")
    result = await connector_service.discover_schema(data_source_id)
    return SchemaDiscoveryResponse(
        tables=[
            TableSchemaResponse(
                name=t.name,
                fields=[
                    SchemaFieldResponse(
                        name=f.name,
                        field_type=f.field_type,
                        nullable=f.nullable,
                    )
                    for f in t.fields
                ],
            )
            for t in result.tables
        ],
        request_id=request_id,
    )


@router.post(
    "/{data_source_id}/query",
    response_model=QueryExecutionResponse,
    summary="Execute a read-only query",
    responses={
        400: {"description": "Invalid query"},
        404: {"description": "Data source not found"},
        502: {"description": "External source error"},
        504: {"description": "Operation timeout"},
    },
)
async def execute_query(
    data_source_id: UUID,
    payload: QueryExecutionRequest,
    request: Request,
    connector_service: ConnectorService = Depends(get_connector_service),
) -> QueryExecutionResponse:
    """Execute a read-only query against an external data source."""
    request_id = getattr(request.state, "request_id", "unknown")
    result, truncated = await connector_service.execute_query(data_source_id, payload.query)
    return QueryExecutionResponse(
        columns=result.columns,
        rows=result.rows,
        row_count=result.row_count,
        source_type=result.source_type,
        truncated=truncated,
        request_id=request_id,
    )
