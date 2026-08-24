"""Unit tests for LineageRecorder."""

from uuid import uuid4

from app.ai.lineage_recorder import LineageRecorder


class TestLineageRecorderStartTrace:
    """Tests for start_trace initialization."""

    def test_start_trace_sets_query_id_and_question(self) -> None:
        recorder = LineageRecorder()
        query_id = uuid4()
        recorder.start_trace(query_id, "What is the budget status?")

        trace = recorder.finalize_trace(answer_generated=True)
        assert trace["query_id"] == str(query_id)
        assert trace["question"] == "What is the budget status?"

    def test_start_trace_resets_steps(self) -> None:
        recorder = LineageRecorder()
        query_id_1 = uuid4()
        recorder.start_trace(query_id_1, "First question")
        recorder.record_catalog_lookup(entries_found=5, entries_used=3, duration_ms=10)
        recorder.finalize_trace(answer_generated=True)

        # Start a new trace — previous steps should be gone
        query_id_2 = uuid4()
        recorder.start_trace(query_id_2, "Second question")
        trace = recorder.finalize_trace(answer_generated=True)

        # Only the synthesis step from finalize
        assert len(trace["steps"]) == 1
        assert trace["steps"][0]["step_type"] == "synthesis"


class TestLineageRecorderCatalogLookup:
    """Tests for record_catalog_lookup."""

    def test_records_catalog_lookup_step(self) -> None:
        recorder = LineageRecorder()
        recorder.start_trace(uuid4(), "Test question")
        recorder.record_catalog_lookup(entries_found=10, entries_used=5, duration_ms=42)

        trace = recorder.finalize_trace(answer_generated=True)
        catalog_steps = [s for s in trace["steps"] if s["step_type"] == "catalog_lookup"]

        assert len(catalog_steps) == 1
        step = catalog_steps[0]
        assert step["status"] == "success"
        assert step["duration_ms"] == 42
        assert step["records_count"] == 5
        assert step["entries_found"] == 10
        assert step["entries_used"] == 5
        assert step["timestamp"] is not None
        assert step["error"] is None

    def test_catalog_lookup_has_null_source_fields(self) -> None:
        recorder = LineageRecorder()
        recorder.start_trace(uuid4(), "Test")
        recorder.record_catalog_lookup(entries_found=3, entries_used=2, duration_ms=15)

        trace = recorder.finalize_trace(answer_generated=True)
        step = trace["steps"][0]
        assert step["tool_name"] is None
        assert step["source_id"] is None
        assert step["source_name"] is None
        assert step["object_name"] is None


class TestLineageRecorderToolInvocation:
    """Tests for record_tool_invocation."""

    def test_records_successful_tool_invocation(self) -> None:
        recorder = LineageRecorder()
        recorder.start_trace(uuid4(), "Budget question")
        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-abc",
            source_name="Finance PostgreSQL",
            object_name="project_finance",
            status="success",
            duration_ms=200,
            records_count=15,
        )

        trace = recorder.finalize_trace(answer_generated=True)
        tool_steps = [s for s in trace["steps"] if s["step_type"] == "tool_invocation"]

        assert len(tool_steps) == 1
        step = tool_steps[0]
        assert step["tool_name"] == "query_connected_source"
        assert step["source_id"] == "src-abc"
        assert step["source_name"] == "Finance PostgreSQL"
        assert step["object_name"] == "project_finance"
        assert step["status"] == "success"
        assert step["duration_ms"] == 200
        assert step["records_count"] == 15
        assert step["error"] is None

    def test_records_failed_tool_invocation_with_error(self) -> None:
        recorder = LineageRecorder()
        recorder.start_trace(uuid4(), "Risk question")
        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-xyz",
            source_name="Risks MongoDB",
            object_name="project_risks",
            status="failed",
            duration_ms=5000,
            records_count=0,
            error="Connection timeout after 5000ms",
        )

        trace = recorder.finalize_trace(answer_generated=True)
        tool_steps = [s for s in trace["steps"] if s["step_type"] == "tool_invocation"]

        step = tool_steps[0]
        assert step["status"] == "failed"
        assert step["error"] == "Connection timeout after 5000ms"
        assert step["records_count"] == 0

    def test_records_multiple_tool_invocations_in_order(self) -> None:
        recorder = LineageRecorder()
        recorder.start_trace(uuid4(), "Cross-source question")

        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-1",
            source_name="Finance PostgreSQL",
            object_name="project_finance",
            status="success",
            duration_ms=100,
            records_count=5,
        )
        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-2",
            source_name="Risks MongoDB",
            object_name="project_risks",
            status="success",
            duration_ms=150,
            records_count=8,
        )

        trace = recorder.finalize_trace(answer_generated=True)
        tool_steps = [s for s in trace["steps"] if s["step_type"] == "tool_invocation"]

        assert len(tool_steps) == 2
        assert tool_steps[0]["source_name"] == "Finance PostgreSQL"
        assert tool_steps[1]["source_name"] == "Risks MongoDB"


