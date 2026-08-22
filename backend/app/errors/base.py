"""
Base error class for the application.

All domain-specific errors inherit from AppError. Each error carries
an error_code, message, and domain identifier. The error category
determines HTTP status mapping at the API boundary.
"""

from enum import StrEnum


class ErrorCategory(StrEnum):
    """Maps domain errors to HTTP status codes."""

    NOT_FOUND = "not_found"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CONFLICT = "conflict"
    CONNECTION = "connection"
    EXTERNAL = "external"
    UNHANDLED = "unhandled"


# Category → HTTP status code mapping
ERROR_CATEGORY_STATUS_MAP: dict[ErrorCategory, int] = {
    ErrorCategory.NOT_FOUND: 404,
    ErrorCategory.VALIDATION: 422,
    ErrorCategory.AUTHENTICATION: 401,
    ErrorCategory.AUTHORIZATION: 403,
    ErrorCategory.CONFLICT: 409,
    ErrorCategory.CONNECTION: 502,
    ErrorCategory.EXTERNAL: 502,
    ErrorCategory.UNHANDLED: 500,
}


class AppError(Exception):
    """
    Base application error.

    All domain errors inherit from this class. Provides consistent
    structure for error propagation and HTTP response mapping.

    Attributes:
        error_code: Machine-readable error identifier (e.g., "PROJECT_NOT_FOUND")
        message: Human-readable error description
        domain: Business domain this error belongs to (e.g., "project", "datasource")
        category: Error category for HTTP status mapping
        detail: Optional additional context for debugging
    """

    def __init__(
        self,
        error_code: str,
        message: str,
        domain: str,
        category: ErrorCategory = ErrorCategory.UNHANDLED,
        detail: str | None = None,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.domain = domain
        self.category = category
        self.detail = detail
        super().__init__(message)

    @property
    def http_status_code(self) -> int:
        """Resolve HTTP status code from the error category."""
        return ERROR_CATEGORY_STATUS_MAP.get(self.category, 500)
