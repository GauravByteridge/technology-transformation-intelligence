"""
Domain error types and exception handling infrastructure.

Usage:
    from app.errors import ProjectNotFoundError, DataSourceConnectionError

All errors inherit from AppError and carry error_code, message, domain,
and category for consistent HTTP status mapping.
"""

from app.errors.ai_errors import AIQueryError, ProviderCredentialError, ProviderResolutionError
from app.errors.base import AppError, ErrorCategory
from app.errors.config_errors import ConfigurationError
from app.errors.datasource_errors import (
    DataSourceConnectionError,
    QueryExecutionError,
    SchemaDiscoveryError,
    UnsupportedDataSourceError,
)
from app.errors.document_errors import (
    ChunkingError,
    ContentExtractionError,
    DocumentStorageError,
    DocumentValidationError,
    EmbeddingGenerationError,
    MetadataExtractionError,
)
from app.errors.handlers import register_exception_handlers
from app.errors.project_errors import ProjectNotFoundError, ProjectValidationError

__all__ = [
    # Base
    "AppError",
    "ErrorCategory",
    # Project
    "ProjectNotFoundError",
    "ProjectValidationError",
    # Data Source
    "DataSourceConnectionError",
    "SchemaDiscoveryError",
    "QueryExecutionError",
    "UnsupportedDataSourceError",
    # Document
    "DocumentValidationError",
    "ContentExtractionError",
    "MetadataExtractionError",
    "ChunkingError",
    "EmbeddingGenerationError",
    "DocumentStorageError",
    # AI
    "ProviderResolutionError",
    "ProviderCredentialError",
    "AIQueryError",
    # Config
    "ConfigurationError",
    # Handlers
    "register_exception_handlers",
]
