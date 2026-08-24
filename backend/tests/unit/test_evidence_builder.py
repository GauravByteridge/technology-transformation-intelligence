"""
Unit tests for the EvidenceBuilder module.

Verifies:
- Database evidence is correctly built from query_connected_source results
- Document evidence is correctly built from search_documents results
- Error results are skipped (no fabricated evidence)
- Groundedness classification works correctly
- Evidence items contain required fields per source type
- Empty/invalid inputs produce empty results (no crashes)
"""

from app.ai.evidence_builder import EvidenceBuilder


class TestBuildEvidence:
    """Tests for EvidenceBuilder.build_evidence method."""

    def setup_method(self) -> None:
        self.builder = EvidenceBuilder()

    def test_empty_results_returns_empty_list(self) -> None:
        result = self.builder.build_evidence([])
        assert result == []

    def test_none_results_returns_empty_list(self) -> None:
        result = self.builder.build_evidence(None)  # type: ignore[arg-type]
        assert result == []

    def test_postgresql_result_produces_evidence(self) -> None:
        tool_results = [
            {
                "columns": ["project_id", "budget", "actual_cost"],
                "rows": [
                    {"project_id": "alpha-001", "budget": 1000000, "actual_cost": 850000}
                ],
                "row_count": 1,
                "source_metadata": {
                    "source_id": "src-pg-001",
                    "source_type": "postgresql",
                    "source_name": "Finance Database",
                    "object_name": "project_finance",
                },
                "duration_ms": 45,
            }
        ]

        evidence = self.builder.build_evidence(tool_results)

        assert len(evidence) == 1
        item = evidence[0]

        # Required fields
        assert "evidence_id" in item
        assert item["source_id"] == "src-pg-001"
        assert item["source_type"] == "postgresql"
        assert item["source_name"] == "Finance Database"
        assert item["object_name"] == "project_finance"
        assert item["column_names"] == ["project_id", "budget", "actual_cost"]
        assert item["confidence"] == "retrieved_fact"

        # PostgreSQL-specific fields
        assert item["table_name"] == "project_finance"

        # Record reference
        assert item["record_reference"] == "1 row"

        # Excerpt contains actual values
        assert "budget" in item["excerpt"]
        assert "1000000" in item["excerpt"]

    def test_mongodb_result_produces_evidence(self) -> None:
        tool_results = [
            {
                "columns": ["risk_id", "severity", "status"],
                "rows": [
                    {"risk_id": "R001", "severity": "high", "status": "open"},
                    {"risk_id": "R002", "severity": "medium", "status": "mitigated"},
                ],
                "row_count": 2,
                "source_metadata": {
                    "source_id": "src-mongo-001",
                    "source_type": "mongodb",
                    "source_name": "Project Management DB",
                    "object_name": "risks",
                },
                "duration_ms": 30,
            }
        ]

        evidence = self.builder.build_evidence(tool_results)

        assert len(evidence) == 1
        item = evidence[0]

        assert item["source_type"] == "mongodb"
        assert item["collection_name"] == "risks"
        assert item["record_reference"] == "rows 1-2"
        assert "severity" in item["excerpt"]

    def test_document_result_produces_evidence(self) -> None:
        tool_results = [
            {
                "document_id": "doc-001",
                "file_name": "project_status_report.pdf",
                "page_number": 3,
                "section": "Risk Assessment",
                "excerpt": "The project faces significant schedule risk due to resource constraints.",
                "chunks": [],
            }
        ]

        evidence = self.builder.build_evidence(tool_results)

        assert len(evidence) == 1
        item = evidence[0]

        assert item["source_type"] == "document"
        assert item["document_id"] == "doc-001"
        assert item["file_name"] == "project_status_report.pdf"
        assert item["page_number"] == 3
        assert item["section"] == "Risk Assessment"
        assert "schedule risk" in item["excerpt"]
        assert item["record_reference"] == "page 3, section: Risk Assessment"

    def test_document_with_sheet_name(self) -> None:
        tool_results = [
            {
                "document_id": "doc-excel-001",
                "file_name": "budget_tracker.xlsx",
                "sheet_name": "Q4 Forecast",
                "page_number": None,
                "section": None,
                "excerpt": "Budget allocation for Q4 is $2.5M",
            }
        ]

        evidence = self.builder.build_evidence(tool_results)

        assert len(evidence) == 1
        item = evidence[0]
        assert item["sheet_name"] == "Q4 Forecast"
        assert item["record_reference"] == "sheet: Q4 Forecast"

    def test_error_results_are_skipped(self) -> None:
        """Error results must not produce evidence items — no fabrication."""
        tool_results = [
            {
                "error": True,
                "error_type": "query_execution_error",
                "message": "Connection timeout",
                "duration_ms": 5000,
            }
        ]

        evidence = self.builder.build_evidence(tool_results)
        assert evidence == []

    def test_multiple_results_produce_multiple_evidence(self) -> None:
        tool_results = [
            {
                "columns": ["budget"],
                "rows": [{"budget": 1000000}],
                "row_count": 1,
                "source_metadata": {
                    "source_id": "src-1",
                    "source_type": "postgresql",
                    "source_name": "Finance DB",
                    "object_name": "project_finance",
                },
                "duration_ms": 20,
            },
            {
                "columns": ["risk_id", "severity"],
                "rows": [{"risk_id": "R001", "severity": "high"}],
                "row_count": 1,
                "source_metadata": {
                    "source_id": "src-2",
                    "source_type": "mongodb",
                    "source_name": "Risk DB",
                    "object_name": "risks",
                },
                "duration_ms": 15,
            },
        ]

        evidence = self.builder.build_evidence(tool_results)
        assert len(evidence) == 2
        assert evidence[0]["source_id"] == "src-1"
        assert evidence[1]["source_id"] == "src-2"

    def test_mixed_results_with_errors_only_builds_successful(self) -> None:
        """Only successful results produce evidence. Errors are skipped."""
        tool_results = [
            {
                "columns": ["budget"],
                "rows": [{"budget": 500000}],
                "row_count": 1,
                "source_metadata": {
                    "source_id": "src-1",
                    "source_type": "postgresql",
                    "source_name": "Finance",
                    "object_name": "budget",
                },
                "duration_ms": 10,
            },
            {
                "error": True,
                "error_type": "source_not_found",
                "message": "Source unavailable",
                "duration_ms": 100,
            },
        ]

        evidence = self.builder.build_evidence(tool_results)
        assert len(evidence) == 1
        assert evidence[0]["source_id"] == "src-1"

    def test_evidence_id_is_unique_uuid(self) -> None:
        tool_results = [
            {
                "columns": ["a"],
                "rows": [{"a": 1}],
                "row_count": 1,
                "source_metadata": {
                    "source_id": "s1",
                    "source_type": "postgresql",
                    "source_name": "DB",
                    "object_name": "t",
                },
                "duration_ms": 5,
            },
            {
                "columns": ["b"],
                "rows": [{"b": 2}],
                "row_count": 1,
                "source_metadata": {
                    "source_id": "s2",
                    "source_type": "postgresql",
                    "source_name": "DB",
                    "object_name": "t2",
                },
                "duration_ms": 5,
            },
        ]

        evidence = self.builder.build_evidence(tool_results)
        ids = [item["evidence_id"] for item in evidence]
        # All IDs are unique
        assert len(set(ids)) == len(ids)

    def test_rows_as_list_tuples_mapped_to_columns(self) -> None:
        """Rows can be lists/tuples — they should be mapped to column names."""
        tool_results = [
            {
                "columns": ["name", "value"],
                "rows": [["Alpha", 100], ["Beta", 200]],
                "row_count": 2,
                "source_metadata": {
                    "source_id": "s1",
                    "source_type": "postgresql",
                    "source_name": "DB",
                    "object_name": "projects",
                },
                "duration_ms": 10,
            }
        ]

        evidence = self.builder.build_evidence(tool_results)
        assert len(evidence) == 1
        summary = evidence[0]["records_summary"]
        assert summary["rows"][0] == {"name": "Alpha", "value": 100}
        assert summary["rows"][1] == {"name": "Beta", "value": 200}

    def test_document_chunks_used_when_no_excerpt(self) -> None:
        """When excerpt is empty, build from chunks list."""
        tool_results = [
            {
                "document_id": "doc-002",
                "file_name": "meeting_notes.docx",
                "page_number": 1,
                "section": None,
                "excerpt": "",
                "chunks": [
                    {"text": "Discussed budget concerns."},
                    {"text": "Action item: review Q4 forecast."},
                ],
            }
        ]

        evidence = self.builder.build_evidence(tool_results)
        assert len(evidence) == 1
        assert "budget concerns" in evidence[0]["excerpt"]
        assert "Q4 forecast" in evidence[0]["excerpt"]


