"""
File validation implementation for the document ingestion pipeline.

Validates file type and size against configured allowed lists before
ingestion processing begins.
"""

from app.errors.document_errors import DocumentValidationError

# Allowed file types for ingestion.
# Architecture accommodates future image formats (png, jpeg) without
# changing core pipeline flow — just add them to this set.
ALLOWED_FILE_TYPES: set[str] = {"txt", "pdf", "docx"}

# Maximum file size in bytes (default: 50 MB)
MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024


class SimpleFileValidator:
    """Validates uploaded files against type and size constraints.

    Satisfies the FileValidator protocol via structural subtyping.
    """

    def __init__(
        self,
        allowed_types: set[str] | None = None,
        max_file_size: int = MAX_FILE_SIZE_BYTES,
    ) -> None:
        """Initialize the validator.

        Args:
            allowed_types: Set of permitted file type identifiers.
                           Defaults to ALLOWED_FILE_TYPES.
            max_file_size: Maximum acceptable file size in bytes.
        """
        self._allowed_types = allowed_types or ALLOWED_FILE_TYPES
        self._max_file_size = max_file_size

    @property
    def allowed_types(self) -> set[str]:
        """The set of file types this validator permits."""
        return self._allowed_types

    async def validate(self, file_name: str, file_type: str, file_size: int) -> bool:
        """Check whether the file is acceptable for ingestion.

        Args:
            file_name: Original file name including extension.
            file_type: MIME type or extension identifier (e.g., "txt", "pdf").
            file_size: File size in bytes.

        Returns:
            True if the file passes all validation checks.

        Raises:
            DocumentValidationError: If the file fails any check.
        """
        normalized_type = file_type.lower().strip()

        if normalized_type not in self._allowed_types:
            raise DocumentValidationError(
                file_name=file_name,
                message=f"Unsupported file type: '{file_type}'",
                detail=f"Allowed types: {', '.join(sorted(self._allowed_types))}",
            )

        if file_size <= 0:
            raise DocumentValidationError(
                file_name=file_name,
                message="File size must be greater than zero",
            )

        if file_size > self._max_file_size:
            max_mb = self._max_file_size / (1024 * 1024)
            raise DocumentValidationError(
                file_name=file_name,
                message=f"File size exceeds maximum allowed ({max_mb:.0f} MB)",
                detail=f"File size: {file_size} bytes, limit: {self._max_file_size} bytes",
            )

        return True
