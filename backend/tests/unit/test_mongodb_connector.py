"""Tests for the MongoDB connector."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError

from app.connectors.mongodb_connector import MongoDBConnector
from app.errors.datasource_errors import DataSourceConnectionError, QueryExecutionError, SchemaDiscoveryError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_CONFIG: dict[str, Any] = {
    "host": "localhost",
    "port": 27017,
    "database": "test_db",
    "username": "readonly_user",
    "password": "secret",
    "source_id": "src-mongo-001",
}

VALID_CONFIG_NO_AUTH: dict[str, Any] = {
    "host": "localhost",
    "port": 27017,
    "database": "test_db",
    "source_id": "src-mongo-002",
}


# ---------------------------------------------------------------------------
# Configuration validation tests
# ---------------------------------------------------------------------------


class TestMongoDBConnectorConfig:
    """Verify connection config validation."""

    def test_accepts_valid_config_with_auth(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)
        assert connector._config == VALID_CONFIG

    def test_accepts_valid_config_without_auth(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG_NO_AUTH)
        assert connector._config == VALID_CONFIG_NO_AUTH

    def test_raises_on_missing_host(self) -> None:
        config = {k: v for k, v in VALID_CONFIG.items() if k != "host"}
        with pytest.raises(DataSourceConnectionError) as exc_info:
            MongoDBConnector(config)
        assert "host" in exc_info.value.message

    def test_raises_on_missing_port(self) -> None:
        config = {k: v for k, v in VALID_CONFIG.items() if k != "port"}
        with pytest.raises(DataSourceConnectionError) as exc_info:
            MongoDBConnector(config)
        assert "port" in exc_info.value.message

    def test_raises_on_missing_database(self) -> None:
        config = {k: v for k, v in VALID_CONFIG.items() if k != "database"}
        with pytest.raises(DataSourceConnectionError) as exc_info:
            MongoDBConnector(config)
        assert "database" in exc_info.value.message

    def test_raises_on_missing_multiple_keys(self) -> None:
        config = {"source_id": "src-123"}
        with pytest.raises(DataSourceConnectionError) as exc_info:
            MongoDBConnector(config)
        error = exc_info.value
        assert error.source_type == "mongodb"
        assert "host" in error.message
        assert "port" in error.message
        assert "database" in error.message

    def test_error_includes_operation_context(self) -> None:
        config = {"source_id": "src-456"}
        with pytest.raises(DataSourceConnectionError) as exc_info:
            MongoDBConnector(config)
        assert "validate_config" in exc_info.value.detail
        assert "src-456" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Connection URI building tests
# ---------------------------------------------------------------------------


class TestMongoDBConnectorURI:
    """Verify connection URI construction."""

    def test_builds_uri_with_auth(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)
        uri = connector._build_connection_uri()
        assert uri == "mongodb://readonly_user:secret@localhost:27017"

    def test_builds_uri_without_auth(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG_NO_AUTH)
        uri = connector._build_connection_uri()
        assert uri == "mongodb://localhost:27017"


# ---------------------------------------------------------------------------
# test_connection tests
# ---------------------------------------------------------------------------


class TestMongoDBConnectorTestConnection:
    """Verify test_connection behavior with mocked Motor client."""

    @pytest.mark.asyncio
    async def test_successful_connection(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value={"ok": 1})

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.test_connection(timeout=5)

        assert result is True
        mock_db.command.assert_called_once_with("ping")
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_failure_raises_domain_error(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.test_connection()

        error = exc_info.value
        assert error.source_type == "mongodb"
        assert "Connection refused" in error.message
        assert "test_connection" in error.detail
        assert "src-mongo-001" in error.detail

    @pytest.mark.asyncio
    async def test_timeout_raises_domain_error(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(
            side_effect=TimeoutError("Connection timed out")
        )

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.test_connection(timeout=2)

        error = exc_info.value
        assert error.source_type == "mongodb"
        assert "timed out" in error.message

    @pytest.mark.asyncio
    async def test_client_closes_on_success(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value={"ok": 1})

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            await connector.test_connection()

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_closes_on_failure(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(side_effect=OSError("Network error"))

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError):
                await connector.test_connection()

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_timeout_to_motor_client(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value={"ok": 1})

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ) as mock_motor:
            await connector.test_connection(timeout=30)

        mock_motor.assert_called_once_with(
            "mongodb://readonly_user:secret@localhost:27017",
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
        )

    @pytest.mark.asyncio
    async def test_default_source_id_when_not_provided(self) -> None:
        config = {k: v for k, v in VALID_CONFIG.items() if k != "source_id"}
        connector = MongoDBConnector(config)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(side_effect=OSError("Connection refused"))

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.test_connection()

        assert "unknown" in exc_info.value.detail


# ---------------------------------------------------------------------------
# discover_metadata tests
# ---------------------------------------------------------------------------


class TestMongoDBConnectorDiscoverMetadata:
    """Verify discover_metadata behavior with mocked Motor client."""

    @pytest.mark.asyncio
    async def test_returns_source_metadata_on_success(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        server_info = {
            "version": "7.0.4",
            "gitVersion": "abc123",
            "modules": ["enterprise"],
            "maxBsonObjectSize": 16777216,
        }

        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value=server_info)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.discover_metadata()

        assert result.source_type == "mongodb"
        assert result.name == "test_db"
        assert result.version == "7.0.4"
        assert "gitVersion" in result.properties
        assert "modules" in result.properties

    @pytest.mark.asyncio
    async def test_filters_sensitive_properties(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        server_info = {
            "version": "7.0.4",
            "password": "should_be_removed",
            "token": "should_be_removed",
            "secret": "should_be_removed",
            "api_key": "should_be_removed",
            "private_key": "should_be_removed",
            "safe_key": "keep_this",
            "uri_with_creds": "mongodb://user:pass@host:27017",
        }

        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value=server_info)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.discover_metadata()

        assert "password" not in result.properties
        assert "token" not in result.properties
        assert "secret" not in result.properties
        assert "api_key" not in result.properties
        assert "private_key" not in result.properties
        assert "uri_with_creds" not in result.properties
        assert result.properties["safe_key"] == "keep_this"

    @pytest.mark.asyncio
    async def test_returns_empty_version_when_missing(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        server_info = {"modules": ["community"]}

        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value=server_info)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.discover_metadata()

        assert result.version == ""

    @pytest.mark.asyncio
    async def test_connection_failure_raises_connection_error(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(
            side_effect=ConnectionFailure("Connection refused")
        )

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.discover_metadata()

        error = exc_info.value
        assert error.source_type == "mongodb"
        assert "discover_metadata" in error.detail

    @pytest.mark.asyncio
    async def test_server_selection_timeout_raises_connection_error(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(
            side_effect=ServerSelectionTimeoutError("Timed out")
        )

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.discover_metadata()

        assert exc_info.value.source_type == "mongodb"

    @pytest.mark.asyncio
    async def test_operation_failure_raises_schema_discovery_error(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(
            side_effect=OperationFailure("not authorized on admin")
        )

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(SchemaDiscoveryError) as exc_info:
                await connector.discover_metadata()

        error = exc_info.value
        assert error.source_type == "mongodb"
        assert "discover_metadata" in error.detail

    @pytest.mark.asyncio
    async def test_client_closes_on_success(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value={"version": "7.0.4"})

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            await connector.discover_metadata()

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_closes_on_connection_failure(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(
            side_effect=ConnectionFailure("Connection refused")
        )

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError):
                await connector.discover_metadata()

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_closes_on_operation_failure(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(
            side_effect=OperationFailure("permission denied")
        )

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(SchemaDiscoveryError):
                await connector.discover_metadata()

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_sanitizes_credentials_in_error_message(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(
            side_effect=ConnectionFailure(
                "mongodb://user:supersecret@host:27017 connection refused"
            )
        )

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.discover_metadata()

        # Credentials should be sanitized out of the error message
        assert "supersecret" not in exc_info.value.message

    @pytest.mark.asyncio
    async def test_uses_configured_connection_timeout(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG, connection_timeout=15)

        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value={"version": "7.0.4"})

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ) as mock_motor:
            await connector.discover_metadata()

        mock_motor.assert_called_once_with(
            "mongodb://readonly_user:secret@localhost:27017",
            serverSelectionTimeoutMS=15000,
            connectTimeoutMS=15000,
        )


# ---------------------------------------------------------------------------
# _infer_field_type tests
# ---------------------------------------------------------------------------


class TestMongoDBConnectorInferFieldType:
    """Verify _infer_field_type deterministic BSON type inference."""

    def _make_connector(self) -> MongoDBConnector:
        return MongoDBConnector(VALID_CONFIG)

    def test_empty_list_returns_null(self) -> None:
        connector = self._make_connector()
        assert connector._infer_field_type([]) == "null"

    def test_all_strings_returns_string(self) -> None:
        connector = self._make_connector()
        assert connector._infer_field_type(["hello", "world", "foo"]) == "string"

    def test_all_ints_returns_int(self) -> None:
        connector = self._make_connector()
        assert connector._infer_field_type([1, 2, 3]) == "int"

    def test_all_floats_returns_double(self) -> None:
        connector = self._make_connector()
        assert connector._infer_field_type([1.0, 2.5, 3.14]) == "double"

    def test_all_bools_returns_bool(self) -> None:
        connector = self._make_connector()
        assert connector._infer_field_type([True, False, True]) == "bool"

    def test_bool_checked_before_int(self) -> None:
        """bool is a subclass of int in Python — must be checked first."""
        connector = self._make_connector()
        # A list of only booleans should return "bool", not "int"
        assert connector._infer_field_type([True, False]) == "bool"

    def test_mixed_bool_and_int_returns_mixed(self) -> None:
        """bool and int are distinct types for inference purposes."""
        connector = self._make_connector()
        assert connector._infer_field_type([True, 42]) == "mixed"

    def test_all_lists_returns_array(self) -> None:
        connector = self._make_connector()
        assert connector._infer_field_type([[1, 2], [3], []]) == "array"

    def test_all_dicts_returns_object(self) -> None:
        connector = self._make_connector()
        assert connector._infer_field_type([{"a": 1}, {"b": 2}]) == "object"

    def test_all_none_returns_null(self) -> None:
        connector = self._make_connector()
        assert connector._infer_field_type([None, None]) == "null"

    def test_all_objectid_returns_objectid(self) -> None:
        from bson import ObjectId

        connector = self._make_connector()
        assert connector._infer_field_type(
            [ObjectId(), ObjectId()]
        ) == "objectId"

    def test_all_datetime_returns_date(self) -> None:
        from datetime import datetime

        connector = self._make_connector()
        assert connector._infer_field_type(
            [datetime(2024, 1, 1), datetime(2024, 6, 15)]
        ) == "date"

    def test_all_decimal128_returns_decimal(self) -> None:
        from bson import Decimal128

        connector = self._make_connector()
        assert connector._infer_field_type(
            [Decimal128("1.23"), Decimal128("4.56")]
        ) == "decimal"

    def test_all_bytes_returns_binary(self) -> None:
        connector = self._make_connector()
        assert connector._infer_field_type([b"data", b"more"]) == "binary"

    def test_mixed_types_returns_mixed(self) -> None:
        connector = self._make_connector()
        assert connector._infer_field_type(["hello", 42, True]) == "mixed"

    def test_string_and_int_returns_mixed(self) -> None:
        connector = self._make_connector()
        assert connector._infer_field_type(["foo", 1]) == "mixed"

    def test_single_value_returns_its_type(self) -> None:
        connector = self._make_connector()
        assert connector._infer_field_type(["single"]) == "string"
        assert connector._infer_field_type([42]) == "int"
        assert connector._infer_field_type([None]) == "null"

    def test_unknown_type_falls_back_to_object(self) -> None:
        """Unknown types (not in the mapping) fall back to 'object'."""
        connector = self._make_connector()

        class CustomType:
            pass

        assert connector._infer_field_type([CustomType()]) == "object"

    def test_null_with_single_type_returns_mixed(self) -> None:
        """None values add 'null' to the type set, causing 'mixed' with other types."""
        connector = self._make_connector()
        assert connector._infer_field_type([None, "hello"]) == "mixed"


# ---------------------------------------------------------------------------
# execute_read tests
# ---------------------------------------------------------------------------


class TestMongoDBConnectorExecuteRead:
    """Verify execute_read behavior with mocked Motor client."""

    def _make_connector(self, **kwargs) -> MongoDBConnector:
        return MongoDBConnector(VALID_CONFIG, **kwargs)

    def _make_mock_cursor(self, documents: list[dict]) -> MagicMock:
        """Create a mock cursor that supports chaining find → sort → limit → to_list."""
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=documents)
        return mock_cursor

    @pytest.mark.asyncio
    async def test_rejects_non_dict_query(self) -> None:
        from app.errors.datasource_errors import QueryValidationError

        connector = self._make_connector()
        with pytest.raises(QueryValidationError) as exc_info:
            await connector.execute_read("SELECT * FROM users")
        assert "dictionary" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_validates_query_via_validate_query(self) -> None:
        from app.errors.datasource_errors import QueryValidationError

        connector = self._make_connector()
        # Missing "collection" key should trigger validation error
        with pytest.raises(QueryValidationError) as exc_info:
            await connector.execute_read({"filter": {"active": True}})
        assert "collection" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_successful_query_returns_query_result(self) -> None:
        connector = self._make_connector()
        documents = [
            {"_id": "abc123", "name": "Alice", "age": 30},
            {"_id": "def456", "name": "Bob", "age": 25},
        ]

        mock_cursor = self._make_mock_cursor(documents)
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.execute_read({"collection": "users"})

        assert result.source_type == "mongodb"
        assert result.row_count == 2
        assert result.columns == ["_id", "name", "age"]
        assert result.rows[0]["name"] == "Alice"
        assert result.rows[1]["name"] == "Bob"
        assert result.has_more_rows is False

    @pytest.mark.asyncio
    async def test_truncation_detection_with_more_rows(self) -> None:
        connector = self._make_connector(row_limit=2)
        # Return 3 documents (limit+1) to trigger truncation detection
        documents = [
            {"name": "Alice"},
            {"name": "Bob"},
            {"name": "Carol"},
        ]

        mock_cursor = self._make_mock_cursor(documents)
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.execute_read({"collection": "users"})

        assert result.has_more_rows is True
        assert result.row_count == 2
        assert len(result.rows) == 2

    @pytest.mark.asyncio
    async def test_user_limit_respected_when_less_than_row_limit(self) -> None:
        connector = self._make_connector(row_limit=1000)
        documents = [{"name": "Alice"}]

        mock_cursor = self._make_mock_cursor(documents)
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.execute_read({"collection": "users", "limit": 5})

        # Should fetch limit+1 = 6
        mock_cursor.limit.assert_called_once_with(6)

    @pytest.mark.asyncio
    async def test_row_limit_caps_user_limit(self) -> None:
        connector = self._make_connector(row_limit=10)
        documents = [{"name": "Alice"}]

        mock_cursor = self._make_mock_cursor(documents)
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.execute_read({"collection": "users", "limit": 9999})

        # Should cap at row_limit (10) + 1 = 11
        mock_cursor.limit.assert_called_once_with(11)

    @pytest.mark.asyncio
    async def test_sort_applied_to_cursor(self) -> None:
        connector = self._make_connector()
        documents = [{"name": "Alice"}]

        mock_cursor = self._make_mock_cursor(documents)
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            await connector.execute_read({
                "collection": "users",
                "sort": {"name": 1},
            })

        mock_cursor.sort.assert_called_once_with([("name", 1)])

    @pytest.mark.asyncio
    async def test_projection_passed_to_find(self) -> None:
        connector = self._make_connector()
        documents = [{"name": "Alice"}]

        mock_cursor = self._make_mock_cursor(documents)
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            await connector.execute_read({
                "collection": "users",
                "filter": {"active": True},
                "projection": {"name": 1, "_id": 0},
            })

        mock_collection.find.assert_called_once_with(
            {"active": True}, {"name": 1, "_id": 0}
        )

    @pytest.mark.asyncio
    async def test_serializes_objectid_to_string(self) -> None:
        from bson import ObjectId

        connector = self._make_connector()
        oid = ObjectId("507f1f77bcf86cd799439011")
        documents = [{"_id": oid, "name": "Alice"}]

        mock_cursor = self._make_mock_cursor(documents)
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.execute_read({"collection": "users"})

        assert result.rows[0]["_id"] == "507f1f77bcf86cd799439011"

    @pytest.mark.asyncio
    async def test_columns_derived_from_all_documents(self) -> None:
        connector = self._make_connector()
        documents = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "email": "bob@example.com"},
        ]

        mock_cursor = self._make_mock_cursor(documents)
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.execute_read({"collection": "users"})

        # Columns should include all keys from all documents
        assert "name" in result.columns
        assert "age" in result.columns
        assert "email" in result.columns

    @pytest.mark.asyncio
    async def test_empty_result_returns_no_columns(self) -> None:
        connector = self._make_connector()

        mock_cursor = self._make_mock_cursor([])
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.execute_read({"collection": "empty"})

        assert result.columns == []
        assert result.rows == []
        assert result.row_count == 0
        assert result.has_more_rows is False

    @pytest.mark.asyncio
    async def test_connection_failure_raises_connection_error(self) -> None:
        connector = self._make_connector()

        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(
            side_effect=ConnectionFailure("Connection refused")
        )
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.execute_read({"collection": "users"})

        error = exc_info.value
        assert error.source_type == "mongodb"
        assert "execute_read" in error.detail

    @pytest.mark.asyncio
    async def test_operation_failure_raises_query_execution_error(self) -> None:
        from app.errors.datasource_errors import QueryExecutionError

        connector = self._make_connector()

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(
            side_effect=OperationFailure("bad query syntax")
        )
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(QueryExecutionError) as exc_info:
                await connector.execute_read({"collection": "users"})

        error = exc_info.value
        assert error.source_type == "mongodb"
        assert "execute_read" in error.detail

    @pytest.mark.asyncio
    async def test_client_closed_on_success(self) -> None:
        connector = self._make_connector()

        mock_cursor = self._make_mock_cursor([{"name": "Alice"}])
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            await connector.execute_read({"collection": "users"})

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_closed_on_failure(self) -> None:
        connector = self._make_connector()

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(side_effect=OSError("Network error"))
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError):
                await connector.execute_read({"collection": "users"})

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_sanitizes_credentials_in_error_message(self) -> None:
        connector = self._make_connector()

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(
            side_effect=ConnectionFailure(
                "mongodb://user:supersecret@host:27017 connection failed"
            )
        )
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.execute_read({"collection": "users"})

        assert "supersecret" not in exc_info.value.message

    @pytest.mark.asyncio
    async def test_uses_configured_connection_timeout(self) -> None:
        connector = self._make_connector(connection_timeout=20)

        mock_cursor = self._make_mock_cursor([{"name": "Alice"}])
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ) as mock_motor:
            await connector.execute_read({"collection": "users"})

        mock_motor.assert_called_once_with(
            "mongodb://readonly_user:secret@localhost:27017",
            serverSelectionTimeoutMS=20000,
            connectTimeoutMS=20000,
        )


# ---------------------------------------------------------------------------
# discover_schema tests
# ---------------------------------------------------------------------------


class TestMongoDBConnectorDiscoverSchema:
    """Verify discover_schema behavior with mocked Motor client."""

    @pytest.mark.asyncio
    async def test_returns_schema_info_with_collections(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(
            return_value=[{"name": "Alice", "age": 30}]
        )

        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=MagicMock(limit=MagicMock(return_value=mock_cursor)))

        mock_db = MagicMock()
        mock_db.list_collection_names = AsyncMock(return_value=["users", "orders"])
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.discover_schema()

        assert len(result.tables) == 2
        assert result.tables[0].name == "orders"  # sorted
        assert result.tables[1].name == "users"

    @pytest.mark.asyncio
    async def test_excludes_system_collections(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[{"x": 1}])

        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=MagicMock(limit=MagicMock(return_value=mock_cursor)))

        mock_db = MagicMock()
        mock_db.list_collection_names = AsyncMock(
            return_value=["users", "system.profile", "system.js"]
        )
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.discover_schema()

        assert len(result.tables) == 1
        assert result.tables[0].name == "users"

    @pytest.mark.asyncio
    async def test_empty_collection_returns_empty_fields(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])

        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=MagicMock(limit=MagicMock(return_value=mock_cursor)))

        mock_db = MagicMock()
        mock_db.list_collection_names = AsyncMock(return_value=["empty_col"])
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await connector.discover_schema()

        assert len(result.tables) == 1
        assert result.tables[0].name == "empty_col"
        assert result.tables[0].fields == []

    @pytest.mark.asyncio
    async def test_connection_failure_raises_connection_error(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.list_collection_names = AsyncMock(
            side_effect=ConnectionFailure("Connection refused")
        )

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.discover_schema()

        error = exc_info.value
        assert error.source_type == "mongodb"
        assert "discover_schema" in error.detail

    @pytest.mark.asyncio
    async def test_operation_failure_raises_schema_discovery_error(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.list_collection_names = AsyncMock(
            side_effect=OperationFailure("not authorized")
        )

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(SchemaDiscoveryError) as exc_info:
                await connector.discover_schema()

        error = exc_info.value
        assert error.source_type == "mongodb"
        assert "discover_schema" in error.detail

    @pytest.mark.asyncio
    async def test_client_closed_on_success(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])

        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=MagicMock(limit=MagicMock(return_value=mock_cursor)))

        mock_db = MagicMock()
        mock_db.list_collection_names = AsyncMock(return_value=["col1"])
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            await connector.discover_schema()

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_closed_on_failure(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.list_collection_names = AsyncMock(
            side_effect=ConnectionFailure("fail")
        )

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError):
                await connector.discover_schema()

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_sanitizes_credentials_in_error_message(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)

        mock_db = MagicMock()
        mock_db.list_collection_names = AsyncMock(
            side_effect=ConnectionFailure(
                "mongodb://user:supersecret@host:27017 connection refused"
            )
        )

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.close = MagicMock()

        with patch(
            "app.connectors.mongodb_connector.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(DataSourceConnectionError) as exc_info:
                await connector.discover_schema()

        assert "supersecret" not in exc_info.value.message


# ---------------------------------------------------------------------------
# _expand_nested_fields nullable inference tests
# ---------------------------------------------------------------------------


class TestMongoDBConnectorNullableInference:
    """Verify nullable inference logic in _expand_nested_fields.

    Validates Requirement 5.7:
    - nullable=True when field is absent from at least one sampled document
    - nullable=False only when field is present in every sampled document
    """

    def _make_connector(self) -> MongoDBConnector:
        return MongoDBConnector(VALID_CONFIG)

    def test_field_present_in_all_documents_is_not_nullable(self) -> None:
        """Field present in every document → nullable=False."""
        connector = self._make_connector()
        documents = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
            {"name": "Carol", "age": 28},
        ]
        fields = connector._expand_nested_fields(documents, max_depth=5)
        field_map = {f.name: f for f in fields}

        assert field_map["name"].nullable is False
        assert field_map["age"].nullable is False

    def test_field_absent_from_one_document_is_nullable(self) -> None:
        """Field absent from at least one document → nullable=True."""
        connector = self._make_connector()
        documents = [
            {"name": "Alice", "age": 30, "email": "a@example.com"},
            {"name": "Bob", "age": 25},
            {"name": "Carol", "age": 28, "email": "c@example.com"},
        ]
        fields = connector._expand_nested_fields(documents, max_depth=5)
        field_map = {f.name: f for f in fields}

        # email is absent from the second document
        assert field_map["email"].nullable is True
        # name and age present in all
        assert field_map["name"].nullable is False
        assert field_map["age"].nullable is False

    def test_field_present_in_only_one_document_is_nullable(self) -> None:
        """Field present in only 1 of N documents → nullable=True."""
        connector = self._make_connector()
        documents = [
            {"name": "Alice"},
            {"name": "Bob"},
            {"name": "Carol", "rare_field": "value"},
        ]
        fields = connector._expand_nested_fields(documents, max_depth=5)
        field_map = {f.name: f for f in fields}

        assert field_map["rare_field"].nullable is True
        assert field_map["name"].nullable is False

    def test_single_document_all_fields_not_nullable(self) -> None:
        """With a single document, all present fields have nullable=False."""
        connector = self._make_connector()
        documents = [
            {"name": "Alice", "age": 30, "email": "a@example.com"},
        ]
        fields = connector._expand_nested_fields(documents, max_depth=5)
        field_map = {f.name: f for f in fields}

        assert field_map["name"].nullable is False
        assert field_map["age"].nullable is False
        assert field_map["email"].nullable is False

    def test_nested_field_nullable_when_parent_absent(self) -> None:
        """Nested dot-notation fields absent when parent object is absent → nullable=True."""
        connector = self._make_connector()
        documents = [
            {"name": "Alice", "address": {"city": "NYC", "zip": "10001"}},
            {"name": "Bob"},  # no address at all
            {"name": "Carol", "address": {"city": "LA", "zip": "90001"}},
        ]
        fields = connector._expand_nested_fields(documents, max_depth=5)
        field_map = {f.name: f for f in fields}

        # address.city and address.zip are absent from doc 2 (no parent object)
        assert field_map["address.city"].nullable is True
        assert field_map["address.zip"].nullable is True
        # name present in all
        assert field_map["name"].nullable is False

    def test_nested_field_nullable_when_key_missing_in_nested_object(self) -> None:
        """Nested field absent from sub-object in one doc → nullable=True."""
        connector = self._make_connector()
        documents = [
            {"address": {"city": "NYC", "zip": "10001"}},
            {"address": {"city": "LA"}},  # zip missing from this nested obj
        ]
        fields = connector._expand_nested_fields(documents, max_depth=5)
        field_map = {f.name: f for f in fields}

        # city present in all nested objects → not nullable
        assert field_map["address.city"].nullable is False
        # zip missing from doc 2's address → nullable
        assert field_map["address.zip"].nullable is True

    def test_empty_documents_list_returns_no_fields(self) -> None:
        """Empty document list produces no fields."""
        connector = self._make_connector()
        fields = connector._expand_nested_fields([], max_depth=5)
        assert fields == []


# ---------------------------------------------------------------------------
# _expand_nested_fields depth limit tests
# ---------------------------------------------------------------------------


class TestMongoDBConnectorExpandNestedFieldsDepthLimit:
    """Verify _expand_nested_fields stops expanding at max_depth.

    Validates Requirement 5.6:
    - Nested fields use dot notation up to max_nesting_depth
    - Fields beyond max_depth are NOT expanded and are represented as field_type "object"
    """

    def _make_connector(self) -> MongoDBConnector:
        return MongoDBConnector(VALID_CONFIG)

    def test_depth_within_limit_expands_nested_fields(self) -> None:
        """Nested dicts within max_depth are expanded with dot notation."""
        connector = self._make_connector()
        documents = [
            {"address": {"city": "NYC", "zip": "10001"}},
        ]
        fields = connector._expand_nested_fields(documents, max_depth=5)
        field_map = {f.name: f for f in fields}

        # Depth 1 dict is expanded at depth <= 5
        assert "address.city" in field_map
        assert "address.zip" in field_map
        assert field_map["address.city"].field_type == "string"
        assert field_map["address.zip"].field_type == "string"

    def test_depth_at_limit_stops_expansion(self) -> None:
        """Nested dicts at depth == max_depth are NOT expanded and type is 'object'."""
        connector = self._make_connector()
        # With max_depth=1, the top-level dict fields are at depth 1.
        # Any nested dict value at depth 1 should NOT be expanded further.
        documents = [
            {"address": {"city": "NYC", "zip": "10001"}},
        ]
        fields = connector._expand_nested_fields(documents, max_depth=1)
        field_map = {f.name: f for f in fields}

        # "address" should exist as type "object" (not expanded)
        assert "address" in field_map
        assert field_map["address"].field_type == "object"
        # Nested keys should NOT appear
        assert "address.city" not in field_map
        assert "address.zip" not in field_map

    def test_deeply_nested_beyond_max_depth_becomes_object(self) -> None:
        """Deeply nested structures beyond max_depth are represented as 'object'."""
        connector = self._make_connector()
        documents = [
            {
                "level1": {
                    "level2": {
                        "level3": {
                            "deep_value": "unreachable",
                        }
                    }
                }
            },
        ]
        # max_depth=2: level1 (depth 1) expanded (1 < 2),
        # level1.level2 at depth 2 is NOT expanded (2 < 2 is false) → "object"
        fields = connector._expand_nested_fields(documents, max_depth=2)
        field_map = {f.name: f for f in fields}

        # level1.level2 should be "object" (not expanded further)
        assert "level1.level2" in field_map
        assert field_map["level1.level2"].field_type == "object"
        # Deeper keys should NOT appear
        assert "level1.level2.level3" not in field_map
        assert "level1.level2.level3.deep_value" not in field_map

    def test_mixed_depths_partially_expanded(self) -> None:
        """Some fields expand while deeper ones stop at depth limit."""
        connector = self._make_connector()
        documents = [
            {
                "name": "Alice",
                "address": {
                    "city": "NYC",
                    "geo": {"lat": 40.7, "lng": -74.0},
                },
            },
        ]
        # max_depth=2: "address" expands (depth 1 < 2), "address.geo" at depth 2
        # should NOT expand further
        fields = connector._expand_nested_fields(documents, max_depth=2)
        field_map = {f.name: f for f in fields}

        assert field_map["name"].field_type == "string"
        assert "address.city" in field_map
        assert field_map["address.city"].field_type == "string"
        # geo at depth 2 → not expanded, becomes "object"
        assert "address.geo" in field_map
        assert field_map["address.geo"].field_type == "object"
        assert "address.geo.lat" not in field_map
        assert "address.geo.lng" not in field_map

    def test_array_at_any_depth_is_array_type(self) -> None:
        """Array fields at any depth are represented as 'array' without element inference."""
        connector = self._make_connector()
        documents = [
            {"tags": ["python", "mongodb"], "meta": {"scores": [90, 95]}},
        ]
        fields = connector._expand_nested_fields(documents, max_depth=5)
        field_map = {f.name: f for f in fields}

        assert field_map["tags"].field_type == "array"
        assert field_map["meta.scores"].field_type == "array"


# ---------------------------------------------------------------------------
# _validate_query tests
# ---------------------------------------------------------------------------


class TestMongoDBConnectorValidateQuery:
    """Verify _validate_query validates MongoDB query dicts against the allowlist."""

    def _make_connector(self) -> MongoDBConnector:
        return MongoDBConnector(VALID_CONFIG)

    def test_allowed_query_keys_class_attribute_defined(self) -> None:
        """_ALLOWED_QUERY_KEYS is a frozenset with the expected keys."""
        assert MongoDBConnector._ALLOWED_QUERY_KEYS == frozenset(
            {"collection", "filter", "projection", "limit", "sort"}
        )

    def test_valid_query_with_all_keys_passes(self) -> None:
        """Query with all permitted keys passes without raising."""
        connector = self._make_connector()
        query = {
            "collection": "users",
            "filter": {"active": True},
            "projection": {"name": 1, "_id": 0},
            "limit": 100,
            "sort": {"name": 1},
        }
        # Should not raise
        connector._validate_query(query)

    def test_valid_query_with_only_collection_passes(self) -> None:
        """Minimal valid query with only 'collection' passes."""
        connector = self._make_connector()
        connector._validate_query({"collection": "orders"})

    def test_rejects_non_dict_query(self) -> None:
        """Non-dict queries raise QueryValidationError."""
        from app.errors.datasource_errors import QueryValidationError

        connector = self._make_connector()

        with pytest.raises(QueryValidationError) as exc_info:
            connector._validate_query("SELECT * FROM users")
        assert exc_info.value.source_type == "mongodb"
        assert "dictionary" in exc_info.value.message

    def test_rejects_list_query(self) -> None:
        """List queries raise QueryValidationError."""
        from app.errors.datasource_errors import QueryValidationError

        connector = self._make_connector()

        with pytest.raises(QueryValidationError) as exc_info:
            connector._validate_query([{"collection": "users"}])
        assert "dictionary" in exc_info.value.message

    def test_rejects_none_query(self) -> None:
        """None queries raise QueryValidationError."""
        from app.errors.datasource_errors import QueryValidationError

        connector = self._make_connector()

        with pytest.raises(QueryValidationError):
            connector._validate_query(None)

    def test_rejects_missing_collection_key(self) -> None:
        """Query without 'collection' key raises QueryValidationError."""
        from app.errors.datasource_errors import QueryValidationError

        connector = self._make_connector()

        with pytest.raises(QueryValidationError) as exc_info:
            connector._validate_query({"filter": {"active": True}})
        assert exc_info.value.source_type == "mongodb"
        assert "collection" in exc_info.value.message

    def test_rejects_unsupported_keys(self) -> None:
        """Query with keys outside the allowlist raises QueryValidationError."""
        from app.errors.datasource_errors import QueryValidationError

        connector = self._make_connector()

        with pytest.raises(QueryValidationError) as exc_info:
            connector._validate_query({
                "collection": "users",
                "filter": {"active": True},
                "aggregate": [{"$group": {}}],
                "delete": True,
            })
        error = exc_info.value
        assert error.source_type == "mongodb"
        assert "aggregate" in error.message
        assert "delete" in error.message
        assert "Permitted keys" in error.message

    def test_rejects_non_dict_sort_value(self) -> None:
        """Query with non-dict sort value raises QueryValidationError."""
        from app.errors.datasource_errors import QueryValidationError

        connector = self._make_connector()

        with pytest.raises(QueryValidationError) as exc_info:
            connector._validate_query({
                "collection": "users",
                "sort": [("name", 1)],
            })
        assert "'sort' must be a dictionary" in exc_info.value.message

    def test_rejects_string_sort_value(self) -> None:
        """String sort value raises QueryValidationError."""
        from app.errors.datasource_errors import QueryValidationError

        connector = self._make_connector()

        with pytest.raises(QueryValidationError) as exc_info:
            connector._validate_query({
                "collection": "users",
                "sort": "name",
            })
        assert "'sort' must be a dictionary" in exc_info.value.message

    def test_accepts_valid_dict_sort(self) -> None:
        """Dict sort value passes validation."""
        connector = self._make_connector()
        connector._validate_query({
            "collection": "users",
            "sort": {"created_at": -1},
        })

    def test_error_lists_invalid_keys_sorted(self) -> None:
        """Error message lists invalid keys in sorted order."""
        from app.errors.datasource_errors import QueryValidationError

        connector = self._make_connector()

        with pytest.raises(QueryValidationError) as exc_info:
            connector._validate_query({
                "collection": "users",
                "zzz_bad": 1,
                "aaa_bad": 2,
            })
        # Keys should appear sorted in the error message
        msg = exc_info.value.message
        assert msg.index("aaa_bad") < msg.index("zzz_bad")

    def test_error_lists_permitted_keys_sorted(self) -> None:
        """Error message lists permitted keys in sorted order."""
        from app.errors.datasource_errors import QueryValidationError

        connector = self._make_connector()

        with pytest.raises(QueryValidationError) as exc_info:
            connector._validate_query({
                "collection": "users",
                "bad_key": 1,
            })
        msg = exc_info.value.message
        assert "Permitted keys" in msg
        assert "collection" in msg
        assert "filter" in msg


# ---------------------------------------------------------------------------
# _serialize_document and _serialize_value tests
# ---------------------------------------------------------------------------


class TestMongoDBConnectorSerializeDocument:
    """Verify _serialize_document converts BSON types to JSON-safe forms.

    Validates: Requirement 6.10 — ObjectId serialization to 24-char hex string,
    plus additional conversions for JSON serializability.
    """

    def _make_connector(self) -> MongoDBConnector:
        return MongoDBConnector(VALID_CONFIG)

    def test_objectid_serialized_to_24_char_hex_string(self) -> None:
        """ObjectId → 24-character hex string via str()."""
        from bson import ObjectId

        connector = self._make_connector()
        oid = ObjectId("507f1f77bcf86cd799439011")
        doc = {"_id": oid, "name": "Alice"}

        result = connector._serialize_document(doc)

        assert result["_id"] == "507f1f77bcf86cd799439011"
        assert len(result["_id"]) == 24
        assert result["name"] == "Alice"

    def test_datetime_serialized_to_iso8601(self) -> None:
        """datetime → ISO 8601 string via isoformat()."""
        from datetime import datetime

        connector = self._make_connector()
        dt = datetime(2024, 6, 15, 10, 30, 0)
        doc = {"created_at": dt}

        result = connector._serialize_document(doc)

        assert result["created_at"] == "2024-06-15T10:30:00"

    def test_decimal128_serialized_to_string(self) -> None:
        """Decimal128 → string via str()."""
        from bson import Decimal128

        connector = self._make_connector()
        dec = Decimal128("123.456")
        doc = {"amount": dec}

        result = connector._serialize_document(doc)

        assert result["amount"] == "123.456"

    def test_bytes_serialized_to_base64(self) -> None:
        """bytes → base64-encoded string."""
        import base64

        connector = self._make_connector()
        raw_bytes = b"hello world"
        doc = {"data": raw_bytes}

        result = connector._serialize_document(doc)

        expected = base64.b64encode(raw_bytes).decode("utf-8")
        assert result["data"] == expected

    def test_nested_dict_recursed(self) -> None:
        """Nested dicts have their values serialized recursively."""
        from bson import ObjectId

        connector = self._make_connector()
        oid = ObjectId("507f1f77bcf86cd799439011")
        doc = {"meta": {"ref_id": oid, "label": "test"}}

        result = connector._serialize_document(doc)

        assert result["meta"]["ref_id"] == "507f1f77bcf86cd799439011"
        assert result["meta"]["label"] == "test"

    def test_list_recursed(self) -> None:
        """Lists have each element serialized recursively."""
        from bson import ObjectId

        connector = self._make_connector()
        oid1 = ObjectId("507f1f77bcf86cd799439011")
        oid2 = ObjectId("507f1f77bcf86cd799439012")
        doc = {"ids": [oid1, oid2, "plain_string"]}

        result = connector._serialize_document(doc)

        assert result["ids"][0] == "507f1f77bcf86cd799439011"
        assert result["ids"][1] == "507f1f77bcf86cd799439012"
        assert result["ids"][2] == "plain_string"

    def test_other_types_passed_through(self) -> None:
        """Non-BSON types (str, int, float, bool, None) passed through unchanged."""
        connector = self._make_connector()
        doc = {
            "name": "Alice",
            "age": 30,
            "score": 9.5,
            "active": True,
            "deleted": None,
        }

        result = connector._serialize_document(doc)

        assert result == doc

    def test_mixed_document_with_all_bson_types(self) -> None:
        """Document containing all supported BSON types serialized correctly."""
        from bson import Decimal128, ObjectId
        from datetime import datetime
        import base64

        connector = self._make_connector()
        oid = ObjectId("507f1f77bcf86cd799439011")
        dt = datetime(2024, 1, 1, 12, 0, 0)
        dec = Decimal128("99.99")
        raw = b"\x00\x01\x02"

        doc = {
            "_id": oid,
            "created": dt,
            "price": dec,
            "binary_data": raw,
            "name": "Test",
            "count": 42,
        }

        result = connector._serialize_document(doc)

        assert result["_id"] == "507f1f77bcf86cd799439011"
        assert result["created"] == "2024-01-01T12:00:00"
        assert result["price"] == "99.99"
        assert result["binary_data"] == base64.b64encode(raw).decode("utf-8")
        assert result["name"] == "Test"
        assert result["count"] == 42

    def test_deeply_nested_structure(self) -> None:
        """Deeply nested structures with mixed types are recursed correctly."""
        from bson import ObjectId
        from datetime import datetime

        connector = self._make_connector()
        oid = ObjectId("507f1f77bcf86cd799439011")
        dt = datetime(2024, 3, 15, 8, 0, 0)

        doc = {
            "level1": {
                "level2": {
                    "id": oid,
                    "items": [{"timestamp": dt}, {"value": 123}],
                }
            }
        }

        result = connector._serialize_document(doc)

        assert result["level1"]["level2"]["id"] == "507f1f77bcf86cd799439011"
        assert result["level1"]["level2"]["items"][0]["timestamp"] == "2024-03-15T08:00:00"
        assert result["level1"]["level2"]["items"][1]["value"] == 123

    def test_empty_document(self) -> None:
        """Empty document returns empty dict."""
        connector = self._make_connector()
        assert connector._serialize_document({}) == {}

    def test_list_of_dicts_in_document(self) -> None:
        """List of dicts (sub-documents) serialized correctly."""
        from bson import ObjectId

        connector = self._make_connector()
        doc = {
            "items": [
                {"_id": ObjectId("507f1f77bcf86cd799439011"), "name": "A"},
                {"_id": ObjectId("507f1f77bcf86cd799439012"), "name": "B"},
            ]
        }

        result = connector._serialize_document(doc)

        assert result["items"][0]["_id"] == "507f1f77bcf86cd799439011"
        assert result["items"][0]["name"] == "A"
        assert result["items"][1]["_id"] == "507f1f77bcf86cd799439012"
        assert result["items"][1]["name"] == "B"
