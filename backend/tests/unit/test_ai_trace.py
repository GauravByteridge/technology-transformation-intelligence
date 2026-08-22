"""
Unit tests for the AI query trace module.

Verifies:
- QueryTrace dataclass captures complete execution trace
- Trace serialization produces expected dict structure
- Credential detection identifies sensitive patterns
- Sanitization redacts credentials from strings
- AIService stores trace after query execution
"""

from uuid import uuid4

import pytest

from app.ai.trace import (
    QueryTrace,
    ToolInvocationTrace,
    contains_sensitive_value,
    sanitize_log_value,
)


class TestToolInvocationTrace:
    """Tests for ToolInvocationTrace dataclass."""

    def test_defaults(self) -> None:
        trace = ToolInvocationTrace(tool_name="query_finance")
        assert trace.tool_name == "query_finance"
        assert trace.source_id is None
        assert trace.execution_status == "success"
        assert trace.duration_ms == 0
        assert trace.error is None
        assert trace.records_returned == 0

    def test_failed_invocation(self) -> None:
        trace = ToolInvocationTrace(
            tool_name="query_resources",
            execution_status="failed",
            error="Connection timeout",
            duration_ms=5000,
        )
        assert trace.execution_status == "failed"
        assert trace.error == "Connection timeout"


class TestQueryTrace:
    """Tests for QueryTrace dataclass."""

    def test_minimal_trace(self) -> None:
        query_id = uuid4()
        conversation_id = uuid4()
        project_id = uuid4()

        trace = QueryTrace(
            query_id=query_id,
            conversation_id=conversation_id,
            question="What is the budget?",
            project_id=project_id,
        )

        assert trace.query_id == query_id
        assert trace.tools_invoked == []
        assert trace.sources_queried == []
        assert trace.evidence_count == 0
        assert trace.is_partial is False
        assert trace.provider == "unknown"
        assert trace.model == "unknown"

    def test_full_trace(self) -> None:
        query_id = uuid4()
        conversation_id = uuid4()
        project_id = uuid4()

        trace = QueryTrace(
            query_id=query_id,
            conversation_id=conversation_id,
            question="Show project risk assessment",
            project_id=project_id,
            tools_invoked=[
                ToolInvocationTrace(
                    tool_name="query_finance",
                    source_id="finance-db-01",
                    execution_status="success",
                    duration_ms=120,
                    records_returned=5,
                ),
                ToolInvocationTrace(
                    tool_name="query_resources",
                    execution_status="failed",
                    error="Timeout",
                    duration_ms=5000,
                ),
            ],
            sources_queried=["Finance PostgreSQL"],
            evidence_count=3,
            failures=["Timeout"],
            is_partial=True,
            provider="MockTextGenerationProvider",
            model="gpt-4",
            duration_ms=5200,
        )

        assert len(trace.tools_invoked) == 2
        assert trace.is_partial is True
        assert trace.provider == "MockTextGenerationProvider"
        assert trace.duration_ms == 5200

    def test_to_dict_serialization(self) -> None:
        query_id = uuid4()
        conversation_id = uuid4()
        project_id = uuid4()

        trace = QueryTrace(
            query_id=query_id,
            conversation_id=conversation_id,
            question="Budget status?",
            project_id=project_id,
            tools_invoked=[
                ToolInvocationTrace(
                    tool_name="query_finance",
                    source_id="src-1",
                    execution_status="success",
                    duration_ms=100,
                    records_returned=3,
                ),
            ],
            sources_queried=["Finance DB"],
            evidence_count=2,
            is_partial=False,
            provider="AzureOpenAI",
            model="gpt-4o",
            duration_ms=450,
        )

        d = trace.to_dict()

        assert d["query_id"] == str(query_id)
        assert d["conversation_id"] == str(conversation_id)
        assert d["project_id"] == str(project_id)
        # NOTE: question text is not in dict — only length (privacy)
        assert d["question_length"] == len("Budget status?")
        assert "Budget status?" not in str(d)
        assert d["provider"] == "AzureOpenAI"
        assert d["model"] == "gpt-4o"
        assert d["duration_ms"] == 450
        assert len(d["tools_invoked"]) == 1
        assert d["tools_invoked"][0]["tool_name"] == "query_finance"
        assert d["tools_invoked"][0]["source_id"] == "src-1"
        assert d["tools_invoked"][0]["execution_status"] == "success"

    def test_to_dict_does_not_contain_credentials(self) -> None:
        """Trace dict representation never includes raw question text."""
        trace = QueryTrace(
            query_id=uuid4(),
            conversation_id=uuid4(),
            question="password=secret123 show me the data",
            project_id=uuid4(),
        )
        d = trace.to_dict()
        # Raw question is not serialized — only length
        assert "password" not in str(d)
        assert "secret123" not in str(d)


