"""
Lineage Recorder — Records the full execution trace for an AI query.

Captures the data lineage path:
    Question → Catalog Lookup → Tool Invocations → Synthesis → Answer

Only actual execution events are recorded — no fabrication. Each step
is timestamped and includes duration, status, and metadata needed to
reconstruct how the final answer was assembled.

Security Invariant:
    The recorder NEVER captures credentials, connection strings, or API keys.
    It only records operational metadata (source IDs, names, durations, counts).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import UUID


class LineageRecorder:
    """Records the data lineage trace for an AI query execution.

    Usage:
        recorder = LineageRecorder()
        recorder.start_trace(query_id, "Why is Project Alpha at risk?")
        recorder.record_catalog_lookup(entries_found=12, entries_used=5, duration_ms=45)
        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-123",
            source_name="Finance PostgreSQL",
            object_name="project_finance",
            status="success",
            duration_ms=200,
            records_count=15,
        )
        trace = recorder.finalize_trace(answer_generated=True)
    """

    def __init__(self) -> None:
        """Initialize a fresh LineageRecorder with no active trace."""
        self._query_id: str | None = None
        self._question: str | None = None
        self._steps: list[dict] = []
        self._start_time_ns: int | None = None

    def start_trace(self, query_id: UUID, question: str) -> None:
        """Initialize a new trace for the given query.

        Args:
            query_id: Unique identifier for this query execution.
            question: The user's original question text.
        """
        self._query_id = str(query_id)
        self._question = question
        self._steps = []
        self._start_time_ns = time.perf_counter_ns()

    def record_catalog_lookup(
        self, entries_found: int, entries_used: int, duration_ms: int
    ) -> None:
        """Record that the catalog was consulted for relevant entries.

        Creates a LineageStep with step_type="catalog_lookup".

        Args:
            entries_found: Total catalog entries that matched the query.
            entries_used: Entries actually injected into LLM context.
            duration_ms: Time taken for the catalog lookup.
        """
        step: dict = {
            "step_type": "catalog_lookup",
            "tool_name": None,
            "source_id": None,
            "source_name": None,
            "object_name": None,
            "status": "success",
            "duration_ms": duration_ms,
            "records_count": entries_used,
            "timestamp": _now_iso(),
            "error": None,
            "entries_found": entries_found,
            "entries_used": entries_used,
        }
        self._steps.append(step)

    def record_tool_invocation(
        self,
        tool_name: str,
        source_id: str,
        source_name: str,
        object_name: str,
        status: str,
        duration_ms: int,
        records_count: int,
        error: str | None = None,
    ) -> None:
        """Record a single tool invocation step with all metadata.

        Creates a LineageStep with step_type="tool_invocation".

        Args:
            tool_name: Name of the tool that was invoked.
            source_id: Identifier of the data source queried.
            source_name: Human-readable name of the data source.
            object_name: Table, collection, or document queried.
            status: Outcome — "success", "failed", or "timeout".
            duration_ms: Time taken for the tool invocation.
            records_count: Number of records/chunks retrieved.
            error: Error description if the invocation failed.
        """
        step: dict = {
            "step_type": "tool_invocation",
            "tool_name": tool_name,
            "source_id": source_id,
            "source_name": source_name,
            "object_name": object_name,
            "status": status,
            "duration_ms": duration_ms,
            "records_count": records_count,
            "timestamp": _now_iso(),
            "error": error,
        }
        self._steps.append(step)

    def finalize_trace(self, answer_generated: bool) -> dict:
        """Finalize the trace and return a serializable dict.

        Computes total duration, extracts sources consulted vs. failed,
        and determines if the answer is partial.

        Args:
            answer_generated: Whether an answer was successfully generated.

        Returns:
            A serializable dict containing:
            - query_id: str
            - question: str
            - steps: list of step dicts
            - total_duration_ms: int
            - sources_consulted: list of source_name strings from successful steps
            - failed_sources: list of source_name strings from failed steps
            - is_partial: bool (True if any failed_sources exist)
        """
        # Calculate total duration from trace start
        total_duration_ms = 0
        if self._start_time_ns is not None:
            elapsed_ns = time.perf_counter_ns() - self._start_time_ns
            total_duration_ms = int(elapsed_ns / 1_000_000)

        # Add synthesis step to mark answer generation
        synthesis_step: dict = {
            "step_type": "synthesis",
            "tool_name": None,
            "source_id": None,
            "source_name": None,
            "object_name": None,
            "status": "success" if answer_generated else "failed",
            "duration_ms": 0,
            "records_count": 0,
            "timestamp": _now_iso(),
            "error": None if answer_generated else "Answer generation failed",
        }
        self._steps.append(synthesis_step)

        # Extract sources consulted (successful tool invocations)
        sources_consulted: list[str] = []
        failed_sources: list[str] = []

        for step in self._steps:
            if step["step_type"] != "tool_invocation":
                continue
            source_name = step.get("source_name")
            if not source_name:
                continue
            if step["status"] == "success":
                if source_name not in sources_consulted:
                    sources_consulted.append(source_name)
            else:
                if source_name not in failed_sources:
                    failed_sources.append(source_name)

        is_partial = len(failed_sources) > 0

        return {
            "query_id": self._query_id,
            "question": self._question,
            "steps": self._steps,
            "total_duration_ms": total_duration_ms,
            "sources_consulted": sources_consulted,
            "failed_sources": failed_sources,
            "is_partial": is_partial,
        }


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()
