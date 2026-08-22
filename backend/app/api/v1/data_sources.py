"""
Data source API route handlers.

Thin route layer: validates input, delegates to connector registry, returns response.
No business logic, no direct database access.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.connectors.registry import ConnectorRegistry
from app.dependencies import get_app_db_session, get_connector_registry
from app.errors.datasource_errors import DataSourceNotFoundError
from app.repositories.data_source_repository import DataSourceRepository
from app.schemas.data_source import TestConnectionResponse

logger = logging.getLogger(__name__)

router = APIRouter()


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
    connector_registry: ConnectorRegistry = Depends(get_connector_registry),
    session=Depends(get_app_db_session),
) -> TestConnectionResponse:
    """
    Test connectivity to a configured data source.

    Resolves the connector from the registry using the source's type
    and connection config, then calls test_connection().

    - Validates data_source_id format (FastAPI handles UUID parsing)
    - Retrieves the data source configuration from the database
    - Instantiates the appropriate connector via registry
    - Calls test_connection() on the resolved connector
    - Returns structured result with request_id for traceability
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Retrieve data source config from the database
    repository = DataSourceRepository(session)
    data_source = await repository.get_data_source(data_source_id)

    if data_source is None:
        raise DataSourceNotFoundError(data_source_id=str(data_source_id))

    # Resolve connector from registry and test connection
    connector = connector_registry.resolve(
        source_type=data_source.source_type,
        connection_config=data_source.connection_config,
    )

    try:
        success = await connector.test_connection(timeout=10)
    except Exception as exc:
        logger.warning(
            "connection_test_failed",
            extra={
                "source_id": str(data_source_id),
                "source_type": data_source.source_type,
                "error": str(exc),
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
