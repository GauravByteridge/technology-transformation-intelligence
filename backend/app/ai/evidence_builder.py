"""
Evidence Builder — Converts tool execution results into structured evidence items.

Responsible for:
- Converting raw tool results (from query_connected_source, search_documents) into
  structured EvidenceItems with full source traceability.
- Classifying the groundedness of claims based on available evidence.

Key Principle: No fabrication — evidence is only built from actual tool execution
results. If a tool was not called, no evidence is generated for it.

Security Invariant: Evidence items never contain credentials, connection strings,
or API keys. Only business-level data values and metadata are included.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Patterns that suggest a value was derived through calculation rather than
# directly retrieved from a data source.
_CALCULATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bvariance\b"),
    re.compile(r"(?i)\bdelta\b"),
    re.compile(r"(?i)\bdifference\b"),
    re.compile(r"(?i)\bpercentage\b"),
    re.compile(r"(?i)\bpercent\b"),
    re.compile(r"(?i)\b%\b"),
    re.compile(r"(?i)\bgrowth\b"),
    re.compile(r"(?i)\bchange\b"),
    re.compile(r"(?i)\bratio\b"),
    re.compile(r"(?i)\baverage\b"),
    re.compile(r"(?i)\bmean\b"),
    re.compile(r"(?i)\bmedian\b"),
    re.compile(r"(?i)\bsum\b"),
    re.compile(r"(?i)\btotal\b"),
    re.compile(r"(?i)\bcount\b"),
    re.compile(r"(?i)\brate\b"),
]

# Maximum number of rows to include in the records_summary
_MAX_SUMMARY_ROWS: int = 5

# Maximum excerpt length for data values
_MAX_EXCERPT_LENGTH: int = 500


class EvidenceBuilder:
    """Builds structured evidence items from tool execution results.

    Every evidence item corresponds to actually retrieved data.
    No fabrication — if a tool was not called, no evidence is generated for it.

    The tool_results list comes from the Cross_Source_Orchestrator after
    Strands tool execution. Each item is either:
    - A query_connected_source result (columns, rows, source_metadata)
    - A search_documents result (chunks, document_id, file_name, excerpt)
    """

    def build_evidence(self, tool_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert tool execution results into structured evidence items.

        Each evidence item links to specific retrieved data with full
        source traceability (source_id, table/collection, columns, records).

        Args:
            tool_results: List of result dicts from tool executions.
                Each dict is either a query_connected_source result or
                a search_documents result.

        Returns:
            List of structured evidence item dicts. Empty list if no
            valid results are provided.
        """
        evidence_items: list[dict[str, Any]] = []

        if not tool_results:
            return evidence_items

        for result in tool_results:
            if not isinstance(result, dict):
                logger.warning(
                    "evidence_builder_skipping_invalid_result",
                    extra={"result_type": type(result).__name__},
                )
                continue

            # Skip error results — no evidence from failed tool executions
            if result.get("error"):
                continue

            evidence_item = self._build_single_evidence(result)
            if evidence_item is not None:
                evidence_items.append(evidence_item)

        logger.info(
            "evidence_built",
            extra={"total_evidence_items": len(evidence_items)},
        )

        return evidence_items

    def classify_groundedness(self, claim: str, evidence: dict[str, Any]) -> str:
        """Classify how grounded a claim is based on available evidence.

        Heuristic classification:
        - "retrieved_fact": Evidence contains actual data values directly from a source.
        - "derived_calculation": Evidence contains calculated/aggregated values
          (variance, percentage, delta, etc.).
        - "ai_explanation": No supporting evidence or evidence is empty.

        Args:
            claim: The claim text to classify.
            evidence: The evidence dict supporting the claim. May be empty.

        Returns:
            One of: "retrieved_fact", "derived_calculation", "ai_explanation".
        """
        # No evidence at all → AI explanation
        if not evidence:
            return "ai_explanation"

        # Check if the evidence has actual data
        excerpt = evidence.get("excerpt", "")
        records_summary = evidence.get("records_summary")
        column_names = evidence.get("column_names") or []

        has_data = bool(excerpt) or bool(records_summary)

        if not has_data:
            return "ai_explanation"

        # Check if the claim or evidence columns suggest a calculation
        text_to_check = f"{claim} {excerpt} {' '.join(column_names)}"
        if self._contains_calculation_indicator(text_to_check):
            return "derived_calculation"

        # Has real data values → retrieved fact
        return "retrieved_fact"

    def _build_single_evidence(self, result: dict[str, Any]) -> dict[str, Any] | None:
        """Build a single evidence item from one tool result.

        Determines the result type (database query vs document search) and
        delegates to the appropriate builder method.

        Args:
            result: A single tool result dict.

        Returns:
            Structured evidence item dict, or None if the result cannot
            be converted to evidence.
        """
        # Determine result type based on structure
        if "source_metadata" in result and "columns" in result:
            return self._build_database_evidence(result)
        elif "document_id" in result or "file_name" in result or "chunks" in result:
            return self._build_document_evidence(result)
        else:
            logger.debug(
                "evidence_builder_unknown_result_format",
                extra={"keys": list(result.keys())},
            )
            return None

    def _build_database_evidence(self, result: dict[str, Any]) -> dict[str, Any]:
        """Build evidence from a query_connected_source result.

        Expected structure:
        {
            "columns": [...],
            "rows": [...],
            "row_count": N,
            "source_metadata": {
                "source_id": "...",
                "source_type": "...",
                "source_name": "...",
                "object_name": "..."
            },
            "duration_ms": N
        }

        Args:
            result: A query_connected_source result dict.

        Returns:
            Structured evidence item dict.
        """
        source_metadata = result.get("source_metadata", {})
        source_type = source_metadata.get("source_type", "unknown")
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        row_count = result.get("row_count", len(rows))

        # Build record reference
        record_reference = self._build_record_reference(row_count)

        # Build records summary (first few rows)
        records_summary = self._build_records_summary(columns, rows)

        # Build excerpt from data values
        excerpt = self._build_data_excerpt(columns, rows)

        evidence_item: dict[str, Any] = {
            "evidence_id": str(uuid.uuid4()),
            "source_id": source_metadata.get("source_id", ""),
            "source_type": source_type,
            "source_name": source_metadata.get("source_name", ""),
            "object_name": source_metadata.get("object_name", ""),
            "column_names": columns,
            "record_reference": record_reference,
            "records_summary": records_summary,
            "excerpt": excerpt,
            "confidence": "retrieved_fact",
        }

        # Add source-type-specific fields
        if source_type == "postgresql":
            evidence_item["database_name"] = source_metadata.get("database_name")
            evidence_item["schema_name"] = source_metadata.get("schema_name")
            evidence_item["table_name"] = source_metadata.get("object_name", "")
        elif source_type == "mongodb":
            evidence_item["collection_name"] = source_metadata.get("object_name", "")

        return evidence_item

    def _build_document_evidence(self, result: dict[str, Any]) -> dict[str, Any]:
        """Build evidence from a search_documents result.

        Expected structure:
        {
            "chunks": [...],
            "document_id": "...",
            "file_name": "...",
            "page_number": N,
            "section": "...",
            "excerpt": "..."
        }

        Or from chunk-level results within a chunks list.

        Args:
            result: A search_documents result dict.

        Returns:
            Structured evidence item dict.
        """
        # Extract document metadata
        document_id = result.get("document_id", "")
        file_name = result.get("file_name", "")
        page_number = result.get("page_number")
        section = result.get("section")
        sheet_name = result.get("sheet_name")
        excerpt = result.get("excerpt", "")

        # If chunks are provided and no excerpt, build from chunks
        chunks = result.get("chunks", [])
        if not excerpt and chunks:
            excerpt = self._build_excerpt_from_chunks(chunks)

        # Build record reference for documents
        record_reference = self._build_document_reference(page_number, section, sheet_name)

        # Source metadata might be present in document results too
        source_metadata = result.get("source_metadata", {})

        evidence_item: dict[str, Any] = {
            "evidence_id": str(uuid.uuid4()),
            "source_id": source_metadata.get("source_id", ""),
            "source_type": source_metadata.get("source_type", "document"),
            "source_name": source_metadata.get("source_name", file_name),
            "object_name": file_name,
            "document_id": document_id,
            "file_name": file_name,
            "page_number": page_number,
            "sheet_name": sheet_name,
            "section": section,
            "record_reference": record_reference,
            "excerpt": excerpt[:_MAX_EXCERPT_LENGTH] if excerpt else "",
            "confidence": "retrieved_fact",
        }

        return evidence_item

    def _build_record_reference(self, row_count: int) -> str:
        """Build a human-readable record reference string.

        Args:
            row_count: Number of rows in the result.

        Returns:
            Reference string like "rows 1-5" or "1 row".
        """
        if row_count == 0:
            return "no records"
        elif row_count == 1:
            return "1 row"
        else:
            display_count = min(row_count, _MAX_SUMMARY_ROWS)
            return f"rows 1-{display_count}" if row_count > 1 else "1 row"

    def _build_document_reference(
        self,
        page_number: int | None,
        section: str | None,
        sheet_name: str | None,
    ) -> str:
        """Build a human-readable reference for a document evidence item.

        Args:
            page_number: Page number if available.
            section: Section name if available.
            sheet_name: Excel sheet name if available.

        Returns:
            Reference string like "page 3" or "sheet: Budget, section: Summary".
        """
        parts: list[str] = []

        if sheet_name:
            parts.append(f"sheet: {sheet_name}")
        if page_number is not None:
            parts.append(f"page {page_number}")
        if section:
            parts.append(f"section: {section}")

        return ", ".join(parts) if parts else "document"

    def _build_records_summary(
        self, columns: list[str], rows: list[Any]
    ) -> dict[str, Any]:
        """Build a summary dict with the first few rows of data.

        Args:
            columns: Column names from the result.
            rows: Row data from the result.

        Returns:
            Dict with column_names and first N rows as list of dicts.
        """
        summary_rows = rows[:_MAX_SUMMARY_ROWS]

        formatted_rows: list[dict[str, Any]] = []
        for row in summary_rows:
            if isinstance(row, dict):
                formatted_rows.append(row)
            elif isinstance(row, (list, tuple)):
                # Map positional values to column names
                row_dict = {}
                for i, col in enumerate(columns):
                    if i < len(row):
                        row_dict[col] = row[i]
                formatted_rows.append(row_dict)
            else:
                formatted_rows.append({"value": row})

        return {
            "column_names": columns,
            "rows": formatted_rows,
            "total_rows": len(rows),
        }

    def _build_data_excerpt(self, columns: list[str], rows: list[Any]) -> str:
        """Build a formatted text excerpt from database query results.

        Creates a readable summary of the data values for display.

        Args:
            columns: Column names from the result.
            rows: Row data from the result.

        Returns:
            Formatted string excerpt of the data values.
        """
        if not rows:
            return "No data returned"

        lines: list[str] = []

        # Show first few rows as key-value pairs
        for row in rows[:_MAX_SUMMARY_ROWS]:
            if isinstance(row, dict):
                parts = [f"{k}: {v}" for k, v in row.items()]
            elif isinstance(row, (list, tuple)):
                parts = [
                    f"{columns[i]}: {row[i]}"
                    for i in range(min(len(columns), len(row)))
                ]
            else:
                parts = [str(row)]
            lines.append(", ".join(parts))

        excerpt = " | ".join(lines)
        return excerpt[:_MAX_EXCERPT_LENGTH]

    def _build_excerpt_from_chunks(self, chunks: list[Any]) -> str:
        """Build an excerpt from document chunks.

        Args:
            chunks: List of chunk dicts or strings from document search.

        Returns:
            Combined text excerpt from the chunks.
        """
        excerpts: list[str] = []

        for chunk in chunks[:3]:  # Limit to first 3 chunks
            if isinstance(chunk, dict):
                text = chunk.get("text", chunk.get("content", ""))
            elif isinstance(chunk, str):
                text = chunk
            else:
                continue

            if text:
                excerpts.append(text.strip())

        combined = " ... ".join(excerpts)
        return combined[:_MAX_EXCERPT_LENGTH]

    def _contains_calculation_indicator(self, text: str) -> bool:
        """Check if text contains patterns indicating a calculated value.

        Args:
            text: Text to check for calculation indicators.

        Returns:
            True if calculation patterns are found.
        """
        for pattern in _CALCULATION_PATTERNS:
            if pattern.search(text):
                return True
        return False
