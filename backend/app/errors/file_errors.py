"""
File domain error types.

Raised by file services when file-related operations fail.
This defines a domain-specific FileNotFoundError distinct from
Python's built-in FileNotFoundError.
"""

from app.errors.base import AppError, ErrorCategory


class FileNotFoundError(AppError):
    """
    Raised when a requested uploaded file record does not exist.

    NOTE: This is a domain error for the file entity, distinct from
    Python's built-in FileNotFoundError (which relates to filesystem I/O).
    """

    def __init__(self, file_id: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="FILE_NOT_FOUND",
            message=f"File '{file_id}' not found",
            domain="file",
            category=ErrorCategory.NOT_FOUND,
            detail=detail,
        )
