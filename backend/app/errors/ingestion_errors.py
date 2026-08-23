"""
Ingestion pipeline domain error types.

Raised during file processing when format-specific parsing,
classification, or data extraction fails.
"""

from app.errors.base import AppError, ErrorCategory


class UnsupportedFileTypeError(AppError):
    """Raised when no processor matches the requested file type."""

    def __init__(
        self,
        file_type: str,
        supported_types: list[str],
        detail: str | None = None,
    ) -> None:
        super().__init__(
            error_code="UNSUPPORTED_FILE_TYPE",
            message=f"File type '{file_type}' is not supported. Supported types: {', '.join(supported_types)}",
            domain="ingestion",
            category=ErrorCategory.VALIDATION,
            detail=detail,
        )
        self.file_type = file_type
        self.supported_types = supported_types


class FileProcessingError(AppError):
    """Raised when a processor fails during file inspection or extraction."""

    def __init__(
        self,
        file_name: str,
        message: str,
        detail: str | None = None,
    ) -> None:
        super().__init__(
            error_code="FILE_PROCESSING_ERROR",
            message=message,
            domain="ingestion",
            category=ErrorCategory.EXTERNAL,
            detail=detail,
        )
        self.file_name = file_name


class ContentClassificationError(AppError):
    """Raised when content classification fails for a detected region."""

    def __init__(
        self,
        region_id: str,
        message: str,
        detail: str | None = None,
    ) -> None:
        super().__init__(
            error_code="CONTENT_CLASSIFICATION_ERROR",
            message=message,
            domain="ingestion",
            category=ErrorCategory.EXTERNAL,
            detail=detail,
        )
        self.region_id = region_id
