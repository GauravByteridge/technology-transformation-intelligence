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

    def resolve(self, source_type: str, connection_config: dict[str, Any], **kwargs: Any) -> DataSourceConnector:
        """Instantiate and return a connector for the requested source type.

        Design Decision — Separation of Credentials and Operational Config:
            connection_config contains ONLY decrypted connection credentials
            (host, port, database, user, password) obtained from decrypt_config().
            It is passed as the first positional argument to the connector constructor.

            Operational configuration (row_limit, connection_timeout, sample_size,
            max_nesting_depth) is passed via **kwargs as separate keyword arguments.
            These are NEVER stored in the connection_config dict and NEVER mixed
            with credentials. This keeps the two concerns in distinct namespaces,
            preventing accidental leakage of credentials through operational config
            paths and vice versa.

        Args:
            source_type: The data source type to resolve (e.g. 'postgresql').
            connection_config: Decrypted connection credentials dict passed as the
                first positional arg to the connector constructor.
            **kwargs: Operational configuration (e.g. row_limit, connection_timeout,
                sample_size, max_nesting_depth) passed as keyword arguments to the
                connector constructor. Defaults to empty when not provided.

        Returns:
            A new connector instance configured with credentials and operational params.

        Raises:
            UnsupportedDataSourceError: If source_type is not registered.
        """
        connector_class = self._connectors.get(source_type)
        if connector_class is None:
            raise UnsupportedDataSourceError(
                requested_type=source_type,
                supported_types=self.list_supported_types(),
            )
        return connector_class(connection_config, **kwargs)  # type: ignore[call-arg]

    def list_supported_types(self) -> list[str]:
        """Return all registered source type identifiers."""
        return list(self._connectors.keys())
