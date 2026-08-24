"""
Unit tests for connector_tools — query_connected_source tool.

Tests validate: read-only enforcement, row capping, error handling,
structured result format, and security (no credential leakage).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.ai.tools.connector_tools import create_query_connected_source, DEFAULT_ROW_LIMIT
from app.connectors.protocol import QueryResult
from app.errors.datasource_errors import QueryExecutionError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_SOURCE_ID = str(uuid4())


def _make_data_source(source_type: str = "postgresql", name: str = "Test DB"):
    """Create a mock DataSource with required attributes."""
    ds = MagicMock()
    ds.id = FAKE_SOURCE_ID
    ds.source_type = source_type
    ds.name = name
    ds.connection_config = {"host": "localhost", "password": "encrypted_secret"}
    return ds


def _make_query_result(row_count: int = 3, has_more: bool = False) -> QueryResult:
    """Create a QueryResult with sample data."""
    rows = [{"id": i, "value": f"row_{i}"} for i in range(row_count)]
    return QueryResult(
        columns=["id", "value"],
        rows=rows,
        row_count=row_count,
        source_type="postgresql",
        has_more_rows=has_more,
    )


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_encryptor():
    enc = MagicMock()
    enc.decrypt_config.return_value = {"host": "localhost", "password": "decrypted"}
    return enc


@pytest.fixture
def mock_registry():
    registry = MagicMock()
    return registry


@pytest.fixture
def tool(mock_repo, mock_encryptor, mock_registry):
    """Create the query_connected_source tool with mocked dependencies."""
    return create_query_connected_source(
        data_source_repository=mock_repo,
        credential_encryptor=mock_encryptor,
        connector_registry=mock_registry,
        row_limit=DEFAULT_ROW_LIMIT,
    )


# ---------------------------------------------------------------------------
# Validation Tests
# ---------------------------------------------------------------------------


class TestQueryValidation:
    """Tests for input validation before query execution."""

    @pytest.mark.asyncio
    async def test_rejects_invalid_uuid(self, tool):
        result = await tool(
            source_id="not-a-uuid",
            query_type="sql",
            query="SELECT 1",
        )
        assert result["error"] is True
        assert result["error_type"] == "validation_error"
        assert "UUID" in result["message"]

    @pytest.mark.asyncio
    async def test_rejects_invalid_query_type(self, tool):
        result = await tool(
            source_id=FAKE_SOURCE_ID,
            query_type="graphql",
            query="{ project { name } }",
        )
        assert result["error"] is True
        assert result["error_type"] == "validation_error"
        assert "query_type" in result["message"]

    @pytest.mark.asyncio
    async def test_rejects_non_string_sql_query(self, tool):
        result = await tool(
            source_id=FAKE_SOURCE_ID,
            query_type="sql",
            query=[{"$match": {}}],
        )
        assert result["error"] is True
        assert result["error_type"] == "validation_error"
        assert "SQL string" in result["message"]

    @pytest.mark.asyncio
    async def test_rejects_non_list_mongodb_query(self, tool):
        result = await tool(
            source_id=FAKE_SOURCE_ID,
            query_type="mongodb",
            query="db.collection.find({})",
        )
        assert result["error"] is True
        assert result["error_type"] == "validation_error"
        assert "list" in result["message"]


class TestReadOnlyEnforcement:
    """Tests that write operations are rejected for SQL queries."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("statement", [
        "INSERT INTO users (name) VALUES ('x')",
        "UPDATE users SET name='x' WHERE id=1",
        "DELETE FROM users WHERE id=1",
        "DROP TABLE users",
        "ALTER TABLE users ADD COLUMN age INT",
        "CREATE TABLE bad (id INT)",
        "TRUNCATE TABLE users",
    ])
    async def test_rejects_write_sql_statements(self, tool, statement):
        result = await tool(
            source_id=FAKE_SOURCE_ID,
            query_type="sql",
            query=statement,
        )
        assert result["error"] is True
        assert result["error_type"] == "query_validation_error"
        assert "read-only" in result["message"].lower() or "Prohibited" in result["message"]

    @pytest.mark.asyncio
    async def test_allows_select_sql(self, tool, mock_repo, mock_registry):
        mock_repo.get_data_source.return_value = _make_data_source()
        mock_connector = AsyncMock()
        mock_connector.execute_read.return_value = _make_query_result()
        mock_registry.resolve.return_value = mock_connector

        result = await tool(
            source_id=FAKE_SOURCE_ID,
            query_type="sql",
            query="SELECT budget FROM project_finance WHERE project_id = '123'",
        )
        assert "error" not in result
        assert result["row_count"] == 3


# ---------------------------------------------------------------------------
# Successful Execution Tests
# ---------------------------------------------------------------------------


