"""Tests for connector registry wiring in the composition root.

Verifies that:
- The ConnectorRegistry is pre-populated with both PostgreSQL and MongoDB connectors
- The registry resolves correct connector types for each source type
- Adding a future connector requires only registration (no changes to existing code)
"""

from __future__ import annotations

from typing import Any

import pytest

from app.connectors import ConnectorRegistry, MongoDBConnector, PostgresConnector
from app.dependencies import get_connector_registry, initialize_connector_registry


class TestConnectorWiring:
    """Verify composition root wires both connectors into the registry at startup."""

    def setup_method(self) -> None:
        """Reset registry state before each test."""
        import app.dependencies

        app.dependencies._connector_registry = None

    def test_registry_populated_after_initialization(self) -> None:
        """After initialize_connector_registry(), both types are registered."""
        initialize_connector_registry()
        registry = get_connector_registry()

        supported = registry.list_supported_types()
        assert "postgresql" in supported
        assert "mongodb" in supported

    def test_registry_resolves_postgres_connector(self) -> None:
        """Registry resolves 'postgresql' to a PostgresConnector instance."""
        initialize_connector_registry()
        registry = get_connector_registry()

        config = {
            "host": "localhost",
            "port": 5432,
            "database": "finance",
            "user": "readonly",
            "password": "secret",
        }
        connector = registry.resolve("postgresql", config)
        assert isinstance(connector, PostgresConnector)

    def test_registry_resolves_mongodb_connector(self) -> None:
        """Registry resolves 'mongodb' to a MongoDBConnector instance."""
        initialize_connector_registry()
        registry = get_connector_registry()

        config = {
            "host": "localhost",
            "port": 27017,
            "database": "resources",
        }
        connector = registry.resolve("mongodb", config)
        assert isinstance(connector, MongoDBConnector)

    def test_get_connector_registry_raises_before_initialization(self) -> None:
        """Calling get_connector_registry() before init raises RuntimeError."""
        with pytest.raises(RuntimeError, match="ConnectorRegistry not initialized"):
            get_connector_registry()

    def test_adding_future_connector_requires_only_registration(self) -> None:
        """Demonstrate that a new connector only needs registration — no other changes."""
        initialize_connector_registry()
        registry = get_connector_registry()

        # Simulate future connector addition
        class FakeSnowflakeConnector:
            def __init__(self, connection_config: dict[str, Any]) -> None:
                self.config = connection_config

            async def test_connection(self, timeout: int = 10) -> bool:
                return True

        # Only action needed: register it
        registry.register("snowflake", FakeSnowflakeConnector)  # type: ignore[arg-type]

        # Existing connectors still work
        assert "postgresql" in registry.list_supported_types()
        assert "mongodb" in registry.list_supported_types()
        # New connector works
        assert "snowflake" in registry.list_supported_types()
        connector = registry.resolve("snowflake", {"account": "test"})
        assert isinstance(connector, FakeSnowflakeConnector)
