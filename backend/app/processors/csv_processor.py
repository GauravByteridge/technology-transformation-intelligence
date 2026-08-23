"""
CSVProcessor — FileProcessor implementation for CSV files.

Detects delimiters, identifies headers, and normalizes CSV content
into structured datasets with source traceability.
"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from typing import Any

from app.errors.ingestion_errors import FileProcessingError
from app.processors.protocol import (
    ColumnSchema,
    DetectedRegion,
    HeaderDetectionResult,
    InspectionResult,
    NormalizedDataset,
    ValidationWarning,
)

logger = logging.getLogger(__name__)

# Configuration
_MAX_SAMPLE_ROWS = 20
_CANDIDATE_DELIMITERS = [",", ";", "\t", "|"]


class CSVProcessor:
    """FileProcessor implementation for CSV files.

    Detects delimiter automatically, applies header heuristics, and
    produces normalized datasets with per-row source traceability.
    """

    def can_process(self, file_type: str) -> bool:
        """Return True for CSV file type.

        Args:
            file_type: File extension identifier.

        Returns:
            True if file_type is "csv".
        """
        return file_type == "csv"

    async def inspect(self, file_path: str) -> InspectionResult:
        """Inspect CSV file structure and detect content regions.

        Reads the file, detects delimiter, parses rows, and applies header
        detection heuristics. Returns a single DetectedRegion for the full file.

        Args:
            file_path: Path to the CSV file on disk.

        Returns:
            InspectionResult with a single detected region.

        Raises:
            FileProcessingError: If the file cannot be read or parsed.
        """
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise FileProcessingError(
                file_name=file_path,
                message=f"CSV file is not valid UTF-8: {exc}",
                detail=str(exc),
            ) from exc
        except OSError as exc:
            raise FileProcessingError(
                file_name=file_path,
                message=f"Failed to read CSV file: {exc}",
                detail=str(exc),
            ) from exc

        if not content.strip():
            raise FileProcessingError(
                file_name=file_path,
                message="CSV file is empty",
            )

        # Detect delimiter from a sample of the content
        delimiter = self._detect_delimiter(content)

        # Parse all rows
        reader = csv.reader(io.StringIO(content), delimiter=delimiter)
        rows: list[list[str]] = []
        for row in reader:
            rows.append(row)

        if not rows:
            raise FileProcessingError(
                file_name=file_path,
                message="CSV file contains no parseable rows",
            )

        # Detect header
        header_result = self._detect_header(rows)

        # Build content sample (first 20 rows)
        content_sample = [
            [str(cell) for cell in row]
            for row in rows[:_MAX_SAMPLE_ROWS]
        ]

        row_count = len(rows)
        column_count = max(len(row) for row in rows) if rows else 0

        file_name = Path(file_path).name

        region = DetectedRegion(
            region_id=f"csv_0_{row_count}_0_{column_count}",
            sheet_name="csv",
            start_row=0,
            end_row=row_count,
            start_column=0,
            end_column=column_count,
            header_row=header_result.header_row if header_result.confidence > 0.3 else None,
            content_sample=content_sample,
            row_count=row_count,
            column_count=column_count,
            raw_text=content,
        )

        return InspectionResult(
            file_name=file_name,
            file_type="csv",
            regions=[region],
            metadata={
                "delimiter": repr(delimiter),
                "row_count": str(row_count),
                "column_count": str(column_count),
            },
        )

    async def extract(
        self, file_path: str, region: DetectedRegion | None = None
    ) -> NormalizedDataset:
        """Extract and normalize CSV data into records.

        Uses detected header to produce records as list of dicts with
        source traceability (source_sheet="csv", source_row per record).

        Args:
            file_path: Path to the CSV file on disk.
            region: Optional region (ignored for CSV — always full file).

        Returns:
            NormalizedDataset with columns, records, and source traceability.

        Raises:
            FileProcessingError: If extraction fails.
        """
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            raise FileProcessingError(
                file_name=file_path,
                message=f"Failed to read CSV for extraction: {exc}",
                detail=str(exc),
            ) from exc

        delimiter = self._detect_delimiter(content)
        reader = csv.reader(io.StringIO(content), delimiter=delimiter)
        rows: list[list[str]] = list(reader)

        if not rows:
            raise FileProcessingError(
                file_name=file_path,
                message="CSV file contains no data rows for extraction",
            )

        # Detect header
        header_result = self._detect_header(rows)
        header_row_idx = header_result.header_row

        # Build column names from header row
        header_values = rows[header_row_idx] if header_row_idx < len(rows) else []
        column_names: list[str] = []
        for idx, val in enumerate(header_values):
            name = val.strip() if val and val.strip() else f"column_{idx}"
            column_names.append(name)

        # Infer schema from data rows
        data_start = header_row_idx + 1
        data_rows = rows[data_start:]
        columns = self._infer_schema(column_names, data_rows)

        # Build records with source traceability
        records: list[dict[str, Any]] = []
        for row_offset, row in enumerate(data_rows):
            record: dict[str, Any] = {}
            for col_idx, col_name in enumerate(column_names):
                value = row[col_idx] if col_idx < len(row) else None
                record[col_name] = value
            # Include source traceability
            record["__source_sheet"] = "csv"
            record["__source_row"] = data_start + row_offset
            records.append(record)

        file_name = Path(file_path).name
        return NormalizedDataset(
            dataset_id=None,
            source_file_id="",
            sheet_name="csv",
            columns=columns,
            records=records,
            classification="STRUCTURED",
            source_location=f"{file_name}:rows {data_start + 1}-{len(rows)}",
            confidence=header_result.confidence,
            warnings=header_result.warnings,
        )

    def validate(self, normalized: NormalizedDataset) -> list[ValidationWarning]:
        """Validate column consistency across records.

        Checks that all records have the expected number of columns and
        flags inconsistencies.

        Args:
            normalized: The normalized dataset to validate.

        Returns:
            List of validation warnings.
        """
        warnings: list[ValidationWarning] = []
        expected_cols = len(normalized.columns)

        # Check for empty column names
        for col in normalized.columns:
            if not col.name or not col.name.strip():
                warnings.append(
                    ValidationWarning(
                        field=f"column_{col.column_index}",
                        message=f"Column at index {col.column_index} has empty name",
                        severity="warning",
                    )
                )

        # Check for duplicate column names
        seen: set[str] = set()
        for col in normalized.columns:
            if col.name in seen:
                warnings.append(
                    ValidationWarning(
                        field=col.name,
                        message=f"Duplicate column name: '{col.name}'",
                        severity="warning",
                    )
                )
            seen.add(col.name)

        # Check record column consistency (exclude __source_ keys)
        for idx, record in enumerate(normalized.records):
            data_keys = [k for k in record if not k.startswith("__source_")]
            if len(data_keys) != expected_cols:
                warnings.append(
                    ValidationWarning(
                        field=f"row_{idx}",
                        message=(
                            f"Row {idx} has {len(data_keys)} columns, "
                            f"expected {expected_cols}"
                        ),
                        severity="warning",
                    )
                )
                if idx >= 5:
                    break

        return warnings

    # -------------------------------------------------------------------------
    # Internal methods
    # -------------------------------------------------------------------------

    def _detect_delimiter(self, sample: str) -> str:
        """Detect the most likely delimiter by consistency of column counts.

        Tries each candidate delimiter on the first several lines and picks
        the one that produces the most consistent (non-trivial) column count.

        Args:
            sample: Raw text content of the CSV file.

        Returns:
            The detected delimiter character.
        """
        # Use first 20 lines for detection
        lines = sample.splitlines()[:_MAX_SAMPLE_ROWS]
        non_empty_lines = [line for line in lines if line.strip()]

        if not non_empty_lines:
            return ","

        best_delimiter = ","
        best_score = -1.0

        for delimiter in _CANDIDATE_DELIMITERS:
            col_counts: list[int] = []
            for line in non_empty_lines:
                # Use csv.reader for proper quote handling
                reader = csv.reader(io.StringIO(line), delimiter=delimiter)
                try:
                    row = next(reader)
                    col_counts.append(len(row))
                except StopIteration:
                    col_counts.append(0)

            if not col_counts:
                continue

            # Score: prefer delimiters that produce consistent, multi-column results
            most_common_count = max(set(col_counts), key=col_counts.count)
            consistency = col_counts.count(most_common_count) / len(col_counts)

            # Penalize single-column results (no split happening)
            if most_common_count <= 1:
                score = 0.0
            else:
                score = consistency * most_common_count

            if score > best_score:
                best_score = score
                best_delimiter = delimiter

        return best_delimiter

    def _detect_header(self, rows: list[list[str]]) -> HeaderDetectionResult:
        """Detect the header row using heuristics similar to ExcelProcessor.

        Heuristics:
        - Text density: header should be mostly text (not numeric)
        - Uniqueness: header cells should be unique
        - Type consistency below: data rows should have consistent types per column

        Args:
            rows: All parsed CSV rows as lists of strings.

        Returns:
            HeaderDetectionResult with header row index, confidence, and reason.
        """
        if not rows:
            return HeaderDetectionResult(
                header_row=0,
                confidence=0.0,
                detection_reason="No rows available",
                warnings=["CSV file has no rows"],
            )

        best_row = 0
        best_score = 0.0
        best_reason = "Default to first row"
        warnings: list[str] = []

        # Check first few rows as candidates
        candidate_limit = min(5, len(rows))

        for candidate_idx in range(candidate_limit):
            candidate_values = rows[candidate_idx]
            score = self._score_header_candidate(rows, candidate_idx, candidate_values)

            if score > best_score:
                best_score = score
                best_row = candidate_idx
                non_empty = [v for v in candidate_values if v.strip()]
                best_reason = (
                    f"Row {candidate_idx} selected as header (score={score:.2f}): "
                    f"{len(non_empty)} non-empty cells with text content"
                )

        confidence = min(1.0, best_score)
        if confidence < 0.5:
            warnings.append(
                "Low confidence header detection — CSV may not have a clear header"
            )

        return HeaderDetectionResult(
            header_row=best_row,
            confidence=round(confidence, 4),
            detection_reason=best_reason,
            warnings=warnings,
        )

    def _score_header_candidate(
        self,
        rows: list[list[str]],
        candidate_idx: int,
        candidate_values: list[str],
    ) -> float:
        """Score a candidate row's likelihood of being a header.

        Args:
            rows: All parsed rows.
            candidate_idx: Index of the candidate row.
            candidate_values: Values of the candidate row.

        Returns:
            Score between 0.0 and 1.0.
        """
        score = 0.0
        non_empty = [v for v in candidate_values if v.strip()]

        if not non_empty:
            return 0.0

        # Signal 1: Text density (non-numeric cells)
        text_count = sum(1 for v in non_empty if not self._looks_numeric(v))
        text_ratio = text_count / len(non_empty)
        score += text_ratio * 0.30

        # Signal 2: Uniqueness of values
        unique_count = len(set(non_empty))
        uniqueness = unique_count / len(non_empty) if non_empty else 0
        score += uniqueness * 0.25

        # Signal 3: Fill rate
        total_cols = max(len(row) for row in rows) if rows else 1
        fill_rate = len(non_empty) / total_cols if total_cols > 0 else 0
        score += fill_rate * 0.15

        # Signal 4: Data type consistency below
        data_rows = rows[candidate_idx + 1: candidate_idx + 11]
        if data_rows:
            consistency = self._check_type_consistency_below(
                data_rows, len(candidate_values)
            )
            score += consistency * 0.20

        # Signal 5: Header cells tend to be shorter labels
        if non_empty and data_rows:
            header_avg_len = sum(len(v) for v in non_empty) / len(non_empty)
            data_lengths: list[int] = []
            for row in data_rows[:5]:
                for cell in row:
                    if cell.strip():
                        data_lengths.append(len(cell))
            data_avg_len = (
                sum(data_lengths) / len(data_lengths) if data_lengths else 0
            )
            if data_avg_len > 0 and header_avg_len <= data_avg_len * 1.5:
                score += 0.10
            elif header_avg_len <= 50:
                score += 0.05

        return min(1.0, score)

    def _check_type_consistency_below(
        self, data_rows: list[list[str]], col_count: int
    ) -> float:
        """Check type consistency in data rows below the candidate header.

        Args:
            data_rows: Rows below the candidate header.
            col_count: Expected number of columns.

        Returns:
            Score 0.0 to 1.0 indicating consistency.
        """
        if not data_rows or col_count == 0:
            return 0.0

        consistent_cols = 0

        for col_idx in range(col_count):
            types_seen: set[str] = set()
            for row in data_rows:
                if col_idx < len(row) and row[col_idx].strip():
                    types_seen.add(self._classify_value_type(row[col_idx]))
            # Consistent if 1-2 types
            if len(types_seen) <= 2:
                consistent_cols += 1

        return consistent_cols / col_count

    def _infer_schema(
        self, column_names: list[str], data_rows: list[list[str]]
    ) -> list[ColumnSchema]:
        """Infer column types from data rows.

        Args:
            column_names: Column names from the header.
            data_rows: Data rows below the header.

        Returns:
            List of ColumnSchema for each column.
        """
        columns: list[ColumnSchema] = []
        rows_to_check = data_rows[:50]

        for col_idx, col_name in enumerate(column_names):
            type_counts: dict[str, int] = {}
            sample_values: list[str] = []
            has_null = False

            for row in rows_to_check:
                value = row[col_idx] if col_idx < len(row) else ""
                if not value.strip():
                    has_null = True
                    continue

                value_type = self._classify_value_type(value)
                type_counts[value_type] = type_counts.get(value_type, 0) + 1

                if len(sample_values) < 5:
                    sample_values.append(value.strip())

            # Determine dominant type
            if type_counts:
                dominant_type = max(type_counts, key=type_counts.get)  # type: ignore[arg-type]
                total = sum(type_counts.values())
                confidence = type_counts[dominant_type] / total
            else:
                dominant_type = "string"
                confidence = 0.5

            columns.append(
                ColumnSchema(
                    name=col_name,
                    data_type=dominant_type,
                    nullable=has_null,
                    column_index=col_idx,
                    sample_values=sample_values,
                    confidence=round(confidence, 4),
                )
            )

        return columns

    @staticmethod
    def _looks_numeric(value: str) -> bool:
        """Check if a value looks numeric (integer, decimal, or percentage)."""
        clean = value.strip().rstrip("%").replace(",", "").replace(" ", "")
        if not clean:
            return False
        try:
            float(clean)
            return True
        except ValueError:
            return False

    @staticmethod
    def _classify_value_type(value: str) -> str:
        """Classify a string value into a type category.

        Args:
            value: The string value to classify.

        Returns:
            One of: "integer", "decimal", "boolean", "date", "string".
        """
        stripped = value.strip()
        if not stripped:
            return "string"

        # Boolean
        if stripped.lower() in ("true", "false", "yes", "no", "1", "0"):
            return "boolean"

        # Numeric
        clean = stripped.replace(",", "").rstrip("%")
        try:
            num = float(clean)
            if "." in clean or "e" in clean.lower():
                return "decimal"
            return "integer"
        except ValueError:
            pass

        # Date-like patterns (simple heuristic)
        if any(sep in stripped for sep in ["/", "-"]) and len(stripped) <= 20:
            parts = stripped.replace("/", "-").split("-")
            if len(parts) >= 3 and all(
                p.strip().isdigit() for p in parts[:3]
            ):
                return "date"

        return "string"
