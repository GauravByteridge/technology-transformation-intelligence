"""Tests for the PostgreSQL connector."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.connectors.postgres_connector import PostgresConnector
from app.errors.datasource_errors import DataSourceConnectionError


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
# Stub method tests
# ---------------------------------------------------------------------------


class TestPostgresConnectorStubs:
    """Verify stub methods raise NotImplementedError."""

    @pytest.mark.asyncio
    async def test_discover_metadata_raises_not_implemented(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        with pytest.raises(NotImplementedError, match="Phase 1"):
            await connector.discover_metadata()

    @pytest.mark.asyncio
    async def test_discover_schema_raises_not_implemented(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        with pytest.raises(NotImplementedError, match="Phase 1"):
            await connector.discover_schema()

    @pytest.mark.asyncio
    async def test_execute_read_raises_not_implemented(self) -> None:
        connector = PostgresConnector(VALID_CONFIG)
        with pytest.raises(NotImplementedError, match="Phase 1"):
            await connector.execute_read("SELECT * FROM users")
