"""
Integration tests for the query execution endpoint (POST /api/v1/data-sources/{id}/query).

Uses FastAPI dependency overrides with a mocked ConnectorService to test
the full HTTP path without external database connections.

Scenarios covered:
1. 200 success with truncated=False
2. 200 success with truncated=True
3. 400 QueryValidationError
4. 404 DataSourceNotFoundError
5. 422 Pydantic validation (missing query field)
6. 502 QueryExecutionError / DataSourceConnectionError
7. 504 TimeoutOperationError
8. request_id present in all responses
9. No credentials leaked in error responses
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.connectors.protocol import QueryResult
from app.errors.datasource_errors import (
    DataSourceConnectionError,
    DataSourceNotFoundError,
    QueryExecutionError,
    QueryValidationError,
    TimeoutOperationError,
)
from app.services.connector_service import ConnectorService


FAKE_DATA_SOURCE_ID = str(uuid4())

# Sensitive values that must never appear in error responses
CREDENTIAL_MARKERS = ["password", "secret", "token", "api_key", "private_key"]


@pytest_asyncio.fixture
async def mock_connector_service():
    """Provide a mocked ConnectorService for dependency injection."""
    return AsyncMock(spec=ConnectorService)


@pytest_asyncio.fixture
async def async_client(mock_connector_service: AsyncMock):
    """
    Provide an httpx AsyncClient with ConnectorService dependency overridden.

    The mocked service is injected so tests can control execute_query behavior
    without hitting real databases.
    """
    from app.dependencies import get_connector_service
    from app.main import create_app

    app = create_app()

    async def override_get_connector_service():
        return mock_connector_service

    app.dependency_overrides[get_connector_service] = override_get_connector_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# =============================================================================
# 1. 200 Success — truncated=False
# =============================================================================


class TestQueryExecutionSuccess:
    """Tests for successful query execution responses."""

    @pytest.mark.asyncio
    async def test_execute_query_returns_200_with_results(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """Successful query returns 200 with columns, rows, and truncated=False."""
        query_result = QueryResult(
            columns=["id", "name", "amount"],
            rows=[
                {"id": 1, "name": "Project A", "amount": 1000},
                {"id": 2, "name": "Project B", "amount": 2000},
            ],
            row_count=2,
            source_type="postgresql",
            has_more_rows=False,
        )
        mock_connector_service.execute_query.return_value = (query_result, False)

        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={"query": "SELECT id, name, amount FROM projects"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["columns"] == ["id", "name", "amount"]
        assert data["row_count"] == 2
        assert len(data["rows"]) == 2
        assert data["source_type"] == "postgresql"
        assert data["truncated"] is False

    # =============================================================================
    # 2. 200 Success — truncated=True
    # =============================================================================

    @pytest.mark.asyncio
    async def test_execute_query_returns_200_with_truncated_true(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """When row cap is hit, truncated=True is returned in response."""
        query_result = QueryResult(
            columns=["id"],
            rows=[{"id": i} for i in range(100)],
            row_count=100,
            source_type="postgresql",
            has_more_rows=True,
        )
        mock_connector_service.execute_query.return_value = (query_result, True)

        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={"query": "SELECT id FROM large_table"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["truncated"] is True
        assert data["row_count"] == 100


# =============================================================================
# 3. 400 — QueryValidationError
# =============================================================================


class TestQueryValidationError:
    """Tests for query validation failures (400)."""

    @pytest.mark.asyncio
    async def test_invalid_query_type_returns_400(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """QueryValidationError from service layer maps to 400."""
        mock_connector_service.execute_query.side_effect = QueryValidationError(
            source_type="postgresql",
            message="PostgreSQL queries must be SQL strings",
        )

        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={"query": {"collection": "users"}},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "QUERY_VALIDATION_ERROR"
        assert "SQL strings" in data["message"]


# =============================================================================
# 4. 404 — DataSourceNotFoundError
# =============================================================================


class TestDataSourceNotFound:
    """Tests for missing data source (404)."""

    @pytest.mark.asyncio
    async def test_nonexistent_data_source_returns_404(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """DataSourceNotFoundError maps to 404."""
        missing_id = str(uuid4())
        mock_connector_service.execute_query.side_effect = DataSourceNotFoundError(
            data_source_id=missing_id,
        )

        response = await async_client.post(
            f"/api/v1/data-sources/{missing_id}/query",
            json={"query": "SELECT 1"},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "DATA_SOURCE_NOT_FOUND"


# =============================================================================
# 5. 422 — Pydantic Validation (missing query field)
# =============================================================================


class TestPydanticValidation:
    """Tests for request body validation failures (422)."""

    @pytest.mark.asyncio
    async def test_missing_query_field_returns_422(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """Request without required 'query' field returns 422."""
        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"
        assert data["field_errors"] is not None
        assert len(data["field_errors"]) > 0


# =============================================================================
# 6. 502 — QueryExecutionError / DataSourceConnectionError
# =============================================================================


class TestExternalSourceErrors:
    """Tests for external source failures (502)."""

    @pytest.mark.asyncio
    async def test_query_execution_error_returns_502(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """QueryExecutionError from connector maps to 502."""
        mock_connector_service.execute_query.side_effect = QueryExecutionError(
            source_type="postgresql",
            message="relation 'nonexistent' does not exist",
        )

        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={"query": "SELECT * FROM nonexistent"},
        )

        assert response.status_code == 502
        data = response.json()
        assert data["error_code"] == "QUERY_EXECUTION_ERROR"

    @pytest.mark.asyncio
    async def test_data_source_connection_error_returns_502(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """DataSourceConnectionError maps to 502."""
        mock_connector_service.execute_query.side_effect = DataSourceConnectionError(
            source_type="postgresql",
            message="Connection refused to host db.example.com:5432",
        )

        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={"query": "SELECT 1"},
        )

        assert response.status_code == 502
        data = response.json()
        assert data["error_code"] == "DATA_SOURCE_CONNECTION_ERROR"


# =============================================================================
# 7. 504 — TimeoutOperationError
# =============================================================================


class TestTimeoutError:
    """Tests for operation timeout (504)."""

    @pytest.mark.asyncio
    async def test_timeout_error_returns_504(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """TimeoutOperationError maps to 504."""
        mock_connector_service.execute_query.side_effect = TimeoutOperationError(
            operation="execute_query",
            timeout_seconds=30,
        )

        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={"query": "SELECT * FROM slow_query"},
        )

        assert response.status_code == 504
        data = response.json()
        assert data["error_code"] == "OPERATION_TIMEOUT"


# =============================================================================
# 8. request_id in All Responses
# =============================================================================


class TestRequestIdPresence:
    """Verify request_id is present in all response types."""

    @pytest.mark.asyncio
    async def test_request_id_in_success_response(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """200 response contains request_id."""
        query_result = QueryResult(
            columns=["x"],
            rows=[{"x": 1}],
            row_count=1,
            source_type="postgresql",
            has_more_rows=False,
        )
        mock_connector_service.execute_query.return_value = (query_result, False)

        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={"query": "SELECT 1 AS x"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert len(data["request_id"]) > 0

    @pytest.mark.asyncio
    async def test_request_id_in_error_response(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """Error responses (4xx/5xx) contain request_id."""
        mock_connector_service.execute_query.side_effect = DataSourceNotFoundError(
            data_source_id="missing-id",
        )

        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={"query": "SELECT 1"},
        )

        assert response.status_code == 404
        data = response.json()
        assert "request_id" in data
        assert len(data["request_id"]) > 0

    @pytest.mark.asyncio
    async def test_request_id_in_validation_error_response(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """422 validation error response contains request_id."""
        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={},
        )

        assert response.status_code == 422
        data = response.json()
        assert "request_id" in data
        assert len(data["request_id"]) > 0

    @pytest.mark.asyncio
    async def test_request_id_in_timeout_response(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """504 timeout response contains request_id."""
        mock_connector_service.execute_query.side_effect = TimeoutOperationError(
            operation="execute_query",
            timeout_seconds=30,
        )

        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={"query": "SELECT 1"},
        )

        assert response.status_code == 504
        data = response.json()
        assert "request_id" in data
        assert len(data["request_id"]) > 0


# =============================================================================
# 9. No Credentials in Error Responses
# =============================================================================


class TestNoCredentialsInErrors:
    """Verify that error responses never leak sensitive credentials."""

    @pytest.mark.asyncio
    async def test_connection_error_does_not_leak_credentials(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """502 error response body must not contain credential-like values."""
        mock_connector_service.execute_query.side_effect = DataSourceConnectionError(
            source_type="postgresql",
            message="Connection refused",
        )

        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={"query": "SELECT 1"},
        )

        assert response.status_code == 502
        response_text = response.text.lower()
        # Error response should not contain raw credential field values
        assert "supersecretpassword" not in response_text
        assert "my-api-key-123" not in response_text
        assert "connection_string" not in response_text

    @pytest.mark.asyncio
    async def test_timeout_error_does_not_leak_credentials(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """504 error response body must not contain credential-like values."""
        mock_connector_service.execute_query.side_effect = TimeoutOperationError(
            operation="execute_query",
            timeout_seconds=30,
        )

        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={"query": "SELECT 1"},
        )

        assert response.status_code == 504
        response_text = response.text.lower()
        assert "supersecretpassword" not in response_text
        assert "my-api-key-123" not in response_text

    @pytest.mark.asyncio
    async def test_validation_error_does_not_expose_internals(
        self, async_client: AsyncClient, mock_connector_service: AsyncMock
    ):
        """400 error response must not expose stack traces or internal paths."""
        mock_connector_service.execute_query.side_effect = QueryValidationError(
            source_type="postgresql",
            message="PostgreSQL queries must be SQL strings",
        )

        response = await async_client.post(
            f"/api/v1/data-sources/{FAKE_DATA_SOURCE_ID}/query",
            json={"query": {"bad": "type"}},
        )

        assert response.status_code == 400
        response_text = response.text
        # No stack traces or file paths in response
        assert "Traceback" not in response_text
        assert ".py" not in response_text
        assert "File \"" not in response_text
