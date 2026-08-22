"""
Document ingestion domain error types.

Raised during the document ingestion pipeline when file processing fails.
"""

from app.errors.base import AppError, ErrorCategory


class DocumentValidationError(AppError):
    """Raised when an uploaded document fails validation (type, size, format)."""

    def __init__(self, file_name: str, message: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="DOCUMENT_VALIDATION_ERROR",
            message=message,
            domain="document",
            category=ErrorCategory.VALIDATION,
            detail=detail,
        )
        self.file_name = file_name


class ContentExtractionError(AppError):
    """Raised when text extraction from a document fails."""

    def __init__(self, file_name: str, message: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="CONTENT_EXTRACTION_ERROR",
            message=message,
            domain="document",
            category=ErrorCategory.EXTERNAL,
            detail=detail,
        )
        self.file_name = file_name


class ChunkingError(AppError):
    """Raised when text chunking fails during document processing."""

    def __init__(self, file_name: str, message: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="CHUNKING_ERROR",
            message=message,
            domain="document",
            category=ErrorCategory.EXTERNAL,
            detail=detail,
        )
        self.file_name = file_name


class MetadataExtractionError(AppError):
    """Raised when metadata extraction from a document fails."""

    def __init__(self, file_name: str, message: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="METADATA_EXTRACTION_ERROR",
            message=message,
            domain="document",
            category=ErrorCategory.EXTERNAL,
            detail=detail,
        )
        self.file_name = file_name


class EmbeddingGenerationError(AppError):
    """Raised when embedding generation fails for document chunks."""

    def __init__(self, file_name: str, message: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="EMBEDDING_GENERATION_ERROR",
            message=message,
            domain="document",
            category=ErrorCategory.EXTERNAL,
            detail=detail,
        )
        self.file_name = file_name


class DocumentStorageError(AppError):
    """Raised when storing document data or embeddings in RAG_DB fails."""

    def __init__(self, file_name: str, message: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="DOCUMENT_STORAGE_ERROR",
            message=message,
            domain="document",
            category=ErrorCategory.EXTERNAL,
            detail=detail,
        )
        self.file_name = file_name
