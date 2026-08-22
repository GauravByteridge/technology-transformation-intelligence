"""
Connector registry — maps data source types to their connector implementations.

The registry holds connector CLASSES (not instances). When resolve() is called,
it instantiates a new connector with the provided connection configuration.
This supports adding new connector types without modifying existing code.
"""

from __future__ import annotations

import logging
from typing import Any

from app.connectors.protocol import DataSourceConnector
from app.errors.datasource_errors import UnsupportedDataSourceError

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """Registry mapping source type strings to connector classes.

    Usage:
        registry = ConnectorRegistry()
        registry.register("postgresql", PostgresConnector)
        connector = registry.resolve("postgresql", {"host": "...", "port": 5432})
    """

    def __init__(self) -> None:
        self._connectors: dict[str, type[DataSourceConnector]] = {}

    def register(self, source_type: str, connector_class: type[DataSourceConnector]) -> None:
        """Register a connector class for a given source type.

        Args:
            source_type: Identifier such as 'postgresql' or 'mongodb'.
            connector_class: Class implementing DataSourceConnector protocol.
        """
        self._connectors[source_type] = connector_class
        logger.info(
            "Connector registered",
            extra={"source_type": source_type, "connector_class": connector_class.__name__},
        )

    def resolve(self, source_type: str, connection_config: dict[str, Any]) -> DataSourceConnector:
        """Instantiate and return a connector for the requested source type.

        Args:
            source_type: The data source type to resolve (e.g. 'postgresql').
            connection_config: Configuration dict passed to the connector constructor.

        Returns:
            A new connector instance configured with the provided config.

        Raises:
            UnsupportedDataSourceError: If source_type is not registered.
        """
        connector_class = self._connectors.get(source_type)
        if connector_class is None:
            raise UnsupportedDataSourceError(
                requested_type=source_type,
                supported_types=self.list_supported_types(),
            )
        return connector_class(connection_config)  # type: ignore[call-arg]

    def list_supported_types(self) -> list[str]:
        """Return all registered source type identifiers."""
        return list(self._connectors.keys())