class TestLineageRecorderFinalizeTrace:
    """Tests for finalize_trace."""

    def test_finalize_adds_synthesis_step(self) -> None:
        recorder = LineageRecorder()
        recorder.start_trace(uuid4(), "Test")

        trace = recorder.finalize_trace(answer_generated=True)
        synthesis_steps = [s for s in trace["steps"] if s["step_type"] == "synthesis"]
        assert len(synthesis_steps) == 1
        assert synthesis_steps[0]["status"] == "success"

    def test_finalize_marks_synthesis_failed_when_no_answer(self) -> None:
        recorder = LineageRecorder()
        recorder.start_trace(uuid4(), "Test")

        trace = recorder.finalize_trace(answer_generated=False)
        synthesis_steps = [s for s in trace["steps"] if s["step_type"] == "synthesis"]
        assert synthesis_steps[0]["status"] == "failed"
        assert synthesis_steps[0]["error"] == "Answer generation failed"

    def test_finalize_computes_total_duration(self) -> None:
        recorder = LineageRecorder()
        recorder.start_trace(uuid4(), "Test")
        # Total duration is wall-clock time from start_trace to finalize_trace
        trace = recorder.finalize_trace(answer_generated=True)
        assert trace["total_duration_ms"] >= 0

    def test_finalize_extracts_sources_consulted(self) -> None:
        recorder = LineageRecorder()
        recorder.start_trace(uuid4(), "Multi-source question")

        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-1",
            source_name="Finance PostgreSQL",
            object_name="budget",
            status="success",
            duration_ms=100,
            records_count=10,
        )
        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-2",
            source_name="RAG Documents",
            object_name="meeting_notes.pdf",
            status="success",
            duration_ms=50,
            records_count=3,
        )

        trace = recorder.finalize_trace(answer_generated=True)
        assert "Finance PostgreSQL" in trace["sources_consulted"]
        assert "RAG Documents" in trace["sources_consulted"]
        assert trace["failed_sources"] == []
        assert trace["is_partial"] is False

    def test_finalize_extracts_failed_sources(self) -> None:
        recorder = LineageRecorder()
        recorder.start_trace(uuid4(), "Partial failure")

        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-1",
            source_name="Finance PostgreSQL",
            object_name="budget",
            status="success",
            duration_ms=100,
            records_count=10,
        )
        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-2",
            source_name="Risks MongoDB",
            object_name="risks",
            status="failed",
            duration_ms=5000,
            records_count=0,
            error="Timeout",
        )

        trace = recorder.finalize_trace(answer_generated=True)
        assert "Finance PostgreSQL" in trace["sources_consulted"]
        assert "Risks MongoDB" in trace["failed_sources"]
        assert trace["is_partial"] is True

    def test_finalize_deduplicates_source_names(self) -> None:
        recorder = LineageRecorder()
        recorder.start_trace(uuid4(), "Duplicate source calls")

        # Same source queried twice (different objects)
        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-1",
            source_name="Finance PostgreSQL",
            object_name="budget",
            status="success",
            duration_ms=100,
            records_count=5,
        )
        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-1",
            source_name="Finance PostgreSQL",
            object_name="invoices",
            status="success",
            duration_ms=80,
            records_count=3,
        )

        trace = recorder.finalize_trace(answer_generated=True)
        assert trace["sources_consulted"].count("Finance PostgreSQL") == 1

    def test_finalize_full_trace_structure(self) -> None:
        recorder = LineageRecorder()
        query_id = uuid4()
        recorder.start_trace(query_id, "Why is Project Alpha at risk?")

        recorder.record_catalog_lookup(entries_found=12, entries_used=5, duration_ms=30)
        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-finance",
            source_name="Finance PostgreSQL",
            object_name="project_finance",
            status="success",
            duration_ms=200,
            records_count=15,
        )
        recorder.record_tool_invocation(
            tool_name="query_connected_source",
            source_id="src-risk",
            source_name="Risks MongoDB",
            object_name="project_risks",
            status="timeout",
            duration_ms=30000,
            records_count=0,
            error="Query exceeded 30s timeout",
        )

        trace = recorder.finalize_trace(answer_generated=True)

        # Structure validation
        assert trace["query_id"] == str(query_id)
        assert trace["question"] == "Why is Project Alpha at risk?"
        assert len(trace["steps"]) == 4  # catalog + 2 tools + synthesis
        assert trace["total_duration_ms"] >= 0
        assert trace["sources_consulted"] == ["Finance PostgreSQL"]
        assert trace["failed_sources"] == ["Risks MongoDB"]
        assert trace["is_partial"] is True
