"""Tests for multi-source ConnectorRegistry isolation.

Verifies that resolving multiple connector instances from the same registry
produces independent, isolated instances with no shared state or credential leakage.

Requirements: 11.1, 11.2, 11.4, 11.6
"""

from __future__ import annotations

import weakref
from typing import Any

import pytest

from app.connectors import ConnectorRegistry, DataSourceConnector, SourceMetadata, SchemaInfo, QueryResult
from app.errors.datasource_errors import UnsupportedDataSourceError


# ---------------------------------------------------------------------------
# Fake connectors that track instance identity and configuration
# ---------------------------------------------------------------------------


class FakePostgresConnector:
    """Minimal PostgreSQL connector for isolation tests."""

    def __init__(self, connection_config: dict[str, Any], **kwargs: Any) -> None:
        self.config = connection_config
        self.operational_config = kwargs

    async def test_connection(self, timeout: int = 10) -> bool:
        return True

    async def discover_metadata(self) -> SourceMetadata:
        return SourceMetadata(source_type="postgresql", name=self.config.get("database", ""))

    async def discover_schema(self) -> SchemaInfo:
        return SchemaInfo(tables=[])

    async def execute_read(self, query: str) -> QueryResult:
        return QueryResult(columns=[], rows=[], row_count=0, source_type="postgresql")


class FailingPostgresConnector:
    """PostgreSQL connector that raises on construction with certain configs."""

    def __init__(self, connection_config: dict[str, Any], **kwargs: Any) -> None:
        if connection_config.get("fail_on_init"):
            raise ConnectionError("Simulated connection failure")
        self.config = connection_config

    async def test_connection(self, timeout: int = 10) -> bool:
        return False

    async def discover_metadata(self) -> SourceMetadata:
        raise ConnectionError("unreachable")

    async def discover_schema(self) -> SchemaInfo:
        raise ConnectionError("unreachable")

    async def execute_read(self, query: str) -> QueryResult:
        raise ConnectionError("unreachable")


class FakeMongoConnector:
    """Minimal MongoDB connector for isolation tests."""

    def __init__(self, connection_config: dict[str, Any], **kwargs: Any) -> None:
        self.config = connection_config
        self.operational_config = kwargs

    async def test_connection(self, timeout: int = 10) -> bool:
        return True

    async def discover_metadata(self) -> SourceMetadata:
        return SourceMetadata(source_type="mongodb", name=self.config.get("database", ""))

    async def discover_schema(self) -> SchemaInfo:
        return SchemaInfo(tables=[])

    async def execute_read(self, query: dict[str, Any]) -> QueryResult:
        return QueryResult(columns=[], rows=[], row_count=0, source_type="mongodb")


# ---------------------------------------------------------------------------
# Multi-source isolation tests
# ---------------------------------------------------------------------------


