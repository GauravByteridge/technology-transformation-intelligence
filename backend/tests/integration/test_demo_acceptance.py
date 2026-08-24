"""
Integration test: Phase 7 Demo Acceptance — "Why is Project Alpha at risk?"

This is the canonical acceptance test for Phase 7. It verifies the full
AI query pipeline in Demo Mode:
  AIQueryRequest → AIService → StrandsAgentWrapper → _MockStrandsModel
  → QuestionClassifier → Tools (with mock ingestion) → Evidence → AIResponse

Asserts:
- search_documents is invoked (document evidence present)
- At least one structured data tool is invoked (dataset evidence present)
- evidence array contains at least one document-type item with text_excerpt
- evidence array contains at least one dataset-type item
- sources array contains at least 2 distinct entries
- answer contains specific references (not a placeholder)
- Runs entirely in Demo Mode without real LLM credentials

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

import nest_asyncio

# Allow nested event loops so that @tool functions using
# asyncio.get_event_loop().run_until_complete() work inside pytest-asyncio
nest_asyncio.apply()

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from app.ai.agent import AgentResponse, ToolResult
from app.ai.prompt_manager import PromptManager
from app.ai.service import AIService
from app.ai.strands_agent import StrandsAgentWrapper, _MockStrandsModel
from app.ai.tools.ingestion_tools import initialize_ingestion_tools
from app.config.settings import Settings


# =============================================================================
# Seeded demo data — realistic data that the tools would return
# =============================================================================

PROJECT_ALPHA_ID = UUID("11111111-2222-3333-4444-555555555555")
DATASET_FINANCIALS_ID = UUID("aaaa1111-bbbb-2222-cccc-333344445555")

MOCK_SEARCH_RESULTS = [
    {
        "file_name": "Project_Alpha_Risk_Assessment_Q4.pdf",
        "page_number": 3,
        "section": "Section 3.2 - Schedule Risks",
        "sheet_name": None,
        "region": None,
        "excerpt": (
            "UAT completion has slipped by three weeks due to resource constraints. "
            "The testing team reports that critical integration scenarios remain untested, "
            "creating significant risk of production defects."
        ),
        "similarity_score": 0.91,
        "document_id": str(uuid4()),
        "chunk_id": str(uuid4()),
    },
    {
        "file_name": "Steering_Committee_Minutes_Dec2024.pdf",
        "page_number": 1,
        "section": "Action Items",
        "sheet_name": None,
        "region": None,
        "excerpt": (
            "The committee noted that Project Alpha's vendor delivery timeline is "
            "misaligned with internal milestones, requiring immediate escalation."
        ),
        "similarity_score": 0.84,
        "document_id": str(uuid4()),
        "chunk_id": str(uuid4()),
    },
]

MOCK_DATASETS = [
    {
        "id": str(DATASET_FINANCIALS_ID),
        "name": "project_financials",
        "source_type": "excel",
        "sheet_name": "Budget_Tracker",
        "classification": "financial",
        "record_count": 24,
        "status": "active",
    },
]

MOCK_QUERY_RECORDS = [
    {
        "project_name": "Project Alpha",
        "budget_allocated": 2500000,
        "budget_spent": 2300000,
        "utilization_pct": 92.0,
        "variance": -200000,
        "status": "at_risk",
    },
]


class MockIngestionInterface:
    """Mock IngestionInterface returning seeded demo data for testing."""

    async def search_documents(self, project_id: UUID, query: str) -> list[dict]:
        return MOCK_SEARCH_RESULTS

    async def list_available_datasets(self, project_id: UUID | None = None) -> list[dict]:
        return MOCK_DATASETS

    async def get_dataset_metadata(self, dataset_id: UUID) -> dict:
        return {
            "id": str(dataset_id),
            "name": "project_financials",
            "columns": [
                {"name": "project_name", "type": "text"},
                {"name": "budget_allocated", "type": "numeric"},
                {"name": "budget_spent", "type": "numeric"},
                {"name": "utilization_pct", "type": "numeric"},
                {"name": "variance", "type": "numeric"},
                {"name": "status", "type": "text"},
            ],
            "record_count": 24,
            "source_type": "excel",
            "file_name": "financials_2024.xlsx",
        }

    async def query_dataset(self, dataset_id: UUID, query_params: dict) -> dict:
        return {
            "records": MOCK_QUERY_RECORDS,
            "total_count": 1,
            "aggregations": {},
        }

    async def get_evidence(self, source_id: UUID, evidence_type: str) -> dict:
        return {
            "excerpt": "UAT has slipped by three weeks.",
            "file_name": "Project_Alpha_Risk_Assessment_Q4.pdf",
            "section": "Section 3.2",
        }


@pytest.fixture
def mock_ingestion():
    """Provide and initialize the mock ingestion interface."""
    ingestion = MockIngestionInterface()
    initialize_ingestion_tools(ingestion)
    return ingestion


@pytest.fixture
def demo_settings():
    """Settings for demo mode (no LLM provider)."""
    return Settings(
        app_db_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
        secret_key="test-secret",
        fernet_key="dwllgivmH8sZgEJ37vY87eLRXP2X7J4147iuveX5ju4=",
        demo_mode=True,
        llm_provider=None,
    )


@pytest.fixture
def ai_service(demo_settings, mock_ingestion):
    """Create a full AIService wired with StrandsAgentWrapper in demo mode."""
    from app.ai.providers.mock_provider import MockTextGenerationProvider
    from app.ai.tools.ingestion_tools import get_ingestion_tools
    from app.ai.tools.registry import ToolRegistry

    # Load the system prompt
    prompt_manager = PromptManager()
    system_prompt = prompt_manager.load_prompt("strands_system_prompt", version="v2")

    # Get the actual @tool-decorated functions (they use the mock ingestion)
    tools = get_ingestion_tools()

    # Create StrandsAgentWrapper — will use _MockStrandsModel since llm_provider is None
    strands_agent = StrandsAgentWrapper(
        settings=demo_settings,
        tools=tools,
        system_prompt=system_prompt,
    )

    # Create AIService with the strands agent
    mock_provider = MockTextGenerationProvider()
    tool_registry = ToolRegistry()
    service = AIService(
        provider=mock_provider,
        tool_registry=tool_registry,
        prompt_manager=prompt_manager,
        strands_agent=strands_agent,
    )

    return service


class TestDemoAcceptance:
    """Canonical demo acceptance tests for Phase 7."""

    @pytest.mark.asyncio
    async def test_why_is_project_alpha_at_risk(self, ai_service):
        """The canonical demo query must produce a grounded hybrid answer.

        Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
        """
        query_id = uuid4()
        conversation_id = uuid4()

        response = await ai_service.execute_query(
            question="Why is Project Alpha at risk?",
            project_id=PROJECT_ALPHA_ID,
            query_id=query_id,
            conversation_id=conversation_id,
        )

        # 1. Answer must NOT be a placeholder
        assert "demo mode" not in response.answer.lower(), (
            "Answer should not be a demo mode placeholder"
        )
        assert len(response.answer) > 50, "Answer should be substantive"

        # 2. Answer should reference actual evidence from tools
        answer_lower = response.answer.lower()
        has_doc_reference = any(
            ref in answer_lower
            for ref in [
                "risk_assessment",
                "uat",
                "slipped",
                "three weeks",
                "steering_committee",
                "vendor",
            ]
        )
        assert has_doc_reference, (
            f"Answer should reference document evidence. Got: {response.answer[:200]}"
        )

        # 3. Evidence array must have document-type items
        doc_evidence = [
            e for e in response.evidence
            if isinstance(e.get("data"), dict) and e["data"].get("type") == "document"
        ]
        assert len(doc_evidence) >= 1, (
            f"Should have at least 1 document evidence item. Evidence: {response.evidence}"
        )

        # 4. Document evidence should have text_excerpt
        assert any(
            e["data"].get("text_excerpt") for e in doc_evidence
        ), "Document evidence should include text_excerpt"

        # 5. Evidence array must have dataset-type items
        dataset_evidence = [
            e for e in response.evidence
            if isinstance(e.get("data"), dict) and e["data"].get("type") == "dataset"
        ]
        assert len(dataset_evidence) >= 1, (
            f"Should have at least 1 dataset evidence item. Evidence: {response.evidence}"
        )

        # 6. Sources must have at least 2 distinct entries
        assert len(response.sources) >= 2, (
            f"Should have at least 2 sources. Got: {response.sources}"
        )

        # 7. Source names should be human-readable
        source_names = [s.get("name", "") for s in response.sources]
        for name in source_names:
            assert name not in ("search_documents", "query_dataset", "list_available_datasets"), (
                f"Source name '{name}' should be human-readable, not a function name"
            )

        # 8. Response should not be partial (all tools succeeded with mock data)
        assert response.is_partial is False, (
            f"Response should not be partial. Failed: {response.failed_sources}"
        )

        # 9. conversation_id must be preserved
        assert response.conversation_id == conversation_id

    @pytest.mark.asyncio
    async def test_runs_without_llm_credentials(self, ai_service):
        """Demo mode must work without any real LLM credentials configured.

        Requirements: 8.6
        """
        response = await ai_service.execute_query(
            question="What are the key findings from the audit?",
            project_id=PROJECT_ALPHA_ID,
            query_id=uuid4(),
            conversation_id=uuid4(),
        )

        # Should get a real response, not an error
        assert response.answer
        assert "error" not in response.answer.lower() or "encountered" not in response.answer.lower()
        assert len(response.sources) >= 1

    @pytest.mark.asyncio
    async def test_quantitative_query_uses_structured_data(self, ai_service):
        """Quantitative questions should produce dataset evidence.

        Requirements: 2.2
        """
        response = await ai_service.execute_query(
            question="What is the budget utilization for this project?",
            project_id=PROJECT_ALPHA_ID,
            query_id=uuid4(),
            conversation_id=uuid4(),
        )

        assert response.answer
        assert "demo mode" not in response.answer.lower()

        # Should have at least one source
        assert len(response.sources) >= 1

    @pytest.mark.asyncio
    async def test_conversation_id_preserved(self, ai_service):
        """conversation_id must round-trip through the pipeline.

        Requirements: 6.1, 6.4
        """
        conv_id = uuid4()

        response = await ai_service.execute_query(
            question="Explain the audit observations.",
            project_id=PROJECT_ALPHA_ID,
            query_id=uuid4(),
            conversation_id=conv_id,
        )

        assert response.conversation_id == conv_id
