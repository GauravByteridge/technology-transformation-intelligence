"""
TextProcessor — FileProcessor implementation for plain text files.

Always classifies content as UNSTRUCTURED → RAG.
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from app.errors.ingestion_errors import FileProcessingError
from app.processors.protocol import (
    DetectedRegion,
    InspectionResult,
    NormalizedDataset,
    ValidationWarning,
)

logger = logging.getLogger(__name__)

# Maximum lines to include in content_sample
_MAX_SAMPLE_LINES = 20


class TextProcessor:
    """FileProcessor for plain text files. Always UNSTRUCTURED → RAG."""

    def can_process(self, file_type: str) -> bool:
        """Return True if this processor handles the given file type.

        Args:
            file_type: File extension or type identifier.

        Returns:
            True for "txt".
        """
        return file_type.lower() == "txt"

    async def inspect(self, file_path: str) -> InspectionResult:
        """Inspect plain text file and produce a single UNSTRUCTURED region.

        Reads the file as UTF-8 text and returns an InspectionResult with a
        single DetectedRegion covering the full file content.

        Args:
            file_path: Path to the text file on disk.

        Returns:
            InspectionResult with a single region representing the full document.

        Raises:
            FileProcessingError: If the file is not found or cannot be read.
        """
        path = Path(file_path)
        file_name = path.name

        if not path.exists():
            raise FileProcessingError(
                file_name=file_name,
                message=f"Text file not found: {file_path}",
            )

        try:
            raw_text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise FileProcessingError(
                file_name=file_name,
                message=f"Failed to read text file: {file_name}",
                detail=str(exc),
            ) from exc

        # Split into lines for content_sample
        lines = raw_text.split("\n")
        content_sample: list[list[str]] = [
            [line] for line in lines[:_MAX_SAMPLE_LINES]
        ]

        # Count total lines
        total_lines = len(lines)

        region = DetectedRegion(
            region_id=str(uuid4()),
            sheet_name="document",
            start_row=1,
            end_row=total_lines,
            start_column=0,
            end_column=0,
            header_row=None,
            content_sample=content_sample,
            row_count=total_lines,
            column_count=1,
            raw_text=raw_text,
        )

        return InspectionResult(
            file_name=file_name,
            file_type="txt",
            regions=[region],
            metadata={},
        )

    async def extract(
        self, file_path: str, region: DetectedRegion | None = None
    ) -> NormalizedDataset:
        """Not applicable for plain text content.

        Text content is routed to RAG pipeline, not structured extraction.

        Raises:
            NotImplementedError: Always — unstructured content is not applicable
                for structured extraction.
        """
        raise NotImplementedError(
            "TextProcessor does not support structured extraction. "
            "Text content is processed through the RAG pipeline."
        )

    def validate(self, normalized: NormalizedDataset) -> list[ValidationWarning]:
        """Validate a normalized dataset. Returns empty list for text content.

        Args:
            normalized: The normalized dataset to validate.

        Returns:
            Empty list — text content is unstructured and not validated this way.
        """
        return []
