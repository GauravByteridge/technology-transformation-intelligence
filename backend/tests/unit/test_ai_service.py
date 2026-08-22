"""
Unit tests for AI Service, Agent, and Tool Registry.

Verifies:
- ToolRegistry registration, lookup, and listing
- AIAgent tool invocation and answer synthesis
- AIService orchestration and response building
- Security invariant: agent never receives credentials
"""

from uuid import uuid4

import pytest

from app.ai.agent import AIAgent, AgentResponse, ToolResult
from app.ai.providers.mock_provider import MockTextGenerationProvider
from app.ai.service import AIService
from app.ai.tools.registry import ToolRegistry
from app.schemas.ai import AIResponse


# =============================================================================
# Tool Registry Tests
# =============================================================================


class TestToolRegistry:
    """Tests for the ToolRegistry."""

    def test_register_and_get_tool(self) -> None:
        registry = ToolRegistry()

        async def mock_tool(**kwargs):
            return {"data": "test"}

        registry.register("get_project_context", mock_tool)
        retrieved = registry.get_tool("get_project_context")

        assert retrieved is mock_tool

    def test_list_tools_returns_sorted_names(self) -> None:
        registry = ToolRegistry()

        async def tool_a(**kwargs):
            return {}

        async def tool_b(**kwargs):
            return {}

        registry.register("query_finance", tool_a)
        registry.register("get_project_context", tool_b)

        result = registry.list_tools()
        assert result == ["get_project_context", "query_finance"]

    def test_get_tool_raises_key_error_for_unknown(self) -> None:
        registry = ToolRegistry()

        with pytest.raises(KeyError, match="not_registered"):
            registry.get_tool("not_registered")

    def test_register_rejects_empty_name(self) -> None:
        registry = ToolRegistry()

        async def tool(**kwargs):
            return {}

        with pytest.raises(ValueError, match="must not be empty"):
            registry.register("", tool)

    def test_register_rejects_non_callable(self) -> None:
        registry = ToolRegistry()

        with pytest.raises(ValueError, match="must be callable"):
            registry.register("bad_tool", "not a function")  # type: ignore[arg-type]

    def test_has_tool_returns_true_for_registered(self) -> None:
        registry = ToolRegistry()

        async def tool(**kwargs):
            return {}

        registry.register("my_tool", tool)
        assert registry.has_tool("my_tool") is True

    def test_has_tool_returns_false_for_unregistered(self) -> None:
        registry = ToolRegistry()
        assert registry.has_tool("missing") is False

    def test_len_returns_registered_count(self) -> None:
        registry = ToolRegistry()

        async def tool(**kwargs):
            return {}

        registry.register("a", tool)
        registry.register("b", tool)

        assert len(registry) == 2


# =============================================================================
# AI Agent Tests
# =============================================================================


class TestAIAgent:
    """Tests for the AIAgent."""

    @pytest.mark.asyncio
    async def test_invoke_with_no_tools_returns_insufficient_data_message(self) -> None:
        provider = MockTextGenerationProvider()
        registry = ToolRegistry()

        agent = AIAgent(provider=provider, tool_registry=registry)
        response = await agent.invoke(
            question="What is project status?",
            project_id=uuid4(),
            query_id=uuid4(),
        )

        assert isinstance(response, AgentResponse)
        assert "unable to retrieve" in response.answer.lower()
        assert response.is_partial is False  # No tools = nothing to fail

    @pytest.mark.asyncio
    async def test_invoke_calls_registered_tools(self) -> None:
        provider = MockTextGenerationProvider()
        registry = ToolRegistry()
        call_log: list[str] = []

        async def mock_tool(project_id, **kwargs):
            call_log.append(str(project_id))
            return {"source_label": "Test Source", "data": "result"}

        registry.register("test_tool", mock_tool)

        agent = AIAgent(provider=provider, tool_registry=registry)
        project_id = uuid4()
        response = await agent.invoke(
            question="Test question",
            project_id=project_id,
            query_id=uuid4(),
        )

        assert len(call_log) == 1
        assert call_log[0] == str(project_id)
        assert response.tool_results[0].success is True

    @pytest.mark.asyncio
    async def test_invoke_handles_tool_failure_gracefully(self) -> None:
        provider = MockTextGenerationProvider()
        registry = ToolRegistry()

        async def failing_tool(**kwargs):
            raise RuntimeError("Connection refused")

        registry.register("failing_tool", failing_tool)

        agent = AIAgent(provider=provider, tool_registry=registry)
        response = await agent.invoke(
            question="Test",
            project_id=uuid4(),
            query_id=uuid4(),
        )

        assert response.is_partial is True
        assert response.tool_results[0].success is False
        assert "Connection refused" in (response.tool_results[0].error or "")

    @pytest.mark.asyncio
    async def test_invoke_partial_when_some_tools_fail(self) -> None:
        provider = MockTextGenerationProvider()
        registry = ToolRegistry()

        async def good_tool(**kwargs):
            return {"source_label": "Good Source", "value": 42}

        async def bad_tool(**kwargs):
            raise ValueError("Unavailable")

        registry.register("good_tool", good_tool)
        registry.register("bad_tool", bad_tool)

        agent = AIAgent(provider=provider, tool_registry=registry)
        response = await agent.invoke(
            question="Test",
            project_id=uuid4(),
            query_id=uuid4(),
        )

        assert response.is_partial is True
        successful = [r for r in response.tool_results if r.success]
        failed = [r for r in response.tool_results if not r.success]
        assert len(successful) == 1
        assert len(failed) == 1

    @pytest.mark.asyncio
    async def test_invoke_with_specific_tools_only_calls_those(self) -> None:
        provider = MockTextGenerationProvider()
        registry = ToolRegistry()
        calls: list[str] = []

        async def tool_a(**kwargs):
            calls.append("a")
            return {"source_label": "A"}

        async def tool_b(**kwargs):
            calls.append("b")
            return {"source_label": "B"}

        registry.register("tool_a", tool_a)
        registry.register("tool_b", tool_b)

        agent = AIAgent(provider=provider, tool_registry=registry)
        await agent.invoke(
            question="Test",
            project_id=uuid4(),
            query_id=uuid4(),
            tools_to_invoke=["tool_a"],
        )

        assert calls == ["a"]


