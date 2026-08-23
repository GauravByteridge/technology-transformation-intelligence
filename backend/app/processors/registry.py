"""
FileProcessor registry — maps file types to their processor implementations.

The registry holds processor INSTANCES (not classes). When get_processor()
is called, it returns the registered processor for the given file type.
This supports adding new file processors without modifying existing code.
"""

from __future__ import annotations

import logging

from app.errors.ingestion_errors import UnsupportedFileTypeError
from app.processors.protocol import FileProcessor

logger = logging.getLogger(__name__)


class FileProcessorRegistry:
    """Registry resolving file types to processor implementations.

    Usage:
        registry = FileProcessorRegistry()
        registry.register("xlsx", excel_processor)
        processor = registry.get_processor("xlsx")
    """

    def __init__(self) -> None:
        self._processors: dict[str, FileProcessor] = {}

    def register(self, file_type: str, processor: FileProcessor) -> None:
        """Register a processor instance for a file type.

        Args:
            file_type: File extension identifier (e.g., "xlsx", "csv", "pdf").
            processor: Processor instance implementing FileProcessor protocol.
        """
        self._processors[file_type] = processor
        logger.info(
            "File processor registered",
            extra={"file_type": file_type, "processor": type(processor).__name__},
        )

    def get_processor(self, file_type: str) -> FileProcessor:
        """Resolve the processor for a given file type.

        Args:
            file_type: File extension identifier to look up.

        Returns:
            The registered FileProcessor instance.

        Raises:
            UnsupportedFileTypeError: If no processor is registered for the file type.
        """
        processor = self._processors.get(file_type)
        if processor is None:
            raise UnsupportedFileTypeError(
                file_type=file_type,
                supported_types=list(self._processors.keys()),
            )
        return processor

    def supported_types(self) -> set[str]:
        """Return all registered file types.

        Returns:
            Set of file type strings that have registered processors.
        """
        return set(self._processors.keys())