class TestContainsSensitiveValue:
    """Tests for credential detection in strings."""

    @pytest.mark.parametrize(
        "text",
        [
            "postgresql+asyncpg://user:pass123@host:5432/db",
            "mongodb+srv://admin:secret@cluster.mongodb.net",
            "api_key=sk-abc123xyz",
            "API_KEY = sk-abc123xyz",
            "password=mysecret",
            "token=eyJhbGciOiJI...",
            "connection_string=Server=myhost;Database=mydb;Uid=user;Pwd=pass;",
        ],
    )
    def test_detects_sensitive_values(self, text: str) -> None:
        assert contains_sensitive_value(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "query_id=550e8400-e29b-41d4-a716-446655440000",
            "tool_name=query_finance",
            "duration_ms=245",
            "The project budget is at risk",
            "source_label=Finance PostgreSQL",
        ],
    )
    def test_ignores_safe_values(self, text: str) -> None:
        assert contains_sensitive_value(text) is False


class TestSanitizeLogValue:
    """Tests for credential redaction."""

    def test_redacts_database_url(self) -> None:
        value = "Error connecting to postgresql+asyncpg://admin:s3cr3t@db.host:5432/mydb"
        result = sanitize_log_value(value)
        assert "s3cr3t" not in result
        assert "[REDACTED]" in result

    def test_redacts_api_key(self) -> None:
        value = "Provider failed: api_key=sk-proj-abc123 timeout"
        result = sanitize_log_value(value)
        assert "sk-proj-abc123" not in result
        assert "[REDACTED]" in result

    def test_preserves_safe_values(self) -> None:
        value = "Tool query_finance completed in 245ms"
        result = sanitize_log_value(value)
        assert result == value

    def test_redacts_mongodb_url(self) -> None:
        value = "mongodb+srv://user:password123@cluster0.abc.mongodb.net"
        result = sanitize_log_value(value)
        assert "password123" not in result
        assert "[REDACTED]" in result


class TestAIServiceTraceRecording:
    """Tests that AIService records traces after query execution."""

    @pytest.mark.asyncio
    async def test_service_stores_trace_after_successful_query(self) -> None:
        from app.ai.providers.mock_provider import MockTextGenerationProvider
        from app.ai.service import AIService
        from app.ai.tools.registry import ToolRegistry

        provider = MockTextGenerationProvider()
        registry = ToolRegistry()

        async def mock_tool(**kwargs):
            return {
                "source_label": "Finance DB",
                "source_type": "postgresql",
                "source_id": "fin-db-01",
                "record_count": 5,
            }

        registry.register("query_finance", mock_tool)

        service = AIService(provider=provider, tool_registry=registry)
        query_id = uuid4()
        conversation_id = uuid4()
        project_id = uuid4()

        await service.execute_query(
            question="What is the budget?",
            project_id=project_id,
            query_id=query_id,
            conversation_id=conversation_id,
        )

        trace = service.last_trace
        assert trace is not None
        assert trace.query_id == query_id
        assert trace.conversation_id == conversation_id
        assert trace.project_id == project_id
        assert trace.question == "What is the budget?"
        assert len(trace.tools_invoked) == 1
        assert trace.tools_invoked[0].tool_name == "query_finance"
        assert trace.tools_invoked[0].execution_status == "success"
        assert trace.tools_invoked[0].source_id == "fin-db-01"
        assert trace.sources_queried == ["Finance DB"]
        assert trace.is_partial is False
        assert trace.duration_ms >= 0
        assert trace.provider == "MockTextGenerationProvider"

    @pytest.mark.asyncio
    async def test_service_trace_captures_partial_failures(self) -> None:
        from app.ai.providers.mock_provider import MockTextGenerationProvider
        from app.ai.service import AIService
        from app.ai.tools.registry import ToolRegistry

        provider = MockTextGenerationProvider()
        registry = ToolRegistry()

        async def good_tool(**kwargs):
            return {"source_label": "Finance", "source_type": "postgresql", "record_count": 2}

        async def bad_tool(**kwargs):
            raise TimeoutError("Connection timed out")

        registry.register("finance", good_tool)
        registry.register("resources", bad_tool)

        service = AIService(provider=provider, tool_registry=registry)

        await service.execute_query(
            question="Overview?",
            project_id=uuid4(),
            query_id=uuid4(),
            conversation_id=uuid4(),
        )

        trace = service.last_trace
        assert trace is not None
        assert trace.is_partial is True
        assert len(trace.failures) == 1
        assert "Connection timed out" in trace.failures[0]
        assert trace.sources_queried == ["Finance"]

    @pytest.mark.asyncio
    async def test_service_trace_does_not_contain_credentials(self) -> None:
        """Even if a tool error contains a connection string, the trace sanitizes it."""
        from app.ai.providers.mock_provider import MockTextGenerationProvider
        from app.ai.service import AIService
        from app.ai.tools.registry import ToolRegistry

        provider = MockTextGenerationProvider()
        registry = ToolRegistry()

        async def leaky_tool(**kwargs):
            raise RuntimeError(
                "Failed connecting to postgresql+asyncpg://admin:s3cr3t@db:5432/prod"
            )

        registry.register("leaky", leaky_tool)

        service = AIService(provider=provider, tool_registry=registry)

        await service.execute_query(
            question="Test?",
            project_id=uuid4(),
            query_id=uuid4(),
            conversation_id=uuid4(),
        )

        trace = service.last_trace
        assert trace is not None
        for failure in trace.failures:
            assert "s3cr3t" not in failure
            assert "[REDACTED]" in failure
