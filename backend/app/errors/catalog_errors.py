"""
Catalog domain error types.

Raised by catalog service and API layer when catalog operations fail.
"""

from app.errors.base import AppError, ErrorCategory


class CatalogEntryNotFoundError(AppError):
    """Raised when a requested catalog entry does not exist."""

    def __init__(self, entry_id: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="CATALOG_ENTRY_NOT_FOUND",
            message=f"Catalog entry '{entry_id}' not found",
            domain="catalog",
            category=ErrorCategory.NOT_FOUND,
            detail=detail,
        )
