"""
HTTP-level integration tests for the schema discovery endpoint.

Tests exercise: HTTP route → FastAPI Depends → ConnectorService (mocked) → Response.
The ConnectorService dependency is overridden with an AsyncMock to test API behavior
without real database connections or external data sources.

These tests validate:
- 200 success with correct response schema (tables, fields, request_id)
- 404 when data source not found
- 422 when data source type is unsupported
- 502 when external source connection or discovery fails
- 504 when operation times out
- request_id present in all responses
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.connectors.protocol import FieldInfo, SchemaInfo, TableSchema
from app.dependencies import get_connector_service
from app.errors.datasource_errors import (
    DataSourceConnectionError,
    DataSourceNotFoundError,
    SchemaDiscoveryError,
    TimeoutOperationError,
    UnsupportedDataSourceError,
)
from app.main import create_app


@pytest_asyncio.fixture
def mock_connector_service():
    """Provide an AsyncMock of ConnectorService for dependency override."""
    return AsyncMock()


@pytest_asyncio.fixture
def app(mock_connector_service):
    """Create a FastAPI app with ConnectorService overridden."""
    application = create_app()
    application.dependency_overrides[get_connector_service] = lambda: mock_connector_service
    return application


@pytest_asyncio.fixture
async def client(app):
    """Provide an httpx AsyncClient wired to the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# =============================================================================
# Schema Discovery — 200 Success
# =============================================================================


