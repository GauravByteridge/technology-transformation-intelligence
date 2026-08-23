"""
FileTypeDetector — determines file format from extension.

Selects the appropriate parser (processor) based on file extension.
This component determines which PARSER to use, NOT which downstream
processing path. Content classification happens AFTER parsing.
"""

from __future__ import annotations

import logging
from pathlib import PurePosixPath, PureWindowsPath

from app.processors.protocol import FileTypeResult

logger = logging.getLogger(__name__)


class FileTypeDetector:
    """Determines file format from extension to select the appropriate parser.

    IMPORTANT: This component determines which PARSER to use, NOT which
    downstream processing path. Content classification happens AFTER parsing.
    """

    SUPPORTED_EXTENSIONS: set[str] = {
        "xlsx", "xls", "csv", "json", "pdf", "docx", "txt",
    }

    IMAGE_EXTENSIONS: set[str] = {"jpg", "jpeg", "png"}  # P2 future

    MIME_TYPES: dict[str, str] = {
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "csv": "text/csv",
        "json": "application/json",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
    }

    def detect(self, file_name: str) -> FileTypeResult:
        """Detect file type from extension. Returns processor_key for registry lookup.

        Extracts the extension from the file name (case-insensitive) and
        resolves the corresponding MIME type and processor key.

        Args:
            file_name: Original file name including extension.

        Returns:
            FileTypeResult with extension, mime_type, processor_key, and is_supported.
            For unsupported extensions, is_supported is False and mime_type is
            "application/octet-stream".
        """
        extension = self._extract_extension(file_name)
        is_supported = extension in self.SUPPORTED_EXTENSIONS
        mime_type = self.MIME_TYPES.get(extension, "application/octet-stream")
        # processor_key matches extension for now; future versions may remap
        processor_key = extension

        logger.debug(
            "File type detected",
            extra={
                "file_name": file_name,
                "extension": extension,
                "is_supported": is_supported,
                "processor_key": processor_key,
            },
        )

        return FileTypeResult(
            extension=extension,
            mime_type=mime_type,
            processor_key=processor_key,
            is_supported=is_supported,
        )

    def _extract_extension(self, file_name: str) -> str:
        """Extract and normalize the file extension (lowercase, no dot).

        Handles both Unix and Windows path separators gracefully.

        Args:
            file_name: File name or path to extract extension from.

        Returns:
            Lowercase extension without the leading dot, or empty string
            if no extension is present.
        """
        # Use PurePosixPath for reliable suffix extraction regardless of OS
        # Try Windows path first if it contains backslashes
        if "\\" in file_name:
            suffix = PureWindowsPath(file_name).suffix
        else:
            suffix = PurePosixPath(file_name).suffix

        # Remove leading dot and normalize to lowercase
        return suffix.lstrip(".").lower()
