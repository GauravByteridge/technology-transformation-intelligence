"""Tests for the PostgreSQL connector."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.connectors.postgres_connector import PostgresConnector
from app.errors.datasource_errors import (
    DataSourceConnectionError,
    QueryExecutionError,
    QueryValidationError,
    SchemaDiscoveryError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_CONFIG: dict[str, Any] = {
    "host": "localhost",
    "port": 5432,
    "database": "test_db",
    "user": "readonly_user",
    "password": "secret",
    "source_id": "src-123",
}


# ---------------------------------------------------------------------------
# Configuration validation tests
# ---------------------------------------------------------------------------


class TestPostgresConnectorConfig:
    """Verify connection config validation."""

    def test_accepts_valid_config(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        assert connector._config == VALID_CONFIG

    def test_accepts_custom_row_limit_and_connection_timeout(self) -> None:
        connector = PostgresConnector(VALID_CONFIG, row_limit=500, connection_timeout=30)
        assert connector._row_limit == 500
        assert connector._connection_timeout == 30

    def test_default_row_limit_is_1000(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        assert connector._row_limit == 1000

    def test_default_connection_timeout_is_10(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        assert connector._connection_timeout == 10

    def test_raises_value_error_when_row_limit_below_minimum(self) -> None:
        with pytest.raises(ValueError, match="row_limit must be between 1 and 100000"):
            PostgresConnector(VALID_CONFIG, row_limit=0)

    def test_raises_value_error_when_row_limit_above_maximum(self) -> None:
        with pytest.raises(ValueError, match="row_limit must be between 1 and 100000"):
            PostgresConnector(VALID_CONFIG, row_limit=100001)

    def test_raises_value_error_when_connection_timeout_below_minimum(self) -> None:
        with pytest.raises(ValueError, match="connection_timeout must be between 1 and 60"):
            PostgresConnector(VALID_CONFIG, connection_timeout=0)

    def test_raises_value_error_when_connection_timeout_above_maximum(self) -> None:
        with pytest.raises(ValueError, match="connection_timeout must be between 1 and 60"):
            PostgresConnector(VALID_CONFIG, connection_timeout=61)

    def test_accepts_boundary_values(self) -> None:
        c1 = PostgresConnector(VALID_CONFIG, row_limit=1, connection_timeout=1)
        assert c1._row_limit == 1
        assert c1._connection_timeout == 1

        c2 = PostgresConnector(VALID_CONFIG, row_limit=100000, connection_timeout=60)
        assert c2._row_limit == 100000
        assert c2._connection_timeout == 60

    def test_raises_on_missing_host(self) -> None:
        config = {k: v for k, v in VALID_CONFIG.items() if k != "host"}
        with pytest.raises(DataSourceConnectionError) as exc_info:
            PostgresConnector(config)
        assert "host" in exc_info.value.message

    def test_raises_on_missing_multiple_keys(self) -> None:
        config = {"source_id": "src-123"}
        with pytest.raises(DataSourceConnectionError) as exc_info:
            PostgresConnector(config)
        error = exc_info.value
        assert error.source_type == "postgresql"
        assert "host" in error.message
        assert "port" in error.message

    def test_raises_on_missing_password(self) -> None:
        config = {k: v for k, v in VALID_CONFIG.items() if k != "password"}
        with pytest.raises(DataSourceConnectionError) as exc_info:
            PostgresConnector(config)
        assert "password" in exc_info.value.message

    def test_error_includes_operation_context(self) -> None:
        config = {"source_id": "src-456"}
        with pytest.raises(DataSourceConnectionError) as exc_info:
            PostgresConnector(config)
        assert "validate_config" in exc_info.value.detail
        assert "src-456" in exc_info.value.detail


# ---------------------------------------------------------------------------
# test_connection tests
# ---------------------------------------------------------------------------


class TestPostgresConnectorTestConnection:
    """Verify test_connection behavior with mocked asyncpg."""

    @pytest.mark.asyncio
    async def test_successful_connection(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            result = await connector.test_connection(timeout=5)

        assert result is True
        mock_conn.fetchval.assert_called_once_with("SELECT 1")
        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_failure_raises_domain_error(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)

        with patch(
            "app.connectors.postgres_connector.asyncpg.connect",
            side_effect=OSError("Connection refused"),
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.test_connection()

        error = exc_info.value
        assert error.source_type == "postgresql"
        assert "Connection refused" in error.message
        assert "test_connection" in error.detail
        assert "src-123" in error.detail

    @pytest.mark.asyncio
    async def test_timeout_raises_domain_error(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)

        with patch(
            "app.connectors.postgres_connector.asyncpg.connect",
            side_effect=TimeoutError("Connection timed out"),
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.test_connection(timeout=2)

        error = exc_info.value
        assert error.source_type == "postgresql"
        assert "timed out" in error.message

    @pytest.mark.asyncio
    async def test_connection_closes_on_success(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            await connector.test_connection()

        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_timeout_to_asyncpg(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn) as mock_connect:
            await connector.test_connection(timeout=30)

        mock_connect.assert_called_once_with(
            host="localhost",
            port=5432,
            database="test_db",
            user="readonly_user",
            password="secret",
            timeout=30,
        )

    @pytest.mark.asyncio
    async def test_default_source_id_when_not_provided(self) -> None:
        config = {k: v for k, v in VALID_CONFIG.items() if k != "source_id"}
        connector = PostgresConnector(config)

        with patch(
            "app.connectors.postgres_connector.asyncpg.connect",
            side_effect=OSError("Connection refused"),
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.test_connection()

        assert "unknown" in exc_info.value.detail


# ---------------------------------------------------------------------------
# discover_metadata tests
# ---------------------------------------------------------------------------


class TestPostgresConnectorDiscoverMetadata:
    """Verify discover_metadata() behavior with mocked asyncpg."""

    @pytest.mark.asyncio
    async def test_returns_source_metadata_on_success(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(
            return_value="PostgreSQL 15.2 on x86_64-pc-linux-gnu"
        )
        mock_conn.fetch = AsyncMock(
            return_value=[
                {"name": "max_connections", "setting": "100"},
                {"name": "server_encoding", "setting": "UTF8"},
                {"name": "TimeZone", "setting": "UTC"},
                {"name": "shared_buffers", "setting": "128MB"},
            ]
        )
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            result = await connector.discover_metadata()

        assert result.source_type == "postgresql"
        assert result.name == "test_db"
        assert result.version == "PostgreSQL 15.2 on x86_64-pc-linux-gnu"
        assert result.properties == {
            "max_connections": "100",
            "server_encoding": "UTF8",
            "TimeZone": "UTC",
            "shared_buffers": "128MB",
        }

    @pytest.mark.asyncio
    async def test_filters_sensitive_properties(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="PostgreSQL 15.2")
        # Simulate a scenario where a sensitive key slips into results
        mock_conn.fetch = AsyncMock(
            return_value=[
                {"name": "max_connections", "setting": "100"},
                {"name": "password", "setting": "should_be_filtered"},
            ]
        )
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            result = await connector.discover_metadata()

        assert "password" not in result.properties
        assert "max_connections" in result.properties

    @pytest.mark.asyncio
    async def test_connection_closed_on_success(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="PostgreSQL 15.2")
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            await connector.discover_metadata()

        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_closed_on_connection_error(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=OSError("Network unreachable"))
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            with pytest.raises(DataSourceConnectionError):
                await connector.discover_metadata()

        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_failure_raises_connection_error(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)

        with patch(
            "app.connectors.postgres_connector.asyncpg.connect",
            side_effect=OSError("Connection refused"),
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.discover_metadata()

        error = exc_info.value
        assert error.source_type == "postgresql"
        assert "Connection refused" in error.message
        assert "discover_metadata" in error.detail

    @pytest.mark.asyncio
    async def test_timeout_raises_connection_error(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)

        with patch(
            "app.connectors.postgres_connector.asyncpg.connect",
            side_effect=TimeoutError("Connection timed out"),
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.discover_metadata()

        error = exc_info.value
        assert error.source_type == "postgresql"
        assert "timed out" in error.message

    @pytest.mark.asyncio
    async def test_postgres_error_raises_schema_discovery_error(self) -> None:
        import asyncpg

        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(
            side_effect=asyncpg.PostgresError("permission denied for relation pg_settings")
        )
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            with pytest.raises(SchemaDiscoveryError) as exc_info:
                await connector.discover_metadata()

        error = exc_info.value
        assert error.source_type == "postgresql"
        assert "permission denied" in error.message
        assert "discover_metadata" in error.detail
        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_sanitizes_credentials_in_connection_error(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)

        with patch(
            "app.connectors.postgres_connector.asyncpg.connect",
            side_effect=OSError(
                "could not connect: password=supersecret host=db.example.com"
            ),
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.discover_metadata()

        # Credentials should be redacted
        assert "supersecret" not in exc_info.value.message

    @pytest.mark.asyncio
    async def test_uses_connection_timeout(self) -> None:
        connector = PostgresConnector(VALID_CONFIG, connection_timeout=5)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="PostgreSQL 15.2")
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn) as mock_connect:
            await connector.discover_metadata()

        mock_connect.assert_called_once_with(
            host="localhost",
            port=5432,
            database="test_db",
            user="readonly_user",
            password="secret",
            timeout=5,
        )

    @pytest.mark.asyncio
    async def test_handles_none_version_string(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=None)
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            result = await connector.discover_metadata()

        assert result.version == ""


# ---------------------------------------------------------------------------
# Stub method tests
# ---------------------------------------------------------------------------


class TestPostgresConnectorDiscoverSchema:
    """Verify discover_schema() behavior with mocked asyncpg."""

    @pytest.mark.asyncio
    async def test_returns_schema_info_with_tables(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            side_effect=[
                # Table discovery result
                [
                    {"table_schema": "public", "table_name": "users"},
                    {"table_schema": "public", "table_name": "orders"},
                ],
                # Columns for public.users
                [
                    {"column_name": "id", "data_type": "integer", "is_nullable": "NO"},
                    {"column_name": "name", "data_type": "character varying", "is_nullable": "YES"},
                ],
                # Columns for public.orders
                [
                    {"column_name": "id", "data_type": "integer", "is_nullable": "NO"},
                    {"column_name": "user_id", "data_type": "integer", "is_nullable": "NO"},
                    {"column_name": "total", "data_type": "numeric", "is_nullable": "YES"},
                ],
            ]
        )
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            result = await connector.discover_schema()

        assert len(result.tables) == 2
        assert result.tables[0].name == "public.users"
        assert result.tables[1].name == "public.orders"
        assert len(result.tables[0].fields) == 2
        assert result.tables[0].fields[0].name == "id"
        assert result.tables[0].fields[0].field_type == "integer"
        assert result.tables[0].fields[0].nullable is False
        assert result.tables[0].fields[1].name == "name"
        assert result.tables[0].fields[1].nullable is True

    @pytest.mark.asyncio
    async def test_fields_sorted_by_ordinal_position(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            side_effect=[
                [{"table_schema": "public", "table_name": "items"}],
                # Columns returned already ordered by ordinal_position in the query
                [
                    {"column_name": "id", "data_type": "integer", "is_nullable": "NO"},
                    {"column_name": "created_at", "data_type": "timestamp", "is_nullable": "NO"},
                    {"column_name": "label", "data_type": "text", "is_nullable": "YES"},
                ],
            ]
        )
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            result = await connector.discover_schema()

        # Verify fields match the ordinal order returned by the query
        fields = result.tables[0].fields
        assert [f.name for f in fields] == ["id", "created_at", "label"]

        # Verify the column query uses ORDER BY ordinal_position
        column_call = mock_conn.fetch.call_args_list[1]
        column_query = column_call[0][0]
        assert "ordinal_position" in column_query

    @pytest.mark.asyncio
    async def test_excludes_system_schemas(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            result = await connector.discover_schema()

        # Verify the query excludes system schemas
        call_args = mock_conn.fetch.call_args_list[0]
        query = call_args[0][0]
        assert "pg_catalog" in query
        assert "information_schema" in query
        assert "pg_toast" in query
        assert result.tables == []

    @pytest.mark.asyncio
    async def test_schema_filter_applied_when_present(self) -> None:
        config = {**VALID_CONFIG, "schema": "analytics"}
        connector = PostgresConnector(config)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            side_effect=[
                [{"table_schema": "analytics", "table_name": "events"}],
                [{"column_name": "event_id", "data_type": "uuid", "is_nullable": "NO"}],
            ]
        )
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            result = await connector.discover_schema()

        # Verify parameterized query was used with the schema filter
        call_args = mock_conn.fetch.call_args_list[0]
        query = call_args[0][0]
        assert "$1" in query
        assert len(result.tables) == 1
        assert result.tables[0].name == "analytics.events"

    @pytest.mark.asyncio
    async def test_returns_empty_schema_for_nonexistent_schema(self) -> None:
        config = {**VALID_CONFIG, "schema": "nonexistent"}
        connector = PostgresConnector(config)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            result = await connector.discover_schema()

        assert result.tables == []

    @pytest.mark.asyncio
    async def test_connection_closed_on_success(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            await connector.discover_schema()

        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_closed_on_error(self) -> None:
        import asyncpg as _asyncpg

        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            side_effect=_asyncpg.PostgresError("permission denied")
        )
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            with pytest.raises(SchemaDiscoveryError):
                await connector.discover_schema()

        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_failure_raises_connection_error(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)

        with patch(
            "app.connectors.postgres_connector.asyncpg.connect",
            side_effect=OSError("Connection refused"),
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.discover_schema()

        error = exc_info.value
        assert error.source_type == "postgresql"
        assert "Connection refused" in error.message
        assert "discover_schema" in error.detail

    @pytest.mark.asyncio
    async def test_postgres_error_raises_schema_discovery_error(self) -> None:
        import asyncpg as _asyncpg

        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            side_effect=_asyncpg.PostgresError("relation does not exist")
        )
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            with pytest.raises(SchemaDiscoveryError) as exc_info:
                await connector.discover_schema()

        error = exc_info.value
        assert error.source_type == "postgresql"
        assert "relation does not exist" in error.message
        assert "discover_schema" in error.detail

    @pytest.mark.asyncio
    async def test_sanitizes_credentials_in_error_messages(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)

        with patch(
            "app.connectors.postgres_connector.asyncpg.connect",
            side_effect=OSError(
                "could not connect: password=supersecret host=db.example.com"
            ),
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.discover_schema()

        assert "supersecret" not in exc_info.value.message


# ---------------------------------------------------------------------------
# execute_read tests
# ---------------------------------------------------------------------------


class TestPostgresConnectorExecuteRead:
    """Verify execute_read behavior with defense-in-depth layers."""

    @pytest.mark.asyncio
    async def test_returns_query_result_on_success(self) -> None:
        connector = PostgresConnector(VALID_CONFIG, row_limit=100)
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        # Simulate asyncpg Records as dicts with .keys() support
        mock_row = {"id": 1, "name": "Alice"}
        mock_conn.fetch = AsyncMock(return_value=[mock_row])
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            result = await connector.execute_read("SELECT id, name FROM users")

        assert result.columns == ["id", "name"]
        assert result.rows == [{"id": 1, "name": "Alice"}]
        assert result.row_count == 1
        assert result.source_type == "postgresql"
        assert result.has_more_rows is False

    @pytest.mark.asyncio
    async def test_sets_transaction_read_only_before_query(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()

        call_order: list[str] = []
        mock_conn.execute.side_effect = lambda sql: call_order.append(f"execute:{sql}")
        mock_conn.fetch.side_effect = lambda sql: (call_order.append(f"fetch:{sql}"), [])[1]

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            await connector.execute_read("SELECT 1")

        assert call_order[0] == "execute:SET TRANSACTION READ ONLY"
        assert call_order[1] == "fetch:SELECT 1"

    @pytest.mark.asyncio
    async def test_rejects_prohibited_sql_before_connection(self) -> None:
        from app.errors.datasource_errors import QueryValidationError

        connector = PostgresConnector(VALID_CONFIG)

        with patch("app.connectors.postgres_connector.asyncpg.connect") as mock_connect:
            with pytest.raises(QueryValidationError) as exc_info:
                await connector.execute_read("DELETE FROM users")

        # Connection should never be established for prohibited SQL
        mock_connect.assert_not_called()
        assert "DELETE" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_rejects_empty_query(self) -> None:
        from app.errors.datasource_errors import QueryValidationError

        connector = PostgresConnector(VALID_CONFIG)

        with patch("app.connectors.postgres_connector.asyncpg.connect") as mock_connect:
            with pytest.raises(QueryValidationError):
                await connector.execute_read("   ")

        mock_connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_multi_statement_query(self) -> None:
        from app.errors.datasource_errors import QueryValidationError

        connector = PostgresConnector(VALID_CONFIG)

        with patch("app.connectors.postgres_connector.asyncpg.connect") as mock_connect:
            with pytest.raises(QueryValidationError):
                await connector.execute_read("SELECT 1; DROP TABLE users")

        mock_connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_row_limit_enforcement_with_has_more_rows(self) -> None:
        connector = PostgresConnector(VALID_CONFIG, row_limit=3)
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        # Return 4 rows (exceeds row_limit of 3)
        mock_rows = [
            {"id": 1, "val": "a"},
            {"id": 2, "val": "b"},
            {"id": 3, "val": "c"},
            {"id": 4, "val": "d"},
        ]
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            result = await connector.execute_read("SELECT id, val FROM data")

        assert result.has_more_rows is True
        assert result.row_count == 3
        assert len(result.rows) == 3
        assert result.rows[-1] == {"id": 3, "val": "c"}

    @pytest.mark.asyncio
    async def test_row_limit_exact_boundary_no_truncation(self) -> None:
        connector = PostgresConnector(VALID_CONFIG, row_limit=3)
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        # Return exactly row_limit rows — no truncation
        mock_rows = [
            {"id": 1, "val": "a"},
            {"id": 2, "val": "b"},
            {"id": 3, "val": "c"},
        ]
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            result = await connector.execute_read("SELECT id, val FROM data")

        assert result.has_more_rows is False
        assert result.row_count == 3

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_columns(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            result = await connector.execute_read("SELECT * FROM empty_table")

        assert result.columns == []
        assert result.rows == []
        assert result.row_count == 0
        assert result.has_more_rows is False

    @pytest.mark.asyncio
    async def test_read_only_violation_raises_query_execution_error(self) -> None:
        import asyncpg.exceptions

        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock(
            side_effect=asyncpg.exceptions.ReadOnlySQLTransactionError(
                "cannot execute DELETE in a read-only transaction"
            )
        )
        mock_conn.close = AsyncMock()

        from app.errors.datasource_errors import QueryExecutionError

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            with pytest.raises(QueryExecutionError) as exc_info:
                # Data-modifying CTE passes Layer 1 but blocked by Layer 2
                await connector.execute_read(
                    "WITH deleted AS (DELETE FROM users RETURNING *) SELECT * FROM deleted"
                )

        error = exc_info.value
        assert "write operation" in error.message
        assert "read-only transaction" in error.message
        assert "execute_read" in error.detail
        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_error_raises_datasource_connection_error(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)

        with patch(
            "app.connectors.postgres_connector.asyncpg.connect",
            side_effect=OSError("Connection refused"),
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.execute_read("SELECT 1")

        error = exc_info.value
        assert error.source_type == "postgresql"
        assert "Connection refused" in error.message
        assert "execute_read" in error.detail

    @pytest.mark.asyncio
    async def test_timeout_raises_datasource_connection_error(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)

        with patch(
            "app.connectors.postgres_connector.asyncpg.connect",
            side_effect=TimeoutError("Connection timed out"),
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.execute_read("SELECT 1")

        error = exc_info.value
        assert "timed out" in error.message

    @pytest.mark.asyncio
    async def test_generic_postgres_error_raises_query_execution_error(self) -> None:
        import asyncpg

        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock(
            side_effect=asyncpg.PostgresError("relation \"nonexistent\" does not exist")
        )
        mock_conn.close = AsyncMock()

        from app.errors.datasource_errors import QueryExecutionError

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            with pytest.raises(QueryExecutionError) as exc_info:
                await connector.execute_read("SELECT * FROM nonexistent")

        error = exc_info.value
        assert "nonexistent" in error.message
        assert "execute_read" in error.detail
        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_closed_in_finally_on_success(self) -> None:
        connector = PostgresConnector(VALID_CONFIG, row_limit=100)
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[{"id": 1}])
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            await connector.execute_read("SELECT id FROM users")

        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_closed_in_finally_on_failure(self) -> None:
        import asyncpg

        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock(
            side_effect=asyncpg.PostgresError("syntax error")
        )
        mock_conn.close = AsyncMock()

        from app.errors.datasource_errors import QueryExecutionError

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            with pytest.raises(QueryExecutionError):
                await connector.execute_read("SELECT bad syntax")

        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_sanitizes_credentials_in_error_messages(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)

        with patch(
            "app.connectors.postgres_connector.asyncpg.connect",
            side_effect=OSError(
                "could not connect password=supersecret to host"
            ),
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.execute_read("SELECT 1")

        # Credentials should be redacted by sanitize_message
        assert "supersecret" not in exc_info.value.message

    @pytest.mark.asyncio
    async def test_uses_connection_timeout(self) -> None:
        connector = PostgresConnector(VALID_CONFIG, connection_timeout=5)
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn) as mock_connect:
            await connector.execute_read("SELECT 1")

        mock_connect.assert_called_once_with(
            host="localhost",
            port=5432,
            database="test_db",
            user="readonly_user",
            password="secret",
            timeout=5,
        )

    # -----------------------------------------------------------------------
    # Scenario 1: Each prohibited statement raises QueryValidationError
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "prohibited_sql",
        [
            "INSERT INTO users (name) VALUES ('x')",
            "UPDATE users SET name = 'x'",
            "DELETE FROM users WHERE id = 1",
            "DROP TABLE users",
            "ALTER TABLE users ADD COLUMN age INT",
            "CREATE TABLE evil (id INT)",
            "TRUNCATE TABLE users",
            "GRANT SELECT ON users TO public",
            "REVOKE SELECT ON users FROM public",
        ],
        ids=[
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "ALTER",
            "CREATE",
            "TRUNCATE",
            "GRANT",
            "REVOKE",
        ],
    )
    async def test_rejects_each_prohibited_statement(
        self, prohibited_sql: str
    ) -> None:
        connector = PostgresConnector(VALID_CONFIG)

        with patch("app.connectors.postgres_connector.asyncpg.connect") as mock_connect:
            with pytest.raises(QueryValidationError):
                await connector.execute_read(prohibited_sql)

        mock_connect.assert_not_called()

    # -----------------------------------------------------------------------
    # Scenario 6: statement_timeout uses remaining budget
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_statement_timeout_set_using_remaining_budget(self) -> None:
        """Verify statement_timeout is set from the propagated timeout_budget,
        not an independent 30s timer."""
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()

        call_order: list[str] = []
        mock_conn.execute.side_effect = lambda sql: call_order.append(sql)
        mock_conn.fetch.side_effect = lambda sql: (call_order.append(f"fetch:{sql}"), [])[1]

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            await connector.execute_read("SELECT 1", timeout_budget=15.5)

        # Verify SET TRANSACTION READ ONLY comes first
        assert call_order[0] == "SET TRANSACTION READ ONLY"
        # Verify statement_timeout is set using the remaining budget (15500ms)
        assert call_order[1] == "SET statement_timeout = '15500ms'"
        # Verify query execution follows
        assert call_order[2] == "fetch:SELECT 1"

    @pytest.mark.asyncio
    async def test_statement_timeout_not_set_when_no_budget(self) -> None:
        """When timeout_budget is None, statement_timeout is not set."""
        connector = PostgresConnector(VALID_CONFIG)
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()

        call_order: list[str] = []
        mock_conn.execute.side_effect = lambda sql: call_order.append(sql)
        mock_conn.fetch.side_effect = lambda sql: (call_order.append(f"fetch:{sql}"), [])[1]

        with patch("app.connectors.postgres_connector.asyncpg.connect", return_value=mock_conn):
            await connector.execute_read("SELECT 1")

        # Only SET TRANSACTION READ ONLY and the query fetch
        assert call_order == ["SET TRANSACTION READ ONLY", "fetch:SELECT 1"]