class TestSchemaDiscoverySuccess:
    """200 success path for schema discovery."""

    @pytest.mark.asyncio
    async def test_returns_200_with_tables_and_fields(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """Successful schema discovery returns tables with fields and request_id."""
        data_source_id = uuid4()
        mock_connector_service.discover_schema.return_value = SchemaInfo(
            tables=[
                TableSchema(
                    name="users",
                    fields=[
                        FieldInfo(name="id", field_type="integer", nullable=False),
                        FieldInfo(name="email", field_type="varchar", nullable=False),
                        FieldInfo(name="name", field_type="varchar", nullable=True),
                    ],
                ),
                TableSchema(
                    name="orders",
                    fields=[
                        FieldInfo(name="id", field_type="integer", nullable=False),
                        FieldInfo(name="user_id", field_type="integer", nullable=False),
                        FieldInfo(name="total", field_type="numeric", nullable=True),
                    ],
                ),
            ]
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/schema")

        assert response.status_code == 200
        data = response.json()
        assert "tables" in data
        assert "request_id" in data
        assert len(data["tables"]) == 2

        # Verify first table structure
        users_table = data["tables"][0]
        assert users_table["name"] == "users"
        assert len(users_table["fields"]) == 3
        assert users_table["fields"][0] == {
            "name": "id",
            "field_type": "integer",
            "nullable": False,
        }
        assert users_table["fields"][1] == {
            "name": "email",
            "field_type": "varchar",
            "nullable": False,
        }

        # Verify second table
        orders_table = data["tables"][1]
        assert orders_table["name"] == "orders"
        assert len(orders_table["fields"]) == 3

    @pytest.mark.asyncio
    async def test_returns_200_with_empty_tables(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """Schema discovery returns empty tables list for sources with no tables."""
        data_source_id = uuid4()
        mock_connector_service.discover_schema.return_value = SchemaInfo(tables=[])

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/schema")

        assert response.status_code == 200
        data = response.json()
        assert data["tables"] == []
        assert "request_id" in data


# =============================================================================
# Schema Discovery — 404 Not Found
# =============================================================================


class TestSchemaDiscoveryNotFound:
    """404 when data source does not exist."""

    @pytest.mark.asyncio
    async def test_returns_404_with_error_code(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        data_source_id = uuid4()
        mock_connector_service.discover_schema.side_effect = DataSourceNotFoundError(
            data_source_id=str(data_source_id)
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/schema")

        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "DATA_SOURCE_NOT_FOUND"
        assert "request_id" in data


# =============================================================================
# Schema Discovery — 422 Unsupported Source Type
# =============================================================================


class TestSchemaDiscoveryUnsupported:
    """422 when data source type is not supported."""

    @pytest.mark.asyncio
    async def test_returns_422_with_error_code(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        data_source_id = uuid4()
        mock_connector_service.discover_schema.side_effect = UnsupportedDataSourceError(
            requested_type="oracle",
            supported_types=["postgresql", "mongodb"],
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/schema")

        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "UNSUPPORTED_DATA_SOURCE"
        assert "request_id" in data


# =============================================================================
# Schema Discovery — 502 Connection / Discovery Error
# =============================================================================


class TestSchemaDiscoveryExternalError:
    """502 when external data source is unreachable or discovery fails."""

    @pytest.mark.asyncio
    async def test_returns_502_on_connection_error(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        data_source_id = uuid4()
        mock_connector_service.discover_schema.side_effect = DataSourceConnectionError(
            source_type="postgresql",
            message="Connection refused to host db.example.com:5432",
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/schema")

        assert response.status_code == 502
        data = response.json()
        assert data["error_code"] == "DATA_SOURCE_CONNECTION_ERROR"
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_returns_502_on_schema_discovery_error(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        data_source_id = uuid4()
        mock_connector_service.discover_schema.side_effect = SchemaDiscoveryError(
            source_type="mongodb",
            message="Failed to list collections: insufficient permissions",
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/schema")

        assert response.status_code == 502
        data = response.json()
        assert data["error_code"] == "SCHEMA_DISCOVERY_ERROR"
        assert "request_id" in data


# =============================================================================
# Schema Discovery — 504 Timeout
# =============================================================================


class TestSchemaDiscoveryTimeout:
    """504 when the operation exceeds the timeout budget."""

    @pytest.mark.asyncio
    async def test_returns_504_with_error_code(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        data_source_id = uuid4()
        mock_connector_service.discover_schema.side_effect = TimeoutOperationError(
            operation="discover_schema",
            timeout_seconds=30,
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/schema")

        assert response.status_code == 504
        data = response.json()
        assert data["error_code"] == "OPERATION_TIMEOUT"
        assert "request_id" in data


# =============================================================================
# Schema Discovery — request_id in All Responses
# =============================================================================


class TestSchemaDiscoveryRequestId:
    """request_id is present in all response scenarios."""

    @pytest.mark.asyncio
    async def test_request_id_in_success_response(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        data_source_id = uuid4()
        mock_connector_service.discover_schema.return_value = SchemaInfo(
            tables=[
                TableSchema(
                    name="products",
                    fields=[FieldInfo(name="id", field_type="integer", nullable=False)],
                )
            ]
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/schema")

        assert response.status_code == 200
        request_id = response.json()["request_id"]
        assert request_id is not None
        assert len(request_id) > 0

    @pytest.mark.asyncio
    async def test_request_id_in_error_responses(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """All error responses include request_id for traceability."""
        data_source_id = uuid4()

        # 404 error
        mock_connector_service.discover_schema.side_effect = DataSourceNotFoundError(
            data_source_id=str(data_source_id)
        )
        response = await client.get(f"/api/v1/data-sources/{data_source_id}/schema")
        assert "request_id" in response.json()

        # 502 connection error
        mock_connector_service.discover_schema.side_effect = DataSourceConnectionError(
            source_type="postgresql",
            message="Connection lost",
        )
        response = await client.get(f"/api/v1/data-sources/{data_source_id}/schema")
        assert "request_id" in response.json()

        # 502 discovery error
        mock_connector_service.discover_schema.side_effect = SchemaDiscoveryError(
            source_type="mongodb",
            message="Discovery failed",
        )
        response = await client.get(f"/api/v1/data-sources/{data_source_id}/schema")
        assert "request_id" in response.json()

        # 504 timeout error
        mock_connector_service.discover_schema.side_effect = TimeoutOperationError(
            operation="discover_schema",
            timeout_seconds=30,
        )
        response = await client.get(f"/api/v1/data-sources/{data_source_id}/schema")
        assert "request_id" in response.json()