# =============================================================================
# AI Service Tests
# =============================================================================


class TestAIService:
    """Tests for the AIService orchestration."""

    @pytest.mark.asyncio
    async def test_execute_query_returns_ai_response(self) -> None:
        provider = MockTextGenerationProvider()
        registry = ToolRegistry()

        async def mock_tool(**kwargs):
            return {"source_label": "Finance DB", "source_type": "postgresql", "record_count": 5}

        registry.register("query_finance", mock_tool)

        service = AIService(provider=provider, tool_registry=registry)
        query_id = uuid4()
        conversation_id = uuid4()

        response = await service.execute_query(
            question="What is the budget status?",
            project_id=uuid4(),
            query_id=query_id,
            conversation_id=conversation_id,
        )

        assert isinstance(response, AIResponse)
        assert response.query_id == query_id
        assert response.conversation_id == conversation_id
        assert response.response_type == "text"

    @pytest.mark.asyncio
    async def test_execute_query_includes_sources(self) -> None:
        provider = MockTextGenerationProvider()
        registry = ToolRegistry()

        async def mock_tool(**kwargs):
            return {"source_label": "JIRA", "source_type": "postgresql", "record_count": 3}

        registry.register("query_jira", mock_tool)

        service = AIService(provider=provider, tool_registry=registry)
        response = await service.execute_query(
            question="Sprint status?",
            project_id=uuid4(),
            query_id=uuid4(),
            conversation_id=uuid4(),
        )

        assert len(response.sources) == 1
        assert response.sources[0]["name"] == "JIRA"

    @pytest.mark.asyncio
    async def test_execute_query_handles_all_tools_failing(self) -> None:
        provider = MockTextGenerationProvider()
        registry = ToolRegistry()

        async def failing_tool(**kwargs):
            raise RuntimeError("Network error")

        registry.register("broken_tool", failing_tool)

        service = AIService(provider=provider, tool_registry=registry)
        response = await service.execute_query(
            question="Test?",
            project_id=uuid4(),
            query_id=uuid4(),
            conversation_id=uuid4(),
        )

        assert response.is_partial is True
        assert len(response.failed_sources) > 0

    @pytest.mark.asyncio
    async def test_execute_query_preserves_partial_results(self) -> None:
        provider = MockTextGenerationProvider()
        registry = ToolRegistry()

        async def good_tool(**kwargs):
            return {"source_label": "Finance", "source_type": "postgresql", "record_count": 2}

        async def bad_tool(**kwargs):
            raise TimeoutError("Timed out")

        registry.register("finance", good_tool)
        registry.register("resources", bad_tool)

        service = AIService(provider=provider, tool_registry=registry)
        response = await service.execute_query(
            question="Overview?",
            project_id=uuid4(),
            query_id=uuid4(),
            conversation_id=uuid4(),
        )

        assert response.is_partial is True
        assert len(response.sources) == 1
        assert response.sources[0]["name"] == "Finance"
        assert len(response.failed_sources) == 1

    @pytest.mark.asyncio
    async def test_execute_query_does_not_expose_credentials(self) -> None:
        """Verify the service/agent chain never passes credentials to tools."""
        provider = MockTextGenerationProvider()
        registry = ToolRegistry()
        received_kwargs: list[dict] = []

        async def spy_tool(**kwargs):
            received_kwargs.append(kwargs)
            return {"source_label": "Spy", "source_type": "test"}

        registry.register("spy_tool", spy_tool)

        service = AIService(provider=provider, tool_registry=registry)
        await service.execute_query(
            question="Test",
            project_id=uuid4(),
            query_id=uuid4(),
            conversation_id=uuid4(),
        )

        # Tool should only receive project_id — no credentials
        assert len(received_kwargs) == 1
        kwargs = received_kwargs[0]
        assert "password" not in kwargs
        assert "connection_string" not in kwargs
        assert "api_key" not in kwargs
        assert "token" not in kwargs
        assert "project_id" in kwargs
