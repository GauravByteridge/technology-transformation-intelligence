"""
ExcelPipelineGraph — LangGraph-style async node pipeline for Excel processing.

Replaces the inline synchronous openpyxl pipeline with discrete, observable
async nodes. Each node does exactly one thing, is non-blocking (all sync I/O
is offloaded to asyncio.to_thread), and updates the shared ExcelProcessingState.

Pipeline flow:
    READ_NODE → INSPECT_NODE → CLASSIFY_NODE → ROUTE
        ├── DATASET_NODE  (STRUCTURED / HYBRID)
        ├── RAG_NODE      (RAG / HYBRID)
        └── SKIP_NODE     (IGNORE / REVIEW_REQUIRED)
    → DONE / FAILED

Key design decisions:
- pandas.read_excel() replaces openpyxl cell-by-cell loops for bulk data reads.
  pandas is 10–100× faster for large sheets (uses openpyxl internally but
  reads entire rows in C rather than Python loops).
- asyncio.to_thread() keeps the event loop responsive for all sync I/O.
- The workbook is opened ONCE per pipeline run (not 3× as before).
- State is a plain dataclass — no external framework required.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.processors.content_classifier import ContentClassifier
from app.processors.excel_state import ExcelProcessingState
from app.processors.protocol import (
    ClassificationResult,
    ColumnSchema,
    DetectedRegion,
    HeaderDetectionResult,
    InspectionResult,
    NormalizedDataset,
)

if TYPE_CHECKING:
    from app.documents.orchestrator import IngestionOrchestrator
    from app.services.dataset_service import DatasetService

logger = logging.getLogger(__name__)

# ── Tuning constants ───────────────────────────────────────────────────────────
_MAX_SAMPLE_ROWS = 20
_MIN_REGION_ROWS = 1
_BLANK_ROW_THRESHOLD = 2   # Consecutive blank rows → new region
_BLANK_COL_THRESHOLD = 2   # Consecutive blank cols → new region


# =============================================================================
# Sync helpers (safe to call inside asyncio.to_thread)
# =============================================================================


def _sync_read_excel(file_path: str) -> dict[str, list[dict]]:
    """Read all sheets with pandas and return as {sheet_name → list-of-row-dicts}.

    Using pandas.read_excel is significantly faster than openpyxl cell-by-cell
    iteration for large files. Runs inside asyncio.to_thread so it never blocks
    the event loop.

    Each row dict maps column names to Python native types. NaN / NaT are
    converted to None so downstream code does not need to import pandas.
    """
    import pandas as pd  # noqa: PLC0415  (deferred — not all code paths need pandas)

    result: dict[str, list[dict]] = {}

    try:
        all_sheets: dict[str, Any] = pd.read_excel(
            file_path,
            sheet_name=None,   # read every sheet
            header=None,       # we detect headers ourselves
            dtype=str,         # keep everything as strings initially; avoids type-coercion surprises
            na_filter=False,   # keep empty strings, don't convert to NaN
            engine="openpyxl",
        )
    except Exception as exc:
        raise RuntimeError(f"pandas.read_excel failed: {exc}") from exc

    for sheet_name, df in all_sheets.items():
        # Replace empty strings with None for consistency with openpyxl behaviour
        rows: list[dict] = []
        for _, row in df.iterrows():
            row_dict: dict[str, Any] = {}
            for col_idx, val in enumerate(row):
                # pandas column names are 0-based ints when header=None
                str_val = str(val).strip() if val is not None and str(val).strip() else None
                row_dict[col_idx] = str_val
            rows.append(row_dict)
        result[sheet_name] = rows

    return result


def _inspect_sheet_data(
    sheet_name: str,
    rows: list[dict],
) -> list[DetectedRegion]:
    """Detect contiguous populated regions within a single sheet's row data.

    Uses the same region-splitting logic as the original ExcelProcessor but
    operates on plain Python dicts (from pandas) rather than openpyxl cell
    objects. This keeps the function pure and fast.

    Args:
        sheet_name: The name of the worksheet.
        rows: List of row dicts {col_int → value_str | None}.

    Returns:
        List of DetectedRegion instances.
    """
    if not rows:
        return []

    num_cols = max((len(r) for r in rows), default=0)

    def row_has_content(row_dict: dict) -> bool:
        return any(v is not None and str(v).strip() for v in row_dict.values())

    def cell_val(row_dict: dict, col_idx: int) -> str | None:
        val = row_dict.get(col_idx)
        return val if val is not None and str(val).strip() else None

    # Find non-empty row indices
    non_empty_rows: list[int] = [
        i for i, r in enumerate(rows) if row_has_content(r)
    ]

    if not non_empty_rows:
        return []

    # Split into row groups by blank-row gaps
    row_groups: list[list[int]] = []
    current_group = [non_empty_rows[0]]
    for i in range(1, len(non_empty_rows)):
        if non_empty_rows[i] - non_empty_rows[i - 1] - 1 >= _BLANK_ROW_THRESHOLD:
            row_groups.append(current_group)
            current_group = [non_empty_rows[i]]
        else:
            current_group.append(non_empty_rows[i])
    if current_group:
        row_groups.append(current_group)

    regions: list[DetectedRegion] = []

    for group in row_groups:
        start_row = group[0]
        end_row = group[-1] + 1  # exclusive

        if end_row - start_row < _MIN_REGION_ROWS:
            continue

        # Find populated column range for this group
        populated_cols: list[int] = []
        for col_idx in range(num_cols):
            for row_idx in group:
                if cell_val(rows[row_idx], col_idx) is not None:
                    populated_cols.append(col_idx)
                    break

        if not populated_cols:
            continue

        # Split populated columns by blank-column gaps
        col_ranges: list[tuple[int, int]] = []
        range_start = populated_cols[0]
        prev_col = populated_cols[0]
        for i in range(1, len(populated_cols)):
            if populated_cols[i] - prev_col - 1 >= _BLANK_COL_THRESHOLD:
                col_ranges.append((range_start, prev_col + 1))  # exclusive end
                range_start = populated_cols[i]
            prev_col = populated_cols[i]
        col_ranges.append((range_start, prev_col + 1))

        for start_col, end_col in col_ranges:
            col_count = end_col - start_col
            row_count = end_row - start_row

            # Build content_sample (up to _MAX_SAMPLE_ROWS rows as string lists)
            sample_rows_count = min(_MAX_SAMPLE_ROWS, row_count)
            content_sample: list[list[str]] = []
            for ri in range(start_row, start_row + sample_rows_count):
                row_vals: list[str] = []
                for ci in range(start_col, end_col):
                    v = cell_val(rows[ri], ci)
                    row_vals.append(v if v is not None else "")
                content_sample.append(row_vals)

            # Build raw_text for classifier
            raw_lines: list[str] = []
            for ri in group:
                parts: list[str] = []
                for ci in range(start_col, end_col):
                    v = cell_val(rows[ri], ci)
                    if v:
                        parts.append(v)
                if parts:
                    raw_lines.append(" ".join(parts))
            raw_text = "\n".join(raw_lines)

            # Detect header row (first row of region that is mostly text)
            header_row = _detect_header_in_rows(rows, start_row, end_row, start_col, end_col)

            region_id = f"{sheet_name}_{start_row}_{end_row}_{start_col}_{end_col}"

            regions.append(
                DetectedRegion(
                    region_id=region_id,
                    sheet_name=sheet_name,
                    start_row=start_row,
                    end_row=end_row,
                    start_column=start_col,
                    end_column=end_col,
                    header_row=header_row,
                    content_sample=content_sample,
                    row_count=row_count,
                    column_count=col_count,
                    raw_text=raw_text,
                )
            )

    return regions


def _detect_header_in_rows(
    rows: list[dict],
    start_row: int,
    end_row: int,
    start_col: int,
    end_col: int,
) -> int | None:
    """Identify the header row within a region using text-density heuristics.

    Args:
        rows: All sheet rows.
        start_row, end_row: Row range (end exclusive).
        start_col, end_col: Column range (end exclusive).

    Returns:
        0-based row index of the best header candidate, or start_row.
    """
    candidates_to_check = min(5, end_row - start_row)
    best_row = start_row
    best_score = -1.0

    for offset in range(candidates_to_check):
        ri = start_row + offset
        vals = [
            rows[ri].get(ci) for ci in range(start_col, end_col)
        ]
        non_empty = [v for v in vals if v and str(v).strip()]
        if not non_empty:
            continue

        # Text density — headers are mostly non-numeric labels
        def looks_numeric(s: str) -> bool:
            try:
                float(s.replace(",", "").replace("$", "").replace("%", ""))
                return True
            except ValueError:
                return False

        text_count = sum(1 for v in non_empty if not looks_numeric(v))
        text_ratio = text_count / len(non_empty)
        uniqueness = len(set(non_empty)) / len(non_empty)
        fill_rate = len(non_empty) / (end_col - start_col)

        score = text_ratio * 0.4 + uniqueness * 0.3 + fill_rate * 0.3

        if score > best_score:
            best_score = score
            best_row = ri

    return best_row if best_score > 0.3 else start_row


def _extract_records_from_rows(
    rows: list[dict],
    region: DetectedRegion,
) -> tuple[list[ColumnSchema], list[dict[str, Any]]]:
    """Extract column schemas and records from a region using pandas-style rows.

    Args:
        rows: Full sheet rows from _sync_read_excel.
        region: The detected region.

    Returns:
        Tuple of (columns, records).
    """
    header_row = region.header_row if region.header_row is not None else region.start_row
    data_start = header_row + 1

    # Build column names from header row
    col_names: list[str] = []
    for ci in range(region.start_column, region.end_column):
        name = rows[header_row].get(ci) if header_row < len(rows) else None
        col_names.append(
            str(name).strip() if name and str(name).strip() else f"Column_{ci - region.start_column + 1}"
        )

    # Deduplicate column names
    seen: dict[str, int] = {}
    deduped: list[str] = []
    for name in col_names:
        if name in seen:
            seen[name] += 1
            deduped.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            deduped.append(name)
    col_names = deduped

    # Read data rows
    records: list[dict[str, Any]] = []
    for ri in range(data_start, region.end_row):
        if ri >= len(rows):
            break
        row_data: dict[str, Any] = {}
        for name, ci in zip(col_names, range(region.start_column, region.end_column)):
            row_data[name] = rows[ri].get(ci)
        records.append(row_data)

    # Infer column schemas
    columns: list[ColumnSchema] = []
    for col_idx, col_name in enumerate(col_names):
        values = [r.get(col_name) for r in records if r.get(col_name) is not None]
        data_type, confidence = _infer_column_type(values)
        columns.append(
            ColumnSchema(
                name=col_name,
                data_type=data_type,
                nullable=any(r.get(col_name) is None for r in records),
                column_index=col_idx,
                sample_values=[str(v) for v in values[:5]],
                confidence=confidence,
            )
        )

    return columns, records


def _infer_column_type(values: list[Any]) -> tuple[str, float]:
    """Infer data type from a list of sampled values."""
    if not values:
        return "unknown", 0.0

    type_counts: dict[str, int] = {}
    for v in values[:50]:
        if isinstance(v, bool):
            t = "boolean"
        elif isinstance(v, int):
            t = "integer"
        elif isinstance(v, float):
            t = "decimal"
        elif isinstance(v, datetime):
            t = "datetime"
        elif isinstance(v, date):
            t = "date"
        elif isinstance(v, str):
            s = v.strip()
            if s.lower() in ("true", "false", "yes", "no", "y", "n"):
                t = "boolean"
            else:
                cleaned = s.replace(",", "").replace("$", "").replace("%", "")
                try:
                    num = float(cleaned)
                    t = "integer" if "." not in cleaned and num == int(num) else "decimal"
                except ValueError:
                    t = "string"
        else:
            t = "string"
        type_counts[t] = type_counts.get(t, 0) + 1

    dominant = max(type_counts, key=type_counts.get)  # type: ignore[arg-type]
    confidence = type_counts[dominant] / len(values)
    return (dominant if confidence >= 0.6 else "string"), round(confidence, 4)


def _extract_text_from_rows(rows: list[dict], region: DetectedRegion) -> str:
    """Extract semantic text from an Excel region for RAG chunking and search.

    If the region has a header row or structured columns, it annotates each row
    with sheet and column names (e.g. `[Sheet: Summary, Row 2] Employee: John Doe | Dept: Eng`)
    so that embedding models and vector similarity search retain column context.
    """
    if not rows:
        return ""

    header_row = region.header_row if region.header_row is not None else region.start_row

    # Collect header names if available
    col_names: list[str] = []
    if header_row < len(rows):
        for ci in range(region.start_column, region.end_column):
            val = rows[header_row].get(ci)
            col_names.append(
                str(val).strip()
                if val is not None and str(val).strip()
                else f"Column_{ci - region.start_column + 1}"
            )

    has_header = region.header_row is not None and region.row_count > 1
    data_start = (header_row + 1) if has_header else region.start_row

    lines: list[str] = [f"### Sheet: {region.sheet_name or 'Sheet'}"]

    for ri in range(data_start, region.end_row):
        if ri >= len(rows):
            break
        parts: list[str] = []
        for col_idx, ci in enumerate(range(region.start_column, region.end_column)):
            v = rows[ri].get(ci)
            if v is not None and str(v).strip():
                if has_header and col_idx < len(col_names):
                    parts.append(f"{col_names[col_idx]}: {str(v).strip()}")
                else:
                    parts.append(str(v).strip())
        if parts:
            lines.append(f"[Row {ri + 1}] " + " | ".join(parts))

    return "\n".join(lines)


# =============================================================================
# Pipeline graph
# =============================================================================


class ExcelPipelineGraph:
    """LangGraph-style async pipeline for Excel file processing.

    Nodes are discrete async methods. Each node:
    1. Sets state.status to a descriptive string.
    2. Does its work (sync I/O offloaded to asyncio.to_thread).
    3. Writes results into the state.
    4. Returns so the orchestrator can call the next node.

    Args:
        classifier: ContentClassifier instance for region classification.
        dataset_service: DatasetService for creating datasets from structured regions.
        orchestrator: IngestionOrchestrator for chunking + embedding + RAG storage.
        db_session_factory: Callable that returns an AsyncSession for updating file status.
    """

    def __init__(
        self,
        classifier: ContentClassifier,
        dataset_service: "DatasetService",
        orchestrator: "IngestionOrchestrator",
        db_session_factory: Any | None = None,
    ) -> None:
        self._classifier = classifier
        self._dataset_service = dataset_service
        self._orchestrator = orchestrator
        self._db_session_factory = db_session_factory

    # ── Node: READ ────────────────────────────────────────────────────────────

    async def read_node(self, state: ExcelProcessingState) -> None:
        """Read all sheets into memory using pandas (non-blocking)."""
        state.status = "reading"
        logger.info("excel_pipeline.read_node", extra={"file": state.file_name})

        try:
            sheet_data = await asyncio.to_thread(_sync_read_excel, state.file_path)
            state.sheet_data = sheet_data
        except Exception as exc:
            state.status = "failed"
            state.errors.append(f"read_node: {exc}")
            raise

    # ── Node: INSPECT ─────────────────────────────────────────────────────────

    async def inspect_node(self, state: ExcelProcessingState) -> None:
        """Detect contiguous data regions in each sheet (non-blocking)."""
        state.status = "inspecting"
        logger.info(
            "excel_pipeline.inspect_node",
            extra={"file": state.file_name, "sheets": list(state.sheet_data.keys())},
        )

        all_regions: list[DetectedRegion] = []
        for sheet_name, rows in state.sheet_data.items():
            # Run Python-side inspection in a thread so it doesn't block
            sheet_regions = await asyncio.to_thread(
                _inspect_sheet_data, sheet_name, rows
            )
            all_regions.extend(sheet_regions)

        state.regions = all_regions
        logger.info(
            "excel_pipeline.inspect_node.done",
            extra={"file": state.file_name, "regions": len(all_regions)},
        )

    # ── Node: CLASSIFY ────────────────────────────────────────────────────────

    async def classify_node(self, state: ExcelProcessingState) -> None:
        """Run ContentClassifier on all detected regions."""
        state.status = "classifying"
        logger.info(
            "excel_pipeline.classify_node",
            extra={"file": state.file_name, "region_count": len(state.regions)},
        )

        # classify_batch is CPU-light heuristics; run in thread defensively
        classifications = await asyncio.to_thread(
            self._classifier.classify_batch, state.regions
        )
        state.classifications = classifications

    # ── Node: ROUTE (calls dataset and/or rag nodes per region) ──────────────

    async def route_node(self, state: ExcelProcessingState) -> None:
        """Route each region to the appropriate downstream handler."""
        state.status = "routing"

        from app.models.enums import ProcessingStrategy  # noqa: PLC0415
        from app.processors.protocol import InspectionResult  # noqa: PLC0415

        for region, classification in zip(state.regions, state.classifications):
            strategy = classification.processing_strategy
            state.regions_processed += 1

            try:
                if strategy in (
                    ProcessingStrategy.DATASET_QUERY.value,
                    ProcessingStrategy.HYBRID.value,
                ):
                    await self._dataset_node(state, region, classification)

                # Index for RAG in DATASET_QUERY, RAG, and HYBRID modes
                if strategy in (
                    ProcessingStrategy.DATASET_QUERY.value,
                    ProcessingStrategy.RAG.value,
                    ProcessingStrategy.HYBRID.value,
                ):
                    await self._rag_node(state, region)

                # IGNORE / REVIEW_REQUIRED: persist region metadata only
                if strategy in (
                    ProcessingStrategy.IGNORE.value,
                    ProcessingStrategy.REVIEW_REQUIRED.value,
                ):
                    single = InspectionResult(
                        file_name=state.file_name,
                        file_type=state.file_type,
                        regions=[region],
                        metadata={},
                    )
                    await self._dataset_service.create_datasets_from_inspection(
                        file_id=state.file_id,
                        inspection=single,
                        classifications=[classification],
                    )

            except Exception as exc:
                logger.warning(
                    "excel_pipeline.route_node.region_error",
                    extra={
                        "file": state.file_name,
                        "region_id": region.region_id,
                        "strategy": strategy,
                        "error": str(exc),
                    },
                )
                state.errors.append(f"region {region.region_id}: {exc}")

        state.status = "done"

    # ── Private region handlers ────────────────────────────────────────────────

    async def _dataset_node(
        self,
        state: ExcelProcessingState,
        region: DetectedRegion,
        classification: ClassificationResult,
    ) -> None:
        """Create a queryable dataset from a structured region."""
        state.status = "extracting"

        from app.processors.protocol import InspectionResult  # noqa: PLC0415

        rows = state.sheet_data.get(region.sheet_name or "", [])
        columns, records = await asyncio.to_thread(
            _extract_records_from_rows, rows, region
        )

        # Build an InspectionResult containing only this region so we can
        # reuse the existing DatasetService API unchanged.
        single_inspection = InspectionResult(
            file_name=state.file_name,
            file_type=state.file_type,
            regions=[region],
            metadata={},
        )
        created = await self._dataset_service.create_datasets_from_inspection(
            file_id=state.file_id,
            inspection=single_inspection,
            classifications=[classification],
        )
        state.datasets_created.extend(created)

    async def _rag_node(
        self,
        state: ExcelProcessingState,
        region: DetectedRegion,
    ) -> None:
        """Extract text from a region and send it through the RAG pipeline."""
        state.status = "indexing"

        rows = state.sheet_data.get(region.sheet_name or "", [])
        text_content = await asyncio.to_thread(_extract_text_from_rows, rows, region)

        if not text_content or not text_content.strip():
            return

        # Delegate to the orchestrator's existing chunk → embed → store pipeline
        chunks = self._orchestrator._text_chunker.chunk(text_content)
        if not chunks:
            return

        chunk_texts = [c.text for c in chunks]
        embeddings = await self._orchestrator._embedding_generator.generate(chunk_texts)

        effective_project_id = state.project_id or state.uploaded_by
        await self._orchestrator._store_results(
            file_name=state.file_name,
            file_type=state.file_type,
            file_size=state.file_size,
            project_id=effective_project_id,
            uploaded_by=state.uploaded_by,
            chunks=chunks,
            embeddings=embeddings,
        )
        state.documents_indexed += len(chunks)

    # ── Public entry point ────────────────────────────────────────────────────

    async def run(self, state: ExcelProcessingState) -> ExcelProcessingState:
        """Execute the full pipeline: READ → INSPECT → CLASSIFY → ROUTE.

        Args:
            state: Pre-constructed ExcelProcessingState with file inputs.

        Returns:
            The same state instance, mutated with all results and final status.
        """
        try:
            await self.read_node(state)
            await self.inspect_node(state)
            await self.classify_node(state)
            await self.route_node(state)
        except Exception as exc:
            state.status = "failed"
            if str(exc) not in state.errors:
                state.errors.append(str(exc))
            logger.error(
                "excel_pipeline.failed",
                extra={"file": state.file_name, "error": str(exc)},
            )

        return state
