"""
ExcelProcessingState — typed state carrier for the Excel pipeline graph.

Mirrors LangGraph's TypedDict state pattern. Each pipeline node reads from
and writes to a single ExcelProcessingState instance, making data flow
explicit and observable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.processors.protocol import ClassificationResult, DetectedRegion


@dataclass
class ExcelProcessingState:
    """Carries all intermediate artefacts between Excel pipeline nodes.

    Lifecycle:
        pending → reading → inspecting → classifying → routing →
        extracting / indexing → done | failed
    """

    # ── Inputs (set at construction) ──────────────────────────────────────
    file_id: UUID
    file_path: str
    file_name: str
    file_size: int
    file_type: str
    project_id: UUID | None
    uploaded_by: UUID

    # ── Status tracking (updated by each node) ────────────────────────────
    status: str = "pending"

    # ── Intermediate artefacts ────────────────────────────────────────────
    # Filled by READ_NODE: {sheet_name → list of rows as dicts}
    sheet_data: dict[str, list[dict]] = field(default_factory=dict)

    # Filled by INSPECT_NODE
    regions: list[DetectedRegion] = field(default_factory=list)

    # Filled by CLASSIFY_NODE
    classifications: list[ClassificationResult] = field(default_factory=list)

    # ── Outputs (accumulated across routing nodes) ────────────────────────
    datasets_created: list[dict] = field(default_factory=list)
    documents_indexed: int = 0
    regions_processed: int = 0

    # ── Error tracking ────────────────────────────────────────────────────
    errors: list[str] = field(default_factory=list)
