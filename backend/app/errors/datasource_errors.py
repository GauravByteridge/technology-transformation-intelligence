"""
Data source domain error types.

Raised by connectors and data source services when external
data source operations fail.
"""

from app.errors.base import AppError, ErrorCategory


class DataSourceNotFoundError(AppError):
    """Raised when a requested data source does not exist."""

    def __init__(self, data_source_id: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="DATA_SOURCE_NOT_FOUND",
            message=f"Data source '{data_source_id}' not found",
            domain="datasource",
            category=ErrorCategory.NOT_FOUND,
            detail=detail,
        )


class DataSourceConnectionError(AppError):
    """Raised when a connection to an external data source fails."""

    def __init__(self, source_type: str, message: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="DATA_SOURCE_CONNECTION_ERROR",
            message=message,
            domain="datasource",
            category=ErrorCategory.CONNECTION,
            detail=detail,
        )
        self.source_type = source_type


class SchemaDiscoveryError(AppError):
    """Raised when schema discovery on an external source fails."""

    def __init__(self, source_type: str, message: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="SCHEMA_DISCOVERY_ERROR",
            message=message,
            domain="datasource",
            category=ErrorCategory.EXTERNAL,
            detail=detail,
        )
        self.source_type = source_type


class QueryExecutionError(AppError):
    """Raised when a query against an external data source fails."""

    def __init__(self, source_type: str, message: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="QUERY_EXECUTION_ERROR",
            message=message,
            domain="datasource",
            category=ErrorCategory.EXTERNAL,
            detail=detail,
        )
        self.source_type = source_type


class UnsupportedDataSourceError(AppError):
    """Raised when a requested data source type is not registered."""

    def __init__(self, requested_type: str, supported_types: list[str]) -> None:
        supported = ", ".join(supported_types) if supported_types else "none"
        super().__init__(
            error_code="UNSUPPORTED_DATA_SOURCE",
            message=f"Data source type '{requested_type}' is not supported. Supported types: {supported}",
            domain="datasource",
            category=ErrorCategory.VALIDATION,
            detail=None,
        )
        self.requested_type = requested_type
        self.supported_types = supported_types
