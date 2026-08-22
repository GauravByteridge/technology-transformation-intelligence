"""
Configuration domain error types.

Raised during startup validation when required configuration
is missing or invalid.
"""

from app.errors.base import AppError, ErrorCategory


class ConfigurationError(AppError):
    """Raised when application configuration is invalid or missing."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="CONFIGURATION_ERROR",
            message=message,
            domain="config",
            category=ErrorCategory.UNHANDLED,
            detail=detail,
        )