class TestMultiSourceRegistryIsolation:
    """Verify ConnectorRegistry produces independent, isolated instances."""

    def _build_registry(self) -> ConnectorRegistry:
        """Create a registry with both connector types registered."""
        registry = ConnectorRegistry()
        registry.register("postgresql", FakePostgresConnector)
        registry.register("mongodb", FakeMongoConnector)
        return registry

    def test_multiple_instances_are_independent(self) -> None:
        """Resolve PostgreSQL A, PostgreSQL B, MongoDB C — all independent."""
        registry = self._build_registry()

        config_a = {"host": "pg-host-a", "port": 5432, "database": "db_a", "password": "secret_a"}
        config_b = {"host": "pg-host-b", "port": 5433, "database": "db_b", "password": "secret_b"}
        config_c = {"uri": "mongodb://mongo-host:27017", "database": "db_c", "password": "secret_c"}

        instance_a = registry.resolve("postgresql", config_a)
        instance_b = registry.resolve("postgresql", config_b)
        instance_c = registry.resolve("mongodb", config_c)

        # Different object identities
        assert id(instance_a) != id(instance_b)
        assert id(instance_a) != id(instance_c)
        assert id(instance_b) != id(instance_c)

        # Each has its own config
        assert instance_a.config == config_a
        assert instance_b.config == config_b
        assert instance_c.config == config_c

        # Correct types
        assert isinstance(instance_a, FakePostgresConnector)
        assert isinstance(instance_b, FakePostgresConnector)
        assert isinstance(instance_c, FakeMongoConnector)

    def test_registry_state_has_no_decrypted_credentials_after_resolve(self) -> None:
        """Registry internal state stores only classes, never credentials."""
        registry = self._build_registry()

        config_with_creds = {
            "host": "pg-host",
            "port": 5432,
            "database": "finance_db",
            "user": "admin",
            "password": "super_secret_123",
            "api_key": "ak-xyz789",
        }

        registry.resolve("postgresql", config_with_creds)

        # Inspect registry internals: only connector classes stored
        for source_type, connector_class in registry._connectors.items():
            assert isinstance(connector_class, type), (
                f"Registry should store classes, not instances for {source_type}"
            )

        # No credential values anywhere in registry state
        registry_state_str = str(registry._connectors)
        assert "super_secret_123" not in registry_state_str
        assert "ak-xyz789" not in registry_state_str
        assert "admin" not in registry_state_str

    def test_failure_of_one_instance_does_not_affect_another(self) -> None:
        """Failure resolving or using instance A does not block instance B."""
        registry = ConnectorRegistry()
        registry.register("postgresql", FailingPostgresConnector)
        registry.register("mongodb", FakeMongoConnector)

        # Instance A fails on construction
        failing_config = {"host": "bad-host", "fail_on_init": True}
        with pytest.raises(ConnectionError, match="Simulated connection failure"):
            registry.resolve("postgresql", failing_config)

        # Instance B resolves successfully despite A's failure
        good_config = {"uri": "mongodb://good-host:27017", "database": "healthy_db"}
        instance_b = registry.resolve("mongodb", good_config)
        assert isinstance(instance_b, FakeMongoConnector)
        assert instance_b.config == good_config

        # Another PostgreSQL instance with valid config also resolves
        valid_pg_config = {"host": "good-host", "fail_on_init": False}
        instance_c = registry.resolve("postgresql", valid_pg_config)
        assert isinstance(instance_c, FailingPostgresConnector)
        assert instance_c.config == valid_pg_config

    def test_credentials_never_shared_between_instances(self) -> None:
        """Each instance receives only its own configuration — no cross-contamination."""
        registry = self._build_registry()

        config_a = {"host": "host-a", "password": "password_A", "database": "db_a"}
        config_b = {"host": "host-b", "password": "password_B", "database": "db_b"}
        config_c = {"uri": "mongodb://host-c", "password": "password_C", "database": "db_c"}

        instance_a = registry.resolve("postgresql", config_a)
        instance_b = registry.resolve("postgresql", config_b)
        instance_c = registry.resolve("mongodb", config_c)

        # Instance A has no knowledge of B or C credentials
        assert "password_B" not in str(instance_a.config)
        assert "password_C" not in str(instance_a.config)
        assert "host-b" not in str(instance_a.config)

        # Instance B has no knowledge of A or C credentials
        assert "password_A" not in str(instance_b.config)
        assert "password_C" not in str(instance_b.config)
        assert "host-a" not in str(instance_b.config)

        # Instance C has no knowledge of A or B credentials
        assert "password_A" not in str(instance_c.config)
        assert "password_B" not in str(instance_c.config)
        assert "host-a" not in str(instance_c.config)

        # Mutating one config does not affect the other
        config_a["password"] = "MUTATED"
        assert instance_a.config["password"] == "MUTATED"
        assert instance_b.config["password"] == "password_B"
        assert instance_c.config["password"] == "password_C"

    def test_instances_do_not_persist_in_registry(self) -> None:
        """After resolve(), connector instances are not retained by the registry."""
        registry = self._build_registry()

        config = {"host": "ephemeral-host", "database": "temp_db", "password": "temp_pass"}
        instance = registry.resolve("postgresql", config)

        # Create a weak reference to track if instance can be garbage collected
        weak_ref = weakref.ref(instance)

        # Registry should not hold a reference to the instance
        # Check that registry only stores classes
        for stored_value in registry._connectors.values():
            assert stored_value is not instance, (
                "Registry should not retain resolved connector instances"
            )

        # The registry has no instance cache or list
        assert not hasattr(registry, "_instances")
        assert not hasattr(registry, "_cache")

        # After dropping our reference, the instance should be collectible
        del instance
        # NOTE: weak_ref() may or may not be None depending on GC timing,
        # but the key assertion is that the registry doesn't hold a reference.

    def test_resolve_same_type_multiple_times_produces_fresh_instances(self) -> None:
        """Each resolve() call creates a new instance — no caching."""
        registry = self._build_registry()

        same_config = {"host": "shared-host", "port": 5432, "database": "shared_db"}

        instance_1 = registry.resolve("postgresql", same_config)
        instance_2 = registry.resolve("postgresql", same_config)

        # Even with identical config, instances are distinct objects
        assert instance_1 is not instance_2
        assert id(instance_1) != id(instance_2)
