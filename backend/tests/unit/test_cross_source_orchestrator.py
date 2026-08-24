"""
Unit tests for CrossSourceOrchestrator.

Validates:
- Dynamic source selection (no hard-coded routing)
- Failure isolation (one source failure doesn't block others)
- Evidence built only from successful results
- Lineage records all attempts (successes and failures)
- is_partial flag and failed_sources tracking
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.ai.agent import AgentResponse, ToolResult
from app.ai.catalog_context import CatalogContext, CatalogContextInjector
from app.ai.cross_source_orchestrator import (
    CrossSourceOrchestrator,
    CrossSourceResult,
    _user_friendly_error,
)
from app.ai.evidence_builder import EvidenceBuilder
from app.ai.groundedness import GroundednessClassifier
from app.ai.lineage_recorder import LineageRecorder


@pytest.fixture
def mock_catalog_context_injector() -> MagicMock:
    """Create a mock CatalogContextInjector."""
    injector = MagicMock(spec=CatalogContextInjector)
    injector.build_relevant_context = AsyncMock(
        return_value=CatalogContext(
            entries=[],
            project_id=None,
            total_available=5,
            included_count=3,
        )
    )
    injector.format_for_system_prompt = MagicMock(
        return_value="Available Enterprise Data Sources:\n\nFinance (PostgreSQL - project_finance):\nProject budget and cost tracking.\n"
    )
    return injector


@pytest.fixture
def evidence_builder() -> EvidenceBuilder:
    """Create a real EvidenceBuilder instance."""
    return EvidenceBuilder()


@pytest.fixture
def lineage_recorder() -> LineageRecorder:
    """Create a real LineageRecorder instance."""
    return LineageRecorder()


@pytest.fixture
def groundedness_classifier() -> GroundednessClassifier:
    """Create a real GroundednessClassifier instance."""
    return GroundednessClassifier()


@pytest.fixture
def orchestrator(
    mock_catalog_context_injector: MagicMock,
    evidence_builder: EvidenceBuilder,
    lineage_recorder: LineageRecorder,
    groundedness_classifier: GroundednessClassifier,
) -> CrossSourceOrchestrator:
    """Create a CrossSourceOrchestrator with dependencies."""
    return CrossSourceOrchestrator(
        catalog_context_injector=mock_catalog_context_injector,
        evidence_builder=evidence_builder,
        lineage_recorder=lineage_recorder,
        groundedness_classifier=groundedness_classifier,
    )


def _make_successful_tool_result(
    tool_name: str = "query_connected_source",
    source_id: str = "src-123",
    source_name: str = "Finance PostgreSQL",
    object_name: str = "project_finance",
    rows: list | None = None,
) -> ToolResult:
    """Create a successful ToolResult with source metadata."""
    return ToolResult(
        tool_name=tool_name,
        success=True,
        data={
            "columns": ["project_id", "budget", "actual_cost"],
            "rows": rows or [["proj-1", 100000, 85000]],
            "row_count": 1,
            "source_metadata": {
                "source_id": source_id,
                "source_type": "postgresql",
                "source_name": source_name,
                "object_name": object_name,
            },
        },
        source_label=source_name,
        duration_ms=150,
    )


def _make_failed_tool_result(
    tool_name: str = "query_connected_source",
    source_label: str = "Risk MongoDB",
    error: str = "Connection timed out",
) -> ToolResult:
    """Create a failed ToolResult."""
    return ToolResult(
        tool_name=tool_name,
        success=False,
        data={},
        source_label=source_label,
        error=error,
        duration_ms=30000,
    )


@pytest.mark.asyncio
async def test_execute_cross_source_query_success(
    orchestrator: CrossSourceOrchestrator,
    mock_catalog_context_injector: MagicMock,
) -> None:
    """All sources succeed — is_partial=False, no failed_sources."""
    # Arrange
    mock_agent = MagicMock()
    mock_agent.invoke = AsyncMock(
        return_value=AgentResponse(
            answer="Project Alpha has a budget of $100,000.",
            model="gpt-4",
            tool_results=[
                _make_successful_tool_result(),
            ],
            is_partial=False,
        )
    )

    project_id = uuid4()
    query_id = uuid4()

    # Act
    result = await orchestrator.execute_cross_source_query(
        question="What is the budget for Project Alpha?",
        project_id=project_id,
        strands_agent=mock_agent,
        query_id=query_id,
    )

    # Assert
    assert isinstance(result, CrossSourceResult)
    assert result.query_id == query_id
    assert result.is_partial is False
    assert result.failed_sources == []
    assert len(result.sources_consulted) == 1
    assert result.sources_consulted[0]["source_name"] == "Finance PostgreSQL"
    assert result.answer == "Project Alpha has a budget of $100,000."
    assert result.lineage_trace is not None
    assert result.lineage_trace["query_id"] == str(query_id)


@pytest.mark.asyncio
async def test_execute_cross_source_query_partial_failure(
    orchestrator: CrossSourceOrchestrator,
    mock_catalog_context_injector: MagicMock,
) -> None:
    """One source fails — is_partial=True, failed_sources populated."""
    # Arrange
    mock_agent = MagicMock()
    mock_agent.invoke = AsyncMock(
        return_value=AgentResponse(
            answer="Based on available data, the budget is $100,000.",
            model="gpt-4",
            tool_results=[
                _make_successful_tool_result(),
                _make_failed_tool_result(),
            ],
            is_partial=True,
        )
    )

    project_id = uuid4()
    query_id = uuid4()

    # Act
    result = await orchestrator.execute_cross_source_query(
        question="Why is Project Alpha at risk?",
        project_id=project_id,
        strands_agent=mock_agent,
        query_id=query_id,
    )

    # Assert
    assert result.is_partial is True
    assert len(result.failed_sources) == 1
    assert result.failed_sources[0]["source"] == "Risk MongoDB"
    assert "timed out" in result.failed_sources[0]["error"]
    assert len(result.sources_consulted) == 1
    assert result.sources_consulted[0]["source_name"] == "Finance PostgreSQL"


@pytest.mark.asyncio
async def test_execute_cross_source_query_all_fail(
    orchestrator: CrossSourceOrchestrator,
    mock_catalog_context_injector: MagicMock,
) -> None:
    """All sources fail — is_partial=True, no evidence, no sources_consulted."""
    mock_agent = MagicMock()
    mock_agent.invoke = AsyncMock(
        return_value=AgentResponse(
            answer="I was unable to retrieve data from any source.",
            model="gpt-4",
            tool_results=[
                _make_failed_tool_result(source_label="Finance DB", error="connection refused"),
                _make_failed_tool_result(source_label="Risk DB", error="timeout"),
            ],
            is_partial=True,
        )
    )

    # Act
    result = await orchestrator.execute_cross_source_query(
        question="What is the project status?",
        project_id=uuid4(),
        strands_agent=mock_agent,
    )

    # Assert
    assert result.is_partial is True
    assert len(result.failed_sources) == 2
    assert result.sources_consulted == []
    assert result.evidence == []


@pytest.mark.asyncio
async def test_catalog_context_is_injected_into_agent(
    orchestrator: CrossSourceOrchestrator,
    mock_catalog_context_injector: MagicMock,
) -> None:
    """Catalog context is built and injected into the agent invocation."""
    mock_agent = MagicMock()
    mock_agent.invoke = AsyncMock(
        return_value=AgentResponse(
            answer="Answer.",
            model="gpt-4",
            tool_results=[],
            is_partial=False,
        )
    )

    project_id = uuid4()

    # Act
    await orchestrator.execute_cross_source_query(
        question="What are the risks?",
        project_id=project_id,
        strands_agent=mock_agent,
    )

    # Assert: catalog context injector was called with correct args
    mock_catalog_context_injector.build_relevant_context.assert_called_once_with(
        question="What are the risks?", project_id=project_id
    )
    mock_catalog_context_injector.format_for_system_prompt.assert_called_once()

    # Assert: agent was invoked with enriched question containing catalog context
    call_kwargs = mock_agent.invoke.call_args.kwargs
    assert "Available Enterprise Data Sources" in call_kwargs["question"]
    assert "What are the risks?" in call_kwargs["question"]


@pytest.mark.asyncio
async def test_lineage_records_all_steps(
    orchestrator: CrossSourceOrchestrator,
    mock_catalog_context_injector: MagicMock,
) -> None:
    """Lineage trace records catalog lookup, tool invocations, and synthesis."""
    mock_agent = MagicMock()
    mock_agent.invoke = AsyncMock(
        return_value=AgentResponse(
            answer="Project Alpha is at risk due to budget overrun.",
            model="gpt-4",
            tool_results=[
                _make_successful_tool_result(
                    source_name="Finance PostgreSQL",
                    object_name="project_finance",
                ),
                _make_failed_tool_result(
                    source_label="Risk MongoDB",
                    error="timeout",
                ),
            ],
            is_partial=True,
        )
    )

    # Act
    result = await orchestrator.execute_cross_source_query(
        question="Why is Project Alpha at risk?",
        project_id=uuid4(),
        strands_agent=mock_agent,
    )

    # Assert lineage structure
    trace = result.lineage_trace
    assert trace is not None
    assert "steps" in trace
    steps = trace["steps"]

    # Should have: catalog_lookup + 2 tool_invocations + synthesis = 4 steps
    assert len(steps) == 4

    # First step: catalog lookup
    assert steps[0]["step_type"] == "catalog_lookup"
    assert steps[0]["status"] == "success"

    # Second step: successful tool invocation
    assert steps[1]["step_type"] == "tool_invocation"
    assert steps[1]["status"] == "success"
    assert steps[1]["source_name"] == "Finance PostgreSQL"

    # Third step: failed tool invocation
    assert steps[2]["step_type"] == "tool_invocation"
    assert steps[2]["status"] == "failed"

    # Fourth step: synthesis
    assert steps[3]["step_type"] == "synthesis"
    assert steps[3]["status"] == "success"


@pytest.mark.asyncio
async def test_evidence_built_only_from_successful_results(
    orchestrator: CrossSourceOrchestrator,
    mock_catalog_context_injector: MagicMock,
) -> None:
    """Evidence is built only from successful tool results, never from failures."""
    mock_agent = MagicMock()
    mock_agent.invoke = AsyncMock(
        return_value=AgentResponse(
            answer="Budget is $100K.",
            model="gpt-4",
            tool_results=[
                _make_successful_tool_result(
                    source_name="Finance PostgreSQL",
                    object_name="project_finance",
                    rows=[["proj-1", 100000, 85000]],
                ),
                _make_failed_tool_result(source_label="Risk MongoDB"),
            ],
            is_partial=True,
        )
    )

    # Act
    result = await orchestrator.execute_cross_source_query(
        question="What is the budget?",
        project_id=uuid4(),
        strands_agent=mock_agent,
    )

    # Assert: evidence items exist from successful result
    assert len(result.evidence) >= 1
    # Evidence should reference Finance PostgreSQL, not Risk MongoDB
    for item in result.evidence:
        assert item.get("source_name") != "Risk MongoDB"


@pytest.mark.asyncio
async def test_no_hard_coded_routing(
    orchestrator: CrossSourceOrchestrator,
    mock_catalog_context_injector: MagicMock,
) -> None:
    """The orchestrator does NOT contain hard-coded routing logic.

    It delegates tool selection entirely to the Strands Agent via catalog context.
    This test verifies the orchestrator passes the question without modification
    to the agent (no keyword-based routing decisions).
    """
    mock_agent = MagicMock()
    mock_agent.invoke = AsyncMock(
        return_value=AgentResponse(
            answer="Some answer.",
            model="gpt-4",
            tool_results=[],
            is_partial=False,
        )
    )

    # Ask a cost-related question — the orchestrator should NOT route to PostgreSQL
    # based on keywords. It provides catalog context and lets the LLM decide.
    await orchestrator.execute_cross_source_query(
        question="What is the total project cost overrun?",
        project_id=uuid4(),
        strands_agent=mock_agent,
    )

    # Assert: agent was invoked — the orchestrator doesn't make routing decisions
    mock_agent.invoke.assert_called_once()
    # The question is passed to the agent (enriched with catalog context)
    call_kwargs = mock_agent.invoke.call_args.kwargs
    assert "total project cost overrun" in call_kwargs["question"]


@pytest.mark.asyncio
async def test_agent_exception_produces_partial_result(
    orchestrator: CrossSourceOrchestrator,
    mock_catalog_context_injector: MagicMock,
) -> None:
    """If the agent raises an exception, the orchestrator returns a valid partial result."""
    mock_agent = MagicMock()
    mock_agent.invoke = AsyncMock(side_effect=RuntimeError("LLM provider unavailable"))

    # Act
    result = await orchestrator.execute_cross_source_query(
        question="What are the risks?",
        project_id=uuid4(),
        strands_agent=mock_agent,
    )

    # Assert
    assert result.is_partial is True
    assert "error" in result.answer.lower() or "encountered" in result.answer.lower()
    assert result.evidence == []
    assert result.lineage_trace is not None


@pytest.mark.asyncio
async def test_query_id_generated_when_not_provided(
    orchestrator: CrossSourceOrchestrator,
    mock_catalog_context_injector: MagicMock,
) -> None:
    """A query_id is auto-generated if not provided."""
    mock_agent = MagicMock()
    mock_agent.invoke = AsyncMock(
        return_value=AgentResponse(
            answer="Answer.",
            model="gpt-4",
            tool_results=[],
            is_partial=False,
        )
    )

    # Act — no query_id passed
    result = await orchestrator.execute_cross_source_query(
        question="Test question",
        project_id=uuid4(),
        strands_agent=mock_agent,
    )

    # Assert: a valid UUID was generated
    assert result.query_id is not None
    assert isinstance(result.query_id, UUID)


class TestUserFriendlyError:
    """Test the error sanitization helper."""

    def test_timeout_error(self) -> None:
        assert _user_friendly_error("Connection timed out") == "Source query timed out"

    def test_connection_error(self) -> None:
        assert _user_friendly_error("Connection refused to host:5432") == "Unable to connect to data source"

    def test_permission_error(self) -> None:
        assert _user_friendly_error("Permission denied for user admin") == "Insufficient permissions to access data source"

    def test_not_found_error(self) -> None:
        assert _user_friendly_error("Source not found") == "Data source not found"

    def test_none_error(self) -> None:
        assert _user_friendly_error(None) == "Source unavailable"

    def test_long_error_truncated(self) -> None:
        long_error = "x" * 200
        result = _user_friendly_error(long_error)
        assert result == "Data source query failed"

    def test_short_generic_error(self) -> None:
        result = _user_friendly_error("Unknown error occurred")
        assert "Query failed" in result
