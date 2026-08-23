"""
HTTP-level integration tests for the metadata discovery endpoint.

Tests exercise: HTTP route → FastAPI Depends → ConnectorService (mocked) → Response.
The ConnectorService dependency is overridden with an AsyncMock to test API behavior
without real database connections or external data sources.

These tests validate:
- 200 success with correct response schema
- 404 when data source not found
- 422 when data source type is unsupported
- 502 when external source connection fails
- 504 when operation times out
- request_id present in all responses
- No credentials leaked in response properties
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.connectors.protocol import SourceMetadata
from app.errors.datasource_errors import (
    DataSourceConnectionError,
    DataSourceNotFoundError,
    TimeoutOperationError,
    UnsupportedDataSourceError,
)


@pytest_asyncio.fixture
def mock_connector_service():
    """Provide an AsyncMock of ConnectorService for dependency override."""
    return AsyncMock()


@pytest_asyncio.fixture
def app(mock_connector_service):
    """Create a FastAPI app with ConnectorService overridden."""
    from app.dependencies import get_connector_service
    from app.main import create_app

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
# Metadata Discovery Tests
# =============================================================================


class TestMetadataDiscoverySuccess:
    """200 success path for metadata discovery."""

    @pytest.mark.asyncio
    async def test_returns_200_with_correct_schema(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """Successful metadata discovery returns source_type, name, version, properties, request_id."""
        data_source_id = uuid4()
        mock_connector_service.discover_metadata.return_value = SourceMetadata(
            source_type="postgresql",
            name="Production DB",
            version="15.2",
            properties={"max_connections": 100, "encoding": "UTF8"},
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/metadata")

        assert response.status_code == 200
        data = response.json()
        assert data["source_type"] == "postgresql"
        assert data["name"] == "Production DB"
        assert data["version"] == "15.2"
        assert data["properties"] == {"max_connections": 100, "encoding": "UTF8"}
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_no_credentials_in_response_properties(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """Response properties must not contain credential-like fields."""
        data_source_id = uuid4()
        # Simulate a connector that correctly strips credentials from properties
        mock_connector_service.discover_metadata.return_value = SourceMetadata(
            source_type="postgresql",
            name="Secure DB",
            version="14.1",
            properties={"host": "db.example.com", "port": 5432},
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/metadata")

        assert response.status_code == 200
        properties = response.json()["properties"]
        # Sensitive fields must not appear
        assert "password" not in properties
        assert "token" not in properties
        assert "api_key" not in properties
        assert "secret" not in properties


class TestMetadataDiscoveryNotFound:
    """404 when data source does not exist."""

    @pytest.mark.asyncio
    async def test_returns_404_with_error_code(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        data_source_id = uuid4()
        mock_connector_service.discover_metadata.side_effect = DataSourceNotFoundError(
            data_source_id=str(data_source_id)
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/metadata")

        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "DATA_SOURCE_NOT_FOUND"
        assert "request_id" in data


class TestMetadataDiscoveryUnsupported:
    """422 when data source type is not supported."""

    @pytest.mark.asyncio
    async def test_returns_422_with_error_code(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        data_source_id = uuid4()
        mock_connector_service.discover_metadata.side_effect = UnsupportedDataSourceError(
            requested_type="oracle",
            supported_types=["postgresql", "mongodb"],
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/metadata")

        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "UNSUPPORTED_DATA_SOURCE"
        assert "request_id" in data


class TestMetadataDiscoveryConnectionError:
    """502 when external data source is unreachable."""

    @pytest.mark.asyncio
    async def test_returns_502_with_error_code(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        data_source_id = uuid4()
        mock_connector_service.discover_metadata.side_effect = DataSourceConnectionError(
            source_type="postgresql",
            message="Connection refused to host db.example.com:5432",
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/metadata")

        assert response.status_code == 502
        data = response.json()
        assert data["error_code"] == "DATA_SOURCE_CONNECTION_ERROR"
        assert "request_id" in data


class TestMetadataDiscoveryTimeout:
    """504 when the operation exceeds the timeout budget."""

    @pytest.mark.asyncio
    async def test_returns_504_with_error_code(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        data_source_id = uuid4()
        mock_connector_service.discover_metadata.side_effect = TimeoutOperationError(
            operation="discover_metadata",
            timeout_seconds=30,
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/metadata")

        assert response.status_code == 504
        data = response.json()
        assert data["error_code"] == "OPERATION_TIMEOUT"
        assert "request_id" in data


class TestMetadataDiscoveryRequestId:
    """request_id is present in all response scenarios."""

    @pytest.mark.asyncio
    async def test_request_id_in_success_response(
        self, client: AsyncClient, mock_connector_service: AsyncMock
    ):
        data_source_id = uuid4()
        mock_connector_service.discover_metadata.return_value = SourceMetadata(
            source_type="mongodb",
            name="Analytics Cluster",
            version="7.0",
            properties={},
        )

        response = await client.get(f"/api/v1/data-sources/{data_source_id}/metadata")

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
        mock_connector_service.discover_metadata.side_effect = DataSourceNotFoundError(
            data_source_id=str(data_source_id)
        )
        response = await client.get(f"/api/v1/data-sources/{data_source_id}/metadata")
        assert "request_id" in response.json()

        # 502 error
        mock_connector_service.discover_metadata.side_effect = DataSourceConnectionError(
            source_type="postgresql",
            message="Connection lost",
        )
        response = await client.get(f"/api/v1/data-sources/{data_source_id}/metadata")
        assert "request_id" in response.json()

        # 504 error
        mock_connector_service.discover_metadata.side_effect = TimeoutOperationError(
            operation="discover_metadata",
            timeout_seconds=30,
        )
        response = await client.get(f"/api/v1/data-sources/{data_source_id}/metadata")
        assert "request_id" in response.json()
