"""
Unit tests for AI Response Builder and markup validation.

Verifies:
- ResponseBuilder constructs valid AIResponse objects
- Markup detection and stripping work correctly
- Partial failure logic: is_partial set when failed sources exist
- Source labels (not tool names) appear in responses
- Pydantic validator rejects HTML/JSX in answer field
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.ai.response import ResponseBuilder, contains_markup, strip_markup
from app.schemas.ai import AIResponse


# =============================================================================
# Markup Detection Tests
# =============================================================================


class TestMarkupDetection:
    """Tests for contains_markup and strip_markup utilities."""

    def test_plain_text_has_no_markup(self) -> None:
        assert contains_markup("The budget is on track.") is False

    def test_detects_html_opening_tag(self) -> None:
        assert contains_markup("Result: <div>hello</div>") is True

    def test_detects_html_self_closing_tag(self) -> None:
        assert contains_markup("Line break here<br/>end") is True

    def test_detects_react_component_tag(self) -> None:
        assert contains_markup("<ChartComponent data={values}/>") is True

    def test_detects_jsx_closing_tag(self) -> None:
        assert contains_markup("content</SomeComponent>") is True

    def test_allows_mathematical_angle_brackets(self) -> None:
        """Mathematical expressions like '5 < 10' should not be flagged."""
        assert contains_markup("The value 5 < 10 is correct") is False

    def test_allows_comparison_operators(self) -> None:
        assert contains_markup("Budget variance < 5%") is False

    def test_strip_markup_removes_tags_preserving_content(self) -> None:
        result = strip_markup("The <strong>budget</strong> is on track.")
        assert result == "The budget is on track."

    def test_strip_markup_removes_self_closing_tags(self) -> None:
        result = strip_markup("Line one<br/>Line two")
        assert result == "Line oneLine two"

    def test_strip_markup_removes_jsx_components(self) -> None:
        result = strip_markup("See <Chart type='bar'/> for details")
        assert result == "See  for details"

    def test_strip_markup_preserves_plain_text(self) -> None:
        text = "No markup here, just plain text with numbers 1 < 2."
        assert strip_markup(text) == text


# =============================================================================
# AIResponse Pydantic Validator Tests
# =============================================================================


class TestAIResponseMarkupValidator:
    """Tests that AIResponse rejects markup in the answer field."""

    def test_rejects_html_in_answer(self) -> None:
        with pytest.raises(ValidationError, match="must not contain HTML/JSX/React markup"):
            AIResponse(
                answer="<p>This is HTML</p>",
                response_type="text",
                query_id=uuid4(),
                conversation_id=uuid4(),
            )

    def test_rejects_jsx_component_in_answer(self) -> None:
        with pytest.raises(ValidationError, match="must not contain HTML/JSX/React markup"):
            AIResponse(
                answer="Render this: <DataTable rows={data}/>",
                response_type="text",
                query_id=uuid4(),
                conversation_id=uuid4(),
            )

    def test_accepts_plain_text_answer(self) -> None:
        response = AIResponse(
            answer="The project is 80% complete with budget variance < 3%.",
            response_type="text",
            query_id=uuid4(),
            conversation_id=uuid4(),
        )
        assert "80% complete" in response.answer

    def test_accepts_markdown_in_answer(self) -> None:
        """Markdown formatting is fine — only HTML/JSX is rejected."""
        response = AIResponse(
            answer="**Budget**: $1.2M allocated\n- Phase 1: $500K\n- Phase 2: $700K",
            response_type="text",
            query_id=uuid4(),
            conversation_id=uuid4(),
        )
        assert "Budget" in response.answer


# =============================================================================
# ResponseBuilder Tests
# =============================================================================


class TestResponseBuilder:
    """Tests for the ResponseBuilder utility."""

    def test_build_minimal_response(self) -> None:
        query_id = uuid4()
        conversation_id = uuid4()

        builder = ResponseBuilder(query_id=query_id, conversation_id=conversation_id)
        builder.set_answer("Test answer")

        response = builder.build()

        assert isinstance(response, AIResponse)
        assert response.answer == "Test answer"
        assert response.response_type == "text"
        assert response.query_id == query_id
        assert response.conversation_id == conversation_id
        assert response.is_partial is False
        assert response.sources == []
        assert response.evidence == []
        assert response.failed_sources == []
        assert response.visualization_spec is None

    def test_build_with_sources_and_evidence(self) -> None:
        builder = ResponseBuilder(query_id=uuid4(), conversation_id=uuid4())
        builder.set_answer("Budget on track.")
        builder.add_source(label="Finance PostgreSQL", source_type="postgresql", records=5)
        builder.add_evidence(
            claim="Budget variance is 2%",
            source="Finance PostgreSQL",
            data={"variance": 0.02},
        )

        response = builder.build()

        assert len(response.sources) == 1
        assert response.sources[0]["name"] == "Finance PostgreSQL"
        assert response.sources[0]["type"] == "postgresql"
        assert response.sources[0]["records_returned"] == 5
        assert len(response.evidence) == 1
        assert response.evidence[0]["claim"] == "Budget variance is 2%"

    def test_build_sets_is_partial_when_failed_sources_present(self) -> None:
        builder = ResponseBuilder(query_id=uuid4(), conversation_id=uuid4())
        builder.set_answer("Partial answer from available sources.")
        builder.add_source(label="JIRA", source_type="postgresql", records=3)
        builder.add_failed_source(source="Confluence", error="Connection timeout")

        response = builder.build()

        assert response.is_partial is True
        assert len(response.sources) == 1
        assert len(response.failed_sources) == 1
        assert response.failed_sources[0]["source"] == "Confluence"
        assert response.failed_sources[0]["error"] == "Connection timeout"

    def test_build_is_not_partial_when_no_failures(self) -> None:
        builder = ResponseBuilder(query_id=uuid4(), conversation_id=uuid4())
        builder.set_answer("Complete answer.")
        builder.add_source(label="Finance", source_type="postgresql", records=10)

        response = builder.build()

        assert response.is_partial is False
        assert response.failed_sources == []

    def test_build_strips_markup_from_answer(self) -> None:
        builder = ResponseBuilder(query_id=uuid4(), conversation_id=uuid4())
        builder.set_answer("The <strong>project</strong> is on track.")

        response = builder.build()

        assert response.answer == "The project is on track."
        assert "<strong>" not in response.answer

    def test_set_response_type_validates_allowed_values(self) -> None:
        builder = ResponseBuilder(query_id=uuid4(), conversation_id=uuid4())

        builder.set_response_type("table")
        builder.set_response_type("chart")
        builder.set_response_type("text")

        with pytest.raises(ValueError, match="must be one of"):
            builder.set_response_type("invalid")

    def test_build_includes_visualization_spec_for_chart(self) -> None:
        builder = ResponseBuilder(query_id=uuid4(), conversation_id=uuid4())
        builder.set_answer("Budget breakdown by phase.")
        builder.set_response_type("chart")
        builder.set_visualization_spec({
            "type": "bar",
            "title": "Budget by Phase",
            "x_axis": "phase",
            "y_axis": "amount",
            "data": [{"phase": "Phase 1", "amount": 500000}],
        })

        response = builder.build()

        assert response.response_type == "chart"
        assert response.visualization_spec is not None
        assert response.visualization_spec["type"] == "bar"

    def test_build_clears_visualization_spec_for_text_type(self) -> None:
        builder = ResponseBuilder(query_id=uuid4(), conversation_id=uuid4())
        builder.set_answer("Plain text answer.")
        builder.set_response_type("text")
        builder.set_visualization_spec({"type": "bar"})

        response = builder.build()

        assert response.visualization_spec is None

    def test_method_chaining(self) -> None:
        response = (
            ResponseBuilder(query_id=uuid4(), conversation_id=uuid4())
            .set_answer("Chained answer.")
            .set_response_type("table")
            .add_source(label="DB", source_type="postgresql", records=2)
            .set_visualization_spec({"type": "table", "columns": ["a", "b"]})
            .build()
        )

        assert response.answer == "Chained answer."
        assert response.response_type == "table"
        assert len(response.sources) == 1

    def test_sources_use_labels_not_tool_names(self) -> None:
        """Verify the builder enforces meaningful source labels per Requirement 11.7."""
        builder = ResponseBuilder(query_id=uuid4(), conversation_id=uuid4())
        builder.set_answer("Result from multiple sources.")
        builder.add_source(label="Finance PostgreSQL", source_type="postgresql", records=5)
        builder.add_source(label="Project Meeting Notes", source_type="document", records=2)

        response = builder.build()

        source_names = [s["name"] for s in response.sources]
        assert "Finance PostgreSQL" in source_names
        assert "Project Meeting Notes" in source_names
        # Ensure no tool-style names leaked through
        for name in source_names:
            assert not name.startswith("query_")
            assert not name.startswith("get_")
