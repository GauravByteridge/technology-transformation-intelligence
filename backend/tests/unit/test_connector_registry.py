"""Tests for the connector registry and protocol types."""

from __future__ import annotations

from typing import Any

import pytest

from app.connectors import (
    ConnectorRegistry,
    DataSourceConnector,
    FieldInfo,
    QueryResult,
    SchemaInfo,
    SourceMetadata,
    TableSchema,
)
from app.errors.datasource_errors import UnsupportedDataSourceError


# ---------------------------------------------------------------------------
# Fake connector for testing — satisfies the DataSourceConnector protocol
# ---------------------------------------------------------------------------


class FakePostgresConnector:
    """Minimal connector implementation for registry tests."""

    def __init__(self, connection_config: dict[str, Any]) -> None:
        self.config = connection_config

    async def test_connection(self, timeout: int = 10) -> bool:
        return True

    async def discover_metadata(self) -> SourceMetadata:
        return SourceMetadata(source_type="postgresql", name="test-db")

    async def discover_schema(self) -> SchemaInfo:
        return SchemaInfo(tables=[])

    async def execute_read(self, query: str) -> QueryResult:
        return QueryResult(columns=[], rows=[], row_count=0, source_type="postgresql")


class FakeMongoConnector:
    """Minimal MongoDB connector implementation for registry tests."""

    def __init__(self, connection_config: dict[str, Any]) -> None:
        self.config = connection_config

    async def test_connection(self, timeout: int = 10) -> bool:
        return True

    async def discover_metadata(self) -> SourceMetadata:
        return SourceMetadata(source_type="mongodb", name="test-mongo")

    async def discover_schema(self) -> SchemaInfo:
        return SchemaInfo(tables=[])

    async def execute_read(self, query: dict[str, Any]) -> QueryResult:
        return QueryResult(columns=[], rows=[], row_count=0, source_type="mongodb")


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestConnectorRegistry:
    """Verify ConnectorRegistry behavior."""

    def test_register_and_list_supported_types(self) -> None:
        registry = ConnectorRegistry()
        registry.register("postgresql", FakePostgresConnector)
        registry.register("mongodb", FakeMongoConnector)

        supported = registry.list_supported_types()
        assert "postgresql" in supported
        assert "mongodb" in supported

    def test_resolve_returns_connector_instance(self) -> None:
        registry = ConnectorRegistry()
        registry.register("postgresql", FakePostgresConnector)

        config = {"host": "localhost", "port": 5432}
        connector = registry.resolve("postgresql", config)

        assert isinstance(connector, FakePostgresConnector)
        assert connector.config == config

    def test_resolve_unregistered_type_raises_unsupported_error(self) -> None:
        registry = ConnectorRegistry()
        registry.register("postgresql", FakePostgresConnector)

        with pytest.raises(UnsupportedDataSourceError) as exc_info:
            registry.resolve("oracle", {"host": "localhost"})

        error = exc_info.value
        assert error.requested_type == "oracle"
        assert "postgresql" in error.supported_types
        assert "oracle" in error.message

    def test_resolve_empty_registry_raises_with_empty_supported_list(self) -> None:
        registry = ConnectorRegistry()

        with pytest.raises(UnsupportedDataSourceError) as exc_info:
            registry.resolve("snowflake", {})

        error = exc_info.value
        assert error.requested_type == "snowflake"
        assert error.supported_types == []

    def test_list_supported_types_empty_by_default(self) -> None:
        registry = ConnectorRegistry()
        assert registry.list_supported_types() == []

    def test_resolve_passes_config_to_connector(self) -> None:
        registry = ConnectorRegistry()
        registry.register("mongodb", FakeMongoConnector)

        config = {"uri": "mongodb://localhost:27017", "database": "mydb"}
        connector = registry.resolve("mongodb", config)

        assert isinstance(connector, FakeMongoConnector)
        assert connector.config == config


# ---------------------------------------------------------------------------
# Protocol type tests
# ---------------------------------------------------------------------------


class TestProtocolTypes:
    """Verify supporting dataclasses work correctly."""

    def test_source_metadata_creation(self) -> None:
        metadata = SourceMetadata(
            source_type="postgresql",
            name="Finance DB",
            version="15.2",
            properties={"ssl": True},
        )
        assert metadata.source_type == "postgresql"
        assert metadata.name == "Finance DB"
        assert metadata.version == "15.2"
        assert metadata.properties == {"ssl": True}

    def test_schema_info_with_tables(self) -> None:
        schema = SchemaInfo(
            tables=[
                TableSchema(
                    name="budgets",
                    fields=[
                        FieldInfo(name="id", field_type="uuid", nullable=False),
                        FieldInfo(name="amount", field_type="decimal"),
                    ],
                )
            ]
        )
        assert len(schema.tables) == 1
        assert schema.tables[0].name == "budgets"
        assert len(schema.tables[0].fields) == 2
        assert schema.tables[0].fields[0].nullable is False
        assert schema.tables[0].fields[1].nullable is True

    def test_query_result_defaults(self) -> None:
        result = QueryResult()
        assert result.columns == []
        assert result.rows == []
        assert result.row_count == 0
        assert result.source_type == ""

    def test_field_info_defaults(self) -> None:
        field_info = FieldInfo(name="email", field_type="varchar")
        assert field_info.nullable is True