class TestSuccessfulExecution:
    """Tests for successful query execution and response structure."""

    @pytest.mark.asyncio
    async def test_returns_structured_result_for_sql(self, tool, mock_repo, mock_encryptor, mock_registry):
        mock_repo.get_data_source.return_value = _make_data_source()
        mock_connector = AsyncMock()
        mock_connector.execute_read.return_value = _make_query_result(row_count=5)
        mock_registry.resolve.return_value = mock_connector

        result = await tool(
            source_id=FAKE_SOURCE_ID,
            query_type="sql",
            query="SELECT id, value FROM test_table",
        )

        assert result["columns"] == ["id", "value"]
        assert result["row_count"] == 5
        assert len(result["rows"]) == 5
        assert result["has_more_rows"] is False
        assert result["source_metadata"]["source_id"] == FAKE_SOURCE_ID
        assert result["source_metadata"]["source_type"] == "postgresql"
        assert result["source_metadata"]["source_name"] == "Test DB"
        assert result["source_metadata"]["object_name"] == "test_table"
        assert "duration_ms" in result

    @pytest.mark.asyncio
    async def test_returns_structured_result_for_mongodb(self, tool, mock_repo, mock_encryptor, mock_registry):
        ds = _make_data_source(source_type="mongodb", name="Mongo Risks")
        mock_repo.get_data_source.return_value = ds
        mock_connector = AsyncMock()
        mock_connector.execute_read.return_value = QueryResult(
            columns=["_id", "status", "count"],
            rows=[{"_id": "open", "status": "open", "count": 5}],
            row_count=1,
            source_type="mongodb",
            has_more_rows=False,
        )
        mock_registry.resolve.return_value = mock_connector

        pipeline = [{"$match": {"project_id": "abc"}}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        result = await tool(
            source_id=FAKE_SOURCE_ID,
            query_type="mongodb",
            query=pipeline,
        )

        assert result["columns"] == ["_id", "status", "count"]
        assert result["row_count"] == 1
        assert result["source_metadata"]["source_type"] == "mongodb"
        assert result["source_metadata"]["source_name"] == "Mongo Risks"
        assert result["source_metadata"]["object_name"] == "aggregation_pipeline"

    @pytest.mark.asyncio
    async def test_credentials_decrypted_before_connector_resolve(
        self, tool, mock_repo, mock_encryptor, mock_registry
    ):
        mock_repo.get_data_source.return_value = _make_data_source()
        mock_connector = AsyncMock()
        mock_connector.execute_read.return_value = _make_query_result()
        mock_registry.resolve.return_value = mock_connector

        await tool(
            source_id=FAKE_SOURCE_ID,
            query_type="sql",
            query="SELECT 1",
        )

        mock_encryptor.decrypt_config.assert_called_once()
        mock_registry.resolve.assert_called_once_with(
            source_type="postgresql",
            connection_config={"host": "localhost", "password": "decrypted"},
        )


# ---------------------------------------------------------------------------
# Row Cap Tests
# ---------------------------------------------------------------------------


class TestRowCap:
    """Tests for result row limit enforcement."""

    @pytest.mark.asyncio
    async def test_caps_rows_at_configured_limit(self, mock_repo, mock_encryptor, mock_registry):
        # Create tool with small row limit for testing
        small_limit = 5
        tool = create_query_connected_source(
            data_source_repository=mock_repo,
            credential_encryptor=mock_encryptor,
            connector_registry=mock_registry,
            row_limit=small_limit,
        )

        mock_repo.get_data_source.return_value = _make_data_source()
        mock_connector = AsyncMock()
        mock_connector.execute_read.return_value = _make_query_result(row_count=20)
        mock_registry.resolve.return_value = mock_connector

        result = await tool(
            source_id=FAKE_SOURCE_ID,
            query_type="sql",
            query="SELECT * FROM large_table",
        )

        assert result["row_count"] == small_limit
        assert len(result["rows"]) == small_limit
        assert result["has_more_rows"] is True

    @pytest.mark.asyncio
    async def test_preserves_has_more_from_connector(self, mock_repo, mock_encryptor, mock_registry):
        tool = create_query_connected_source(
            data_source_repository=mock_repo,
            credential_encryptor=mock_encryptor,
            connector_registry=mock_registry,
            row_limit=100,
        )

        mock_repo.get_data_source.return_value = _make_data_source()
        mock_connector = AsyncMock()
        # Connector says there are more rows, even though count < limit
        mock_connector.execute_read.return_value = _make_query_result(row_count=10, has_more=True)
        mock_registry.resolve.return_value = mock_connector

        result = await tool(
            source_id=FAKE_SOURCE_ID,
            query_type="sql",
            query="SELECT * FROM table",
        )

        assert result["has_more_rows"] is True


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for error conditions and security of error responses."""

    @pytest.mark.asyncio
    async def test_source_not_found_returns_error(self, tool, mock_repo):
        mock_repo.get_data_source.return_value = None

        result = await tool(
            source_id=FAKE_SOURCE_ID,
            query_type="sql",
            query="SELECT 1",
        )

        assert result["error"] is True
        assert result["error_type"] == "source_not_found"

    @pytest.mark.asyncio
    async def test_query_execution_error_does_not_leak_details(
        self, tool, mock_repo, mock_encryptor, mock_registry
    ):
        mock_repo.get_data_source.return_value = _make_data_source()
        mock_connector = AsyncMock()
        mock_connector.execute_read.side_effect = QueryExecutionError(
            source_type="postgresql",
            message="connection refused to host=secret.internal:5432",
        )
        mock_registry.resolve.return_value = mock_connector

        result = await tool(
            source_id=FAKE_SOURCE_ID,
            query_type="sql",
            query="SELECT 1",
        )

        assert result["error"] is True
        assert result["error_type"] == "query_execution_error"
        # Ensure the internal error details (host, port) are NOT exposed
        assert "secret.internal" not in result["message"]
        assert "5432" not in result["message"]

    @pytest.mark.asyncio
    async def test_unexpected_error_does_not_leak_credentials(
        self, tool, mock_repo, mock_encryptor, mock_registry
    ):
        mock_repo.get_data_source.return_value = _make_data_source()
        mock_connector = AsyncMock()
        mock_connector.execute_read.side_effect = RuntimeError(
            "password='super_secret' connection failed"
        )
        mock_registry.resolve.return_value = mock_connector

        result = await tool(
            source_id=FAKE_SOURCE_ID,
            query_type="sql",
            query="SELECT 1",
        )

        assert result["error"] is True
        assert result["error_type"] == "internal_error"
        assert "super_secret" not in result["message"]
        assert "password" not in result["message"]
