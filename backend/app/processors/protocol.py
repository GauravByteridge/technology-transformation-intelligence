"""
FileProcessor protocol and supporting data classes.

Defines the common interface that all format-specific file processors
must implement, along with the data structures for inspection results,
detected regions, normalized datasets, and classification outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


# ---------------------------------------------------------------------------
# Supporting data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileTypeResult:
    """Result of file type detection. Identifies parser, not processing strategy.

    Attributes:
        extension: Normalized file extension (e.g., "xlsx", "pdf").
        mime_type: MIME type corresponding to the extension.
        processor_key: Key to look up in FileProcessorRegistry.
        is_supported: True if the extension is in the supported set.
    """

    extension: str
    mime_type: str
    processor_key: str
    is_supported: bool


@dataclass
class DetectedRegion:
    """A region detected within a file, with content for classification.

    Attributes:
        region_id: Unique identifier for this region within the file.
        sheet_name: Sheet name for multi-sheet formats (None for single-sheet).
        start_row: Zero-based starting row of the region.
        end_row: Zero-based ending row (exclusive).
        start_column: Zero-based starting column.
        end_column: Zero-based ending column (exclusive).
        header_row: Row index containing headers, if detected.
        content_sample: Sample rows for classification (list of row lists).
        row_count: Total number of rows in the region.
        column_count: Total number of columns in the region.
        raw_text: Raw text content for unstructured regions.
    """

    region_id: str
    sheet_name: str | None
    start_row: int
    end_row: int
    start_column: int
    end_column: int
    header_row: int | None
    content_sample: list[list[str]]
    row_count: int
    column_count: int
    raw_text: str | None = None


@dataclass
class InspectionResult:
    """Result of file inspection containing detected regions with content.

    Attributes:
        file_name: Original file name.
        file_type: Detected file type extension.
        regions: List of detected content regions.
        metadata: File-level metadata (author, creation date, etc.).
    """

    file_name: str
    file_type: str
    regions: list[DetectedRegion] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class ColumnSchema:
    """Schema definition for a single column in a normalized dataset.

    Attributes:
        name: Column name (from header or generated).
        data_type: Inferred data type (string, integer, decimal, boolean, date, datetime, unknown).
        nullable: Whether the column contains null values.
        column_index: Zero-based position in the dataset.
        sample_values: Representative sample values from the column.
        confidence: Confidence in the data type inference (0.0 to 1.0).
    """

    name: str
    data_type: str
    nullable: bool
    column_index: int
    sample_values: list[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class NormalizedDataset:
    """Normalized tabular data extracted from a file region.

    Attributes:
        dataset_id: Optional ID if persisted, None during extraction.
        source_file_id: ID of the source uploaded file.
        sheet_name: Sheet name for multi-sheet formats.
        columns: Inferred column schema.
        records: Extracted records as list of dictionaries.
        classification: Content classification (STRUCTURED, SEMI_STRUCTURED, etc.).
        source_location: Human-readable location within the file.
        confidence: Confidence in the extraction quality (0.0 to 1.0).
        warnings: List of extraction warnings.
    """

    dataset_id: str | None
    source_file_id: str
    sheet_name: str | None
    columns: list[ColumnSchema]
    records: list[dict]
    classification: str
    source_location: str
    confidence: float
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HeaderDetectionResult:
    """Result of header row detection within a region.

    Attributes:
        header_row: Zero-based row index of the detected header.
        confidence: Confidence in the detection (0.0 to 1.0).
        detection_reason: Explanation of why this row was selected.
        warnings: Any issues encountered during detection.
    """

    header_row: int
    confidence: float
    detection_reason: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SheetInfo:
    """Metadata about a single sheet in a workbook.

    Attributes:
        name: Sheet name.
        visible: Whether the sheet is visible to users.
        row_count: Total row count in the sheet.
        column_count: Total column count in the sheet.
        merged_cell_count: Number of merged cell ranges.
    """

    name: str
    visible: bool
    row_count: int
    column_count: int
    merged_cell_count: int = 0


@dataclass(frozen=True)
class ValidationWarning:
    """Warning generated during dataset validation.

    Attributes:
        field: Column or field name where the issue was found.
        message: Description of the validation issue.
        severity: Severity level (info, warning, error).
    """

    field: str
    message: str
    severity: str


@dataclass(frozen=True)
class ClassificationResult:
    """Result of content classification for a single region.

    Attributes:
        classification: Content structure type (from ContentClassification enum).
        processing_strategy: Downstream processing path (from ProcessingStrategy enum).
        confidence: Classification confidence (0.0 to 1.0).
        reason: Human-readable explanation of the classification decision.
        signals: Individual signal scores used in classification.
    """

    classification: str
    processing_strategy: str
    confidence: float
    reason: str
    signals: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# FileProcessor Protocol
# ---------------------------------------------------------------------------


class FileProcessor(Protocol):
    """Common protocol for all format-specific file processors.

    Every processor inspects content and returns regions with enough
    information for the ContentClassifier to determine processing strategy.
    """

    def can_process(self, file_type: str) -> bool:
        """Return True if this processor handles the given file type.

        Args:
            file_type: File extension or type identifier.

        Returns:
            True if this processor can handle the file type.
        """
        ...

    async def inspect(self, file_path: str) -> InspectionResult:
        """Inspect file structure, detect regions, and provide content for classification.

        Returns an InspectionResult containing detected regions with their
        raw content, enabling downstream ContentClassifier to assign
        processing strategies.

        Args:
            file_path: Path to the file on disk.

        Returns:
            InspectionResult with detected regions and file metadata.

        Raises:
            FileProcessingError: If inspection fails.
        """
        ...

    async def extract(
        self, file_path: str, region: DetectedRegion | None = None
    ) -> NormalizedDataset:
        """Extract and normalize data from the file or a specific region.

        Args:
            file_path: Path to the file on disk.
            region: Optional specific region to extract. If None, extracts all.

        Returns:
            NormalizedDataset with extracted records and schema.

        Raises:
            FileProcessingError: If extraction fails.
        """
        ...

    def validate(self, normalized: NormalizedDataset) -> list[ValidationWarning]:
        """Validate a normalized dataset for consistency issues.

        Args:
            normalized: The normalized dataset to validate.

        Returns:
            List of validation warnings (empty if no issues found).
        """
        ...
