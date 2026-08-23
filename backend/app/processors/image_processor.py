"""
ImageProcessor — Placeholder FileProcessor for image files (JPG, PNG).

Registers support for image file types but raises NotImplementedError on
inspect/extract, indicating that OCR/vision capabilities require an
external provider to be configured. Validate returns no warnings since
no processing is attempted.
"""

from __future__ import annotations

from app.processors.protocol import (
    DetectedRegion,
    InspectionResult,
    NormalizedDataset,
    ValidationWarning,
)


class ImageProcessor:
    """FileProcessor placeholder for image files (JPG, JPEG, PNG).

    Recognizes image file types so the registry can report them as
    "known but not yet processable" rather than unsupported. Actual
    processing requires an OCR or vision provider to be configured.
    """

    def can_process(self, file_type: str) -> bool:
        """Return True for image file types.

        Args:
            file_type: File extension identifier.

        Returns:
            True for "jpg", "jpeg", or "png".
        """
        return file_type in ("jpg", "jpeg", "png")

    async def inspect(self, file_path: str) -> InspectionResult:
        """Not implemented — requires OCR/vision provider.

        Raises:
            NotImplementedError: Always. Image processing requires an external
                OCR or vision provider to be configured.
        """
        raise NotImplementedError(
            "Image processing not available. OCR/vision provider required."
        )

    async def extract(
        self, file_path: str, region: DetectedRegion | None = None
    ) -> NormalizedDataset:
        """Not implemented — requires OCR/vision provider.

        Raises:
            NotImplementedError: Always. Image processing requires an external
                OCR or vision provider to be configured.
        """
        raise NotImplementedError(
            "Image processing not available. OCR/vision provider required."
        )

    def validate(self, normalized: NormalizedDataset) -> list[ValidationWarning]:
        """Return empty list — no validation possible without processing.

        Args:
            normalized: The normalized dataset (unused).

        Returns:
            Empty list of warnings.
        """
        return []
