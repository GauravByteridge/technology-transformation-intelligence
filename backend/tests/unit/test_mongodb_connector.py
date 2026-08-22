"""Tests for the MongoDB connector."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.connectors.mongodb_connector import MongoDBConnector
from app.errors.datasource_errors import DataSourceConnectionError


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
# Stub method tests
# ---------------------------------------------------------------------------


class TestMongoDBConnectorStubs:
    """Verify stub methods raise NotImplementedError."""

    @pytest.mark.asyncio
    async def test_discover_metadata_raises_not_implemented(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)
        with pytest.raises(NotImplementedError, match="Phase 1"):
            await connector.discover_metadata()

    @pytest.mark.asyncio
    async def test_discover_schema_raises_not_implemented(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)
        with pytest.raises(NotImplementedError, match="Phase 1"):
            await connector.discover_schema()

    @pytest.mark.asyncio
    async def test_execute_read_raises_not_implemented(self) -> None:
        connector = MongoDBConnector(VALID_CONFIG)
        query = {"collection": "resources", "filter": {"project": "alpha"}}
        with pytest.raises(NotImplementedError, match="Phase 1"):
            await connector.execute_read(query)
