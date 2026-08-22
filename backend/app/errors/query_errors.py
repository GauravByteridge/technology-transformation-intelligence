"""
Query domain error types.

Raised by query history and saved query services when
query-related operations fail.
"""

from app.errors.base import AppError, ErrorCategory


class QueryHistoryNotFoundError(AppError):
    """Raised when a requested query history record does not exist."""

    def __init__(self, query_id: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="QUERY_HISTORY_NOT_FOUND",
            message=f"Query history '{query_id}' not found",
            domain="query",
            category=ErrorCategory.NOT_FOUND,
            detail=detail,
        )


class SavedQueryNotFoundError(AppError):
    """Raised when a requested saved query does not exist."""

    def __init__(self, saved_query_id: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="SAVED_QUERY_NOT_FOUND",
            message=f"Saved query '{saved_query_id}' not found",
            domain="query",
            category=ErrorCategory.NOT_FOUND,
            detail=detail,
        )