class TestClassifyGroundedness:
    """Tests for EvidenceBuilder.classify_groundedness method."""

    def setup_method(self) -> None:
        self.builder = EvidenceBuilder()

    def test_no_evidence_returns_ai_explanation(self) -> None:
        result = self.builder.classify_groundedness("The project is at risk", {})
        assert result == "ai_explanation"

    def test_empty_evidence_returns_ai_explanation(self) -> None:
        evidence = {"excerpt": "", "records_summary": None, "column_names": []}
        result = self.builder.classify_groundedness("Something", evidence)
        assert result == "ai_explanation"

    def test_direct_data_returns_retrieved_fact(self) -> None:
        evidence = {
            "excerpt": "budget: 1000000, actual_cost: 850000",
            "records_summary": {"rows": [{"budget": 1000000}]},
            "column_names": ["budget", "actual_cost"],
        }
        result = self.builder.classify_groundedness(
            "The budget is $1,000,000", evidence
        )
        assert result == "retrieved_fact"

    def test_variance_claim_returns_derived_calculation(self) -> None:
        evidence = {
            "excerpt": "budget: 1000000, actual_cost: 850000",
            "records_summary": {"rows": [{"budget": 1000000}]},
            "column_names": ["budget", "actual_cost", "variance"],
        }
        result = self.builder.classify_groundedness(
            "The budget variance is 15%", evidence
        )
        assert result == "derived_calculation"

    def test_percentage_in_claim_returns_derived_calculation(self) -> None:
        evidence = {
            "excerpt": "progress: 75",
            "records_summary": {"rows": [{"progress": 75}]},
            "column_names": ["progress"],
        }
        result = self.builder.classify_groundedness(
            "The project is 75 percent complete", evidence
        )
        assert result == "derived_calculation"

    def test_average_in_claim_returns_derived_calculation(self) -> None:
        evidence = {
            "excerpt": "score: 8.5",
            "records_summary": {"rows": [{"score": 8.5}]},
            "column_names": ["score"],
        }
        result = self.builder.classify_groundedness(
            "The average risk score is 8.5", evidence
        )
        assert result == "derived_calculation"

    def test_simple_data_retrieval_returns_retrieved_fact(self) -> None:
        evidence = {
            "excerpt": "project_name: Alpha, status: active",
            "records_summary": {"rows": [{"project_name": "Alpha", "status": "active"}]},
            "column_names": ["project_name", "status"],
        }
        result = self.builder.classify_groundedness(
            "Project Alpha is currently active", evidence
        )
        assert result == "retrieved_fact"
