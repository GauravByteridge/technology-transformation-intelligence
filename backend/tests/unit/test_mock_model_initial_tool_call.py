"""
Unit tests for _MockStrandsModel initial tool_use event emission (Task 3.1).

Verifies:
- Qualitative questions emit search_documents tool_use
- Quantitative questions emit list_available_datasets tool_use
- Hybrid questions emit search_documents tool_use (first step)
- Project_id is correctly extracted and included in tool arguments
- StreamEvent sequence follows Strands protocol
- Search query is derived from user question
"""

import asyncio
import json

import pytest


@pytest.fixture
def mock_model():
    """Create a fresh _MockStrandsModel instance."""
    from app.ai.strands_agent import _MockStrandsModel

    return _MockStrandsModel()


def _build_messages(question: str, project_id: str) -> list:
    """Build a Strands-style messages list with contextualized prompt."""
    prompt = f"Project context \u2014 Project ID: {project_id}\n\nUser question: {question}"
    return [{"role": "user", "content": [{"text": prompt}]}]


async def _collect_events(model, messages):
    """Collect all stream events from model."""
    events = []
    async for event in model.stream(messages):
        events.append(event)
    return events


class TestInitialToolCallEmission:
    """Verify that initial calls (no tool_result) emit correct tool_use events."""

    @pytest.mark.asyncio
    async def test_qualitative_emits_search_documents(self, mock_model):
        """QUALITATIVE question should emit search_documents tool_use."""
        messages = _build_messages(
            "Why is Project Alpha at risk?",
            "12345678-1234-1234-1234-123456789abc",
        )

        events = await _collect_events(mock_model, messages)

        # Should have 5 events: messageStart, contentBlockStart, contentBlockDelta, contentBlockStop, messageStop
        assert len(events) == 5

        # Check contentBlockStart contains search_documents
        content_start = events[1]
        assert "contentBlockStart" in content_start
        tool_use = content_start["contentBlockStart"]["start"]["toolUse"]
        assert tool_use["name"] == "search_documents"
        assert len(tool_use["toolUseId"]) == 8

    @pytest.mark.asyncio
    async def test_quantitative_emits_list_available_datasets(self, mock_model):
        """QUANTITATIVE question should emit list_available_datasets tool_use."""
        messages = _build_messages(
            "What is the total budget for this project?",
            "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        )

        events = await _collect_events(mock_model, messages)
        assert len(events) == 5

        content_start = events[1]
        tool_use = content_start["contentBlockStart"]["start"]["toolUse"]
        assert tool_use["name"] == "list_available_datasets"

    @pytest.mark.asyncio
    async def test_hybrid_emits_search_documents_first(self, mock_model):
        """HYBRID question should emit search_documents as the first tool."""
        messages = _build_messages(
            "What risks are related to budget overrun?",
            "11111111-2222-3333-4444-555555555555",
        )

        events = await _collect_events(mock_model, messages)
        assert len(events) == 5

        content_start = events[1]
        tool_use = content_start["contentBlockStart"]["start"]["toolUse"]
        assert tool_use["name"] == "search_documents"

    @pytest.mark.asyncio
    async def test_project_id_included_in_arguments(self, mock_model):
        """Project ID from contextualized prompt must appear in tool arguments."""
        project_id = "abcdefab-1234-5678-9012-abcdefabcdef"
        messages = _build_messages("Describe the audit findings", project_id)

        events = await _collect_events(mock_model, messages)

        # contentBlockDelta has the arguments JSON
        delta_event = events[2]
        args_json = delta_event["contentBlockDelta"]["delta"]["toolUse"]["input"]
        args = json.loads(args_json)
        assert args["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_search_query_derived_from_question(self, mock_model):
        """search_documents args should contain a derived query from the user question."""
        messages = _build_messages(
            "Explain the key concerns from the latest audit",
            "12345678-1234-1234-1234-123456789abc",
        )

        events = await _collect_events(mock_model, messages)

        delta_event = events[2]
        args_json = delta_event["contentBlockDelta"]["delta"]["toolUse"]["input"]
        args = json.loads(args_json)
        assert "query" in args
        assert "Explain the key concerns from the latest audit" in args["query"]

    @pytest.mark.asyncio
    async def test_stop_reason_is_tool_use(self, mock_model):
        """messageStop event should have stopReason 'tool_use'."""
        messages = _build_messages(
            "What are the risk factors?",
            "12345678-1234-1234-1234-123456789abc",
        )

        events = await _collect_events(mock_model, messages)

        message_stop = events[4]
        assert message_stop["messageStop"]["stopReason"] == "tool_use"


class TestStreamEventProtocol:
    """Verify Strands streaming protocol structure."""

    @pytest.mark.asyncio
    async def test_event_sequence_order(self, mock_model):
        """Events must follow: messageStart, contentBlockStart, delta, stop, messageStop."""
        messages = _build_messages(
            "Why is this project delayed?",
            "12345678-1234-1234-1234-123456789abc",
        )

        events = await _collect_events(mock_model, messages)

        assert "messageStart" in events[0]
        assert "contentBlockStart" in events[1]
        assert "contentBlockDelta" in events[2]
        assert "contentBlockStop" in events[3]
        assert "messageStop" in events[4]

    @pytest.mark.asyncio
    async def test_message_start_role(self, mock_model):
        """messageStart should have role 'assistant'."""
        messages = _build_messages("What happened?", "12345678-1234-1234-1234-123456789abc")
        events = await _collect_events(mock_model, messages)

        assert events[0]["messageStart"]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_content_block_index_consistency(self, mock_model):
        """All content block events should reference index 0."""
        messages = _build_messages("Show me the report", "12345678-1234-1234-1234-123456789abc")
        events = await _collect_events(mock_model, messages)

        assert events[1]["contentBlockStart"]["contentBlockIndex"] == 0
        assert events[2]["contentBlockDelta"]["contentBlockIndex"] == 0
        assert events[3]["contentBlockStop"]["contentBlockIndex"] == 0


class TestProjectIdExtraction:
    """Verify project_id extraction from various prompt formats."""

    @pytest.mark.asyncio
    async def test_standard_format(self, mock_model):
        """Standard contextualized prompt format extracts UUID correctly."""
        project_id = "ffeeddcc-aabb-1122-3344-556677889900"
        messages = _build_messages("What is the status?", project_id)
        events = await _collect_events(mock_model, messages)

        delta_event = events[2]
        args = json.loads(delta_event["contentBlockDelta"]["delta"]["toolUse"]["input"])
        assert args["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_missing_project_id_returns_empty(self, mock_model):
        """If no UUID pattern found, project_id should be empty string."""
        messages = [{"role": "user", "content": [{"text": "Just a plain question"}]}]
        events = await _collect_events(mock_model, messages)

        delta_event = events[2]
        args = json.loads(delta_event["contentBlockDelta"]["delta"]["toolUse"]["input"])
        assert args["project_id"] == ""


class TestToolResultDetection:
    """Verify _has_tool_results correctly identifies continuation calls."""

    @pytest.mark.asyncio
    async def test_no_tool_results_emits_tool_use(self, mock_model):
        """Messages without tool results should trigger initial tool_use emission."""
        messages = _build_messages("Explain findings", "12345678-1234-1234-1234-123456789abc")
        events = await _collect_events(mock_model, messages)

        # Should get tool_use events (messageStop with stopReason=tool_use)
        assert events[4]["messageStop"]["stopReason"] == "tool_use"

    @pytest.mark.asyncio
    async def test_with_tool_results_emits_text(self, mock_model):
        """Messages with tool results should trigger continuation (text for now)."""
        messages = [
            {"role": "user", "content": [{"text": "Project context \u2014 Project ID: 12345678-1234-1234-1234-123456789abc\n\nUser question: What are the risks?"}]},
            {"role": "assistant", "content": [{"toolUse": {"toolUseId": "abc123", "name": "search_documents", "input": {}}}]},
            {"role": "user", "content": [{"toolResult": {"toolUseId": "abc123", "content": [{"text": "some results"}]}}]},
        ]
        events = await _collect_events(mock_model, messages)

        # Should emit text (end_turn) since it's a continuation call
        assert events[4]["messageStop"]["stopReason"] == "end_turn"
