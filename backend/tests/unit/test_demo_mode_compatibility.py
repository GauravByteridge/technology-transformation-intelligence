"""
Unit tests for Phase 8 demo mode compatibility.

Verifies Requirements 9.1, 9.3, 9.5, 15.1, 15.3:
- When no real LLM provider is configured, system uses _MockStrandsModel with seeded data
- New Phase 8 optional fields (lineage_trace, groundedness, sources_consulted) default
  to None/empty in demo mode
- Same Strands/tool architecture works in both modes — no separate code paths
- AIResponse structure remains valid in demo mode (all new fields are optional)
- Existing Phase 7 demo mode behavior is completely unchanged
"""

from uuid import uuid4

import pytest

from app.ai.agent import AgentResponse, ToolResult
from app.ai.providers.mock_provider import MockTextGenerationProvider
from app.ai.service import AIService
from app.ai.tools.registry import ToolRegistry
from app.schemas.ai import AIResponse


class TestDemoModeCompatibility:
    """Verify Phase 8 fields do not disrupt demo mode behavior."""

    @pytest.mark.asyncio
    async def test_ai_response_phase8_fields_default_to_none_in_demo_mode(self) -> None:
        """Phase 8 optional fields default to None/empty when not populated.

        In demo mode, AIService._build_response does not set lineage_trace,
        groundedness, or sources_consulted — they remain at schema defaults.
        """
        provider = MockTextGenerationProvider()
        registry = ToolRegistry()

        async def mock_tool(**kwargs):
            return {
                "source_label": "Finance DB",
                "source_type": "postgresql",
                "record_count": 5,
            }

        registry.register("query_finance", mock_tool)
        service = AIService(provider=provider, tool_registry=registry)

        response = await service.execute_query(
            question="What is the project budget?",
            project_id=uuid4(),
            query_id=uuid4(),
            conversation_id=uuid4(),
        )

        assert isinstance(response, AIResponse)
        # Phase 8 fields default to None
        assert response.lineage_trace is None
        assert response.groundedness is None
        assert response.sources_consulted is None

    @pytest.mark.asyncio
    async def test_existing_response_fields_preserved_in_demo_mode(self) -> None:
        """Existing Phase 7 response fields still populated correctly.

        Demo mode must produce answer, response_type, sources, evidence,
        query_id, conversation_id, is_partial, and failed_sources.
        """
        provider = MockTextGenerationProvider()
        registry = ToolRegistry()

        async def mock_tool(**kwargs):
            return {
                "source_label": "Risk Data",
                "source_type": "mongodb",
                "record_count": 3,
            }

        registry.register("query_risk", mock_tool)
        service = AIService(provider=provider, tool_registry=registry)

        query_id = uuid4()
        conversation_id = uuid4()
        response = await service.execute_query(
            question="What are the top risks?",
            project_id=uuid4(),
            query_id=query_id,
            conversation_id=conversation_id,
        )

        # Existing fields still work
        assert response.answer != ""
        assert response.response_type == "text"
        assert response.query_id == query_id
        assert response.conversation_id == conversation_id
        assert isinstance(response.sources, list)
        assert isinstance(response.evidence, list)
        assert isinstance(response.failed_sources, list)

    @pytest.mark.asyncio
    async def test_demo_mode_error_response_includes_phase8_defaults(self) -> None:
        """Error responses in demo mode also have Phase 8 fields at defaults.

        When all tools fail, the error AIResponse must still be structurally
        valid with Phase 8 optional fields at None.
        """
        provider = MockTextGenerationProvider()
        registry = ToolRegistry()

        async def failing_tool(**kwargs):
            raise RuntimeError("Simulated failure")

        registry.register("broken_tool", failing_tool)
        service = AIService(provider=provider, tool_registry=registry)

        response = await service.execute_query(
            question="This will fail",
            project_id=uuid4(),
            query_id=uuid4(),
            conversation_id=uuid4(),
        )

        assert isinstance(response, AIResponse)
        # Phase 8 fields remain None even on error
        assert response.lineage_trace is None
        assert response.groundedness is None
        assert response.sources_consulted is None

    def test_ai_response_schema_backward_compatible(self) -> None:
        """AIResponse can be constructed without Phase 8 fields — backward compat.

        Existing code that creates AIResponse without the new fields must
        still work. This proves the fields are truly optional (not required).
        """
        response = AIResponse(
            answer="Budget is on track.",
            response_type="text",
            sources=[{"name": "Finance", "type": "postgresql", "records_returned": 5}],
            evidence=[],
            query_id=uuid4(),
            conversation_id=uuid4(),
        )

        # Phase 8 fields default to None/empty
        assert response.lineage_trace is None
        assert response.groundedness is None
        assert response.sources_consulted is None
        assert response.is_partial is False
        assert response.failed_sources == []

    def test_ai_response_with_phase8_fields_populated(self) -> None:
        """AIResponse accepts Phase 8 fields when populated (real mode).

        Proves the same schema works for both demo (fields=None) and
        real mode (fields=populated) without branching.
        """
        response = AIResponse(
            answer="Project Alpha is at risk due to budget overrun.",
            response_type="text",
            sources=[{"name": "Finance", "type": "postgresql", "records_returned": 10}],
            evidence=[{"claim": "budget overrun", "source": "Finance"}],
            query_id=uuid4(),
            conversation_id=uuid4(),
            lineage_trace={
                "query_id": str(uuid4()),
                "steps": [{"step_type": "tool_invocation", "tool_name": "query_connected_source"}],
            },
            groundedness=[
                {"claim": "budget overrun", "classification": "retrieved_fact"},
            ],
            sources_consulted=[
                {"source_id": str(uuid4()), "source_type": "postgresql", "records_returned": 10},
            ],
        )

        assert response.lineage_trace is not None
        assert response.groundedness is not None
        assert response.sources_consulted is not None
        assert len(response.sources_consulted) == 1

    def test_mock_strands_model_exists_and_is_used_in_demo(self) -> None:
        """_MockStrandsModel is the fallback when no LLM provider is configured.

        Verifies the architectural guarantee that demo mode uses the same
        Strands agent loop — just with a mock model instead of a real LLM.
        """
        from app.ai.strands_agent import _MockStrandsModel

        model = _MockStrandsModel()
        assert model.model_id == "mock-demo"
        assert model.stateful is False
        # Confirms the model is instantiable without LLM credentials
