"""
JSONProcessor — FileProcessor implementation for JSON files.

Parses JSON content, identifies root structure (array vs object),
flattens nested objects to dot-notation keys, and produces normalized
datasets with source traceability via JSON paths.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.errors.ingestion_errors import FileProcessingError
from app.processors.protocol import (
    ColumnSchema,
    DetectedRegion,
    InspectionResult,
    NormalizedDataset,
    ValidationWarning,
)

logger = logging.getLogger(__name__)

# Configuration
_MAX_SAMPLE_ROWS = 20
_MAX_FLATTEN_DEPTH = 2


class JSONProcessor:
    """FileProcessor implementation for JSON files.

    Handles JSON arrays of objects (tabular datasets) and single JSON objects
    (wrapped as single-record datasets). Nested objects are flattened to
    dot-notation keys up to 2 levels deep.
    """

    def can_process(self, file_type: str) -> bool:
        """Return True for JSON file type.

        Args:
            file_type: File extension identifier.

        Returns:
            True if file_type is "json".
        """
        return file_type == "json"

    async def inspect(self, file_path: str) -> InspectionResult:
        """Inspect JSON file and detect content structure.

        Parses the JSON, validates syntax, identifies root structure (array vs
        object), builds content samples from the first 20 records, and infers
        column schema from keys and value types.

        Args:
            file_path: Path to the JSON file on disk.

        Returns:
            InspectionResult with a single detected region.

        Raises:
            FileProcessingError: If JSON is invalid or file cannot be read.
        """
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise FileProcessingError(
                file_name=file_path,
                message=f"JSON file is not valid UTF-8: {exc}",
                detail=str(exc),
            ) from exc
        except OSError as exc:
            raise FileProcessingError(
                file_name=file_path,
                message=f"Failed to read JSON file: {exc}",
                detail=str(exc),
            ) from exc

        if not content.strip():
            raise FileProcessingError(
                file_name=file_path,
                message="JSON file is empty",
            )

        # Parse JSON — raise on syntax error
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise FileProcessingError(
                file_name=file_path,
                message=f"Invalid JSON syntax: {exc}",
                detail=str(exc),
            ) from exc

        # Identify root structure and normalize to records
        root_structure = self._identify_root_structure(data)
        records = self._normalize_to_records(data, root_structure)

        if not records:
            raise FileProcessingError(
                file_name=file_path,
                message="JSON file contains no processable records",
            )

        # Flatten records for tabular representation
        flat_records = self._flatten_records(records, max_depth=_MAX_FLATTEN_DEPTH)

        # Collect all keys across records for column schema
        all_keys: list[str] = []
        seen_keys: set[str] = set()
        for record in flat_records:
            for key in record:
                if key not in seen_keys:
                    all_keys.append(key)
                    seen_keys.add(key)

        # Build content sample (first 20 records as list of values)
        content_sample: list[list[str]] = []
        # First row is column names (header)
        content_sample.append(all_keys)
        for record in flat_records[:_MAX_SAMPLE_ROWS]:
            row = [str(record.get(key, "")) for key in all_keys]
            content_sample.append(row)

        row_count = len(flat_records) + 1  # +1 for header
        column_count = len(all_keys)
        file_name = Path(file_path).name

        region = DetectedRegion(
            region_id=f"json_0_{row_count}_0_{column_count}",
            sheet_name="json",
            start_row=0,
            end_row=row_count,
            start_column=0,
            end_column=column_count,
            header_row=0,  # JSON keys are always the header
            content_sample=content_sample,
            row_count=row_count,
            column_count=column_count,
            raw_text=content,
        )

        return InspectionResult(
            file_name=file_name,
            file_type="json",
            regions=[region],
            metadata={
                "root_structure": root_structure,
                "record_count": str(len(records)),
                "column_count": str(column_count),
            },
        )

    async def extract(
        self, file_path: str, region: DetectedRegion | None = None
    ) -> NormalizedDataset:
        """Extract and normalize JSON data into records.

        Parses JSON, normalizes records, and flattens nested objects to
        dot-notation keys. Provides JSON path per record for source traceability.

        Args:
            file_path: Path to the JSON file on disk.
            region: Optional region (ignored for JSON — always full file).

        Returns:
            NormalizedDataset with columns, records, and source traceability.

        Raises:
            FileProcessingError: If extraction fails.
        """
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            data = json.loads(content)
        except (UnicodeDecodeError, OSError, json.JSONDecodeError) as exc:
            raise FileProcessingError(
                file_name=file_path,
                message=f"Failed to read JSON for extraction: {exc}",
                detail=str(exc),
            ) from exc

        root_structure = self._identify_root_structure(data)
        records = self._normalize_to_records(data, root_structure)
        flat_records = self._flatten_records(records, max_depth=_MAX_FLATTEN_DEPTH)

        if not flat_records:
            raise FileProcessingError(
                file_name=file_path,
                message="JSON file contains no data for extraction",
            )

        # Collect all keys across flat records
        all_keys: list[str] = []
        seen_keys: set[str] = set()
        for record in flat_records:
            for key in record:
                if key not in seen_keys:
                    all_keys.append(key)
                    seen_keys.add(key)

        # Infer schema
        columns = self._infer_schema(all_keys, flat_records)

        # Build records with source traceability (JSON path)
        output_records: list[dict[str, Any]] = []
        for idx, record in enumerate(flat_records):
            output_record: dict[str, Any] = {}
            for key in all_keys:
                output_record[key] = record.get(key)

            # JSON path traceability
            if root_structure == "array":
                output_record["__source_sheet"] = "json"
                output_record["__source_row"] = idx
            else:
                output_record["__source_sheet"] = "json"
                output_record["__source_row"] = 0

            output_records.append(output_record)

        file_name = Path(file_path).name
        return NormalizedDataset(
            dataset_id=None,
            source_file_id="",
            sheet_name="json",
            columns=columns,
            records=output_records,
            classification="STRUCTURED",
            source_location=f"{file_name}:{root_structure}[0..{len(flat_records) - 1}]",
            confidence=0.9,
            warnings=[],
        )

    def validate(self, normalized: NormalizedDataset) -> list[ValidationWarning]:
        """Validate a normalized JSON dataset for consistency.

        Checks column presence and data completeness.

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

        # Check record completeness (exclude __source_ keys)
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

    def _identify_root_structure(self, data: Any) -> str:
        """Identify whether the JSON root is an array or object.

        Args:
            data: Parsed JSON data.

        Returns:
            "array" if root is a list, "object" otherwise.
        """
        if isinstance(data, list):
            return "array"
        return "object"

    def _normalize_to_records(self, data: Any, root_structure: str) -> list[dict]:
        """Normalize JSON data to a list of record dicts.

        - Array of objects with consistent keys → records as-is
        - Single object → wrap as single-record dataset
        - Array of non-objects → wrap each as {"value": item}

        Args:
            data: Parsed JSON data.
            root_structure: "array" or "object".

        Returns:
            List of record dictionaries.
        """
        if root_structure == "array":
            if not data:
                return []
            # Check if array items are objects
            if isinstance(data[0], dict):
                return [item for item in data if isinstance(item, dict)]
            # Array of primitives — wrap each
            return [{"value": item} for item in data]
        else:
            # Single object — wrap as one record
            if isinstance(data, dict):
                return [data]
            return [{"value": data}]

    def _flatten_records(
        self, records: list[dict], max_depth: int = 2
    ) -> list[dict]:
        """Flatten nested objects to dot-notation keys.

        Only flattens dict values up to max_depth levels deep.
        Lists and other non-dict values are converted to string representation.

        Args:
            records: List of record dictionaries (potentially nested).
            max_depth: Maximum nesting depth to flatten (default 2).

        Returns:
            List of flattened record dictionaries.
        """
        return [self._flatten_single(record, max_depth) for record in records]

    def _flatten_single(
        self, obj: dict, max_depth: int, prefix: str = "", depth: int = 0
    ) -> dict:
        """Flatten a single nested dict to dot-notation keys.

        Args:
            obj: The dictionary to flatten.
            max_depth: Maximum depth for flattening.
            prefix: Current key prefix for recursion.
            depth: Current recursion depth.

        Returns:
            Flattened dictionary.
        """
        flat: dict[str, Any] = {}

        for key, value in obj.items():
            full_key = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"

            if isinstance(value, dict) and depth < max_depth:
                # Recurse into nested dict
                nested = self._flatten_single(
                    value, max_depth, full_key, depth + 1
                )
                flat.update(nested)
            elif isinstance(value, list):
                # Convert lists to string representation
                flat[full_key] = json.dumps(value)
            else:
                flat[full_key] = value

        return flat

    def _infer_schema(
        self, column_names: list[str], records: list[dict]
    ) -> list[ColumnSchema]:
        """Infer column types from record values.

        Args:
            column_names: Ordered list of column names.
            records: Flattened records to analyze.

        Returns:
            List of ColumnSchema for each column.
        """
        columns: list[ColumnSchema] = []
        rows_to_check = records[:50]

        for col_idx, col_name in enumerate(column_names):
            type_counts: dict[str, int] = {}
            sample_values: list[str] = []
            has_null = False

            for record in rows_to_check:
                value = record.get(col_name)
                if value is None:
                    has_null = True
                    continue

                value_type = self._classify_json_value_type(value)
                type_counts[value_type] = type_counts.get(value_type, 0) + 1

                if len(sample_values) < 5:
                    sample_values.append(str(value)[:100])

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
    def _classify_json_value_type(value: Any) -> str:
        """Classify a JSON value into a type category.

        Args:
            value: The value to classify.

        Returns:
            One of: "integer", "decimal", "boolean", "string".
        """
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "decimal"
        if isinstance(value, str):
            # Try to detect numeric strings
            stripped = value.strip()
            if not stripped:
                return "string"
            try:
                num = float(stripped.replace(",", ""))
                if "." in stripped:
                    return "decimal"
                return "integer"
            except ValueError:
                pass
            # Date-like
            if any(sep in stripped for sep in ["/", "-"]) and len(stripped) <= 20:
                parts = stripped.replace("/", "-").split("-")
                if len(parts) >= 3 and all(
                    p.strip().isdigit() for p in parts[:3]
                ):
                    return "date"
            return "string"
        return "string"
